"""Minimal checkpoint compatibility and continuation tests."""

import json

import pytest
from openmdbench.core.entities import Domain, EntityRegistry, PlatformAsset, Side
from openmdbench.core.rng import SessionRNG
from openmdbench.core.scheduling import EventQueue, SimulationClock
from openmdbench.replay.checkpoint import create_checkpoint, restore_checkpoint


def _core() -> tuple[SimulationClock, EntityRegistry, EventQueue, SessionRNG]:
    clock = SimulationClock()
    registry = EntityRegistry()
    registry.register(
        PlatformAsset(
            id="usv-1",
            side=Side.BLUE,
            domain=Domain.SURFACE,
            platform_type="usv",
            position=(0.0, 0.0, 0.0),
        )
    )
    events = EventQueue()
    events.schedule(50, "weather-change", {"weather": "rain"})
    rng = SessionRNG(7)
    rng.stream("weather").random(3)
    return clock, registry, events, rng


def test_restored_core_matches_continuous_next_100_ticks() -> None:
    clock, registry, events, rng = _core()
    payload = create_checkpoint(
        config_hash="sha256:test",
        clock=clock,
        registry=registry,
        events=events,
        rng=rng,
        task_state={"status": "running"},
    )
    restored = restore_checkpoint(payload, expected_config_hash="sha256:test")

    continuous_draws = []
    restored_draws = []
    for _ in range(100):
        continuous_draws.append(rng.stream("weather").random())
        restored_draws.append(restored.rng.stream("weather").random())
        clock.advance()
        restored.clock.advance()
    assert continuous_draws == restored_draws
    assert clock.tick == restored.clock.tick == 100
    assert events.pop_due(100) == restored.events.pop_due(100)
    assert registry.all_entities() == restored.registry.all_entities()
    assert restored.task_state == {"status": "running"}


def test_incompatible_version_and_config_are_rejected() -> None:
    clock, registry, events, rng = _core()
    payload = create_checkpoint(
        config_hash="sha256:test",
        clock=clock,
        registry=registry,
        events=events,
        rng=rng,
        task_state={},
    )
    with pytest.raises(ValueError, match="hash mismatch"):
        restore_checkpoint(payload, expected_config_hash="sha256:other")

    incompatible = json.loads(payload)
    incompatible["schema_version"] = "2.0"
    with pytest.raises(ValueError, match="unsupported"):
        restore_checkpoint(json.dumps(incompatible), expected_config_hash="sha256:test")
