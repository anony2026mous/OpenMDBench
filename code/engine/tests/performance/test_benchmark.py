"""Performance requirement smoke and result completeness tests."""

from openmdbench.benchmark import (
    benchmark_concurrency,
    benchmark_logging,
    benchmark_replay,
    benchmark_scenario,
)


def test_cpu_rtf_and_memory_baseline() -> None:
    result = benchmark_scenario("MD-REC-001", 200)
    assert float(result["rtf"]) >= 1.0
    assert float(result["peak_rss_mb"]) <= 4_096.0


def test_concurrency_logging_and_replay_metrics() -> None:
    for sessions in (4, 8):
        concurrency = benchmark_concurrency(sessions, ticks=20)
        assert concurrency["sessions"] == sessions
        assert concurrency["aggregate_ticks_per_second"] > 0.0
    logging = benchmark_logging(20)
    assert logging["bytes_per_tick"] > 0.0
    replay = benchmark_replay(100)
    assert replay["frames"] == 100
    assert replay["frames_per_second"] > 0.0
