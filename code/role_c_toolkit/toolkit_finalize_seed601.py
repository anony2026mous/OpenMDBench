"""Finish the existing seed-601 episode, summarize, and never start another."""
import argparse
import ctypes
import os
import subprocess
import sys
from pathlib import Path

from toolkit_seed_first_resume import load, save
from p1_6_campaign import now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--child-pid', type=int, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    status_path = out / 'seed_first_20260929/status.json'
    status = load(status_path)
    ident = status['current']
    if ident != 'ie_04_combined_arms_pure-llm_s601_a1':
        raise RuntimeError('Unexpected current episode; inspect before finalizing')
    request = out / 'seed_first_20260929/stop_after_seed601.json'
    with request.open('x', encoding='utf-8') as stream:
        import json
        json.dump({'requested_utc': now(), 'finish_seed': 601,
                   'cancelled_seeds': [602, 603], 'episode_pid': args.child_pid,
                   'reason': 'User requested stop after this seed; no further episodes authorized.'}, stream, indent=2)
    status.update(phase='finishing_current_seed', scheduler_stopped=True,
                  finalizer_pid=os.getpid(), cancelled_seeds=[602, 603],
                  stop_reason='user_requested_stop_after_seed601', updated_utc=now())
    save(status_path, status)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.WaitForSingleObject.restype = ctypes.c_ulong
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x00100000, False, args.child_pid)
    if handle:
        try:
            while True:
                result = kernel.WaitForSingleObject(handle, 5000)
                if result == 0:
                    break
                if result != 258:
                    raise RuntimeError(f'Process wait failed: {result}')
                status['updated_utc'] = now()
                save(status_path, status)
        finally:
            kernel.CloseHandle(handle)
    elif load(out / (ident + '_manifest.json')).get('status') != 'complete':
        raise RuntimeError('Episode process missing without complete result')
    kit = Path(__file__).resolve().parent
    for name in ('p1_6_analyze.py', 'toolkit_four_arm_audit.py'):
        with (out / 'seed_first_20260929' / (name + '_finalize.log')).open('x', encoding='utf-8') as log:
            subprocess.run([sys.executable, str(kit / name), '--output-dir', str(out)],
                           cwd=kit, stdout=log, stderr=subprocess.STDOUT, check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
    report = load(out / 'four_arm_audit/summary.json')
    done = report['seed_progress']['601']['execution_complete']
    if not done:
        raise RuntimeError('Seed 601 has incomplete results; no automatic restart')
    for cell in report['cells']:
        if cell['status'] == 'execution_complete':
            if cell['run_id'] not in status['reused'] and cell['run_id'] not in status['newly_completed']:
                status['newly_completed'].append(cell['run_id'])
            arms = status['seed_progress'][str(cell['seed'])]['scenes'][cell['scenario']]
            if cell['arm'] not in arms:
                arms.append(cell['arm'])
    for seed, item in status['seed_progress'].items():
        item['completed'] = report['seed_progress'][seed]['execution_completed']
    status.update(phase='stopped_after_seed601', current=None, child_pid=None,
                  seed601_execution_complete=True, strict_audit_limitations=report['limitations'],
                  updated_utc=now(), finished_utc=now())
    save(status_path, status)
    print('Seed 601 finished. Seeds 602 and 603 not started. IE11 limitations retained.', flush=True)


if __name__ == '__main__':
    main()
