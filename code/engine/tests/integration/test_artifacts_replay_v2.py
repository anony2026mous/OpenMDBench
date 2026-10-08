"""RF-11 authoritative frame, live bus, and simulation-free replay contracts."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from openmdbench.replay.v2 import ReplayHeaderV2, ReplayReaderV2, ReplayRecordV2, ReplayWriterV2
from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2
from openmdbench.visualization.v2 import FrameBuilderV2, LiveFrameBusV2
from tests.integration.test_session_action_world_v2 import _session


def _record(session: SessionLifecycleV2, tick: int, checkpoint_hash: str) -> ReplayRecordV2:
    observation = session.world_view.observation(observer_faction_id="coalition.alpha")
    frame = FrameBuilderV2.from_observation(observation, scenario_id="scenario.generic-artifact")
    payload = {
        "schema_version": "replay-record@2.0",
        "tick": tick,
        "frame": frame.model_dump(mode="json"),
        "world_checkpoint_hash": checkpoint_hash,
        "event_receipt_hashes": (),
    }
    return ReplayRecordV2(
        tick=tick,
        frame=frame,
        world_checkpoint_hash=checkpoint_hash,
        record_hash=ReplayRecordV2.compute_hash(payload),
    )


def test_live_bus_is_bounded_drop_oldest_and_does_not_advance_session() -> None:
    session = _session("session.live-v2").load().start()
    bus = LiveFrameBusV2(capacity=2)
    for index in range(3):
        session.step(operation_id=f"live.tick.{index}", expected_tick=index)
        observation = session.world_view.observation(observer_faction_id="coalition.alpha")
        bus.publish(FrameBuilderV2.from_observation(observation, scenario_id="scenario.any"))
    before = session.world_view.tick
    frames = bus.drain()
    assert tuple(frame.tick for frame in frames) == (2, 3)
    assert bus.dropped_frames == 1
    assert session.world_view.tick == before
    session.stop().close()


def test_live_and_replay_frames_are_exact_and_replay_has_no_kernel_imports(
    tmp_path: Path,
) -> None:
    session = _session("session.replay-v2").load().start()
    session.step(operation_id="replay.tick.0", expected_tick=0)
    checkpoint = session.world_view.checkpoint()
    record = _record(session, 1, checkpoint.checkpoint_hash)
    header = ReplayHeaderV2(
        session_id=session.session_id,
        resolved_hash=session.resolved.resolved_hash,
        catalog_hash=session.catalog_hash,
        model_registry_hash=session.model_registry_hash,
        seed=session.seed,
    )
    path = tmp_path / "artifact.jsonl"
    writer = ReplayWriterV2(path, header=header)
    writer.write(record)
    assert not path.exists()
    writer.close()
    reader = ReplayReaderV2(
        path,
        expected_resolved_hash=header.resolved_hash,
        expected_catalog_hash=header.catalog_hash,
        expected_model_registry_hash=header.model_registry_hash,
    )
    assert reader.frame_index()[1] == record.frame
    source = inspect.getsource(__import__("openmdbench.replay.v2", fromlist=["ReplayReaderV2"]))
    for forbidden in (
        "from openmdbench.world",
        "from openmdbench.dynamics",
        "from openmdbench.sessions",
        "import random",
    ):
        assert forbidden not in source
    session.stop().close()


def test_replay_rejects_anchor_and_coordinated_record_tamper(tmp_path: Path) -> None:
    session = _session("session.replay-attack").load().start()
    session.step(operation_id="attack.tick.0", expected_tick=0)
    checkpoint = session.world_view.checkpoint()
    record = _record(session, 1, checkpoint.checkpoint_hash)
    header = ReplayHeaderV2(
        session_id=session.session_id,
        resolved_hash=session.resolved.resolved_hash,
        catalog_hash=session.catalog_hash,
        model_registry_hash=session.model_registry_hash,
        seed=session.seed,
    )
    path = tmp_path / "attack.jsonl"
    with ReplayWriterV2(path, header=header) as writer:
        writer.write(record)
    with pytest.raises(ValueError):
        ReplayReaderV2(
            path,
            expected_resolved_hash="sha256:" + "0" * 64,
            expected_catalog_hash=header.catalog_hash,
            expected_model_registry_hash=header.model_registry_hash,
        )
    raw = path.read_text().replace('"tick":1', '"tick":2', 1)
    path.write_text(raw)
    reader = ReplayReaderV2(
        path,
        expected_resolved_hash=header.resolved_hash,
        expected_catalog_hash=header.catalog_hash,
        expected_model_registry_hash=header.model_registry_hash,
    )
    with pytest.raises(ValueError):
        tuple(reader.records())
    session.stop().close()
