"""Rich live/replay visualization gates for the native MD-AD-002 V2 packages."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

from matplotlib.figure import Figure
from openmdbench.replay.v2 import ReplayReaderV2
from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
from openmdbench.schemas.core_v2 import VisualizationFrameV2
from openmdbench.sessions.formal_v2 import create_formal_gateway_v2, create_formal_session_v2
from openmdbench.visualization.formal_v2 import build_formal_frame_v2
from openmdbench.visualization.live_formal_v2 import (
    _LivePacerV2,
    _presentation_status,
    run_live_formal_v2,
)
from openmdbench.visualization.playback_v2 import run_replay_formal_v2
from openmdbench.visualization.renderer_v2 import (
    LivePresentationStatusV2,
    MatplotlibRendererV2,
    interpolate_frame_v2,
)
from openmdbench.world.factory_v2 import WorldStateV2

PUBLIC_IDS = ("MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD")


def test_live_pacer_separates_tick_deadlines_from_frame_sampling() -> None:
    pacer = _LivePacerV2(
        target_speed=10.0,
        render_fps_cap=5.0,
        started_wall_time_s=100.0,
        initial_sim_time_s=0.0,
    )
    assert pacer.next_tick_deadline(current_sim_time_s=0.0, tick_seconds=1.0) == 100.1
    assert pacer.render_due(wall_time_s=100.0)

    first = pacer.record_render(tick=1, sim_time_s=1.0, wall_time_s=101.0)
    assert first.rendered_fps == pytest.approx(1.0)
    assert first.skipped_ticks == 0
    assert not pacer.render_due(wall_time_s=100.25)

    second = pacer.record_render(tick=4, sim_time_s=4.0, wall_time_s=104.0)
    assert second.rendered_fps == pytest.approx(0.5)
    assert second.skipped_ticks == 2
    status = _presentation_status(second)
    assert status.target_speed == 10.0
    assert status.skipped_ticks == 2


def test_interactive_live_path_paints_when_authority_tick_is_slower_than_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A slow authority tick must not starve the GUI or replay writer."""

    import matplotlib.pyplot as plt

    rendered: list[tuple[int, LivePresentationStatusV2 | None]] = []
    original_update = MatplotlibRendererV2.update

    def capture_update(
        renderer: MatplotlibRendererV2,
        frame: VisualizationFrameV2,
        *,
        presentation_status: LivePresentationStatusV2 | None = None,
    ) -> None:
        rendered.append((frame.tick, presentation_status))
        original_update(renderer, frame, presentation_status=presentation_status)

    monkeypatch.setattr(matplotlib, "get_backend", lambda: "mock-interactive")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)
    monkeypatch.setattr(MatplotlibRendererV2, "update", capture_update)
    monkeypatch.setattr(
        WorldStateV2,
        "checkpoint",
        lambda _world: (_ for _ in ()).throw(AssertionError("replay must not checkpoint per tick")),
    )

    replay_path = tmp_path / "interactive-frame-drop.jsonl"
    assert (
        run_live_formal_v2(
            "MD-AD-002-EASY",
            seed=73,
            speed=10_000.0,
            render_fps=1.0,
            max_ticks=3,
            replay_path=replay_path,
            block_on_finish=True,
        )
        == replay_path
    )
    assert rendered[0][0] == 1
    assert rendered[-1][0] == 3
    assert all(item[1] is not None for item in rendered)
    final_status = rendered[-1][1]
    assert final_status is not None
    assert final_status.skipped_ticks >= 1
    resolved, _catalog = compile_formal_scenario_v2("MD-AD-002-EASY")
    reader = ReplayReaderV2(
        replay_path,
        expected_resolved_hash=resolved.resolved_hash,
        expected_catalog_hash=resolved.catalog_hash,
        expected_model_registry_hash=resolved.model_registry_hash,
    )
    records = tuple(reader.records())
    assert tuple(item.tick for item in records) == (1, 2, 3)
    assert all(item.authority_receipt_hash is not None for item in records)


def test_interactive_slow_motion_retains_interpolated_presentations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The accelerated-frame optimization must not remove slow-motion interpolation."""

    import matplotlib.pyplot as plt
    from matplotlib.backend_bases import FigureCanvasBase

    rendered_ticks: list[int] = []

    def capture_update(
        _renderer: MatplotlibRendererV2,
        frame: VisualizationFrameV2,
        *,
        presentation_status: LivePresentationStatusV2 | None = None,
    ) -> None:
        assert presentation_status is not None
        rendered_ticks.append(frame.tick)

    monkeypatch.setattr(matplotlib, "get_backend", lambda: "mock-interactive")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)
    monkeypatch.setattr(FigureCanvasBase, "start_event_loop", lambda _canvas, timeout=0: None)
    monkeypatch.setattr(MatplotlibRendererV2, "update", capture_update)

    assert (
        run_live_formal_v2(
            "MD-AD-002-EASY",
            seed=73,
            speed=0.5,
            max_ticks=2,
            block_on_finish=True,
        )
        is None
    )
    assert rendered_ticks == [1, 2, 2]


def _advance_isolated_session(public_id: str) -> tuple[str, tuple[int, ...], str]:
    session = create_formal_session_v2(
        public_id, session_id=f"parallel.{public_id.lower()}", seed=73
    )
    session.load().start()
    observed: list[int] = []
    try:
        for expected_tick in range(20):
            session.step(
                operation_id=f"parallel.{public_id}.{expected_tick}",
                expected_tick=expected_tick,
            )
            observed.append(session.world_view.tick)
        return session.session_id, tuple(observed), session.world_view.checkpoint().resolved_hash
    finally:
        session.stop().close()


@pytest.mark.parametrize("public_id", PUBLIC_IDS)
def test_rich_frame_contains_configured_map_layers_and_scenario_panels(public_id: str) -> None:
    resolved, catalog = compile_formal_scenario_v2(public_id)
    session = create_formal_session_v2(public_id, session_id=f"viz.{public_id}", seed=73)
    session.load().start()
    try:
        session.step(operation_id="tick.0", expected_tick=0)
        frame = build_formal_frame_v2(session, catalog, view="referee")
        assert frame.scenario_id == resolved.scenario_id
        assert frame.map_identity["exact_ref"] == "map.weihai-local@2.1.0"
        assert frame.map_identity["source_hash"].startswith("sha256:")
        assert len(frame.static_lines) == 134
        assert len(frame.static_polygons) >= 2
        assert {item["id"] for item in frame.zones} == {
            "zone.denial",
            "zone.spawn-east",
            "zone.spawn-northeast",
        }
        assert frame.sensor_coverage
        assert frame.weapon_coverage
        assert frame.targeting_links
        assert all("communication_status" in item for item in frame.entities)
        assert all("endurance_fraction" in item for item in frame.entities)
        assert frame.environment["declared"]
        assert frame.mission["duration_ticks"] == 1800
        assert tuple(item["wave_id"] for item in frame.mission["waves"]) == (
            "wave-1",
            "wave-2",
            "wave-3",
        )
        assert frame.mission["next_wave"] == "wave-2"
        assert "score.denial" in frame.scores_by_faction["scenario"]
        assert len(frame.entities) == 11
    finally:
        session.stop().close()


def test_gateway_faction_visualization_uses_rich_frame_without_truth_leak() -> None:
    gateway = create_formal_gateway_v2("MD-AD-002-MEDIUM")
    gateway.create(session_id="viz.gateway", seed=73)
    gateway.control("viz.gateway", "load")
    gateway.control("viz.gateway", "start")
    gateway.step("viz.gateway", operation_id="tick.0", expected_tick=0)
    frame = gateway.visualization("viz.gateway", faction_id="coalition.defender")
    assert frame.view == "faction"
    assert frame.view_faction_id == "coalition.defender"
    assert frame.static_lines
    assert all(item["faction_id"] == "coalition.defender" for item in frame.entities)
    gateway.close("viz.gateway")


def test_renderer_consumes_frame_only_and_retains_bounded_trajectories() -> None:
    _resolved, catalog = compile_formal_scenario_v2("MD-AD-002-MEDIUM")
    session = create_formal_session_v2("MD-AD-002-MEDIUM", session_id="viz.renderer", seed=73)
    session.load().start()
    figure = Figure(figsize=(12, 7))
    axes = figure.add_subplot(1, 1, 1)
    renderer = MatplotlibRendererV2(figure, axes, trajectory_points=2)
    presentation_status = LivePresentationStatusV2(
        target_speed=10.0,
        rendered_fps=8.5,
        render_fps_cap=12.0,
        skipped_ticks=2,
    )
    try:
        for tick in range(3):
            session.step(operation_id=f"tick.{tick}", expected_tick=tick)
            frame = build_formal_frame_v2(session, catalog, view="referee")
            renderer.update(
                frame,
                presentation_status=presentation_status if tick == 2 else None,
            )
        assert renderer._trajectories
        assert max(len(points) for points in renderer._trajectories.values()) <= 2
        assert len(renderer._trajectory_artists) == len(session.world_view.entities_stable())
        assert len(renderer._status_badges) == len(session.world_view.entities_stable())
        assert all(
            badge["battery_text"].get_text() == "100%"
            and len(badge["signal_bars"]) == 4
            and badge["sensor_text"].get_text() in {"+", "−"}
            for badge in renderer._status_badges.values()
        )
        assert renderer._entity_artists
        assert "simulation 10x" in axes.get_title()
        assert "target" not in axes.get_title()
        assert "actual" not in axes.get_title()
        assert "display 8.5/12 FPS" in axes.get_title()
    finally:
        renderer.close()
        session.stop().close()


def test_visualization_hides_destroyed_and_disabled_entities_but_retains_artifact_history() -> None:
    _resolved, catalog = compile_formal_scenario_v2("MD-AD-002-MEDIUM")
    session = create_formal_session_v2("MD-AD-002-MEDIUM", session_id="viz.unavailable", seed=73)
    session.load().start()
    figure = Figure(figsize=(12, 7))
    axes = figure.add_subplot(1, 1, 1)
    renderer = MatplotlibRendererV2(figure, axes)
    try:
        session.step(operation_id="tick.0", expected_tick=0)
        before = build_formal_frame_v2(session, catalog, view="referee")
        hidden_ids = (str(before.entities[0]["entity_id"]), str(before.entities[1]["entity_id"]))
        renderer.update(before)

        world = session._mutable_world()
        world._entities[hidden_ids[0]].state.lifecycle = "disabled"
        world._entities[hidden_ids[1]].state.lifecycle = "destroyed"
        after = build_formal_frame_v2(session, catalog, view="referee")
        renderer.update(after)

        rendered_ids = {str(item["entity_id"]) for item in after.entities}
        assert not rendered_ids.intersection(hidden_ids)
        assert all(not renderer._entity_artists[item].get_visible() for item in hidden_ids)
        assert all(not renderer._trajectory_artists[item].get_visible() for item in hidden_ids)
        assert all(
            not renderer._status_badges[item]["annotation"].get_visible() for item in hidden_ids
        )

        legacy_frame = before.model_copy(
            update={
                "entities": tuple(
                    {
                        **item,
                        "lifecycle_state": (
                            "destroyed"
                            if item["entity_id"] == hidden_ids[0]
                            else item["lifecycle_state"]
                        ),
                    }
                    for item in before.entities
                )
            }
        )
        renderer.update(legacy_frame)
        assert not renderer._entity_artists[hidden_ids[0]].get_visible()
    finally:
        renderer.close()
        session.stop().close()


def test_live_record_and_simulation_free_replay_render_exact_same_rich_frames(
    tmp_path: Path,
) -> None:
    path = tmp_path / "md-ad-002-medium-v2.jsonl"
    run_live_formal_v2(
        "MD-AD-002-MEDIUM",
        seed=73,
        speed=1_000.0,
        max_ticks=3,
        replay_path=path,
        block_on_finish=False,
    )
    resolved, _catalog = compile_formal_scenario_v2("MD-AD-002-MEDIUM")
    reader = ReplayReaderV2(
        path,
        expected_resolved_hash=resolved.resolved_hash,
        expected_catalog_hash=resolved.catalog_hash,
        expected_model_registry_hash=resolved.model_registry_hash,
    )
    records = tuple(reader.records())
    assert tuple(item.tick for item in records) == (1, 2, 3)
    assert all(item.frame.static_lines and item.frame.zones for item in records)
    assert records[0].frame.map_identity == records[-1].frame.map_identity
    initial_positions = {
        item["entity_id"]: item["position_m"] for item in records[0].frame.entities
    }
    final_positions = {item["entity_id"]: item["position_m"] for item in records[-1].frame.entities}
    assert any(final_positions[key] != value for key, value in initial_positions.items())
    run_replay_formal_v2(path, speed=1_000.0, block_on_finish=False)


def test_renderer_interpolates_motion_and_draws_authoritative_fire_and_links() -> None:
    _resolved, catalog = compile_formal_scenario_v2("MD-AD-002-MEDIUM")
    session = create_formal_session_v2("MD-AD-002-MEDIUM", session_id="viz.effects", seed=73)
    session.load().start()
    figure = Figure(figsize=(12, 7))
    axes = figure.add_subplot(1, 1, 1)
    renderer = MatplotlibRendererV2(figure, axes)
    try:
        session.step(operation_id="tick.0", expected_tick=0)
        first = build_formal_frame_v2(session, catalog, view="referee")
        session.step(operation_id="tick.1", expected_tick=1)
        second = build_formal_frame_v2(session, catalog, view="referee")
        middle = interpolate_frame_v2(first, second, 0.5)
        entity_id = str(second.entities[0]["entity_id"])
        first_position = next(
            item["position_m"] for item in first.entities if item["entity_id"] == entity_id
        )
        second_position = next(
            item["position_m"] for item in second.entities if item["entity_id"] == entity_id
        )
        middle_position = next(
            item["position_m"] for item in middle.entities if item["entity_id"] == entity_id
        )
        assert middle.sim_time_s == pytest.approx((first.sim_time_s + second.sim_time_s) / 2)
        assert middle_position[0] == pytest.approx((first_position[0] + second_position[0]) / 2)
        attacker, target = second.entities[:2]
        effects = second.model_copy(
            update={
                "communication_links": (
                    {
                        "start_m": attacker["position_m"],
                        "end_m": target["position_m"],
                        "status": "delivered",
                    },
                ),
                "events": (
                    {
                        "event_type": "weapon_fired",
                        "start_m": attacker["position_m"],
                        "end_m": target["position_m"],
                        "hit": True,
                    },
                ),
            }
        )
        renderer.update(effects)
        assert len(renderer._overlays) >= 4
    finally:
        renderer.close()
        session.stop().close()


def test_playback_import_graph_is_simulation_free() -> None:
    source = Path("openmdbench/visualization/playback_v2.py").read_text(encoding="utf-8")
    renderer_source = Path("openmdbench/visualization/renderer_v2.py").read_text(encoding="utf-8")
    forbidden_imports = (
        "openmdbench.sessions",
        "openmdbench.world",
        "openmdbench.scenarios",
        "openmdbench.catalog",
    )
    assert not any(token in source for token in forbidden_imports)
    assert not any(token in renderer_source for token in forbidden_imports)


def test_three_scenarios_advance_concurrently_without_tick_gaps_or_cross_talk() -> None:
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = tuple(executor.map(_advance_isolated_session, PUBLIC_IDS))
    assert len({item[0] for item in results}) == 3
    assert all(item[1] == tuple(range(1, 21)) for item in results)
    assert len({item[2] for item in results}) == 3
