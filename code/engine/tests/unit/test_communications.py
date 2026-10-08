"""Communication range, latency, outage, expiry, and checkpoint tests."""

import pytest
from openmdbench.core.rng import SessionRNG
from openmdbench.systems.communications import (
    CommEndpoint,
    CommunicationNetwork,
    LinkKind,
)


def _acoustic_network(seed: int = 7) -> CommunicationNetwork:
    network = CommunicationNetwork(SessionRNG(seed))
    network.register(CommEndpoint("auv-1", (0.0, 0.0, -50.0), LinkKind.ACOUSTIC, 5_000.0, 1_000.0))
    network.register(
        CommEndpoint("auv-2", (100.0, 0.0, -50.0), LinkKind.ACOUSTIC, 5_000.0, 1_000.0)
    )
    return network


def test_acoustic_latency_is_two_to_five_seconds_and_seed_deterministic() -> None:
    first = _acoustic_network(7).send(
        "auv-1", "auv-2", {"command": "hold"}, tick=10, expires_tick=30, payload_bytes=10
    )
    second = _acoustic_network(7).send(
        "auv-1", "auv-2", {"command": "hold"}, tick=10, expires_tick=30, payload_bytes=10
    )
    assert first == second
    assert 2 <= first.arrival_tick - first.sent_tick <= 5


def test_bandwidth_range_and_interference_are_enforced() -> None:
    network = _acoustic_network()
    with pytest.raises(ValueError, match="bandwidth"):
        network.send("auv-1", "auv-2", {}, tick=0, expires_tick=10, payload_bytes=126)
    with pytest.raises(ConnectionError, match="unavailable"):
        network.send(
            "auv-1", "auv-2", {}, tick=0, expires_tick=10, payload_bytes=1, interfered=True
        )


def test_recovery_does_not_execute_expired_or_overwrite_new_command() -> None:
    network = _acoustic_network()
    message = network.send(
        "auv-1", "auv-2", {"command": "old"}, tick=0, expires_tick=3, payload_bytes=10
    )
    network.set_online("auv-2", False)
    assert network.deliver(message.arrival_tick) == ()
    network.set_online("auv-2", True)
    assert network.deliver(6) == ()
    assert "auv-2" not in network.last_commands


def test_message_queue_round_trips_through_checkpoint() -> None:
    rng = SessionRNG(7)
    network = CommunicationNetwork(rng)
    network.register(CommEndpoint("a", (0.0, 0.0, 0.0), LinkKind.WIRED, 0.0, 0.0))
    network.register(CommEndpoint("b", (1e6, 0.0, 0.0), LinkKind.WIRED, 0.0, 0.0))
    network.send("a", "b", {"command": "hold"}, tick=5, expires_tick=10, payload_bytes=1_000_000)
    restored = CommunicationNetwork.from_snapshot(SessionRNG(7), network.snapshot())
    assert restored.deliver(5) == network.deliver(5)
