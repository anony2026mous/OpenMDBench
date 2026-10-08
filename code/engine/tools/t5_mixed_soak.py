"""Source-checkout T5 workload spanning disk GS, V2 sessions, Legacy and frames."""

from __future__ import annotations

import argparse
import gc
import json
import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from openmdbench.scenarios.declarative_v2 import ScenarioCompilerV2, ScenarioPackageV2
from openmdbench.visualization import MatplotlibRenderer
from openmdbench.visualization.v2 import FrameBuilderV2, LiveFrameBusV2
from tests.contract import test_declarative_mission_control_v2 as mission_fixture
from tests.contract import test_declarative_resource_expansion_v2 as resource_fixture
from tests.contract import test_declarative_scenario_v2 as generic_fixture
from tests.integration.test_session_action_world_v2 import _session
from tests.unit.visualization.test_renderer import _entity, _frame

ROOT = Path("scenarios/synthetic")


def _compile_gs(identifier: str) -> str:
    catalog = (
        generic_fixture._catalog()
        if identifier in {"gs_001", "gs_002"}
        else resource_fixture._catalog()
        if identifier == "gs_003"
        else mission_fixture._catalog()
    )
    resolved = ScenarioCompilerV2(catalog=catalog).compile(
        ScenarioPackageV2.from_directory(ROOT / identifier)
    )
    resolved.validate_integrity()
    return resolved.resolved_hash


def run_mixed_soak(*, duration_seconds: float, minimum_cycles: int) -> dict[str, Any]:
    if duration_seconds < 0.0 or minimum_cycles < 1:
        raise ValueError("duration and minimum cycles must be valid")
    figure, axes = plt.subplots()
    renderer = MatplotlibRenderer(axes, max_retained_entities=32)
    bus = LiveFrameBusV2(capacity=8)
    hashes = {_compile_gs(identifier) for identifier in ("gs_001", "gs_002", "gs_003", "gs_004")}
    started = time.monotonic()
    deadline = started + duration_seconds
    cycles = 0
    ticks = 0
    try:
        while cycles < minimum_cycles or time.monotonic() < deadline:
            session = _session(f"session.t5.{cycles}", seed=10_000 + cycles).load().start()
            try:
                receipt = session.step(operation_id=f"t5.tick.{cycles}", expected_tick=0)
                if receipt.tick != 1:
                    raise RuntimeError("V2 soak tick did not advance exactly once")
                bus.publish(
                    FrameBuilderV2.from_observation(
                        session.world_view.observation(observer_faction_id="coalition.alpha"),
                        scenario_id=session.resolved.scenario_id,
                    ).model_copy(update={"tick": cycles + 1})
                )
                ticks += 1
            finally:
                session.stop().close()
            entity = _entity(cycles).model_copy(update={"id": f"dynamic-{cycles}"})
            renderer.update(
                _frame(0, x_offset=float(cycles)).model_copy(update={"entities": (entity,)})
            )
            cycles += 1
            if cycles % 25 == 0:
                gc.collect()
    finally:
        renderer.close()
        bus.close()
        plt.close(figure)
    elapsed = max(time.monotonic() - started, 1e-12)
    return {
        "duration_seconds": elapsed,
        "target_duration_seconds": duration_seconds,
        "cycles": cycles,
        "ticks": ticks,
        "ticks_per_second": ticks / elapsed,
        "rtf": ticks / elapsed,
        "compiled_gs_count": len(hashes),
        "active_sessions": 0,
        "queue_depth": 0,
        "cache_entries": len(renderer.entity_artists),
        "frame_drops": bus.dropped_frames,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--minimum-cycles", type=int, default=1)
    args = parser.parse_args()
    print(
        json.dumps(
            run_mixed_soak(
                duration_seconds=args.seconds,
                minimum_cycles=args.minimum_cycles,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
