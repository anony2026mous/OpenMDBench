"""MD3-10 public system determinism and authority-boundary contracts."""

from __future__ import annotations

from pathlib import Path

import pytest
from openmdbench.replay.v2 import ReplayReaderV2
from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
from openmdbench.schemas.core_v2 import VisualizationFrameV2
from openmdbench.sessions.formal_v2 import create_formal_gateway_v2, create_formal_session_v2
from openmdbench.sessions.lifecycle_v2 import (
    RunnerModeV2,
    SessionCheckpointV2,
    SessionFailureV2,
)
from openmdbench.visualization.formal_v2 import build_formal_frame_v2
from openmdbench.visualization.live_formal_v2 import run_live_formal_v2
from openmdbench.world.factory_v2 import FactoryErrorV2

PUBLIC_IDS = ("MD-INT-003-EASY", "MD-INT-003-MEDIUM", "MD-INT-003-HARD")
GENERIC_PRODUCTION_ROOTS = (
    "api",
    "combat",
    "dynamics",
    "missions",
    "replay",
    "sessions",
    "sdk",
    "systems",
    "visualization",
    "world",
)


def _authority_frame_payload(frame: VisualizationFrameV2) -> dict[str, object]:
    """Compare simulation evidence while retaining per-session traceability in the DTO."""

    payload = frame.model_dump(mode="json")
    payload.pop("session_id")
    return payload


def _frames(
    public_id: str,
    *,
    session_id: str,
    seed: int,
    runner_mode: RunnerModeV2 = RunnerModeV2.LOCKSTEP,
    polling_reads: int = 0,
    operation_prefix: str = "md3.det.tick",
) -> tuple[tuple[dict[str, object], ...], SessionCheckpointV2]:
    _resolved, catalog = compile_formal_scenario_v2(public_id)
    session = create_formal_session_v2(
        public_id,
        session_id=session_id,
        seed=seed,
        runner_mode=runner_mode,
    )
    session.load().start()
    try:
        frames: list[dict[str, object]] = []
        for tick in range(3):
            for _ in range(polling_reads):
                assert (
                    session.world_view.observation(observer_faction_id="faction.defender").tick
                    == tick
                )
            assert session.world_view.tick == tick
            session.step(operation_id=f"{operation_prefix}.{tick}", expected_tick=tick)
            frames.append(
                _authority_frame_payload(build_formal_frame_v2(session, catalog, view="referee"))
            )
        return tuple(frames), session.checkpoint()
    finally:
        session.stop().close()


@pytest.mark.parametrize("public_id", PUBLIC_IDS)
def test_same_seed_timeline_is_session_id_independent_across_three_levels(
    public_id: str,
) -> None:
    first, first_checkpoint = _frames(
        public_id,
        session_id="md3.det.first",
        seed=73,
    )
    second, second_checkpoint = _frames(
        public_id,
        session_id="md3.det.second",
        seed=73,
    )
    assert first == second
    assert first_checkpoint.seed == second_checkpoint.seed == 73
    assert first_checkpoint.world_checkpoint["seed"] == second_checkpoint.world_checkpoint["seed"]


def test_seed_and_runner_mode_are_explicit_and_do_not_change_authority_timeline() -> None:
    lockstep, seed_73 = _frames(
        "MD-INT-003-EASY",
        session_id="md3.det.lockstep",
        seed=73,
        runner_mode=RunnerModeV2.LOCKSTEP,
    )
    continuous, same_seed = _frames(
        "MD-INT-003-EASY",
        session_id="md3.det.continuous",
        seed=73,
        runner_mode=RunnerModeV2.CONTINUOUS,
    )
    _other_frames, different_seed = _frames(
        "MD-INT-003-EASY",
        session_id="md3.det.lockstep",
        seed=74,
    )
    assert lockstep == continuous
    assert seed_73.seed == same_seed.seed == 73
    assert different_seed.seed == 74
    assert different_seed.checkpoint_hash != seed_73.checkpoint_hash
    assert different_seed.world_checkpoint["seed"] == 74


def test_speed_renderer_and_polling_do_not_change_authority_frames(tmp_path: Path) -> None:
    resolved, _catalog = compile_formal_scenario_v2("MD-INT-003-EASY")
    replay_paths = []
    for speed in (1.0, 10.0, 1_000.0):
        path = tmp_path / f"live-{speed}.jsonl"
        assert (
            run_live_formal_v2(
                "MD-INT-003-EASY",
                seed=73,
                speed=speed,
                max_ticks=3,
                replay_path=path,
                block_on_finish=False,
                maintain_declared_motion=False,
                use_rule_agents=False,
            )
            == path
        )
        replay_paths.append(path)
    recorded = [
        [
            _authority_frame_payload(record.frame)
            for record in ReplayReaderV2(
                path,
                expected_resolved_hash=resolved.resolved_hash,
                expected_catalog_hash=resolved.catalog_hash,
                expected_model_registry_hash=resolved.model_registry_hash,
            ).records()
        ]
        for path in replay_paths
    ]
    unrendered, _checkpoint = _frames(
        "MD-INT-003-EASY",
        session_id="live.md-int-003-easy",
        seed=73,
        polling_reads=3,
        operation_prefix="live.tick",
    )
    assert recorded[0] == recorded[1] == recorded[2] == list(unrendered)


def test_all_formal_views_filter_by_authority_without_advancing() -> None:
    _resolved, catalog = compile_formal_scenario_v2("MD-INT-003-EASY")
    session = create_formal_session_v2("MD-INT-003-EASY", session_id="md3.det.views", seed=73)
    session.load().start()
    try:
        session.step(operation_id="md3.det.views.0", expected_tick=0)
        before = session.world_view.tick
        referee = build_formal_frame_v2(session, catalog, view="referee")
        defender = build_formal_frame_v2(
            session, catalog, view="faction", faction_id="faction.defender"
        )
        attacker = build_formal_frame_v2(
            session, catalog, view="faction", faction_id="faction.attacker"
        )
        public = build_formal_frame_v2(session, catalog, view="public")
        assert session.world_view.tick == before == 1
        assert {item["faction_id"] for item in referee.entities} == {
            "faction.defender",
            "faction.attacker",
        }
        assert {item["faction_id"] for item in defender.entities} == {"faction.defender"}
        assert {item["faction_id"] for item in attacker.entities} == {"faction.attacker"}
        assert not public.entities
        for restricted in (defender, attacker, public):
            assert not restricted.events
            assert set(restricted.environment) == {
                "declared",
                "weather_state",
                "zone_activation_state",
            }
        assert "faction.attacker" not in str(defender.model_dump(mode="json"))
        assert "faction.defender" not in str(attacker.model_dump(mode="json"))
    finally:
        session.stop().close()


def test_forged_session_checkpoint_fails_closed_without_advancing_original_session() -> None:
    gateway = create_formal_gateway_v2("MD-INT-003-EASY")
    session = create_formal_session_v2("MD-INT-003-EASY", session_id="md3.det.forgery", seed=73)
    gateway.attach(session)
    session.load().start()
    try:
        session.step(operation_id="md3.det.forgery.0", expected_tick=0)
        checkpoint = session.checkpoint()
        payload = checkpoint.model_dump(mode="json")
        payload["seed"] = 74
        payload["checkpoint_hash"] = SessionCheckpointV2.compute_hash(payload)
        forged = SessionCheckpointV2.model_validate(payload)
        with pytest.raises((SessionFailureV2, FactoryErrorV2)):
            gateway.restore(forged)
        assert session.world_view.tick == 1
        assert gateway.session_ids == (session.session_id,)
    finally:
        gateway.close(session.session_id)


def test_generic_production_modules_contain_no_md_int_003_or_fixed_side_fixture_branch() -> None:
    root = Path("openmdbench")
    forbidden = (
        "MD-INT-003",
        "MD_INT_003",
        "red-usv-1",
        "red-usv-2",
        "red-usv-3",
        "blue-usv-1",
        "blue-usv-2",
        "blue-usv-3",
        "scenario_id ==",
    )
    for directory in GENERIC_PRODUCTION_ROOTS:
        for path in (root / directory).rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert all(token not in source for token in forbidden), path
