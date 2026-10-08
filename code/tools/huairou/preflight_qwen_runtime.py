"""Exercise the actual runtime and JIT compiler without loading model weights."""
import json
import os
from datetime import datetime, timezone

import start_qwen_service as launch


def main():
    os.environ.update(launch.service_environment('0,1', 'a'))
    import torch
    import flashinfer
    import flashinfer.comm.fd_exchange

    checks = []
    for index in range(2):
        with torch.cuda.device(index):
            a = torch.ones((64, 64), device=f'cuda:{index}', dtype=torch.bfloat16)
            result = a @ a
            assert result[0, 0].item() == 64
            probabilities = torch.zeros((2, 32), device=f'cuda:{index}', dtype=torch.float32)
            probabilities[:, 0] = 1
            sampled = flashinfer.sampling.sampling_from_probs(probabilities)
            torch.cuda.synchronize(index)
            assert sampled.tolist() == [0, 0]
            checks.append({'gpu': index, 'name': torch.cuda.get_device_name(index),
                           'bf16_matmul_passed': True, 'flashinfer_sampling_passed': True})
    report = {'status': 'runtime_preflight_passed',
              'checked_utc': datetime.now(timezone.utc).isoformat(),
              'torch': torch.__version__, 'cuda_build': torch.version.cuda,
              'cuda_home': os.environ['CUDA_HOME'], 'gpus': checks,
              'model_weights_loaded': False, 'model_service_validated': False}
    (launch.SERVICE / 'flashinfer-preflight.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
