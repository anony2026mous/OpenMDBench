"""Streaming, validated JSONL visualization replay writer."""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import TextIO

from openmdbench.visualization.schema import ReplayMetadata, VisualizationFrame


class ReplayWriter:
    """Write one complete JSON object per line; metadata is always the first record.

    `flush_every=1` is the durability-oriented default. Larger values improve throughput while
    making only the most recent incomplete flush batch vulnerable to process interruption.
    """

    def __init__(
        self,
        path: str | Path,
        metadata: ReplayMetadata,
        *,
        flush_every: int = 1,
    ) -> None:
        if flush_every <= 0:
            raise ValueError("flush_every must be positive")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.flush_every = flush_every
        self._frames_since_flush = 0
        self._last_timestamp: int | None = None
        self._stream = self._open_exclusive(self.path)
        self._write_line(metadata.model_dump_json())
        self._stream.flush()

    @staticmethod
    def _open_exclusive(path: Path) -> TextIO:
        if path.suffix == ".gz":
            return gzip.open(path, mode="xt", encoding="utf-8", newline="\n")
        return path.open(mode="x", encoding="utf-8", newline="\n")

    def _write_line(self, encoded: str) -> None:
        self._stream.write(encoded + "\n")

    def write_frame(self, frame: VisualizationFrame) -> None:
        if self._stream.closed:
            raise RuntimeError("cannot write to a closed replay")
        if self._last_timestamp is not None and frame.timestamp <= self._last_timestamp:
            raise ValueError("replay frame timestamps must be strictly increasing")
        encoded = frame.model_dump_json()
        self._write_line(encoded)
        self._last_timestamp = frame.timestamp
        self._frames_since_flush += 1
        if self._frames_since_flush >= self.flush_every:
            self._stream.flush()
            self._frames_since_flush = 0

    def close(self) -> None:
        if not self._stream.closed:
            self._stream.flush()
            self._stream.close()

    def __enter__(self) -> ReplayWriter:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
