"""Immutable lifecycle execution evidence for session-owned v2 worlds."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from types import MappingProxyType
from typing import Any, Literal


def _canonical(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _canonical(value.model_dump(mode="json"))
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _canonical(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_canonical(item) for item in value]
    return value


def lifecycle_blueprint_hash(value: object | None) -> str | None:
    if value is None:
        return None
    encoded = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


@dataclass(frozen=True, slots=True)
class LifecycleReceiptV2:
    tick: int
    operation_id: str
    status: Literal["committed", "committed_with_cleanup_errors"]
    applied_event_ids: tuple[str, ...]
    spawned_entity_ids: tuple[str, ...]
    despawned_entity_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LifecycleTombstoneV2:
    entity_id: str
    tick: int
    source_event_id: str
    adapters_closed: bool
    cleanup_errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LifecycleAuditRecordV2:
    operation_id: str
    tick: int
    status: Literal["committed", "committed_with_cleanup_errors", "rolled_back"]
    staged_adapter_instance_ids: tuple[str, ...] = ()
    closed_adapter_instance_ids: tuple[str, ...] = ()
    cleanup_errors: tuple[str, ...] = ()


@dataclass(slots=True)
class LifecycleFaultInjectorV2:
    fail_after_staged_entities: int | None = None
    fail_after_staged_adapters: int | None = None
    close_error_entity_ids: set[str] | None = None
    fail_after_created_adapters: int | None = None

    def close_error_ids(self) -> frozenset[str]:
        return frozenset(self.close_error_entity_ids or ())


def frozen_ledger(
    value: Mapping[str, LifecycleReceiptV2],
) -> Mapping[str, LifecycleReceiptV2]:
    return MappingProxyType(dict(value))


def frozen_tombstones(
    value: Mapping[str, LifecycleTombstoneV2],
) -> Mapping[str, LifecycleTombstoneV2]:
    return MappingProxyType(dict(value))


__all__ = [
    "LifecycleAuditRecordV2",
    "LifecycleFaultInjectorV2",
    "LifecycleReceiptV2",
    "LifecycleTombstoneV2",
    "frozen_ledger",
    "frozen_tombstones",
    "lifecycle_blueprint_hash",
]
