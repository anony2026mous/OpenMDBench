"""AD2-09 HARD routed contact delivery and jamming boundaries."""

import json
from typing import Any, cast

from openmdbench.core.entities import Domain, Lifecycle, PlatformAsset, Side
from openmdbench.core.world import ContactTrack
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.policies import AD2RedBaselineAgent


def _track(tick: int) -> ContactTrack:
    return ContactTrack(
        contact_id="contact-red-test",
        owner_side=Side.RED,
        estimated_domain=Domain.AIR,
        position=(10_000.0, 0.0, 100.0),
        velocity=(-30.0, 0.0, 0.0),
        uncertainty_m=100.0,
        confidence=0.8,
        first_detected_tick=tick,
        detected_by=("red-interceptor-uav-1:radar_uav",),
        inferred_type="hostile_uav",
        last_update_tick=tick,
    )


def test_hard_jamming_forces_uav_contact_through_usv_and_recovers() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=111)
    env.reset(seed=111)
    assert env.world is not None and env._communication is not None
    env._route_ad2_tracks((_track(900),), 900)
    uav = env.world.registry.get("red-interceptor-uav-1")
    assert isinstance(uav, PlatformAsset)
    assert uav.components.communication_status == "relayed"
    queued = cast(
        dict[str, Any],
        next(event for event in env.wave_events if event.get("event_type") == "message_queued"),
    )
    assert queued["route"][0] == "red-interceptor-uav-1"
    assert any(str(endpoint).startswith("red-picket-usv-") for endpoint in queued["route"])
    assert queued["arrival_tick"] >= 902
    assert queued["physical_latency_ms"] >= 100.0
    assert env.world.contacts.get(Side.RED, []) == []
    env._deliver_ad2_messages(int(queued["arrival_tick"]))
    assert env.world.contacts[Side.RED][0].contact_id == "contact-red-test"

    env._route_ad2_tracks((), 1_200)
    recovered = env.world.registry.get("red-interceptor-uav-1")
    assert isinstance(recovered, PlatformAsset)
    assert recovered.components.communication_status == "connected"


def test_hard_no_relay_means_offline_and_no_contact_message() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=112)
    env.reset(seed=112)
    assert env.world is not None and env._communication is not None
    for endpoint_id in ("red-picket-usv-1", "red-picket-usv-2"):
        env._communication.set_relay_enabled(endpoint_id, False)
    env._route_ad2_tracks((_track(900),), 900)
    uav = env.world.registry.get("red-interceptor-uav-1")
    assert isinstance(uav, PlatformAsset)
    assert uav.components.communication_status == "offline"
    assert not any(event.get("event_type") == "message_queued" for event in env.wave_events)


def test_hard_jamming_boundaries_and_pending_queue_survive_json_checkpoint() -> None:
    continuous = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=113)
    restored = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=113)
    continuous.reset(seed=113)
    restored.reset(seed=113)
    continuous._apply_ad2_difficulty_events(899)
    assert not continuous._ad2_blocked_links(899)
    continuous._apply_ad2_difficulty_events(900)
    assert continuous._ad2_blocked_links(900)
    assert continuous.world is not None
    continuous.world.tick = 900
    assert any(
        event["event_type"] == "jamming_started"
        for event in continuous.red_observation().visible_events
    )
    continuous._route_ad2_tracks((_track(900),), 900)
    checkpoint = json.loads(json.dumps(continuous.export_state()))
    restored.import_state(checkpoint)
    continuous._deliver_ad2_messages(902)
    restored._deliver_ad2_messages(902)
    assert continuous.world is not None and restored.world is not None
    assert continuous.world.contacts == restored.world.contacts
    continuous._apply_ad2_difficulty_events(1_200)
    assert not continuous._ad2_blocked_links(1_200)
    assert continuous.wave_events[-1]["event_type"] == "jamming_ended"


def test_hard_positive_latency_command_applies_on_later_decision_tick() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=114)
    env.reset(seed=114)
    assert env.world is not None
    protected = (float(env._protected_point[0]), float(env._protected_point[1]))
    agent = AD2RedBaselineAgent(protected)
    first_batch = agent.act(env.red_observation())
    _observation, _reward, _terminated, _truncated, first_info = env.step_red_action_batch(
        first_batch
    )
    uav = env.world.registry.get("red-interceptor-uav-1")
    shore = env.world.registry.get("red-island-radar-1")
    assert isinstance(uav, PlatformAsset) and isinstance(shore, PlatformAsset)
    assert uav.components.current_command is None
    assert shore.components.current_command is not None
    communication_events = cast(tuple[dict[str, Any], ...], first_info["communication_events"])
    assert any(event["event_type"] == "message_queued" for event in communication_events)

    second_batch = agent.act(env.red_observation())
    env.step_red_action_batch(second_batch)
    delivered_uav = env.world.registry.get("red-interceptor-uav-1")
    assert isinstance(delivered_uav, PlatformAsset)
    assert delivered_uav.components.current_command is not None
    queued = [
        event
        for event in env.wave_events
        if event.get("event_type") == "message_queued"
        and event.get("route") == ("red-command", "red-interceptor-uav-1")
    ]
    assert queued and queued[0]["sent_tick"] == 0 and queued[0]["arrival_tick"] == 1


def test_hard_communication_state_is_isolated_across_sessions() -> None:
    environments = [
        OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=200 + index) for index in range(16)
    ]
    for index, env in enumerate(environments):
        env.reset(seed=200 + index)
        assert env._communication is not None
    first = environments[0]._communication
    second = environments[1]._communication
    assert first is not None and second is not None and first is not second
    first.set_relay_enabled("red-picket-usv-1", False)
    assert not first.endpoints["red-picket-usv-1"].relay_enabled
    assert second.endpoints["red-picket-usv-1"].relay_enabled


def test_delayed_command_for_destroyed_platform_is_discarded() -> None:
    env = OpenMDBenchEnv(scenario_id="MD-AD-002-HARD", seed=216)
    env.reset(seed=216)
    assert env.world is not None
    protected = (float(env._protected_point[0]), float(env._protected_point[1]))
    agent = AD2RedBaselineAgent(protected)
    env.step_red_action_batch(agent.act(env.red_observation()))
    uav = env.world.registry.get("red-interceptor-uav-1")
    assert isinstance(uav, PlatformAsset)
    env.world.registry.update(uav.model_copy(update={"lifecycle": Lifecycle.DESTROYED}))
    _observation, _reward, _terminated, _truncated, info = env.step_red_action_batch(
        agent.act(env.red_observation())
    )
    assert any(
        event["event_type"] == "command_discarded_unavailable"
        for event in cast(tuple[dict[str, Any], ...], info["communication_events"])
    )
