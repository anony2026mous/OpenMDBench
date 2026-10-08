# Ubuntu installation

OpenMDBench targets Ubuntu 22.04/24.04 on Python 3.11 or 3.12. The baseline import and
quality checks are CPU-only; CUDA is not required.

## System prerequisites

```bash
sudo apt-get update
sudo apt-get install -y git make python3.11 python3.11-venv
```

Ubuntu 22.04 users must first make Python 3.11 available from an approved package source or
their organization's Python distribution; the stock Python 3.10 is not supported. On Ubuntu
24.04, install `python3.12` and `python3.12-venv`, then pass `PYTHON=python3.12` to Make.
From the directory that contains `pyproject.toml`, create the development environment:

```bash
make setup PYTHON=python3.11
source .venv/bin/activate
python -c "import openmdbench; print(openmdbench.__version__)"
make lint
make typecheck
make test
```

`make setup` defaults to `python3.11` so it cannot silently create an unsupported Python 3.10
environment. Select Python 3.12 explicitly on Ubuntu 24.04:

```bash
make setup PYTHON=python3.12
```

`make setup` installs the `core` and `dev` dependency groups. Training, REST, and optional CUDA
dependencies are intentionally separate:

```bash
.venv/bin/python -m pip install -e ".[train]"
.venv/bin/python -m pip install -e ".[server]"
.venv/bin/python -m pip install -e ".[cuda]"
```

The `cuda` group records the optional acceleration capability separately. Installing it does
not make CUDA mandatory: the package entry point and baseline checks continue to run on CPU.

For a CPU-only training workstation, install PyTorch from its CPU wheel index before enabling
the training group. This prevents pip from selecting CUDA runtime wheels on Linux:

```bash
.venv/bin/python -m pip install "torch>=2.10,<3" --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -e ".[train]"
```

The original `env/`, `model/`, and `framework/` modules remain available during incremental
migration. They are not imported by the lightweight `openmdbench` package entry point.
