"""Snapshot only the newly authorized owner-A run; do not alter simulation."""
import collections
import datetime as dt
import json
from pathlib import Path
from launch_confirm import ROOT, OUTPUT


def main():
    launch = json.loads((ROOT / 'runtime/launch_record.json').read_text())
    proc = Path('/proc') / str(launch['pid'])
    process_state = None
    if proc.exists():
        stat = (proc / 'stat').read_text()
        process_state = stat[stat.rfind(')') + 2:].split()[0]
    episodes = []
    for folder in Path('/proc').iterdir():
        if not folder.name.isdigit():
            continue
        try:
            args = (folder / 'cmdline').read_bytes().split(b'\0')
            if any(b'episode_adapter.py' in arg for arg in args) and any(str(OUTPUT).encode() in arg for arg in args):
                args = [a.decode(errors='replace') for a in args if a]
                episodes.append({'pid': int(folder.name), 'arm': args[args.index('--arm') + 1],
                                 'scenario': args[args.index('--scenario') + 1]})
        except (OSError, ProcessLookupError):
            continue
    calls = collections.Counter()
    request_parameters = []
    partial_lines = 0
    for path in OUTPUT.rglob('llm_calls.jsonl'):
        for line in path.read_text().splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                partial_lines += 1
                continue
            calls[event['kind']] += 1
            if event['kind'] == 'request':
                request_parameters.append({key: event.get(key) for key in ['enable_thinking', 'temperature', 'model']})
    snapshot = {'time': dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
                'pid': launch['pid'], 'controller_state': process_state,
                'status': json.loads((OUTPUT / 'status.json').read_text()),
                'official_total': 60, 'canonical_completed': len(list((OUTPUT / 'confirmation').rglob('completion.json'))),
                'active_episodes': episodes, 'llm_events': dict(calls),
                'llm_frozen_request_parameters_verified': bool(request_parameters) and all(
                    p == {'enable_thinking': False, 'temperature': 0, 'model': 'Qwen3.8-27B'} for p in request_parameters),
                'partially_written_log_lines': partial_lines,
                'confirmation_log_tail': (ROOT / 'runtime/confirmation.log').read_text(errors='replace')[-2000:]}
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime('%Y%m%dT%H%M%S')
    with (ROOT / 'runtime' / ('startup_snapshot_' + stamp + '.json')).open('x') as stream:
        json.dump(snapshot, stream, indent=2)
    print(json.dumps(snapshot))


if __name__ == '__main__':
    main()
