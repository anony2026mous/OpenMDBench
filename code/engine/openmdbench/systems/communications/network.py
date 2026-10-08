"""Distance, bandwidth, outage, and delayed-command communication model."""

from __future__ import annotations

import heapq
import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from openmdbench.core.rng import SessionRNG


class LinkKind(StrEnum):
    LOS = "line_of_sight"
    WIRED = "wired"
    ACOUSTIC = "acoustic"


@dataclass(frozen=True, slots=True)
class CommEndpoint:
    endpoint_id: str
    position: tuple[float, float, float]
    link_kind: LinkKind
    range_m: float
    bandwidth_bps: float
    online: bool = True
    side: str | None = None
    relay_enabled: bool = False
    physical_latency_ms: float = 0.0


@dataclass(order=True, frozen=True, slots=True)
class Message:
    arrival_tick: int
    sequence: int
    sender_id: str
    recipient_id: str
    sent_tick: int
    expires_tick: int
    payload: dict[str, Any]
    generated_tick: int | None = None
    route: tuple[str, ...] = ()
    physical_latency_ms: float = 0.0


class CommunicationNetwork:
    def __init__(self, rng: SessionRNG, *, tick_seconds: float = 1.0) -> None:
        self._session_rng = rng
        self._rng = rng.stream("communication")
        self.tick_seconds = tick_seconds
        self.endpoints: dict[str, CommEndpoint] = {}
        self._queue: list[Message] = []
        self._next_sequence = 0
        self.last_commands: dict[str, Message] = {}
        self.events: list[dict[str, Any]] = []

    def register(self, endpoint: CommEndpoint) -> None:
        if endpoint.endpoint_id in self.endpoints:
            raise ValueError(f"duplicate communication endpoint: {endpoint.endpoint_id}")
        self.endpoints[endpoint.endpoint_id] = endpoint

    def set_online(self, endpoint_id: str, online: bool) -> None:
        endpoint = self.endpoints[endpoint_id]
        self.endpoints[endpoint_id] = CommEndpoint(
            endpoint.endpoint_id,
            endpoint.position,
            endpoint.link_kind,
            endpoint.range_m,
            endpoint.bandwidth_bps,
            online,
            endpoint.side,
            endpoint.relay_enabled,
            endpoint.physical_latency_ms,
        )

    def set_relay_enabled(self, endpoint_id: str, enabled: bool) -> None:
        endpoint = self.endpoints[endpoint_id]
        self.endpoints[endpoint_id] = CommEndpoint(
            endpoint.endpoint_id,
            endpoint.position,
            endpoint.link_kind,
            endpoint.range_m,
            endpoint.bandwidth_bps,
            endpoint.online,
            endpoint.side,
            enabled,
            endpoint.physical_latency_ms,
        )

    def update_position(self, endpoint_id: str, position: tuple[float, float, float]) -> None:
        endpoint = self.endpoints[endpoint_id]
        self.endpoints[endpoint_id] = CommEndpoint(
            endpoint.endpoint_id,
            position,
            endpoint.link_kind,
            endpoint.range_m,
            endpoint.bandwidth_bps,
            endpoint.online,
            endpoint.side,
            endpoint.relay_enabled,
            endpoint.physical_latency_ms,
        )

    @staticmethod
    def _same_side(first: CommEndpoint, second: CommEndpoint) -> bool:
        return first.side is None or second.side is None or first.side == second.side

    @classmethod
    def _reachable(cls, first: CommEndpoint, second: CommEndpoint) -> bool:
        if not first.online or not second.online or not cls._same_side(first, second):
            return False
        if first.link_kind is LinkKind.WIRED and second.link_kind is LinkKind.WIRED:
            return True
        ranges = tuple(value for value in (first.range_m, second.range_m) if value > 0.0)
        return bool(ranges) and math.dist(first.position, second.position) <= min(ranges)

    def route(
        self,
        sender_id: str,
        recipient_id: str,
        *,
        max_relay_hops: int = 2,
        blocked_endpoint_ids: Iterable[str] = (),
        blocked_links: Iterable[tuple[str, str]] = (),
    ) -> tuple[str, ...]:
        """Choose the shortest stable same-side route with at most two relays."""
        if max_relay_hops < 0 or max_relay_hops > 2:
            raise ValueError("max_relay_hops must be between zero and two")
        blocked = set(blocked_endpoint_ids)
        blocked_edges = {frozenset(link) for link in blocked_links}
        if sender_id in blocked or recipient_id in blocked:
            raise ConnectionError("communication endpoint is blocked")
        frontier: list[tuple[str, ...]] = [(sender_id,)]
        while frontier:
            path = frontier.pop(0)
            current = self.endpoints[path[-1]]
            candidates = [recipient_id]
            if len(path) - 1 <= max_relay_hops:
                candidates.extend(
                    endpoint_id
                    for endpoint_id, endpoint in sorted(self.endpoints.items())
                    if endpoint.relay_enabled
                    and endpoint_id not in path
                    and endpoint_id not in blocked
                    and endpoint_id not in {sender_id, recipient_id}
                )
            for endpoint_id in candidates:
                if endpoint_id in blocked or endpoint_id in path:
                    continue
                endpoint = self.endpoints[endpoint_id]
                if frozenset((path[-1], endpoint_id)) in blocked_edges:
                    continue
                if not self._reachable(current, endpoint):
                    continue
                candidate = (*path, endpoint_id)
                if endpoint_id == recipient_id:
                    return candidate
                if len(candidate) - 2 < max_relay_hops:
                    frontier.append(candidate)
        raise ConnectionError("no legal communication route")

    def send_routed(
        self,
        sender_id: str,
        recipient_id: str,
        payload: dict[str, Any],
        *,
        tick: int,
        expires_tick: int,
        payload_bytes: int,
        max_relay_hops: int = 2,
        loss_probability: float = 0.0,
        blocked_endpoint_ids: Iterable[str] = (),
        blocked_links: Iterable[tuple[str, str]] = (),
        generated_tick: int | None = None,
    ) -> Message | None:
        if not 0.0 <= loss_probability <= 1.0:
            raise ValueError("loss_probability must be within [0,1]")
        if expires_tick < tick or payload_bytes < 0:
            raise ValueError("invalid message expiry or size")
        route = self.route(
            sender_id,
            recipient_id,
            max_relay_hops=max_relay_hops,
            blocked_endpoint_ids=blocked_endpoint_ids,
            blocked_links=blocked_links,
        )
        hops = tuple(zip(route[:-1], route[1:], strict=True))
        capacity_bytes = min(
            min(self.endpoints[left].bandwidth_bps, self.endpoints[right].bandwidth_bps)
            * self.tick_seconds
            / 8.0
            for left, right in hops
        )
        if payload_bytes > capacity_bytes:
            raise ValueError("message exceeds routed per-tick link bandwidth")
        physical_latency_ms = sum(
            max(
                self.endpoints[left].physical_latency_ms,
                self.endpoints[right].physical_latency_ms,
            )
            for left, right in hops
        )
        arrival_tick = tick + sum(
            (
                0
                if max(
                    self.endpoints[left].physical_latency_ms,
                    self.endpoints[right].physical_latency_ms,
                )
                == 0.0
                else max(
                    1,
                    math.ceil(
                        max(
                            self.endpoints[left].physical_latency_ms,
                            self.endpoints[right].physical_latency_ms,
                        )
                        / (self.tick_seconds * 1_000.0)
                    ),
                )
            )
            for left, right in hops
        )
        dropped = float(self._rng.random()) < loss_probability
        event = {
            "event_type": "message_dropped" if dropped else "message_queued",
            "generated_tick": tick if generated_tick is None else generated_tick,
            "sent_tick": tick,
            "arrival_tick": arrival_tick,
            "expires_tick": expires_tick,
            "route": route,
            "physical_latency_ms": physical_latency_ms,
            "quantized_hops": len(hops),
        }
        self.events.append(event)
        if dropped:
            return None
        message = Message(
            arrival_tick=arrival_tick,
            sequence=self._next_sequence,
            sender_id=sender_id,
            recipient_id=recipient_id,
            sent_tick=tick,
            expires_tick=expires_tick,
            payload=payload,
            generated_tick=tick if generated_tick is None else generated_tick,
            route=route,
            physical_latency_ms=physical_latency_ms,
        )
        self._next_sequence += 1
        heapq.heappush(self._queue, message)
        return message

    def send(
        self,
        sender_id: str,
        recipient_id: str,
        payload: dict[str, Any],
        *,
        tick: int,
        expires_tick: int,
        payload_bytes: int,
        terrain_blocked: bool = False,
        interfered: bool = False,
    ) -> Message:
        sender = self.endpoints[sender_id]
        recipient = self.endpoints[recipient_id]
        if not sender.online or terrain_blocked or interfered:
            raise ConnectionError("communication link is unavailable")
        if expires_tick < tick or payload_bytes < 0:
            raise ValueError("invalid message expiry or size")
        if sender.link_kind is not LinkKind.WIRED and math.dist(
            sender.position, recipient.position
        ) > min(sender.range_m, recipient.range_m):
            raise ConnectionError("communication endpoints are out of range")
        capacity_bytes = sender.bandwidth_bps * self.tick_seconds / 8.0
        if sender.link_kind is not LinkKind.WIRED and payload_bytes > capacity_bytes:
            raise ValueError("message exceeds per-tick link bandwidth")
        latency = 0
        if sender.link_kind is LinkKind.ACOUSTIC:
            latency = int(self._rng.integers(2, 6))
        message = Message(
            arrival_tick=tick + latency,
            sequence=self._next_sequence,
            sender_id=sender_id,
            recipient_id=recipient_id,
            sent_tick=tick,
            expires_tick=expires_tick,
            payload=payload,
        )
        self._next_sequence += 1
        heapq.heappush(self._queue, message)
        return message

    def deliver(self, tick: int) -> tuple[Message, ...]:
        delivered: list[Message] = []
        deferred: list[Message] = []
        while self._queue and self._queue[0].arrival_tick <= tick:
            message = heapq.heappop(self._queue)
            recipient = self.endpoints[message.recipient_id]
            if tick > message.expires_tick:
                self.events.append(
                    {
                        "event_type": "message_expired",
                        "sequence": message.sequence,
                        "tick": tick,
                        "sender_id": message.sender_id,
                        "recipient_id": message.recipient_id,
                        "route": message.route,
                        "sent_tick": message.sent_tick,
                        "arrival_tick": message.arrival_tick,
                    }
                )
                continue
            if not recipient.online:
                deferred.append(message)
                continue
            previous = self.last_commands.get(message.recipient_id)
            if previous is None or message.sent_tick >= previous.sent_tick:
                self.last_commands[message.recipient_id] = message
                delivered.append(message)
                self.events.append(
                    {
                        "event_type": "message_delivered",
                        "sequence": message.sequence,
                        "tick": tick,
                        "sender_id": message.sender_id,
                        "recipient_id": message.recipient_id,
                        "route": message.route,
                        "sent_tick": message.sent_tick,
                        "arrival_tick": message.arrival_tick,
                        "physical_latency_ms": message.physical_latency_ms,
                    }
                )
        for message in deferred:
            heapq.heappush(self._queue, message)
        return tuple(delivered)

    def snapshot(self) -> dict[str, Any]:
        return {
            "rng": self._session_rng.snapshot(),
            "tick_seconds": self.tick_seconds,
            "endpoints": [asdict(endpoint) for endpoint in self.endpoints.values()],
            "last_commands": {
                endpoint_id: asdict(message) for endpoint_id, message in self.last_commands.items()
            },
            "next_sequence": self._next_sequence,
            "queue": [asdict(message) for message in sorted(self._queue)],
            "events": self.events,
        }

    @classmethod
    def from_snapshot(cls, rng: SessionRNG, snapshot: dict[str, Any]) -> CommunicationNetwork:
        restored_rng = SessionRNG.from_snapshot(snapshot["rng"]) if "rng" in snapshot else rng
        network = cls(restored_rng, tick_seconds=float(snapshot.get("tick_seconds", 1.0)))
        for endpoint_record in snapshot["endpoints"]:
            values = dict(endpoint_record)
            values["link_kind"] = LinkKind(values["link_kind"])
            values["position"] = tuple(values["position"])
            network.register(CommEndpoint(**values))

        def restore_message(record: dict[str, Any]) -> Message:
            values = dict(record)
            values["route"] = tuple(values.get("route", ()))
            return Message(**values)

        network._queue = [restore_message(record) for record in snapshot["queue"]]
        heapq.heapify(network._queue)
        network._next_sequence = int(snapshot["next_sequence"])
        network.last_commands = {
            endpoint_id: restore_message(record)
            for endpoint_id, record in snapshot["last_commands"].items()
        }
        network.events = list(snapshot.get("events", []))
        return network
