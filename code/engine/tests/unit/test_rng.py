"""Tests for the session-level deterministic RNG entry point."""

from openmdbench.core.rng import SessionRNG, configuration_hash


def test_same_seed_repeats_and_different_seed_changes() -> None:
    first = SessionRNG(7).generator.random(8)
    second = SessionRNG(7).generator.random(8)
    different = SessionRNG(8).generator.random(8)
    assert (first == second).all()
    assert (first != different).any()


def test_configuration_hash_is_order_independent() -> None:
    assert configuration_hash({"b": 2, "a": 1}) == configuration_hash({"a": 1, "b": 2})


def test_named_streams_are_independent() -> None:
    baseline = SessionRNG(7)
    expected_weather = baseline.stream("weather").random(4)

    changed = SessionRNG(7)
    changed.stream("sensor").random(100)
    actual_weather = changed.stream("weather").random(4)
    assert (actual_weather == expected_weather).all()


def test_snapshot_restores_each_stream_at_next_draw() -> None:
    original = SessionRNG(7)
    original.stream("combat").random(3)
    original.stream("communication").random(2)
    restored = SessionRNG.from_snapshot(original.snapshot())
    assert original.stream("combat").random() == restored.stream("combat").random()
    assert original.stream("communication").random() == restored.stream("communication").random()
