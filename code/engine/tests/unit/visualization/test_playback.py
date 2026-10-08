"""Playback operation sequences, boundaries, speed, and immutability."""

from pathlib import Path

import pytest
from openmdbench.replay import ReplayReader, ReplayWriter
from openmdbench.visualization import PlaybackController
from openmdbench.visualization.schema import (
    DetectionSets,
    ReplayMetadata,
    ScoreSets,
    SideScore,
    VisualizationFrame,
)


def _controller(tmp_path: Path) -> tuple[PlaybackController, Path]:
    path = tmp_path / "playback.jsonl"
    metadata = ReplayMetadata(
        match_id="playback",
        scenario_id="MD-REC-001",
        seed=1,
        tick_seconds=1.0,
        coordinate_system="local_enu",
        engine_version="1.0",
        config_hash="sha256:abc",
    )
    with ReplayWriter(path, metadata) as writer:
        for timestamp in (0, 2, 5, 9):
            writer.write_frame(
                VisualizationFrame(
                    timestamp=timestamp,
                    entities=(),
                    detections=DetectionSets(),
                    scores=ScoreSets(
                        blue=SideScore(total=timestamp / 10.0), red=SideScore(total=0.0)
                    ),
                )
            )
    return PlaybackController(ReplayReader(path)), path


def test_operation_sequence_and_boundaries(tmp_path: Path) -> None:
    controller, _ = _controller(tmp_path)
    assert controller.timeline.current == 0
    assert controller.step_backward().timestamp == 0
    assert controller.step_forward().timestamp == 2
    assert controller.seek(9).timestamp == 9
    controller.play()
    assert not controller.playing
    assert controller.step_forward().timestamp == 9
    assert controller.jump_to_start().timestamp == 0
    assert controller.jump_to_end().timestamp == 9
    with pytest.raises(KeyError, match="not found"):
        controller.seek(3)


def test_speed_and_pause_use_frame_order_not_timestamp_mutation(tmp_path: Path) -> None:
    controller, path = _controller(tmp_path)
    original = path.read_bytes()
    controller.set_speed(2.0)
    controller.play()
    assert controller.advance(1.0).timestamp == 5
    controller.pause()
    assert controller.advance(100.0).timestamp == 5
    controller.play()
    assert controller.advance(0.5).timestamp == 9
    assert not controller.playing
    assert path.read_bytes() == original
    with pytest.raises(ValueError, match="positive"):
        controller.set_speed(0.0)
