"""Detached sequencer. Does not signal or modify the existing E1 supervisor."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from e1_split import write, now

BASE = Path('/root/openmd/runs/e1-split-v13-20261003')
REPO = Path('/root/openmd/releases/gitlab-ccabad00154e/repo')
SOURCE = Path('/root/openmd/runs/p0-next-20261002/E1-count')
BATCH = Path('/root/openmd/runs/E1_partial-direction_split_p01_20261003')
CODE = Path('/root/openmd/runs/p0-next-20261002/code')


def main():
    write(BASE / 'runtime/launch_record.json', {'pid': os.getpid(), 'time': now(),
          'batch': str(BATCH), 'watch_pid': 168667, 'stop_after_export': True,
          'confirmation_auto_start': False, 'current_calibration_children_signalled': False})
    script = BASE / 'code/e1_split.py'
    common = ['--repo', str(REPO), '--code', str(CODE), '--source', str(SOURCE), '--batch', str(BATCH)]
    with (BASE / 'runtime/freeze.log').open('x') as log:
        subprocess.run([sys.executable, '-B', '-u', str(script), 'freeze', *common,
                        '--checklist', str(BASE / 'code/checklist_v13.md'),
                        '--model-dir', '/mnt/QTJC/chenyi-codex/models/Qwen3.8-27B-BF16'],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    with (BASE / 'runtime/supervisor.log').open('x') as log:
        subprocess.run([sys.executable, '-B', '-u', str(script), 'screen-export', *common,
                        '--watch-pid', '168667'], stdout=log, stderr=subprocess.STDOUT, check=True)


if __name__ == '__main__':
    main()
