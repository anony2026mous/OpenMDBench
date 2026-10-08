"""Frozen-input, seed-level statistics shared by P0 strengthening experiments."""
import hashlib
import json
from pathlib import Path
import numpy as np


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def estimate(values, seed=20261001, draws=20000):
    x = np.asarray(values, dtype=float)
    if not len(x) or not np.isfinite(x).all():
        raise ValueError("Statistics require finite, nonempty observations")
    rng = np.random.default_rng(seed)
    samples = x[rng.integers(0, len(x), size=(draws, len(x)))].mean(axis=1)
    return {"n_seeds": len(x), "mean": float(x.mean()),
            "ci95": np.quantile(samples, [.025, .975]).tolist(),
            "bootstrap_draws": draws}
