"""Fast correctness gates for the separately runnable T5 resource sampler."""

from __future__ import annotations

import os
import subprocess
import sys
import time

import pytest
from tools.t5_mixed_soak import run_mixed_soak
from tools.t5_resource_probe import (
    ResourceSampler,
    extract_workload_metrics,
    run_measured,
    sample_process,
    source_tree_hash,
    summarize,
)


def test_process_sample_reports_real_proc_resources_without_fabricated_defaults() -> None:
    sample = sample_process()
    assert sample.monotonic_seconds > 0.0
    if os.path.isdir("/proc/self"):
        assert sample.rss_bytes is not None and sample.rss_bytes > 0
        assert sample.fd_count is not None and sample.fd_count > 0
        assert sample.thread_count is not None and sample.thread_count > 0
        assert sample.child_process_count is not None and sample.child_process_count >= 0
    assert source_tree_hash().startswith("sha256:")
    assert len(source_tree_hash()) == 71


def test_sampler_records_first_last_peak_and_actual_growth() -> None:
    sampler = ResourceSampler(interval_seconds=0.001)
    sampler.start()
    time.sleep(0.005)
    samples = sampler.stop()
    summary = summarize(samples)
    assert summary["sample_count"] >= 2
    for name in ("rss_bytes", "fd_count", "thread_count", "child_process_count"):
        values = summary[name]
        if values["first"] is not None:
            assert values["minimum"] <= values["first"] <= values["maximum"]
            assert values["growth"] == values["last"] - values["first"]


def test_process_sample_aggregates_owned_child_process_resources() -> None:
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1)"])
    try:
        sample = sample_process()
        assert sample.child_process_count is not None and sample.child_process_count >= 1
        assert sample.rss_bytes is not None and sample.rss_bytes > 0
    finally:
        child.terminate()
        child.wait(timeout=2.0)


def test_measured_failure_is_recorded_and_not_reported_as_success() -> None:
    def fail() -> dict[str, object]:
        raise RuntimeError("intentional probe failure")

    report = run_measured("failure", fail, interval=0.001)
    assert report["result"] == {}
    assert report["error"] == {
        "type": "RuntimeError",
        "message": "intentional probe failure",
    }
    assert report["resources"]["sample_count"] >= 2


def test_invalid_sampling_interval_is_rejected() -> None:
    with pytest.raises(ValueError):
        ResourceSampler(interval_seconds=0.0)


def test_workload_counters_are_extracted_only_from_real_numeric_output() -> None:
    output = {
        "ticks_per_second": 12.5,
        "rtf": 3.0,
        "resources": {"queue_depth": 4, "cache_entries": 9, "frame_drops": 2},
        "fabricated": {"frame_drops": "zero"},
    }
    assert extract_workload_metrics(output) == {
        "tick_per_second": [12.5],
        "rtf": [3.0],
        "queue_depth": [4.0],
        "cache_entries": [9.0],
        "frame_drops": [2.0],
    }


def test_mixed_workload_compiles_all_disk_gs_and_releases_owned_resources() -> None:
    result = run_mixed_soak(duration_seconds=0.0, minimum_cycles=2)
    assert result["compiled_gs_count"] == 4
    assert result["cycles"] == result["ticks"] == 2
    assert result["active_sessions"] == 0
    assert result["queue_depth"] == result["cache_entries"] == 0
    assert result["ticks_per_second"] > 0.0
