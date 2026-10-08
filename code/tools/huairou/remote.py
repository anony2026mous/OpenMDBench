"""Local-authoritative, snapshot-based SSH test loop; Python standard library only."""
import argparse
import collections
import datetime
import fnmatch
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).with_name('config.json')
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
SECRET = re.compile(rb'-----BEGIN [A-Z ]*PRIVATE KEY-----|(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{24,}|(?<![A-Za-z0-9])AKIA[A-Z0-9]{16}|eyJ[A-Za-z0-9_-]{12,}\.eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{16,}')

# Sent as code, not saved into the project or the remote user's shell profile.
DEPLOY = r'''
import hashlib, json, os, pathlib, sys, tarfile
base = pathlib.Path(sys.argv[1])
owner, release, previous_release = sys.argv[2:5]
if not base.is_absolute() or '..' in base.parts or base.resolve() != base:
    raise RuntimeError('Unsafe remote root or symlink in remote path')
marker = base / '.huairou-owner.json'
if base.exists():
    if not marker.is_file() or json.loads(marker.read_text()).get('workspace_id') != owner:
        raise RuntimeError('Existing destination is not owned by this sync tool; refusing to overwrite')
else:
    base.mkdir(parents=True, mode=0o700)
    marker.write_text(json.dumps({'workspace_id': owner}))
snapshots = base / 'snapshots'
snapshots.mkdir(exist_ok=True)
if snapshots.is_symlink():
    raise RuntimeError('Snapshots directory must not be a symlink')
dest = snapshots / release
dest.mkdir(mode=0o700)
seen = {}
with tarfile.open(fileobj=sys.stdin.buffer, mode='r|gz') as archive:
    for member in archive:
        p = pathlib.PurePosixPath(member.name)
        if p.is_absolute() or '..' in p.parts or not member.isfile() or member.name in seen:
            raise RuntimeError('Invalid archive member')
        target = dest.joinpath(*p.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256()
        with archive.extractfile(member) as source, target.open('xb') as out:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                h.update(chunk)
        os.chmod(str(target), 0o755 if member.mode & 0o111 else 0o644)
        seen[member.name] = h.hexdigest()
manifest = json.loads((dest / '.huairou-manifest.json').read_text())
expected = {item['path']: item['sha256'] for item in manifest['files']}
actual = {name: digest for name, digest in seen.items() if name != '.huairou-manifest.json'}
if set(actual) - set(expected):
    raise RuntimeError('Unexpected file in archive')
for name, digest in expected.items():
    p = pathlib.PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or not p.parts:
        raise RuntimeError('Unsafe manifest path')
    if name in actual:
        continue
    if not previous_release or pathlib.PurePosixPath(previous_release).name != previous_release:
        raise RuntimeError('A full upload is required; use --full')
    source = snapshots / previous_release / name
    if source.resolve() != source or not source.is_file():
        raise RuntimeError('Previous source missing or symlinked; use --full')
    target = dest / name
    target.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    with source.open('rb') as inp, target.open('xb') as out:
        while True:
            chunk = inp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            h.update(chunk)
    os.chmod(str(target), source.stat().st_mode & 0o777)
    actual[name] = h.hexdigest()
if actual != expected:
    raise RuntimeError('Source hash verification failed; not publishing current. Remote edits may exist; use --full to create a fresh snapshot.')
current = base / 'current'
if current.exists() and not current.is_symlink():
    raise RuntimeError('current is not a symlink; refusing to replace it')
temporary = base / ('.current-' + release)
temporary.symlink_to('snapshots/' + release)
os.replace(str(temporary), str(current))
print(json.dumps({'snapshot': str(dest), 'current': str(current), 'files': len(expected)}))
'''

PROBE = r'''
import importlib.util, json, platform, sys
info = {'host': platform.node(), 'python': platform.python_version(),
        'project_python_compatible': (3, 11) <= sys.version_info[:2] < (3, 13),
        'pytest_installed': importlib.util.find_spec('pytest') is not None}
try:
    import torch
    info.update(torch=torch.__version__, cuda_available=torch.cuda.is_available(), gpu_count=torch.cuda.device_count())
except ImportError:
    info['torch'] = None
print(json.dumps(info, indent=2))
print('INFRASTRUCTURE CHECK ONLY: project tests were not run.')
'''

VERSION_CHECK = "import sys; ok=(3,11)<=sys.version_info[:2]<(3,13); print('Project Python:',sys.version.split()[0]); print('Set remote_python to an isolated Python 3.11/3.12 environment before running project tests.' if not ok else 'Python version supported'); sys.exit(0 if ok else 86)"

def is_link(path):
    st = path.lstat()
    return path.is_symlink() or bool(getattr(st, 'st_file_attributes', 0) & 0x400)

def safe_relative(value):
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or ':' in value or '\\' in value:
        raise ValueError('Expected a relative POSIX path: ' + value)
    return path

def discover(root, config):
    files, skipped = {}, collections.Counter()
    excluded = {name.casefold() for name in config['exclude_dirs']}
    patterns = [pattern.casefold() for pattern in config['exclude_globs']]
    def denied(path):
        return any(fnmatch.fnmatchcase(path.name.casefold(), p) for p in patterns)
    def add(path, explicit=False):
        if is_link(path):
            skipped['symlinks_or_junctions'] += 1
        elif denied(path):
            skipped['excluded_names'] += 1
        elif path.suffix.lower() not in config['extensions'] and not (explicit and path.suffix.lower() in ('.npz', '.pt')):
            skipped['non_source_extensions'] += 1
        elif path.stat().st_size > config['max_file_mib'] * 1024**2:
            raise ValueError('Included source exceeds max_file_mib; review/exclude explicitly: ' + str(path.relative_to(root)))
        else:
            files[path.relative_to(root).as_posix()] = path
    for item in config['include']:
        safe_relative(item)
        path = root / item
        if not path.exists():
            raise ValueError('Configured include is missing: ' + item)
        if is_link(path):
            raise ValueError('Configured include is a symlink or junction: ' + item)
        if path.is_file():
            add(path)
            continue
        for directory, dirs, names in os.walk(path, followlinks=False):
            keep = []
            for name in dirs:
                child = Path(directory) / name
                if name.casefold() in excluded or denied(child) or is_link(child):
                    skipped['excluded_directories'] += 1
                else:
                    keep.append(name)
            dirs[:] = sorted(keep)
            for name in sorted(names):
                add(Path(directory) / name)
    for item in config.get('include_files', []):
        safe_relative(item)
        path = root / item
        if not path.is_file():
            raise ValueError('Configured explicit file is missing: ' + item)
        relative = path.relative_to(root)
        if any(is_link(root.joinpath(*relative.parts[:i])) for i in range(1, len(relative.parts) + 1)):
            raise ValueError('Configured explicit file traverses a symlink or junction: ' + item)
        if any(fnmatch.fnmatchcase(part.casefold(), p) for part in relative.parts for p in patterns):
            raise ValueError('Configured explicit file matches an excluded name: ' + item)
        if path.suffix.lower() not in config['extensions'] and path.suffix.lower() not in ('.npz', '.pt'):
            raise ValueError('Unsupported explicit file type: ' + item)
        add(path, explicit=True)
    return sorted(files.items()), dict(skipped)

def source_bytes(path):
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
        raise ValueError('File changed during packaging; save and retry: ' + str(path))
    if SECRET.search(data):
        raise ValueError('Potential credential detected; content withheld. Review/exclude: ' + str(path))
    return data

def package(files, archive_path, previous=None):
    previous_hashes = {item['path']: item['sha256'] for item in (previous or {}).get('files', [])}
    manifest = {'files': []}
    with tarfile.open(archive_path, 'w:gz') as archive:
        for relative, path in files:
            data = source_bytes(path)
            digest = hashlib.sha256(data).hexdigest()
            manifest['files'].append({'path': relative, 'size': len(data), 'sha256': digest})
            if previous_hashes.get(relative) == digest:
                continue
            entry = tarfile.TarInfo(relative)
            entry.size = len(data)
            entry.mode = 0o755 if path.suffix == '.sh' else 0o644
            archive.addfile(entry, io.BytesIO(data))
        data = json.dumps(manifest, ensure_ascii=True).encode('utf-8')
        entry = tarfile.TarInfo('.huairou-manifest.json')
        entry.size = len(data)
        archive.addfile(entry, io.BytesIO(data))
    return manifest

def ssh_args(config, command):
    windows_ssh = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/OpenSSH/ssh.exe'
    ssh = str(windows_ssh) if windows_ssh.is_file() else shutil.which('ssh')
    if not ssh:
        raise ValueError('OpenSSH client not found')
    host = config['host']
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', host):
        raise ValueError('Invalid SSH host alias')
    return [ssh, '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10', host, command]

def deploy(config, archive, release, previous_release=''):
    remote_root = PurePosixPath(config['remote_root'])
    if not remote_root.is_absolute() or '..' in remote_root.parts or len(remote_root.parts) < 4:
        raise ValueError('Use a dedicated absolute remote workspace directory')
    command = shlex.join(['python3', '-c', DEPLOY, str(remote_root), config['workspace_id'], release, previous_release])
    with archive.open('rb') as source:
        result = subprocess.run(ssh_args(config, command), stdin=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=NO_WINDOW)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', 'replace').strip() or 'SSH upload failed')
    return json.loads(result.stdout)

def run_logged(config, command, log_path):
    with log_path.open('wb') as log:
        process = subprocess.Popen(ssh_args(config, command), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
        try:
            for line in iter(process.stdout.readline, b''):
                log.write(line)
                log.flush()
                print(line.decode('utf-8', 'replace'), end='', flush=True)
            return process.wait()
        except KeyboardInterrupt:
            process.terminate()
            process.wait()
            raise

def command_for(config, snapshot, action, profile_name, pytest_args, custom_command):
    profile = config['profiles'][profile_name]
    for value in [profile['cwd'], *profile['pythonpath']]:
        safe_relative(value)
    python = config['remote_python']
    prefix = ['set -eu', 'cd ' + shlex.quote(str(PurePosixPath(snapshot) / profile['cwd']))]
    prefix += ['export MPLBACKEND=Agg', 'export PYTHONUNBUFFERED=1', 'export MPLCONFIGDIR=' + shlex.quote(snapshot + '/.runtime/matplotlib')]
    if profile['pythonpath']:
        prefix += ['export PYTHONPATH=' + shlex.quote(':'.join(str(PurePosixPath(snapshot) / p) for p in profile['pythonpath']))]
    if profile.get('engine_root'):
        safe_relative(profile['engine_root'])
        prefix += ['export OPENMDBENCH_ROOT=' + shlex.quote(str(PurePosixPath(snapshot) / profile['engine_root']))]
    if action == 'smoke':
        prefix += [shlex.join([python, '-c', PROBE])]
    elif action == 'test':
        args = pytest_args[1:] if pytest_args[:1] == ['--'] else pytest_args
        prefix += [shlex.join([python, '-c', VERSION_CHECK]), shlex.join([python, '-m', 'pytest', *(args or ['--collect-only', '-q'])])]
    else:
        if not custom_command:
            raise ValueError('run requires --command; no command was executed')
        prefix += [custom_command]
    return '\n'.join(prefix)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('preview', 'sync', 'smoke', 'test', 'run'):
        item = sub.add_parser(action)
        if action != 'preview':
            item.add_argument('--full', action='store_true', help='Upload all sources without reusing a previous snapshot')
        if action in ('smoke', 'test', 'run'):
            item.add_argument('--profile', default='engine' if action == 'test' else 'workspace')
        if action == 'test':
            item.add_argument('pytest_args', nargs=argparse.REMAINDER)
        if action == 'run':
            item.add_argument('--command', required=True)
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    if args.action in ('smoke', 'test', 'run') and args.profile not in config['profiles']:
        raise ValueError('Unknown profile: ' + args.profile)
    files, skipped = discover(ROOT, config)
    if not files:
        raise ValueError('No source files selected')
    total = sum(path.stat().st_size for _, path in files)
    print(json.dumps({'included_files': len(files), 'source_mib': round(total / 1024**2, 2), 'excluded_counts': skipped, 'remote_root': config['remote_root']}, indent=2), flush=True)
    if args.action == 'preview':
        for _, path in files:
            source_bytes(path)
        print('PREVIEW ONLY: no files uploaded. Credential heuristic passed (not a complete secret audit).')
        print('Included roots: ' + ', '.join(config['include']))
        return 0
    state = ROOT / '.huairou'
    logs = state / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    last_path = state / 'last-sync.json'
    previous = None
    identity = {key: config[key] for key in ('host', 'remote_root', 'workspace_id')}
    if not args.full and last_path.exists():
        candidate = json.loads(last_path.read_text(encoding='utf-8'))
        if candidate.get('identity') == identity:
            previous = candidate
    release = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    with tempfile.TemporaryDirectory(prefix='pack-', dir=state) as temporary:
        archive = Path(temporary) / 'source.tar.gz'
        manifest = package(files, archive, previous['manifest'] if previous else None)
        with tarfile.open(archive) as bundle:
            changed = len(bundle.getnames()) - 1
        print('Changed files: %d; reused files: %d' % (changed, len(files) - changed), flush=True)
        print('Archive MiB: %.2f' % (archive.stat().st_size / 1024**2), flush=True)
        deployed = deploy(config, archive, release, previous['release'] if previous else '')
    next_state = {'identity': identity, 'manifest': manifest, 'release': release}
    temporary_state = state / ('last-sync-' + release + '.tmp')
    temporary_state.write_text(json.dumps(next_state), encoding='utf-8')
    os.replace(temporary_state, last_path)
    print(json.dumps(deployed, indent=2), flush=True)
    metadata = {'release': release, 'action': args.action, **deployed, 'manifest': manifest}
    receipt = logs / (release + '.json')
    receipt.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    if args.action == 'sync':
        print('SYNC COMPLETE: tests were not run.')
        return 0
    command = command_for(config, deployed['snapshot'], args.action, args.profile, getattr(args, 'pytest_args', []), getattr(args, 'command', None))
    log_path = logs / (release + '.log')
    print('LOCAL LOG: ' + str(log_path), flush=True)
    code = run_logged(config, command, log_path)
    metadata.update(exit_code=code, profile=args.profile, log=str(log_path))
    receipt.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print('REMOTE EXIT CODE: ' + str(code), flush=True)
    return code

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('Interrupted locally; confirm remote process status before retrying.', file=sys.stderr)
        sys.exit(130)
