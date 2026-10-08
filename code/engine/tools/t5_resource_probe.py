"""Reproducible T5 resource sampler and bounded release probes.

Formal multi-hour execution is intentionally opt-in. Every report records the requested tier,
actual wall duration, host identity and raw samples; a smoke run is never labelled a soak.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import platform
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ResourceSample:
    monotonic_seconds: float
    rss_bytes: int | None
    fd_count: int | None
    thread_count: int | None
    child_process_count: int | None


def sample_process(pid: int | None = None) -> ResourceSample:
    process_id = os.getpid() if pid is None else pid
    descendants = _process_tree(process_id)
    rss_values = tuple(value for child in descendants if (value := _rss(child)) is not None)
    fd_values = tuple(value for child in descendants if (value := _fd_count(child)) is not None)
    thread_values = tuple(
        value for child in descendants if (value := _thread_count(child)) is not None
    )
    return ResourceSample(
        monotonic_seconds=time.monotonic(),
        rss_bytes=sum(rss_values) if rss_values else None,
        fd_count=sum(fd_values) if fd_values else None,
        thread_count=sum(thread_values) if thread_values else None,
        child_process_count=max(0, len(descendants) - 1),
    )


def _direct_children(pid: int) -> tuple[int, ...]:
    try:
        payload = (Path("/proc") / str(pid) / "task" / str(pid) / "children").read_text()
        return tuple(int(value) for value in payload.split())
    except (FileNotFoundError, PermissionError, ValueError):
        return ()


def _process_tree(pid: int) -> tuple[int, ...]:
    result: list[int] = []
    pending = [pid]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        result.append(current)
        pending.extend(_direct_children(current))
    return tuple(result)


def _rss(pid: int) -> int | None:
    try:
        fields = (Path("/proc") / str(pid) / "statm").read_text(encoding="utf-8").split()
        return int(fields[1]) * os.sysconf("SC_PAGE_SIZE")
    except (FileNotFoundError, PermissionError, IndexError, ValueError):
        return None


def _fd_count(pid: int) -> int | None:
    try:
        return len(tuple((Path("/proc") / str(pid) / "fd").iterdir()))
    except (FileNotFoundError, PermissionError):
        return None


def _thread_count(pid: int) -> int | None:
    try:
        for line in (Path("/proc") / str(pid) / "status").read_text().splitlines():
            if line.startswith("Threads:"):
                return int(line.split(":", 1)[1])
    except (FileNotFoundError, PermissionError, ValueError):
        return None
    return None


class ResourceSampler:
    def __init__(self, *, pid: int | None = None, interval_seconds: float = 1.0) -> None:
        if interval_seconds <= 0.0:
            raise ValueError("sample interval must be positive")
        self.pid = os.getpid() if pid is None else pid
        self.interval_seconds = interval_seconds
        self.samples: list[ResourceSample] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _sample(self) -> None:
        while not self._stop.is_set():
            item = sample_process(self.pid)
            self.samples.append(item)
            self._stop.wait(self.interval_seconds)

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("resource sampler already started")
        self._thread = threading.Thread(
            target=self._sample, name="t5-resource-sampler", daemon=True
        )
        self._thread.start()

    def stop(self) -> tuple[ResourceSample, ...]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval_seconds * 2.0))
        self.samples.append(sample_process(self.pid))
        return tuple(self.samples)


def summarize(samples: tuple[ResourceSample, ...]) -> dict[str, Any]:
    def values(name: str) -> list[int]:
        return [int(value) for item in samples if (value := getattr(item, name)) is not None]

    result: dict[str, Any] = {"sample_count": len(samples)}
    for field in ("rss_bytes", "fd_count", "thread_count", "child_process_count"):
        observed = values(field)
        result[field] = {
            "first": observed[0] if observed else None,
            "last": observed[-1] if observed else None,
            "minimum": min(observed) if observed else None,
            "maximum": max(observed) if observed else None,
            "growth": observed[-1] - observed[0] if observed else None,
        }
    stable = samples[max(0, len(samples) // 10) : max(1, len(samples) - len(samples) // 10)]
    rss_points = tuple(
        (item.monotonic_seconds, item.rss_bytes) for item in stable if item.rss_bytes is not None
    )
    result["rss_slope_bytes_per_hour"] = _slope_per_hour(rss_points)
    return result


def _slope_per_hour(points: tuple[tuple[float, int], ...]) -> float | None:
    if len(points) < 2:
        return None
    origin = points[0][0]
    xs = tuple(item[0] - origin for item in points)
    ys = tuple(float(item[1]) for item in points)
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    denominator = sum((value - mean_x) ** 2 for value in xs)
    if denominator <= 0.0:
        return None
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    return covariance / denominator * 3600.0


def run_measured(
    label: str, operation: Callable[[], dict[str, Any]], *, interval: float
) -> dict[str, Any]:
    sampler = ResourceSampler(interval_seconds=interval)
    started = time.perf_counter()
    sampler.start()
    error: dict[str, str] | None = None
    payload: dict[str, Any] = {}
    try:
        payload = operation()
    except Exception as caught:  # evidence must record failures rather than hide them
        error = {"type": type(caught).__name__, "message": str(caught)}
    samples = sampler.stop()
    return {
        "label": label,
        "elapsed_seconds": time.perf_counter() - started,
        "result": payload,
        "error": error,
        "resources": summarize(samples),
        "samples": [asdict(item) for item in samples],
    }


def run_command(command: list[str]) -> dict[str, Any]:
    environment = dict(os.environ)
    environment.setdefault("MPLCONFIGDIR", "/tmp/openmdbench-mpl")
    completed = subprocess.run(
        command, capture_output=True, text=True, check=False, env=environment
    )
    parsed: Any = None
    decoder = json.JSONDecoder()
    for index, character in enumerate(completed.stdout):
        if character != "{":
            continue
        with contextlib.suppress(json.JSONDecodeError):
            candidate, end = decoder.raw_decode(completed.stdout[index:])
            if not completed.stdout[index + end :].strip():
                parsed = candidate
                break
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4_000:],
        "stderr_tail": completed.stderr[-4_000:],
        "json_output": parsed,
    }


def extract_workload_metrics(value: Any) -> dict[str, list[float]]:
    """Extract only declared numeric workload counters; absent counters remain absent."""
    aliases = {
        "ticks_per_second": "tick_per_second",
        "aggregate_ticks_per_second": "tick_per_second",
        "rtf": "rtf",
        "queue_depth": "queue_depth",
        "cache_entries": "cache_entries",
        "frame_drops": "frame_drops",
        "dropped_frames": "frame_drops",
    }
    result: dict[str, list[float]] = {}

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                target = aliases.get(str(key))
                if (
                    target is not None
                    and isinstance(child, (int, float))
                    and not isinstance(child, bool)
                ):
                    result.setdefault(target, []).append(float(child))
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return result


def source_tree_hash() -> str:
    digest = hashlib.sha256()
    files = tuple(
        sorted(
            (
                *Path("openmdbench").rglob("*.py"),
                *Path("tools").glob("t5_*.py"),
                *Path("scenarios/synthetic").rglob("*.yaml"),
            ),
            key=lambda path: path.as_posix(),
        )
    )
    for path in files:
        digest.update(path.as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=("smoke", "short", "formal"), required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--max-rss-bytes", type=int, default=4 * 1024**3)
    parser.add_argument("--max-rss-slope-bytes-per-hour", type=float, default=64 * 1024**2)
    parser.add_argument("--min-rtf", type=float, default=1.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.command:
        parser.error("a command after -- is required")
    command = args.command[1:] if args.command[0] == "--" else args.command
    measured = run_measured(args.label, lambda: run_command(command), interval=args.interval)
    workload_metrics = extract_workload_metrics(measured["result"].get("json_output"))
    resources = measured["resources"]
    rtf_values = workload_metrics.get("rtf", ())
    gates = {
        "command_succeeded": measured["error"] is None and measured["result"]["returncode"] == 0,
        "peak_rss_within_limit": resources["rss_bytes"]["maximum"] is not None
        and resources["rss_bytes"]["maximum"] <= args.max_rss_bytes,
        "rss_slope_within_limit": resources["rss_slope_bytes_per_hour"] is not None
        and resources["rss_slope_bytes_per_hour"] <= args.max_rss_slope_bytes_per_hour,
        "fd_returned_to_baseline": resources["fd_count"]["last"] <= resources["fd_count"]["first"],
        "threads_returned_to_baseline": resources["thread_count"]["last"]
        <= resources["thread_count"]["first"],
        "children_returned_to_baseline": resources["child_process_count"]["last"] == 0,
        "rtf_met": bool(rtf_values) and min(rtf_values) >= args.min_rtf,
    }
    report = {
        "schema_version": "t5-resource-report@1.0",
        "qualification": args.tier,
        "is_formal_soak": args.tier == "formal",
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
        },
        "source_tree_hash": source_tree_hash(),
        "probe": measured,
        "workload_metrics": workload_metrics,
        "missing_workload_metrics": sorted(
            {"tick_per_second", "rtf", "queue_depth", "cache_entries", "frame_drops"}
            - set(workload_metrics)
        ),
        "thresholds": {
            "max_rss_bytes": args.max_rss_bytes,
            "max_rss_slope_bytes_per_hour": args.max_rss_slope_bytes_per_hour,
            "min_rtf": args.min_rtf,
        },
        "gates": gates,
        "passed": all(gates.values()),
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
