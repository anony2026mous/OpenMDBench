"""One-command release self-test and machine-readable report generation."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess  # nosec B404
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from openmdbench import __version__
from openmdbench.benchmark import run_benchmark_suite


def configuration_hash(root: Path) -> str:
    """Hash release configuration and all authoritative scenario files."""
    digest = hashlib.sha256()
    paths = [root / "pyproject.toml", *sorted((root / "scenarios").rglob("*.yaml"))]
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return f"sha256:{digest.hexdigest()}"


def _run(command: list[str], root: Path, matplotlib_config: Path) -> tuple[int, str, float]:
    started = time.perf_counter()
    completed = subprocess.run(  # noqa: S603  # nosec B603
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "MPLCONFIGDIR": str(matplotlib_config),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        },
    )
    output = completed.stdout + completed.stderr
    return completed.returncode, output, time.perf_counter() - started


def run_selftest(root: str | Path = ".", report_dir: str | Path = "reports") -> dict[str, Any]:
    """Run static, typed, full functional, coverage and performance gates."""
    project = Path(root).resolve()
    reports = project / report_dir
    reports.mkdir(parents=True, exist_ok=True)
    python = str(project / ".venv/bin/python")
    log_path = reports / f"selftest_{__version__}.log"
    coverage_path = reports / f"coverage_{__version__}.json"
    checks: list[dict[str, Any]] = []
    log_sections: list[str] = []
    started = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="openmdbench-selftest-") as temporary:
        matplotlib_config = Path(temporary) / "matplotlib"
        matplotlib_config.mkdir()
        commands = (
            ("ruff", [python, "-m", "ruff", "check", "openmdbench", "tests"]),
            ("mypy", [python, "-m", "mypy"]),
            ("coverage_erase", [python, "-m", "coverage", "erase"]),
            (
                "pytest",
                [
                    python,
                    "-m",
                    "coverage",
                    "run",
                    "--source=openmdbench",
                    "-m",
                    "pytest",
                ],
            ),
            (
                "coverage_json",
                [python, "-m", "coverage", "json", "-o", str(coverage_path)],
            ),
        )
        for name, command in commands:
            code, output, duration = _run(command, project, matplotlib_config)
            checks.append({"name": name, "passed": code == 0, "duration_seconds": duration})
            log_sections.append(f"## {name}\n{output}")
            if code != 0:
                break

        pytest_output = next(
            (section for section in log_sections if section.startswith("## pytest\n")), ""
        )
        counts = {
            label: sum(int(value) for value in re.findall(rf"(\d+) {label}", pytest_output))
            for label in ("passed", "failed", "error", "skipped")
        }
        test_counts = {
            "tests": sum(counts.values()),
            "failures": counts["failed"],
            "errors": counts["error"],
            "skipped": counts["skipped"],
        }

    coverage = 0.0
    if coverage_path.exists():
        coverage = float(json.loads(coverage_path.read_text())["totals"]["percent_covered"])
    performance = run_benchmark_suite() if all(check["passed"] for check in checks) else {}
    performance_path = reports / f"performance_{__version__}.json"
    performance_path.write_text(json.dumps(performance, indent=2, sort_keys=True) + "\n")
    log_path.write_text("\n\n".join(log_sections), encoding="utf-8")

    result = {
        "version": __version__,
        "passed": all(check["passed"] for check in checks) and test_counts["skipped"] == 0,
        "system": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "processor": platform.processor() or platform.machine(),
        },
        "configuration_hash": configuration_hash(project),
        "checks": checks,
        "test_counts": test_counts,
        "coverage_percent": coverage,
        "performance": performance,
        "duration_seconds": time.perf_counter() - started,
        "failure_log": str(log_path.relative_to(project)),
    }
    json_path = reports / f"selftest_{__version__}.json"
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path = reports / f"selftest_{__version__}.md"
    markdown_path.write_text(
        "\n".join(
            (
                f"# OpenMDBench {__version__} 自测试",
                "",
                f"- 结果：{'通过' if result['passed'] else '失败'}",
                f"- 测试：{test_counts['tests']}（失败 "
                f"{test_counts['failures'] + test_counts['errors']}，"
                f"跳过 {test_counts['skipped']}）",
                f"- 覆盖率：{coverage:.2f}%",
                f"- 配置哈希：`{result['configuration_hash']}`",
                f"- 峰值 RSS：{performance.get('peak_rss_mb', 'unavailable')} MiB",
                f"- 耗时：{result['duration_seconds']:.2f} 秒",
                f"- 完整日志：`{result['failure_log']}`",
                "",
            )
        ),
        encoding="utf-8",
    )
    return result
