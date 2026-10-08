"""Simulation-free playback of rich V2 visualization artifacts."""

from __future__ import annotations

import time
from pathlib import Path

from openmdbench.replay.v2 import ReplayHeaderV2, ReplayReaderV2
from openmdbench.visualization.renderer_v2 import MatplotlibRendererV2, interpolate_frame_v2


def run_replay_formal_v2(path: Path, *, speed: float = 20.0, block_on_finish: bool = True) -> None:
    """Render recorded authority frames without importing Session, World, or dynamics."""

    if speed <= 0.0:
        raise ValueError("replay speed must be positive")
    import matplotlib

    if block_on_finish and "agg" in matplotlib.get_backend().lower():
        try:
            matplotlib.use("TkAgg", force=True)
        except ImportError as exc:
            raise RuntimeError(
                "interactive replay requires a GUI Matplotlib backend (TkAgg)"
            ) from exc
    import matplotlib.pyplot as plt

    with path.open(encoding="utf-8") as stream:
        header = ReplayHeaderV2.model_validate_json(stream.readline())
    reader = ReplayReaderV2(
        path,
        expected_resolved_hash=header.resolved_hash,
        expected_catalog_hash=header.catalog_hash,
        expected_model_registry_hash=header.model_registry_hash,
    )
    figure, axes = plt.subplots(figsize=(16, 9))
    figure.subplots_adjust(right=0.76)
    if block_on_finish:
        plt.show(block=False)
    renderer = MatplotlibRendererV2(figure, axes)
    previous = None
    try:
        for record in reader.records():
            wall_tick_started = time.monotonic()
            if not plt.fignum_exists(figure.number):
                break
            if block_on_finish:
                subframes = 2 if previous is not None and speed <= 0.5 else 1
                for index in range(1, subframes + 1):
                    presentation = (
                        record.frame
                        if previous is None
                        else interpolate_frame_v2(previous, record.frame, index / subframes)
                    )
                    renderer.update(presentation)
                    figure.canvas.flush_events()
                    remaining = max(0.001, 1.0 / speed - (time.monotonic() - wall_tick_started))
                    figure.canvas.start_event_loop(remaining / (subframes - index + 1))
            else:
                renderer.update(record.frame)
                figure.canvas.draw()
            previous = record.frame
        if block_on_finish and plt.fignum_exists(figure.number):
            plt.show(block=True)
    finally:
        renderer.close()
        if not block_on_finish and plt.fignum_exists(figure.number):
            plt.close(figure)


__all__ = ["run_replay_formal_v2"]
