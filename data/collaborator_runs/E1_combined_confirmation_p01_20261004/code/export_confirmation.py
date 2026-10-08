"""Read-only source audit and complete portable ZIP export for a finished E1 owner."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import zipfile


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    source = a.source.resolve()
    state = read(source / 'status.json')
    manifest = read(source / 'run_manifest.json')
    if state['state'] != 'confirmation-complete' or state['cases'] != 60:
        raise ValueError('Finished owner block required')
    expected = {(f'COUNT-IE-05-MULTI-AXIS-N{count:03d}', arm, seed)
                for count in manifest['assigned_counts'] for arm in ['rule', 'llm', 'llm-rl']
                for seed in range(4201, 4211)}
    actual = set()
    for path in (source / 'confirmation').rglob('completion.json'):
        c = read(path)
        key = tuple(c['config'][k] for k in ['scenario', 'arm', 'seed'])
        if key in actual or c['exit_code'] != 0 or sha(path.parent / 'report.json') != c['report_sha']:
            raise ValueError('Invalid/duplicate completion: ' + str(path))
        actual.add(key)
    if actual != expected:
        raise ValueError('Missing/unexpected owner cases')
    paths = sorted(p for p in source.rglob('*') if p.is_file())
    files = {p.relative_to(source).as_posix(): {'sha256': sha(p), 'bytes': p.stat().st_size} for p in paths}
    a.output.mkdir(parents=True, exist_ok=False)
    archive = a.output / ('E1_' + manifest['owner'] + '_confirmation_complete_v1.zip')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as z:
        for path in paths:
            z.write(path, path.relative_to(source).as_posix())
    with zipfile.ZipFile(archive) as z:
        if set(z.namelist()) != set(files) or z.testzip() is not None:
            raise ValueError('ZIP completeness/CRC failed')
        for name, record in files.items():
            if hashlib.sha256(z.read(name)).hexdigest() != record['sha256']:
                raise ValueError('Export hash mismatch: ' + name)
    # Check immutable source after the entire export, not just before it.
    if any(sha(source / name) != record['sha256'] for name, record in files.items()):
        raise ValueError('Source changed during export')
    result = {'schema': 'E1-confirmation-delivery@1',
              'time': dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
              'source': str(source), 'owner': manifest['owner'], 'cases': 60,
              'archive': str(archive), 'archive_sha256': sha(archive),
              'archive_bytes': archive.stat().st_size, 'files': files,
              'file_count': len(files), 'full_output_included': True,
              'source_unchanged_after_export': True, 'zip_crc_and_all_member_hashes_verified': True}
    save(a.output / 'EXPORT_VERIFICATION.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}))


if __name__ == '__main__':
    main()
