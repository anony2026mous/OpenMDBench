"""Deterministic tick quantization and checkpointable transport outcomes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal


def quantize_delay_ticks_v2(*, delay_seconds: float, physics_dt_seconds: float) -> int:
    if (
        any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in (delay_seconds, physics_dt_seconds)
        )
        or delay_seconds < 0.0
        or physics_dt_seconds <= 0.0
    ):
        raise ValueError("delay and physics dt must be finite with valid signs")
    return 0 if delay_seconds == 0.0 else max(1, math.ceil(delay_seconds / physics_dt_seconds))


@dataclass(frozen=True, slots=True)
class TransportReceiptV2:
    message_id: str
    origin_tick: int
    delivery_tick: int
    expiry_tick: int
    delay_ticks: int
    status: Literal["queued", "delivered", "expired", "dropped", "blocked"]


def schedule_transport_v2(
    *,
    message_id: str,
    origin_tick: int,
    ttl_ticks: int,
    delay_seconds: float,
    physics_dt_seconds: float,
    link_available: bool,
    dropped: bool = False,
) -> TransportReceiptV2:
    if (
        not message_id
        or not isinstance(origin_tick, int)
        or isinstance(origin_tick, bool)
        or origin_tick < 0
        or not isinstance(ttl_ticks, int)
        or isinstance(ttl_ticks, bool)
        or ttl_ticks < 0
        or not isinstance(link_available, bool)
        or not isinstance(dropped, bool)
    ):
        raise ValueError("transport identity or tick input is invalid")
    delay = quantize_delay_ticks_v2(
        delay_seconds=delay_seconds, physics_dt_seconds=physics_dt_seconds
    )
    delivery, expiry = origin_tick + delay, origin_tick + ttl_ticks
    status: Literal["queued", "delivered", "expired", "dropped", "blocked"]
    if not link_available:
        status = "blocked"
    elif dropped:
        status = "dropped"
    elif delivery > expiry:
        status = "expired"
    else:
        status = "queued"
    return TransportReceiptV2(message_id, origin_tick, delivery, expiry, delay, status)


__all__ = ["TransportReceiptV2", "quantize_delay_ticks_v2", "schedule_transport_v2"]
