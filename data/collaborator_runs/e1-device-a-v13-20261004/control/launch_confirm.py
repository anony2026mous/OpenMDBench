"""Audited detached launch of the frozen E1 device-A confirmation only."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request


ROOT = Path('/root/openmd/runs/e1-device-a-v13-20261004')
FOLLOWUP = Path('/root/openmd/runs/E1_partial-direction_split_p01_20261003')
BUNDLE = FOLLOWUP / 'handoff-r01'
OUTPUT = Path('/root/openmd/runs/E1_confirm_device-a_p01_20261004')
EXPECTED_SPLIT = 'f28855e53f50202cac2444982aa93088aaec8a18754a919a4645d0a5e83cc189'
ENDPOINTS = ['http://127.0.0.1:8101/v1', 'http://127.0.0.1:8102/v1']


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    status = read(FOLLOWUP / 'status.json')
    if status['state'] != 'paused-after-calibration-and-gates':
        raise ValueError('Expected frozen predecessor pause')
    if status['valid_calibration'] != 960 or status['completed_gates'] != 200:
        raise ValueError('Incomplete calibration or gates')
    if OUTPUT.exists():
        raise ValueError('Output already exists; refuse accidental duplicate/resume')
    manifest_path = BUNDLE / 'protocol/split_execution.json'
    if digest(manifest_path) != EXPECTED_SPLIT:
        raise ValueError('Unexpected split protocol')
    manifest = read(manifest_path)
    receipt = read(BUNDLE / 'MODEL_VERIFIED.json')
    if receipt['manifest_sha256'] != EXPECTED_SPLIT or receipt['model_checkpoint'] != manifest['model_checkpoint']:
        raise ValueError('Verified actual model receipt required')
    if manifest['assignments']['device-a'] != [17, 18] or manifest['confirmation_seeds'] != list(range(4201, 4211)):
        raise ValueError('Wrong frozen assignment')
    models = []
    for endpoint in ENDPOINTS:
        with urllib.request.urlopen(endpoint + '/models', timeout=20) as response:
            data = json.load(response)
        if 'Qwen3.8-27B' not in [item['id'] for item in data['data']]:
            raise ValueError('Expected model unavailable')
        models.append(data)
    # Never alter or signal existing runs. Refuse any active owner-A duplicate.
    for folder in Path('/proc').iterdir():
        if not folder.name.isdigit() or int(folder.name) == os.getpid():
            continue
        try:
            argv = (folder / 'cmdline').read_bytes().split(b'\0')
            if b'device-a' in argv and any(b'e1_split.py' in arg for arg in argv):
                raise ValueError('Owner A already active: ' + folder.name)
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    runtime = ROOT / 'runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / 'tmp').mkdir(exist_ok=False)
    cmd = [sys.executable, '-B', '-u', str(BUNDLE / 'code/e1_split.py'),
           'confirm', '--bundle', str(BUNDLE), '--owner', 'device-a',
           '--output', str(OUTPUT), '--endpoint-0', ENDPOINTS[0], '--endpoint-1', ENDPOINTS[1]]
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               TI_CPU_MAX_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', MPLBACKEND='Agg',
               MPLCONFIGDIR=str(runtime / 'mpl'), TMPDIR=str(runtime / 'tmp'))
    with (runtime / 'confirmation.log').open('x') as log:
        proc = subprocess.Popen(cmd, env=env, stdin=subprocess.DEVNULL, stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True)
    record = {'time': dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
              'pid': proc.pid, 'command': cmd, 'owner': 'device-a',
              'condition_order': [17, 18], 'seeds': list(range(4201, 4211)), 'planned_cases': 60,
              'formal_output': str(OUTPUT), 'split_manifest_sha256': EXPECTED_SPLIT,
              'toolkit_sha256': digest(BUNDLE / 'code/e1_split.py'),
              'verification_receipt': receipt['time'], 'model_endpoints': models,
              'scheduler': {'cpu': 24, 'LLM_per_endpoint': 2},
              'scientific_parameters_changed': False,
              'predecessor_data_or_device_b_modified': False}
    with (runtime / 'launch_record.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    print(json.dumps(record, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
