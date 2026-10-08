SHELL := /bin/bash
PYTHON ?= python3.11
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
PYTEST := PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 $(VENV_PYTHON) -m pytest

.PHONY: setup lint typecheck security-check test contract-test scenario-test determinism-test selftest md-ad-002-selftest benchmark benchmark-md-ad-002 full-test serve clean

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -e ".[core,dev]"

lint:
	$(VENV_PYTHON) -m ruff check openmdbench tests

typecheck:
	$(VENV_PYTHON) -m mypy

security-check:
	$(VENV_PYTHON) -m bandit -q -r openmdbench

test:
	$(PYTEST)

contract-test:
	$(PYTEST) tests/contract

scenario-test:
	$(PYTEST) tests/scenarios

determinism-test:
	$(PYTEST) tests/determinism

selftest: md-ad-002-selftest

md-ad-002-selftest:
	MPLCONFIGDIR=/tmp/openmdbench-matplotlib $(VENV_PYTHON) -m openmdbench.cli selftest --scenario MD-AD-002-EASY --seed 7
	MPLCONFIGDIR=/tmp/openmdbench-matplotlib $(VENV_PYTHON) -m openmdbench.cli selftest --scenario MD-AD-002-MEDIUM --seed 7
	MPLCONFIGDIR=/tmp/openmdbench-matplotlib $(VENV_PYTHON) -m openmdbench.cli selftest --scenario MD-AD-002-HARD --seed 7

benchmark:
	$(PYTEST) tests/performance

benchmark-md-ad-002:
	$(VENV_PYTHON) -c 'import json; from openmdbench.release_validation import benchmark_training_sessions, host_metadata; print(json.dumps({"host": host_metadata(), "concurrency": [benchmark_training_sessions(16), benchmark_training_sessions(32)]}, indent=2))'

full-test: lint typecheck security-check
	MPLCONFIGDIR=/tmp/openmdbench-matplotlib $(PYTEST) -p pytest_cov tests --cov=openmdbench --cov-fail-under=80 --cov-report=xml --cov-report=html
	$(VENV_PYTHON) -m openmdbench.full_test_report

serve:
	$(VENV_PYTHON) -m uvicorn openmdbench.api.app:app --host 0.0.0.0 --port 8000

clean:
	$(PYTEST) --cache-clear >/dev/null 2>&1 || true
