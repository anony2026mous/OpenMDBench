"""Start one independent Huairou inference replica; never train or edit weights."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess

BASE = Path('/mnt/<lab>/<user>-codex')
MODELS = BASE / 'models'
MODEL = MODELS / 'Qwen3.8-27B-BF16'
EIGHT_B_MODEL = MODELS / 'Qwen3-8B-BF16'
SERVICE = BASE / 'services/qwen'
PYTHON = BASE / 'envs/qwen-vllm0271-py312/bin/python'
CUDA_HOME = BASE / 'tools/cuda-12.9'
CURAND_INCLUDE = PYTHON.parent.parent / 'lib/python3.12/site-packages/nvidia/curand/include'
REPLICAS = {'a': ('0,1', 8001), 'b': ('2,3', 8002), 'c': ('2,3', 8003)}
MODEL_DIRS = {'a': MODEL, 'b': MODEL, 'c': EIGHT_B_MODEL}
SERVED_NAMES = {'a': 'Qwen3.8-27B', 'b': 'Qwen3.8-27B', 'c': 'Qwen3-8B'}
# Measured layout matches the reference (1568-token blocks, FP8 KV, TP=2).
# A6000 auto-allocation gave 406 blocks; cap to the reference's 296 blocks.
REFERENCE_KV_BLOCKS = 296
# Replica c is the E6 second model.  Qwen3-8B has 36 layers, 8 KV heads and head_dim
# 128; a 16-token block therefore costs 16*36*8*128*2 bytes = 1,179,648 bytes, and the
# measured runtime reported the same 16-token grid (65,006 blocks from 35.71 GiB).
# Its cache budget is sized to roughly the 27B reference capacity instead of letting
# the allocator claim the whole card.  It never reuses the 27B reference block count,
# which belongs to a different KV layout.
EIGHT_B_LAYERS = 36
EIGHT_B_KV_HEADS = 8
EIGHT_B_HEAD_DIM = 128
EIGHT_B_TOKENS_PER_BLOCK = 16
EIGHT_B_BLOCK_BYTES = (EIGHT_B_TOKENS_PER_BLOCK * EIGHT_B_LAYERS * EIGHT_B_KV_HEADS *
                       EIGHT_B_HEAD_DIM * 2)
EIGHT_B_KV_BUDGET_BYTES = 16 * 1024 ** 3


def model_dir(replica: str) -> Path:
    return MODEL_DIRS[replica]


def served_name(replica: str) -> str:
    return SERVED_NAMES[replica]


def kv_blocks(replica: str) -> int:
    if replica != 'c':
        return REFERENCE_KV_BLOCKS
    return EIGHT_B_KV_BUDGET_BYTES // EIGHT_B_BLOCK_BYTES


def max_model_len(replica: str) -> int:
    """Serve each checkpoint at the context it actually declares.

    The 27B reference is validated at 131072.  The 8B checkpoint declares
    max_position_embeddings = 40960, and forcing a longer context through
    VLLM_ALLOW_LONG_MAX_MODEL_LEN is documented by the runtime as able to produce
    NaN positions with relative position encoding, so its own limit is kept.
    """
    return 131072 if replica != 'c' else 40960


def service_environment(devices: str, replica: str) -> dict[str, str]:
    return dict(os.environ, CUDA_VISIBLE_DEVICES=devices, HF_HUB_OFFLINE='1',
                OMP_NUM_THREADS='4', PYTHONUNBUFFERED='1',
                VIRTUAL_ENV=str(PYTHON.parent.parent),
                CUDA_HOME=str(CUDA_HOME),
                CPATH=os.pathsep.join(filter(None, [str(CURAND_INCLUDE), os.environ.get('CPATH', '')])),
                FLASHINFER_NVCC=str(CUDA_HOME / 'bin/nvcc'),
                FLASHINFER_WORKSPACE_BASE=str(SERVICE / 'flashinfer-workspace'),
                MAX_JOBS='4',
                PATH=os.pathsep.join([str(PYTHON.parent), str(CUDA_HOME / 'bin'),
                                      os.environ.get('PATH', '')]),
                VLLM_CACHE_ROOT=str(SERVICE / ('cache-' + replica)))


def command(port: int, replica: str) -> list[str]:
    return [
        str(PYTHON), '-u', '-m', 'vllm.entrypoints.openai.api_server',
        '--model', str(model_dir(replica)), '--served-model-name', served_name(replica),
        '--host', '127.0.0.1', '--port', str(port),
        '--dtype', 'bfloat16', '--tensor-parallel-size', '2',
        '--max-model-len', str(max_model_len(replica)), '--kv-cache-dtype', 'fp8',
        '--num-gpu-blocks-override', str(kv_blocks(replica)),
        '--gpu-memory-utilization', '0.92', '--no-enable-prefix-caching',
        '--no-calculate-kv-scales', '--mamba-cache-dtype', 'auto',
        '--mamba-ssm-cache-dtype', 'float32', '--mamba-cache-mode', 'none',
        '--default-chat-template-kwargs', '{"enable_thinking":false}',
    ]


def main() -> None:
    import fcntl
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replica', choices=REPLICAS, required=True)
    args = parser.parse_args()
    SERVICE.mkdir(parents=True, exist_ok=True)
    with (SERVICE / ('replica-' + args.replica + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = SERVICE / ('replica-' + args.replica + '.json')
        if state.exists():
            prior = json.loads(state.read_text())
            if Path('/proc', str(prior['pid'])).exists():
                raise RuntimeError('Recorded replica process still exists; inspect it before retrying')
        devices, port = REPLICAS[args.replica]
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))
        directory = model_dir(args.replica)
        receipt = json.loads((directory / 'download-complete.json').read_text())
        if receipt['status'] != 'all_files_sha256_verified':
            raise RuntimeError('Weights are not completely downloaded and verified')
        manifest_bytes = (directory / 'source-manifest.json').read_bytes()
        if hashlib.sha256(manifest_bytes).hexdigest() != receipt['manifest_sha256']:
            raise RuntimeError('Source manifest changed after download verification')
        manifest = json.loads(manifest_bytes)
        if manifest.get('repository') != receipt.get('repository'):
            raise RuntimeError('Manifest repository differs from the download receipt')
        for item in manifest['files']:
            path = directory / item['Path']
            if not path.is_file() or path.stat().st_size != int(item['Size']):
                raise RuntimeError('Model file is missing or changed: ' + item['Path'])
        version = importlib.metadata.version('vllm')
        if version != '0.27.1+cu129':
            raise RuntimeError('Unexpected vLLM build: ' + version)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        log = SERVICE / 'logs' / f'replica-{args.replica}-{stamp}.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        env = service_environment(devices, args.replica)
        ninja = shutil.which('ninja', path=env['PATH'])
        if not ninja:
            raise RuntimeError('ninja is not available in the service environment PATH')
        subprocess.run([ninja, '--version'], env=env, check=True,
                       capture_output=True, text=True, timeout=15)
        nvcc_version = subprocess.run([str(CUDA_HOME / 'bin/nvcc'), '--version'],
                                      env=env, check=True, capture_output=True,
                                      text=True, timeout=15).stdout
        if 'release 12.9' not in nvcc_version:
            raise RuntimeError('CUDA compiler must match the selected 12.9 runtime')
        if not (CURAND_INCLUDE / 'curand.h').is_file():
            raise RuntimeError('Matching cuRAND development headers are missing')
        argv = command(port, args.replica)
        with log.open('xb') as output:
            process = subprocess.Popen(argv, cwd=SERVICE, env=env,
                                       stdin=subprocess.DEVNULL, stdout=output,
                                       stderr=subprocess.STDOUT, start_new_session=True)
        record = {'replica': args.replica, 'pid': process.pid, 'port': port,
                  'gpu_devices': devices, 'log': str(log), 'command': argv,
                  'model_dir': str(directory), 'served_model_name': served_name(args.replica),
                  'repository': manifest.get('repository'),
                  'kv_blocks': kv_blocks(args.replica),
                  'max_model_len': max_model_len(args.replica),
                  'started_utc': stamp, 'status': 'starting_not_validated',
                  'model_manifest_sha256': receipt['manifest_sha256'],
                  'reference_host_hashes_compared': False}
        temporary = state.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, indent=2))
        temporary.replace(state)
        (SERVICE / f'replica-{args.replica}-{stamp}.json').write_text(json.dumps(record, indent=2))
        print(json.dumps({key: record[key] for key in
                          ('replica', 'pid', 'port', 'gpu_devices', 'log', 'status')},
                         indent=2), flush=True)


if __name__ == '__main__':
    main()
