"""AD2-09 deterministic routed communication semantics."""

import pytest
from openmdbench.core.rng import SessionRNG
from openmdbench.systems.communications import CommEndpoint, CommunicationNetwork, LinkKind


def _endpoint(
    endpoint_id: str,
    x: float,
    *,
    relay: bool = False,
    online: bool = True,
) -> CommEndpoint:
    return CommEndpoint(
        endpoint_id,
        (x, 0.0, 0.0),
        LinkKind.LOS,
        11_000.0,
        5_000_000.0,
        online,
        "red",
        relay,
        20.0,
    )


def _network(
    order: tuple[str, ...] = ("command", "relay-a", "relay-b", "uav"),
) -> CommunicationNetwork:
    endpoints = {
        "command": _endpoint("command", 0.0),
        "relay-a": _endpoint("relay-a", 10_000.0, relay=True),
        "relay-b": _endpoint("relay-b", 20_000.0, relay=True),
        "uav": _endpoint("uav", 30_000.0),
    }
    network = CommunicationNetwork(SessionRNG(101))
    for endpoint_id in order:
        network.register(endpoints[endpoint_id])
    return network


def test_direct_and_relay_routes_never_arrive_on_send_tick() -> None:
    network = _network()
    direct = network.send_routed(
        "command", "relay-a", {}, tick=5, expires_tick=20, payload_bytes=10
    )
    assert direct is not None and direct.route == ("command", "relay-a")
    assert direct.arrival_tick == 6
    assert network.deliver(5) == ()
    assert network.deliver(6) == (direct,)

    double = network.send_routed("command", "uav", {}, tick=10, expires_tick=20, payload_bytes=10)
    assert double is not None
    assert double.route == ("command", "relay-a", "relay-b", "uav")
    assert double.arrival_tick == 13


def test_route_is_registration_order_independent_and_hop_bounded() -> None:
    forward = _network().route("command", "uav")
    reverse = _network(("uav", "relay-b", "relay-a", "command")).route("command", "uav")
    assert forward == reverse == ("command", "relay-a", "relay-b", "uav")
    with pytest.raises(ConnectionError, match="no legal"):
        _network().route("command", "uav", max_relay_hops=1)


def test_blocked_direct_link_uses_relay_without_blocking_endpoint() -> None:
    network = _network()
    network.endpoints["uav"] = _endpoint("uav", 10_000.0)
    route = network.route("command", "uav", blocked_links={("command", "uav")})
    assert route == ("command", "relay-a", "uav")


def test_zero_physical_latency_wired_link_can_arrive_same_tick() -> None:
    network = CommunicationNetwork(SessionRNG(102))
    for endpoint_id in ("command", "shore"):
        network.register(
            CommEndpoint(
                endpoint_id,
                (0.0, 0.0, 0.0),
                LinkKind.WIRED,
                0.0,
                100_000_000.0,
                True,
                "red",
            )
        )
    message = network.send_routed("command", "shore", {}, tick=7, expires_tick=8, payload_bytes=10)
    assert message is not None and message.arrival_tick == 7


def test_offline_blocked_cross_side_and_ttl_fail_closed() -> None:
    network = _network()
    network.set_online("relay-b", False)
    with pytest.raises(ConnectionError, match="no legal"):
        network.route("command", "uav")
    network.set_online("relay-b", True)
    with pytest.raises(ConnectionError, match="blocked"):
        network.route("command", "uav", blocked_endpoint_ids={"command"})
    network.register(
        CommEndpoint(
            "blue-relay",
            (10_000.0, 0.0, 0.0),
            LinkKind.LOS,
            50_000.0,
            5_000_000.0,
            True,
            "blue",
            True,
            20.0,
        )
    )
    assert "blue-relay" not in network.route("command", "uav")
    message = network.send_routed("command", "uav", {}, tick=0, expires_tick=2, payload_bytes=10)
    assert message is not None and message.arrival_tick == 3
    assert network.deliver(3) == ()
    assert network.events[-1]["event_type"] == "message_expired"


def test_loss_rng_queue_and_next_draw_round_trip_checkpoint() -> None:
    continuous = _network()
    first = continuous.send_routed(
        "command",
        "relay-a",
        {},
        tick=0,
        expires_tick=10,
        payload_bytes=10,
        loss_probability=0.5,
    )
    restored = CommunicationNetwork.from_snapshot(SessionRNG(999), continuous.snapshot())
    second_continuous = continuous.send_routed(
        "command",
        "relay-a",
        {},
        tick=1,
        expires_tick=10,
        payload_bytes=10,
        loss_probability=0.5,
    )
    second_restored = restored.send_routed(
        "command",
        "relay-a",
        {},
        tick=1,
        expires_tick=10,
        payload_bytes=10,
        loss_probability=0.5,
    )
    assert second_continuous == second_restored
    assert continuous.snapshot() == restored.snapshot()
    assert (first is None) == (continuous.events[0]["event_type"] == "message_dropped")


def test_route_and_message_validation_fail_closed() -> None:
    network = CommunicationNetwork(SessionRNG(103))
    endpoint = CommEndpoint("a", (0.0, 0.0, 0.0), LinkKind.LOS, 10_000.0, 1_000_000.0, side="red")
    network.register(endpoint)
    with pytest.raises(ValueError, match="duplicate"):
        network.register(endpoint)
    network.register(
        CommEndpoint("b", (100.0, 0.0, 0.0), LinkKind.LOS, 10_000.0, 1_000_000.0, side="red")
    )
    with pytest.raises(ValueError, match="max_relay_hops"):
        network.route("a", "b", max_relay_hops=3)
    with pytest.raises(ValueError, match="loss_probability"):
        network.send_routed(
            "a",
            "b",
            {},
            tick=0,
            expires_tick=1,
            payload_bytes=1,
            loss_probability=1.1,
        )
    with pytest.raises(ValueError, match="expiry"):
        network.send_routed("a", "b", {}, tick=1, expires_tick=0, payload_bytes=1)
