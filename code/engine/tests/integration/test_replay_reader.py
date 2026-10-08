"""Streaming, indexing, gzip, and diagnostic behavior for replay reading."""

import gzip
import tracemalloc
from pathlib import Path

import pytest
from openmdbench.replay import ReplayFormatError, ReplayReader, ReplayWriter
from openmdbench.visualization.schema import (
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
        entities=(),
        detections=DetectionSets(),
        scores=ScoreSets(blue=SideScore(total=0.5), red=SideScore(total=0.4)),
    )


def test_plain_index_and_gzip_seek_are_accurate(tmp_path: Path) -> None:
    plain = tmp_path / "plain.replay.jsonl"
    compressed = tmp_path / "compressed.replay.jsonl.gz"
    for path in (plain, compressed):
        with ReplayWriter(path, _metadata()) as writer:
            for timestamp in (2, 5, 9):
                writer.write_frame(_frame(timestamp))
        reader = ReplayReader(path)
        assert [frame.timestamp for frame in reader.frames()] == [2, 5, 9]
        assert reader.seek(5) == _frame(5)
        with pytest.raises(KeyError, match="not found"):
            reader.seek(6)
    assert Path(f"{plain}.idx").stat().st_size == 3 * 16
    assert not Path(f"{compressed}.idx").exists()


def test_reader_diagnoses_missing_metadata_corruption_and_regression(tmp_path: Path) -> None:
    missing = tmp_path / "missing.jsonl"
    missing.write_text(_frame(0).model_dump_json() + "\n", encoding="utf-8")
    with pytest.raises(ReplayFormatError, match="first replay record"):
        ReplayReader(missing)

    corrupt = tmp_path / "corrupt.jsonl"
    corrupt.write_text(_metadata().model_dump_json() + "\n{bad json}\n", encoding="utf-8")
    with pytest.raises(ReplayFormatError, match="line 2"):
        ReplayReader(corrupt)

    regression = tmp_path / "regression.jsonl.gz"
    with gzip.open(regression, "wt", encoding="utf-8") as stream:
        stream.write(_metadata().model_dump_json() + "\n")
        stream.write(_frame(2).model_dump_json() + "\n")
        stream.write(_frame(1).model_dump_json() + "\n")
    reader = ReplayReader(regression)
    with pytest.raises(ReplayFormatError, match="timestamp regression"):
        list(reader.frames())


def test_one_hundred_thousand_frames_stream_with_bounded_memory(tmp_path: Path) -> None:
    path = tmp_path / "large.replay.jsonl"
    with ReplayWriter(path, _metadata(), flush_every=1_000) as writer:
        for timestamp in range(100_000):
            writer.write_frame(_frame(timestamp))
    tracemalloc.start()
    reader = ReplayReader(path)
    count = sum(1 for _ in reader.frames())
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert count == 100_000
    assert peak < 12 * 1024 * 1024
