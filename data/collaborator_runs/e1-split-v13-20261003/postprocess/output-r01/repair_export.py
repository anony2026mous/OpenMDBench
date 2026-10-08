"""Finish E1's interrupted export only; never launch/reinterpret simulations."""
import argparse
import ast
import datetime as dt
import hashlib
import importlib.metadata as md
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import zipfile


def sha_file(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def write(p, value):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    tmp.replace(p)


def now():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()


def packages(distributions=None):
    """Inventory installed distributions without pip, network, or installation."""
    rows = {}
    for d in md.distributions() if distributions is None else distributions:
        name = d.metadata.get('Name')
        if not name or not d.version:
            raise ValueError('Distribution name/version missing')
        key = name.lower().replace('_', '-').replace('.', '-')
        if key in rows and rows[key]['version'] != d.version:
            raise ValueError('Conflicting installed distribution versions: ' + name)
        rows[key] = {'name': name, 'version': d.version}
    if not rows:
        raise ValueError('Installed distribution inventory is empty')
    return [rows[k] for k in sorted(rows)]


def archived_readme(script):
    """Reuse the exact original README literal, without running its campaign."""
    tree = ast.parse(Path(script).read_text(encoding='utf-8'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'export_handoff')
    values = [n.value.value for n in ast.walk(fn) if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == 'text' for t in n.targets)
              and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)]
    if len(values) != 1:
        raise ValueError('Original README literal not uniquely found')
    return values[0]


def verify_zip(archive, inventory):
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        expected = set(inventory) | {'DELIVERY_MANIFEST.json'}
        if len(names) != len(set(names)) or set(names) != expected:
            raise ValueError('ZIP member inventory mismatch/duplicates')
        for name, expected_sha in inventory.items():
            h = hashlib.sha256()
            with z.open(name) as f:
                for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
                    h.update(block)
            if h.hexdigest() != expected_sha:
                raise ValueError('ZIP member hash mismatch: ' + name)
        if z.testzip() is not None:
            raise ValueError('ZIP CRC validation failed')
        manifest = json.loads(z.read('DELIVERY_MANIFEST.json'))
        if manifest['files'] != inventory:
            raise ValueError('Archived delivery manifest mismatch')


def expected_sources(repo, source, batch, code):
    files = {}
    def tree(src, dest, predicate=lambda f: True):
        for f in src.rglob('*'):
            if f.is_file() and '__pycache__' not in f.parts and f.suffix != '.pyc' and '.git' not in f.parts and predicate(f):
                files[(Path(dest) / f.relative_to(src)).as_posix()] = f
    for name in ['protocol', 'analysis', 'reports', 'code']:
        tree(batch / name, name)
    tree(code, 'frozen/code')
    tree(Path(read(source / 'variants.json')['engine']), 'frozen/engine')
    tree(repo / 'openmd/source-code/source_codes', 'frozen/repo/openmd/source-code/source_codes')
    tree(repo / 'openmd/code/eval', 'frozen/repo/openmd/code/eval', lambda f: f.suffix == '.py')
    for name in read(batch / 'protocol/split_execution.json')['weights']:
        rel = 'frozen/repo/openmd/code/eval/_w1_runs/rl/' + name
        files[rel] = repo / 'openmd/code/eval/_w1_runs/rl' / name
    cases = read(batch / 'analysis/calibration_cases.json')
    if len(cases) != 960:
        raise ValueError('960 calibration cases required')
    for c in cases:
        f = Path(c['source'])
        for name in ['report.json', 'completion.json']:
            rel = (Path('data/calibration') / f.relative_to(source) / name).as_posix()
            files[rel] = f / name
    tree(batch / 'gate-screening', 'data/gate-screening')
    tree(batch / 'attempts', 'data/gate-attempts')
    for rec in ['r01', 'r02']:
        tree(source / 'recovery' / rec, 'data/calibration-engineering-audit/' + rec,
             lambda f: f.suffix == '.json' or f.name == 'scheduler_events.jsonl')
    for name in ['status.json', 'protocol.json', 'variants.json']:
        files['data/original-campaign/' + name] = source / name
    return files


def main():
    p = argparse.ArgumentParser()
    for name in ['repo', 'source', 'batch', 'code']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    repo, source, batch, code = [getattr(a, n).resolve() for n in ['repo', 'source', 'batch', 'code']]
    recovery = batch / 'recovery/output-r01'
    recovery.mkdir(parents=True, exist_ok=False)
    import fcntl
    lock = (batch / 'supervisor.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    before = read(batch / 'status.json')
    if before['state'] != 'review-required' or 'pip' not in before.get('error', ''):
        raise ValueError('Unexpected recovery state; do not overwrite')
    shutil.copy2(batch / 'status.json', recovery / 'previous_status.json')
    target = batch / 'handoff-r01'
    archive = batch / 'E1_v13_handoff_r01.zip'
    if archive.exists() or (target / 'DELIVERY_MANIFEST.json').exists():
        raise ValueError('Completed/interrupted archive already exists; retain for review')
    frozen = read(batch / 'protocol/split_execution.json')
    if sha_file(target / 'code/e1_split.py') != frozen['toolkit_sha256']:
        raise ValueError('Frozen toolkit changed')
    expected = expected_sources(repo, source, batch, code)
    existing = {f.relative_to(target).as_posix() for f in target.rglob('*') if f.is_file()}
    if set(expected) != existing:
        raise ValueError('Partial export incomplete/unexpected: ' + str({'missing': sorted(set(expected) - existing), 'extra': sorted(existing - set(expected))}))
    input_hashes = {name: sha_file(f) for name, f in expected.items()}
    for name, h in input_hashes.items():
        if sha_file(target / name) != h:
            raise ValueError('Partial exported copy differs: ' + name)
    write(recovery / 'input_hashes.json', input_hashes)
    for phase, root, required in [('calibration', target / 'data/calibration', 960), ('gates', target / 'data/gate-screening', 200)]:
        completions = list(root.rglob('completion.json'))
        if len(completions) != required:
            raise ValueError('Wrong completion count: ' + phase)
        for f in completions:
            c = read(f)
            if c['exit_code'] != 0 or sha_file(f.parent / 'report.json') != c['report_sha']:
                raise ValueError('Invalid exported completion: ' + str(f))
    if len(read(batch / 'analysis/gates.json')) != 4:
        raise ValueError('Incomplete gate summary')
    rows = packages()
    write(target / 'runtime.json', {'python': sys.version, 'platform': platform.platform(),
          'collection_method': 'Python standard library importlib.metadata.distributions; pip absent',
          'installed_distributions': rows, 'distribution_count': len(rows),
          'requirements_snapshot_scope': 'Installed names/versions, not pip-freeze editable/direct-URL provenance or a platform-independent solver lockfile',
          'new_episodes': 0, 'LLM_calls': 0})
    (target / 'requirements-environment.txt').write_text(''.join(r['name'] + '==' + r['version'] + '\n' for r in rows), encoding='utf-8')
    text = archived_readme(target / 'code/e1_split.py')
    text += '\n## 导出恢复说明\n\n原导出在pip freeze处停止，仿真与门禁结果已完整。现仅改用Python标准库采集已安装包名/版本，未安装pip、未改变环境、未改冻结程序或门禁，未新增对局。requirements-environment.txt为原服务器环境快照，含平台相关软件，并非跨平台锁文件；模型服务的独立vLLM环境不等于本引擎环境。\n'
    (target / 'README.md').write_text(text, encoding='utf-8')
    write(target / 'EXPORT_RECOVERY.json', {'time': now(), 'reason': before['error'],
          'repair_code_sha256': sha_file(__file__), 'source_partial_files_verified': len(expected),
          'input_hashes_sha256': sha_file(recovery / 'input_hashes.json'), 'frozen_inputs_unchanged': True,
          'new_episodes': 0, 'LLM_calls': 0, 'confirmation_auto_start': False})
    # Recheck all original files: no experiment result/source mutated during repair.
    for name, f in expected.items():
        if sha_file(f) != input_hashes[name] or sha_file(target / name) != input_hashes[name]:
            raise ValueError('Input changed during export recovery: ' + name)
    all_files = {f.relative_to(target).as_posix(): sha_file(f) for f in sorted(target.rglob('*')) if f.is_file()}
    write(target / 'DELIVERY_MANIFEST.json', {'created_at': now(), 'files': all_files,
          'counts': {'calibration_cases': 960, 'gate_cases': 200, 'confirmation_cases': 0},
          'source_original': str(source), 'source_followup': str(batch), 'export_recovery': str(recovery)})
    write(batch / 'status.json', {'state': 'exporting-handoff', 'time': now(), 'confirmation_auto_start': False})
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as z:
        for f in sorted(target.rglob('*')):
            if f.is_file():
                z.write(f, f.relative_to(target).as_posix())
    verify_zip(archive, all_files)
    verification = {'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': sha_file(archive),
          'source_file_count': len(all_files), 'zip_member_count': len(all_files) + 1,
          'zip_crc_verified': True, 'all_zip_member_sha256_verified': True,
          'original_export_source_hashes_unchanged': True, 'verified_original_files': len(expected),
          'delivery_manifest_sha256': sha_file(target / 'DELIVERY_MANIFEST.json'),
          'installed_distribution_count': len(rows), 'new_episodes': 0, 'new_LLM_calls': 0}
    write(batch / 'handoff_verification.json', verification)
    write(recovery / 'verification.json', verification)
    write(batch / 'status.json', {'state': 'paused-after-calibration-and-gates', 'time': now(),
          'valid_calibration': 960, 'completed_gates': 200, 'completed_confirmation': 0,
          'confirmation_auto_start': False, 'handoff_archive': str(archive),
          'export_recovery': str(recovery), 'note': 'Export repaired and validated; no confirmation started. Original failed status retained.'})
    print(json.dumps(verification, ensure_ascii=False), flush=True)
    lock.close()


if __name__ == '__main__':
    main()
