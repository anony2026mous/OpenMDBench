"""Install NVIDIA CUDA 12.9 compiler components in the project tools directory."""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

BASE = Path('/mnt/<lab>/<user>-codex/tools')
TARGET = BASE / 'cuda-12.9'
SOURCE = 'https://developer.download.nvidia.com/compute/cuda/redist/'
COMPONENTS = [
    ('cuda_nvcc', '12.9.86', '7a1a5b652e5ef85c82b721d10672fc9a2dbaab44e9bd3c65a69517bf53998c35'),
    ('cuda_cudart', '12.9.79', '1f6ad42d4f530b24bfa35894ccf6b7209d2354f59101fd62ec4a6192a184ce99'),
    ('cuda_cccl', '12.9.27', '8b1a5095669e94f2f9afd7715533314d418179e9452be61e2fde4c82a3e542aa'),
]


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise RuntimeError('This tool targets the verified Linux x86_64 server only')
    if TARGET.exists():
        receipt = TARGET / 'installation-receipt.json'
        if not receipt.exists() or json.loads(receipt.read_text())['components'] != [list(c) for c in COMPONENTS]:
            raise RuntimeError('Existing toolkit is not owned by this installation; refusing overwrite')
        subprocess.run([str(TARGET / 'bin/nvcc'), '--version'], check=True)
        return
    cache = BASE / 'cuda-redist-packages'
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cuda129-staging-', dir=BASE) as temporary:
        stage = Path(temporary) / 'toolkit'
        stage.mkdir()
        for name, version, expected in COMPONENTS:
            filename = f'{name}-linux-x86_64-{version}-archive.tar.xz'
            archive = cache / filename
            if not archive.exists():
                partial = archive.with_suffix('.partial')
                url = SOURCE + name + '/linux-x86_64/' + filename
                print('DOWNLOAD', name, version, flush=True)
                with urllib.request.urlopen(url, timeout=90) as response, partial.open('wb') as output:
                    shutil.copyfileobj(response, output, 4 * 1024 * 1024)
                if sha256(partial) != expected:
                    raise RuntimeError('Archive hash mismatch: ' + name)
                partial.replace(archive)
            if sha256(archive) != expected:
                raise RuntimeError('Cached archive hash mismatch: ' + name)
            unpacked = Path(temporary) / name
            unpacked.mkdir()
            with tarfile.open(archive) as bundle:
                bundle.extractall(unpacked, filter='data')
            children = list(unpacked.iterdir())
            if len(children) != 1 or not children[0].is_dir():
                raise RuntimeError('Unexpected archive layout')
            shutil.copytree(children[0], stage, symlinks=True, dirs_exist_ok=True)
            print('VERIFIED_COMPONENT', name, expected, flush=True)
        if (stage / 'lib').is_dir() and not (stage / 'lib64').exists():
            (stage / 'lib64').symlink_to('lib', target_is_directory=True)
        subprocess.run([str(stage / 'bin/nvcc'), '--version'], check=True)
        probe = Path(temporary) / 'compile_probe.cu'
        probe.write_text('extern "C" __global__ void increment(float* x) { x[threadIdx.x] += 1.0f; }')
        output = Path(temporary) / 'compile_probe.cubin'
        subprocess.run([str(stage / 'bin/nvcc'), '-arch=sm_86', '-cubin', str(probe),
                        '-o', str(output)], check=True, timeout=90)
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError('Compiler did not produce an sm_86 cubin')
        receipt = {'components': COMPONENTS, 'source_manifest': SOURCE + 'redistrib_12.9.1.json',
                   'sm86_compilation_passed': True, 'system_cuda_modified': False,
                   'driver_modified': False}
        (stage / 'installation-receipt.json').write_text(json.dumps(receipt, indent=2))
        stage.rename(TARGET)
    print('CUDA_TOOLCHAIN_READY', TARGET, flush=True)


if __name__ == '__main__':
    main()
