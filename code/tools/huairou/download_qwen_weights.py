"""Download one shared Qwen weight directory on Linux; never launch a model."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download(item: dict, root: Path, repository: str) -> None:
    name = item['Path']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in ('.', '..'):
        raise ValueError('Unsafe model filename')
    sha, revision, size = item['Sha256'], item['Revision'], int(item['Size'])
    if not re.fullmatch('[0-9a-f]{64}', sha) or not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Missing pinned revision or SHA256')
    final = root / name
    part = root / (name + '.partial')
    if final.is_symlink() or part.is_symlink():
        raise ValueError('Refusing symlink output')
    if final.exists():
        if final.stat().st_size != size or digest(final) != sha:
            raise ValueError('Existing file differs from manifest: ' + name)
        print('VERIFIED_EXISTING', name, flush=True)
        return
    url = 'https://modelscope.cn/api/v1/models/' + repository + '/repo?' + urllib.parse.urlencode(
        {'Revision': revision, 'FilePath': name})
    for attempt in range(5):
        try:
            offset = part.stat().st_size if part.exists() else 0
            if offset > size:
                raise ValueError('Partial file exceeds expected size: ' + name)
            if offset < size:
                headers = {'Range': f'bytes={offset}-'} if offset else {}
                request = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(request, timeout=90) as response:
                    if response.status == 206:
                        if not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                            raise ValueError('Invalid Content-Range')
                    elif response.status == 200:
                        offset = 0  # Server ignored Range: restart, never append a full response.
                    else:
                        raise ValueError('Unexpected HTTP status')
                    last_report = offset
                    with part.open('ab' if offset else 'wb') as target:
                        while block := response.read(4 * 1024 * 1024):
                            if offset + len(block) > size:
                                raise ValueError('Download exceeds expected size')
                            target.write(block)
                            offset += len(block)
                            if offset - last_report >= 256 * 1024 * 1024:
                                print('PROGRESS', name, offset, '/', size, flush=True)
                                last_report = offset
            if part.stat().st_size != size:
                raise OSError('Incomplete response: ' + name)
            if digest(part) != sha:
                raise ValueError('SHA256 mismatch; preserving partial for inspection: ' + name)
            part.replace(final)
            print('VERIFIED', name, size, flush=True)
            return
        except (OSError, TimeoutError) as exc:
            print('RETRY', name, attempt + 1, type(exc).__name__, flush=True)
            if attempt == 4:
                raise
            time.sleep(min(2 ** (attempt + 1), 30))


def reviewed_repository(manifest: dict, allow_other: bool) -> str:
    """Refuse an unreviewed repository before any byte is requested."""
    repository = manifest.get('repository')
    if not isinstance(repository, str) or not repository:
        raise ValueError('Manifest does not name its repository')
    if repository != 'Qwen/Qwen3.8-27B' and not allow_other:
        raise ValueError('Unexpected model repository: ' + repository +
                         ' (pass --allow-other-repository after reviewing the manifest)')
    return repository


def main() -> None:
    import fcntl
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--allow-other-repository', action='store_true',
                        help='required to download any repository other than Qwen/Qwen3.8-27B')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    repository = reviewed_repository(manifest, args.allow_other_repository)
    files = manifest['files']
    if len({x['Path'] for x in files}) != len(files):
        raise ValueError('Duplicate manifest paths')
    root = args.destination.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.download.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock.seek(0); lock.truncate(); lock.write(str(os.getpid())); lock.flush()
        pinned = root / 'source-manifest.json'
        if pinned.exists() and json.loads(pinned.read_text(encoding='utf-8')) != manifest:
            raise ValueError('Destination is pinned to another manifest')
        pinned.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        print('START', repository, 'files', len(files),
              'bytes', sum(int(x['Size']) for x in files), flush=True)
        # Validate small configs first; only one shard is in transfer at a time.
        for item in sorted(files, key=lambda x: (x['Path'].endswith('.safetensors'), x['Path'])):
            download(item, root, repository)
        receipt = {'status': 'all_files_sha256_verified', 'repository': repository,
                   'files': len(files), 'manifest_sha256': digest(pinned),
                   'reference_host_hashes_compared': False}
        temporary = root / 'download-complete.json.tmp'
        temporary.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        temporary.replace(root / 'download-complete.json')
        print('DOWNLOAD_COMPLETE', root, flush=True)


if __name__ == '__main__':
    main()
