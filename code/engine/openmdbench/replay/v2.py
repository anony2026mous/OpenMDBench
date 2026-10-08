"""Authoritative JSONL artifact writer and simulation-free schema-v2 replay reader."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from openmdbench.schemas.core_v2 import VisualizationFrameV2

HASH = r"^sha256:[0-9a-f]{64}$"


class ReplayHeaderV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: str = "replay@2.0"
    session_id: str = Field(min_length=1)
    resolved_hash: str = Field(pattern=HASH)
    catalog_hash: str = Field(pattern=HASH)
    model_registry_hash: str = Field(pattern=HASH)
    seed: int = Field(ge=0)


class ReplayRecordV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: str = "replay-record@2.0"
    tick: int = Field(ge=0)
    frame: VisualizationFrameV2
    world_checkpoint_hash: str | None = Field(default=None, pattern=HASH)
    authority_receipt_hash: str | None = Field(default=None, pattern=HASH)
    event_receipt_hashes: tuple[str, ...] = ()
    record_hash: str = Field(pattern=HASH)

    @model_validator(mode="after")
    def validate_authority_anchor(self) -> ReplayRecordV2:
        if self.world_checkpoint_hash is None and self.authority_receipt_hash is None:
            raise ValueError("replay record requires a checkpoint or authority receipt hash")
        return self

    @staticmethod
    def compute_hash(value: Mapping[str, Any]) -> str:
        payload = {key: item for key, item in value.items() if item is not None}
        payload.pop("record_hash", None)
        return (
            "sha256:"
            + hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            ).hexdigest()
        )


class ReplayWriterV2:
    """Collect replay records in memory and write them once at match end."""

    def __init__(self, path: Path, *, header: ReplayHeaderV2) -> None:
        self.path = path
        if path.exists():
            raise FileExistsError(path)
        self._header = header
        self._records: list[ReplayRecordV2] = []
        self._last_tick = -1
        self._closed = False

    def write(self, record: ReplayRecordV2) -> None:
        if self._closed:
            raise ValueError("cannot append to a closed replay writer")
        if record.tick <= self._last_tick or record.frame.tick != record.tick:
            raise ValueError("replay record tick is not canonical")
        if record.record_hash != ReplayRecordV2.compute_hash(record.model_dump(mode="json")):
            raise ValueError("replay record hash mismatch")
        self._records.append(record)
        self._last_tick = record.tick

    def close(self) -> None:
        if self._closed:
            return
        with self.path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(self._header.model_dump_json() + "\n")
            for record in self._records:
                stream.write(record.model_dump_json(exclude_none=True) + "\n")
        self._closed = True

    def __enter__(self) -> ReplayWriterV2:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


class ReplayReaderV2:
    """Read artifacts only; this module does not import Session, World, RNG, or dynamics."""

    def __init__(
        self,
        path: Path,
        *,
        expected_resolved_hash: str,
        expected_catalog_hash: str,
        expected_model_registry_hash: str,
    ) -> None:
        self.path = path
        with path.open(encoding="utf-8") as stream:
            line = stream.readline()
        self.header = ReplayHeaderV2.model_validate_json(line)
        if (
            self.header.resolved_hash != expected_resolved_hash
            or self.header.catalog_hash != expected_catalog_hash
            or self.header.model_registry_hash != expected_model_registry_hash
        ):
            raise ValueError("replay trust anchors differ from explicit expectations")

    def records(self) -> Iterator[ReplayRecordV2]:
        prior_tick = -1
        with self.path.open(encoding="utf-8") as stream:
            stream.readline()
            for line in stream:
                record = ReplayRecordV2.model_validate_json(line)
                if record.tick <= prior_tick or record.record_hash != ReplayRecordV2.compute_hash(
                    record.model_dump(mode="json")
                ):
                    raise ValueError("replay record sequence or hash is invalid")
                prior_tick = record.tick
                yield record

    def frame_index(self) -> Mapping[int, VisualizationFrameV2]:
        return MappingProxyType({record.tick: record.frame for record in self.records()})


__all__ = [
    "ReplayHeaderV2",
    "ReplayReaderV2",
    "ReplayRecordV2",
    "ReplayWriterV2",
]
