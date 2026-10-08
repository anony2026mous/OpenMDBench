"""Round-trip, ordering, flush, and interruption behavior for replay writing."""

from pathlib import Path

import pytest
from openmdbench.replay import ReplayWriter
from openmdbench.visualization.schema import (
    REPLAY_RECORD_ADAPTER,
    DetectionSets,
    ReplayMetadata,
    ScoreSets,
    SideScore,
    VisualizationFrame,
)


def _metadata() -> ReplayMetadata:
    return ReplayMetadata(
        match_id="match-1",
        scenario_id="MD-REC-001",
        seed=7,
        tick_seconds=1.0,
        coordinate_system="local_enu",
        engine_version="1.0.0",
        config_hash="sha256:abc",
    )


def _frame(timestamp: int) -> VisualizationFrame:
    return VisualizationFrame(
        timestamp=timestamp,
        actions=({"type": "hold_position"},),
        entities=(),
        detections=DetectionSets(),
        events=(),
        scores=ScoreSets(blue=SideScore(total=0.5), red=SideScore(total=0.4)),
    )


def test_one_thousand_frames_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "match.replay.jsonl"
    with ReplayWriter(path, _metadata(), flush_every=32) as writer:
        for timestamp in range(1_000):
            writer.write_frame(_frame(timestamp))
    lines = path.read_text(encoding="utf-8").splitlines()
    records = [REPLAY_RECORD_ADAPTER.validate_json(line) for line in lines]
    assert len(records) == 1_001
    assert records[0] == _metadata()
    assert records[-1] == _frame(999)


def test_flushed_complete_lines_survive_interruption(tmp_path: Path) -> None:
    path = tmp_path / "interrupted.replay.jsonl"
    writer = ReplayWriter(path, _metadata())
    writer.write_frame(_frame(0))
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert all(REPLAY_RECORD_ADAPTER.validate_json(line) for line in lines)
    writer.close()


def test_writer_rejects_time_regression_and_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "ordered.replay.jsonl"
    with ReplayWriter(path, _metadata()) as writer:
        writer.write_frame(_frame(2))
        with pytest.raises(ValueError, match="strictly increasing"):
            writer.write_frame(_frame(2))
    with pytest.raises(FileExistsError):
        ReplayWriter(path, _metadata())
