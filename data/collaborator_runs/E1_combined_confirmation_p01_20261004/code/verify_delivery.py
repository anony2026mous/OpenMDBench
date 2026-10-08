"""Verify all ZIP members against remote export inventory; optionally extract safely."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--extract', type=Path)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    if hashlib.sha256(args.archive.read_bytes()).hexdigest() != manifest['archive_sha256']:
        raise ValueError('Archive SHA256 mismatch')
    with zipfile.ZipFile(args.archive) as z:
        if set(z.namelist()) != set(manifest['files']) or len(z.namelist()) != len(manifest['files']):
            raise ValueError('Missing or duplicate ZIP members')
        if z.testzip() is not None:
            raise ValueError('ZIP CRC failed')
        for name, record in manifest['files'].items():
            p = PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:
                raise ValueError('Unsafe ZIP path')
            raw = z.read(name)
            if len(raw) != record['bytes'] or hashlib.sha256(raw).hexdigest() != record['sha256']:
                raise ValueError('Member mismatch: ' + name)
        if args.extract:
            args.extract.mkdir(parents=True, exist_ok=False)
            z.extractall(args.extract)
            for name, record in manifest['files'].items():
                if hashlib.sha256((args.extract / name).read_bytes()).hexdigest() != record['sha256']:
                    raise ValueError('Extracted file mismatch')
    result = {'owner': manifest['owner'], 'cases': manifest['cases'],
              'archive_sha256': manifest['archive_sha256'], 'members': len(manifest['files']),
              'all_member_sha256_and_crc_pass': True,
              'extracted_to': str(args.extract) if args.extract else None}
    with args.receipt.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
