"""Stop one recorded Huairou inference replica for a planned GPU reallocation.

Refuses to act when the recorded process already exited, when a client is still
connected, or when the process ignores SIGTERM.  Weights and caches are never
touched; the only writes are a receipt and the recorded state status.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time


def clients(port: int) -> list[str]:
    try:
        output = subprocess.run(['ss', '-tn'], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [line for line in output.splitlines() if f':{port}' in line]


def port_open(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(2)
        return probe.connect_ex(('127.0.0.1', port)) == 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--service', type=Path, default=Path('/mnt/<lab>/<user>-codex/services/qwen'))
    parser.add_argument('--replica', default='b')
    parser.add_argument('--reason', required=True)
    parser.add_argument('--allow-connected', action='store_true',
                        help='proceed even when a client socket is still open')
    parser.add_argument('--wait-seconds', type=int, default=30)
    args = parser.parse_args()
    state_path = args.service / f'replica-{args.replica}.json'
    state = json.loads(state_path.read_text(encoding='utf-8'))
    pid, port = int(state['pid']), int(state['port'])
    if not Path('/proc', str(pid)).exists():
        raise SystemExit(f'Recorded process {pid} is not running; inspect before retrying')
    connected = clients(port)
    print('clients:', connected or 'none', flush=True)
    if connected and not args.allow_connected:
        raise SystemExit('A client is still connected; stop the job first or pass --allow-connected')
    os.kill(pid, signal.SIGTERM)
    stopped_after = None
    for second in range(1, args.wait_seconds + 1):
        if not Path('/proc', str(pid)).exists():
            stopped_after = second
            break
        time.sleep(1)
    if stopped_after is None:
        raise SystemExit('Process ignored SIGTERM; not escalating automatically')
    still_open = port_open(port)
    receipt = {'action': f'stop_replica_{args.replica}', 'reason': args.reason,
               'replica': args.replica, 'pid': pid, 'port': port,
               'gpu_devices': state.get('gpu_devices'), 'model_dir': state.get('model_dir'),
               'stopped_after_seconds': stopped_after, 'port_still_open': still_open,
               'stopped_utc': datetime.now(timezone.utc).isoformat(),
               'weights_untouched': True,
               'restart': f'cd {args.service} && python start_qwen_service.py --replica {args.replica}'}
    out = args.service / f'shutdown-replica-{args.replica}-e6.json'
    out.write_text(json.dumps(receipt, indent=2) + chr(10), encoding='utf-8')
    state['status'] = 'stopped_for_planned_gpu_reallocation'
    state['stopped_utc'] = receipt['stopped_utc']
    state_path.write_text(json.dumps(state, indent=2) + chr(10), encoding='utf-8')
    print(json.dumps(receipt, indent=2), flush=True)


if __name__ == '__main__':
    main()
