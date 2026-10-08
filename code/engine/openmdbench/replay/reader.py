"""Streaming replay reader with disk-backed random-access indexes."""

from __future__ import annotations

import gzip
import struct
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO, cast

from pydantic import ValidationError

from openmdbench.visualization.schema import (
    REPLAY_RECORD_ADAPTER,
    ReplayMetadata,
    VisualizationFrame,
)

INDEX_ENTRY = struct.Struct(">qq")


class ReplayFormatError(ValueError):
    pass


class ReplayReader:
    def __init__(
        self,
        path: str | Path,
        *,
        expected_resolved_hash: str | None = None,
        expected_map_hash: str | None = None,
    ) -> None:
        self.path = Path(path)
        self.compressed = self.path.suffix == ".gz"
        self.metadata = self._read_metadata()
        if (
            expected_resolved_hash is not None
            and self.metadata.resolved_hash != expected_resolved_hash
        ):
            raise ReplayFormatError("replay resolved hash does not match")
        if expected_map_hash is not None:
            identity = self.metadata.map_identity or {}
            if expected_map_hash not in {
                identity.get("raw_sha256"),
                identity.get("xy_sha256"),
            }:
                raise ReplayFormatError("replay map hash does not match")
        self.index_path: Path | None = None
        if not self.compressed:
            self.index_path = Path(f"{self.path}.idx")
            self._build_index()

    def _open(self) -> TextIO:
        if self.compressed:
            return gzip.open(self.path, mode="rt", encoding="utf-8", newline="")
        return self.path.open(mode="r", encoding="utf-8", newline="")

    @staticmethod
    def _parse(line: str, line_number: int) -> ReplayMetadata | VisualizationFrame:
        try:
            return REPLAY_RECORD_ADAPTER.validate_json(line)
        except ValidationError as error:
            message = f"invalid replay record at line {line_number}: {error}"
            raise ReplayFormatError(message) from error

    def _read_metadata(self) -> ReplayMetadata:
        with self._open() as stream:
            first = stream.readline()
        if not first:
            raise ReplayFormatError("replay is empty; metadata record is required")
        record = self._parse(first, 1)
        if not isinstance(record, ReplayMetadata):
            raise ReplayFormatError("first replay record must be metadata")
        return record

    def _build_index(self) -> None:
        if self.index_path is None:
            raise RuntimeError("compressed replay cannot build a byte index")
        temporary = Path(f"{self.index_path}.tmp")
        last_timestamp: int | None = None
        try:
            with self.path.open("rb") as source, temporary.open("wb") as index:
                source.readline()
                line_number = 1
                while True:
                    offset = source.tell()
                    raw = source.readline()
                    if not raw:
                        break
                    line_number += 1
                    try:
                        line = raw.decode("utf-8")
                    except UnicodeDecodeError as error:
                        raise ReplayFormatError(
                            f"invalid UTF-8 replay record at line {line_number}"
                        ) from error
                    record = self._parse(line, line_number)
                    if not isinstance(record, VisualizationFrame):
                        raise ReplayFormatError(f"unexpected metadata at line {line_number}")
                    if last_timestamp is not None and record.timestamp <= last_timestamp:
                        raise ReplayFormatError(
                            f"timestamp regression at line {line_number}: {record.timestamp}"
                        )
                    index.write(INDEX_ENTRY.pack(record.timestamp, offset))
                    last_timestamp = record.timestamp
            temporary.replace(self.index_path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    def frames(self) -> Iterator[VisualizationFrame]:
        last_timestamp: int | None = None
        with self._open() as stream:
            stream.readline()
            for line_number, line in enumerate(stream, start=2):
                record = self._parse(line, line_number)
                if not isinstance(record, VisualizationFrame):
                    raise ReplayFormatError(f"unexpected metadata at line {line_number}")
                if last_timestamp is not None and record.timestamp <= last_timestamp:
                    raise ReplayFormatError(
                        f"timestamp regression at line {line_number}: {record.timestamp}"
                    )
                last_timestamp = record.timestamp
                yield record

    def seek(self, timestamp: int) -> VisualizationFrame:
        if timestamp < 0:
            raise ValueError("timestamp must be non-negative")
        if self.compressed:
            for frame in self.frames():
                if frame.timestamp == timestamp:
                    return frame
                if frame.timestamp > timestamp:
                    break
            raise KeyError(f"timestamp not found: {timestamp}")
        offset = self._lookup_offset(timestamp)
        with self.path.open("rb") as stream:
            stream.seek(offset)
            line = stream.readline().decode("utf-8")
        return cast(VisualizationFrame, self._parse(line, -1))

    def _lookup_offset(self, timestamp: int) -> int:
        if self.index_path is None:
            raise RuntimeError("compressed replay has no byte index")
        with self.index_path.open("rb") as index:
            count = self.index_path.stat().st_size // INDEX_ENTRY.size
            low, high = 0, count
            while low < high:
                middle = (low + high) // 2
                index.seek(middle * INDEX_ENTRY.size)
                current_timestamp, offset = INDEX_ENTRY.unpack(index.read(INDEX_ENTRY.size))
                if current_timestamp < timestamp:
                    low = middle + 1
                elif current_timestamp > timestamp:
                    high = middle
                else:
                    return int(offset)
        raise KeyError(f"timestamp not found: {timestamp}")
