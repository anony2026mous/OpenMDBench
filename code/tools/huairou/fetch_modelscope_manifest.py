"""Fetch and pin a ModelScope repository file manifest; never download weights.

The output keeps the same schema as ``models/Qwen3.8-27B-BF16/source-manifest.json``
so ``download_qwen_weights.py`` can verify every file byte-for-byte:

    {"repository": ..., "source": ..., "verification": ..., "files": [
        {"Path": ..., "Size": ..., "Sha256": ..., "Revision": ..., "IsLFS": bool}, ...]}

Revision is resolved once from the requested revision name and written into every
file entry, so a later ``master`` move cannot silently change what is downloaded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.parse
import urllib.request

API = 'https://modelscope.cn/api/v1/models/{repository}/repo/files'


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def fetch(repository: str, revision: str) -> dict:
    url = (API.format(repository=repository) + '?' +
           urllib.parse.urlencode({'Revision': revision, 'Recursive': 'true'}))
    request = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode('utf-8'))


def entries(payload: dict) -> list[dict]:
    data = payload.get('Data')
    if not isinstance(data, dict):
        raise ValueError('Unexpected ModelScope response: no Data object')
    files = data.get('Files')
    if not isinstance(files, list) or not files:
        raise ValueError('Unexpected ModelScope response: no Files list')
    rows = []
    for item in files:
        path = item.get('Path')
        size = item.get('Size')
        digest = item.get('Sha256')
        if not isinstance(path, str) or not path:
            raise ValueError('Manifest entry without Path')
        if not isinstance(size, int) or size < 0:
            raise ValueError('Manifest entry without a byte Size: ' + path)
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('Manifest entry without a full SHA256: ' + path)
        rows.append({'Path': path, 'Size': size, 'Sha256': digest,
                     'Revision': item.get('Revision'), 'IsLFS': bool(item.get('IsLFS'))})
    if len({row['Path'] for row in rows}) != len(rows):
        raise ValueError('Duplicate paths in repository listing')
    return rows


def resolve_revision(rows: list[dict], requested: str) -> list[str]:
    """Pin every file to its own commit.

    ModelScope records the last commit that touched each file, so a repository-wide
    branch name is not a pin: the same URL can return different content tomorrow.
    Per-file revisions are therefore what gets frozen, and each must be a 40-hex
    commit or the entry is refused.
    """
    revisions = set()
    for row in rows:
        revision = row.get('Revision')
        if not isinstance(revision, str) or not re.fullmatch('[0-9a-f]{40}', revision):
            raise ValueError('File is not pinned to a 40-hex commit: ' + row['Path'])
        revisions.add(revision)
    print('REQUESTED_BRANCH', requested, 'DISTINCT_FILE_COMMITS', len(revisions), flush=True)
    return sorted(revisions)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--revision', default='master')
    parser.add_argument('--output', type=Path, required=True,
                        help='manifest path to write (existing file is never overwritten)')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repository):
        raise ValueError('Repository must be <owner>/<name>')
    if args.output.exists():
        raise FileExistsError('Manifest already exists; inspect it before replacing: ' + str(args.output))
    rows = entries(fetch(args.repository, args.revision))
    pinned = resolve_revision(rows, args.revision)
    manifest = {
        'repository': args.repository,
        'source': (API.format(repository=args.repository) + '?' +
                   urllib.parse.urlencode({'Revision': args.revision, 'Recursive': 'true'})),
        'branch': args.revision,
        'file_commits': pinned,
        'verification': ('File list, sizes and SHA256 taken from the ModelScope repository '
                         'listing; every file is pinned to the commit that last touched it '
                         '(' + str(len(pinned)) + ' distinct commits) so a later branch move '
                         'cannot change what is downloaded'),
        'files': rows,
    }
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + chr(10)
    temporary = args.output.with_suffix(args.output.suffix + '.tmp')
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text(text, encoding='utf-8')
    os.replace(temporary, args.output)
    total = sum(row['Size'] for row in rows)
    print(json.dumps({'repository': args.repository, 'branch': args.revision,
                      'file_commits': pinned, 'files': len(rows),
                      'total_bytes': total, 'manifest': str(args.output),
                      'manifest_sha256': sha256_text(text)}, indent=2), flush=True)


if __name__ == '__main__':
    main()
