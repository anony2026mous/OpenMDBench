"""Self-contained hash-chained authority log for MD-AD-002."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, TextIO


class AD2AuthorityLog:
    """Append a hash-chained authority log with bounded output buffering.

    The in-memory simulation ledger remains authoritative while a match is
    running.  Batching compression-stream flushes avoids making every
    simulation tick wait for the file system; :meth:`close` always flushes the
    final partial batch before closing the completed replay artifact.
    """

    _DEFAULT_FLUSH_EVERY = 256

    def __init__(
        self,
        path: str | Path,
        metadata: dict[str, Any],
        *,
        flush_every: int = _DEFAULT_FLUSH_EVERY,
    ) -> None:
        if flush_every <= 0:
            raise ValueError("flush_every must be positive")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream: TextIO = (
            gzip.open(self.path, "xt", encoding="utf-8")  # noqa: SIM115
            if self.path.suffix == ".gz"
            else self.path.open("x", encoding="utf-8")
        )
        self._previous_hash = "sha256:" + "0" * 64
        self._sequence = 0
        self._flush_every = flush_every
        self._records_since_flush = 0
        self._pending_lines: list[str] = []
        self.append("metadata", {"schema_version": "1.0", **metadata})

    def append(self, record_type: str, payload: dict[str, Any]) -> None:
        body = {
            "sequence": self._sequence,
            "previous_hash": self._previous_hash,
            "record_type": record_type,
            "payload": payload,
        }
        canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        record_hash = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
        self._pending_lines.append(
            json.dumps({**body, "record_hash": record_hash}, ensure_ascii=False, sort_keys=True)
            + "\n"
        )
        self._previous_hash = record_hash
        self._sequence += 1
        self._records_since_flush += 1
        if self._records_since_flush >= self._flush_every:
            self._flush_pending()

    def _flush_pending(self) -> None:
        """Write one bounded batch so gzip does not compress every tick separately."""
        if not self._pending_lines:
            return
        self._stream.write("".join(self._pending_lines))
        self._stream.flush()
        self._pending_lines.clear()
        self._records_since_flush = 0

    def close(self) -> None:
        if not self._stream.closed:
            self._flush_pending()
            self._stream.close()

    @staticmethod
    def read(path: str | Path) -> tuple[dict[str, Any], ...]:
        selected = Path(path)
        with (
            gzip.open(selected, "rt", encoding="utf-8")
            if selected.suffix == ".gz"
            else selected.open(encoding="utf-8")
        ) as stream:
            return tuple(json.loads(line) for line in stream)

    @classmethod
    def read_view(cls, path: str | Path, view: str) -> tuple[dict[str, Any], ...]:
        if view not in {"referee", "red", "blue", "public"}:
            raise ValueError("unknown replay view")
        records = cls.read(path)
        if view == "referee":
            return records
        filtered: list[dict[str, Any]] = []
        for record in records:
            if record["record_type"] == "metadata":
                filtered.append(record)
                continue
            payload = record["payload"]
            base: dict[str, Any] = {
                "timestamp": payload["timestamp"],
                "public_combat_events": payload["public_combat_events"],
            }
            if view == "red":
                base.update(
                    red_observation=payload["red_observation"],
                    red_action=payload["red_action"],
                )
            elif view == "blue":
                entities = payload["world"]["entities"]
                base.update(
                    blue_action=payload["blue_action"],
                    blue_entities=[entity for entity in entities if entity["side"] == "blue"],
                )
            else:
                mission = payload["red_observation"]["mission_status"]
                base["mission_status"] = mission
            filtered.append({**record, "payload": base})
        return tuple(filtered)
