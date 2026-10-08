"""Every persisted match writes a complete, directly readable authority log."""

from pathlib import Path

from openmdbench.api.sessions import SessionStore
from openmdbench.replay import ReplayReader
from openmdbench.scenarios.loader import load_scenario_id


def test_three_matches_are_saved_from_creation_through_close(tmp_path: Path) -> None:
    store = SessionStore(replay_dir=tmp_path, audit_dir=tmp_path)
    session_ids: list[str] = []
    for seed in (3, 5, 7):
        session = store.create("MD-REC-001", seed)
        session_ids.append(session.session_id)
        store.step(session, (1.0, 45.0))
        store.step(session, (2.0, 90.0))
        store.delete(session.session_id)

    assert len(tuple(tmp_path.glob("*.replay.jsonl"))) == 3
    for session_id, seed in zip(session_ids, (3, 5, 7), strict=True):
        reader = ReplayReader(tmp_path / f"{session_id}.replay.jsonl")
        frames = list(reader.frames())
        assert reader.metadata.match_id == session_id
        assert reader.metadata.seed == seed
        assert [frame.timestamp for frame in frames] == [0, 1, 2]
        assert frames[0].actions == ()
        assert frames[1].actions[0]["type"] == "kinematic"
        assert {entity.id for entity in frames[0].entities} == {
            entity.id for entity in load_scenario_id("MD-REC-001").entities
        }
        assert frames[-1].entities[0].position != frames[0].entities[0].position
        assert "reward" in frames[-1].scores.blue.metrics


def test_match_log_format_document_is_present() -> None:
    document = Path(__file__).parents[2] / "docs/match_log_format.md"
    content = document.read_text(encoding="utf-8")
    for required in ("ReplayMetadata", "VisualizationFrame", "每 tick", "审计日志"):
        assert required in content
