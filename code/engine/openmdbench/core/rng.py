"""Session-scoped deterministic random number entry point."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from typing import Any

import numpy as np
from numpy.random import Generator


class SessionRNG:
    """Own all random draws for one simulation session."""

    def __init__(self, seed: int) -> None:
        if seed < 0:
            raise ValueError("seed must be non-negative")
        self.seed = int(seed)
        self._streams: dict[str, Generator] = {}

    @property
    def generator(self) -> Generator:
        """Backward-compatible default stream."""
        return self.stream("default")

    def stream(self, name: str) -> Generator:
        """Return a stable named stream whose draws cannot perturb other streams."""
        if not name:
            raise ValueError("RNG stream name cannot be empty")
        if name not in self._streams:
            digest = hashlib.sha256(name.encode("utf-8")).digest()
            name_entropy = np.frombuffer(digest[:16], dtype=np.uint32).tolist()
            seed_sequence = np.random.SeedSequence([self.seed, *name_entropy])
            self._streams[name] = np.random.default_rng(seed_sequence)
        return self._streams[name]

    def reset(self, seed: int) -> None:
        """Restart this session's stream from an explicit seed."""
        if seed < 0:
            raise ValueError("seed must be non-negative")
        self.seed = int(seed)
        self._streams.clear()

    def snapshot(self) -> dict[str, Any]:
        """Serialize all materialized stream states for a checkpoint."""
        return {
            "seed": self.seed,
            "streams": {
                name: copy.deepcopy(generator.bit_generator.state)
                for name, generator in sorted(self._streams.items())
            },
        }

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any]) -> SessionRNG:
        """Restore named streams at the exact next draw."""
        rng = cls(int(snapshot["seed"]))
        stream_states = snapshot.get("streams", {})
        if not isinstance(stream_states, Mapping):
            raise ValueError("RNG snapshot streams must be a mapping")
        for name, state in stream_states.items():
            generator = rng.stream(str(name))
            generator.bit_generator.state = copy.deepcopy(state)
        return rng


def configuration_hash(config: Mapping[str, Any]) -> str:
    """Return a stable SHA-256 identifier for JSON-compatible session configuration."""
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
