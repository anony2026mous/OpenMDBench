"""MD3-09 live, replay, view-filter, and checkpoint contracts."""

from __future__ import annotations

from pathlib import Path

from openmdbench.replay.v2 import ReplayReaderV2
from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
from openmdbench.schemas.core_v2 import VisualizationFrameV2
from openmdbench.sessions.formal_v2 import create_formal_gateway_v2, create_formal_session_v2
from openmdbench.visualization.formal_v2 import build_formal_frame_v2
from openmdbench.visualization.live_formal_v2 import run_live_formal_v2


def _frame_payload(frame: VisualizationFrameV2) -> dict[str, object]:
    return frame.model_dump(mode="json")


def test_formal_task_viewport_uses_declared_geometry_without_view_leakage() -> None:
    resolved, catalog = compile_formal_scenario_v2("MD-INT-003-EASY")
    session = create_formal_session_v2(
        "MD-INT-003-EASY", session_id="md3.viz.task-viewport", seed=73
    )
    session.load().start()
    try:
        referee = build_formal_frame_v2(session, catalog, view="referee")
        defender = build_formal_frame_v2(
            session, catalog, view="faction", faction_id="faction.defender"
        )
        public = build_formal_frame_v2(session, catalog, view="public")
        assert referee.world_bounds_m == defender.world_bounds_m == public.world_bounds_m
        assert referee.world_bounds_m is not None
        minimum_x, minimum_y, maximum_x, maximum_y = referee.world_bounds_m
        frame = resolved.world.coordinate_frame
        assert frame is not None
        lower, upper = frame.local_bounds_m
        assert referee.world_bounds_m != (lower[0], lower[1], upper[0], upper[1])
        assert maximum_x - minimum_x < 40_000.0
        assert maximum_y - minimum_y < 30_000.0
        for zone in resolved.world.zones:
            if any(str(tag).startswith("terrain:") for tag in zone.tags):
                continue
            for point in zone.geometry.positions_m:
                assert minimum_x <= point[0] <= maximum_x
                assert minimum_y <= point[1] <= maximum_y
    finally:
        session.stop().close()


def test_formal_views_are_non_advancing_and_hide_unowned_truth() -> None:
    resolved, catalog = compile_formal_scenario_v2("MD-INT-003-EASY")
    session = create_formal_session_v2("MD-INT-003-EASY", session_id="md3.viz.views", seed=73)
    session.load().start()
    try:
        session.step(operation_id="md3.viz.views.tick.0", expected_tick=0)
        before = session.world_view.tick
        referee = build_formal_frame_v2(session, catalog, view="referee")
        defender = build_formal_frame_v2(
            session, catalog, view="faction", faction_id="faction.defender"
        )
        public = build_formal_frame_v2(session, catalog, view="public")
        assert session.world_view.tick == before == referee.tick == defender.tick == public.tick
        assert referee.scenario_id == resolved.scenario_id
        assert referee.map_identity["exact_ref"] == "map.weihai-local@2.0.0"
        assert all(item["faction_id"] == "faction.defender" for item in defender.entities)
        assert not public.entities
        assert not public.sensor_coverage and not public.weapon_coverage
        defender_payload = _frame_payload(defender)
        public_payload = _frame_payload(public)
        assert not defender.events and not public.events
        assert set(defender.environment) == {
            "declared",
            "weather_state",
            "zone_activation_state",
        }
        assert set(public.environment) == set(defender.environment)
        assert "unit.raid.usv.01" not in str(defender_payload)
        assert "faction.attacker" not in str(defender_payload)
        assert "faction.attacker" not in str(public_payload)
    finally:
        session.stop().close()


def test_live_records_replay_exactly_matches_authority_frames(tmp_path: Path) -> None:
    replay_path = tmp_path / "md-int-003-live.jsonl"
    assert (
        run_live_formal_v2(
            "MD-INT-003-EASY",
            seed=73,
            speed=1_000.0,
            max_ticks=3,
            replay_path=replay_path,
            block_on_finish=False,
            maintain_declared_motion=False,
            use_rule_agents=False,
        )
        == replay_path
    )
    resolved, catalog = compile_formal_scenario_v2("MD-INT-003-EASY")
    reader = ReplayReaderV2(
        replay_path,
        expected_resolved_hash=resolved.resolved_hash,
        expected_catalog_hash=resolved.catalog_hash,
        expected_model_registry_hash=resolved.model_registry_hash,
    )
    records = tuple(reader.records())
    assert tuple(record.tick for record in records) == (1, 2, 3)
    assert all(record.authority_receipt_hash is not None for record in records)

    session = create_formal_session_v2(
        "MD-INT-003-EASY", session_id="live.md-int-003-easy", seed=73
    )
    session.load().start()
    try:
        authority_frames = []
        for tick in range(3):
            session.step(operation_id=f"md3.viz.replay.tick.{tick}", expected_tick=tick)
            authority_frames.append(build_formal_frame_v2(session, catalog, view="referee"))
        assert [_frame_payload(record.frame) for record in records] == [
            _frame_payload(frame) for frame in authority_frames
        ]
    finally:
        session.stop().close()


def test_high_sea_checkpoint_restore_preserves_subsequent_rich_frames() -> None:
    continuous = create_formal_gateway_v2("MD-INT-003-HARD")
    session_id = "md3.viz.high-sea"
    continuous.create(session_id=session_id, seed=73)
    continuous.control(session_id, "load")
    continuous.control(session_id, "start")
    try:
        for tick in range(301):
            continuous.step(
                session_id,
                operation_id=f"md3.viz.high-sea.continuous.{tick}",
                expected_tick=tick,
            )
        checkpoint = continuous.checkpoint(session_id)
        high_sea = continuous.visualization(session_id, faction_id="faction.defender")
        assert high_sea.tick == 301
        assert high_sea.environment["declared"]["weather"] == "high_sea_state"

        expected_frames = []
        for tick in range(301, 303):
            continuous.step(
                session_id,
                operation_id=f"md3.viz.high-sea.continuous.{tick}",
                expected_tick=tick,
            )
            expected_frames.append(
                continuous.visualization(session_id, faction_id="faction.defender")
            )
    finally:
        continuous.close(session_id)

    restored = create_formal_gateway_v2("MD-INT-003-HARD")
    assert restored.restore(checkpoint) == session_id
    try:
        actual_frames = []
        for tick in range(301, 303):
            restored.step(
                session_id,
                operation_id=f"md3.viz.high-sea.restored.{tick}",
                expected_tick=tick,
            )
            actual_frames.append(restored.visualization(session_id, faction_id="faction.defender"))
        assert [_frame_payload(frame) for frame in actual_frames] == [
            _frame_payload(frame) for frame in expected_frames
        ]
    finally:
        restored.close(session_id)
