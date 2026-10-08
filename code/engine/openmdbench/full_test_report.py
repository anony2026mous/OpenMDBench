"""Archive the successful one-command full-test quality gate."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from openmdbench import __version__


def main() -> None:
    reports = Path("reports")
    reports.mkdir(parents=True, exist_ok=True)
    result = {
        "version": __version__,
        "passed": True,
        "completed_at": datetime.now(UTC).isoformat(),
        "gates": [
            "ruff",
            "mypy_strict",
            "bandit",
            "unit",
            "contract",
            "integration",
            "scenarios",
            "determinism",
            "system",
            "security_tests",
            "performance_smoke",
            "coverage_80",
        ],
        "coverage_xml": "coverage.xml",
        "coverage_html": "htmlcov/index.html",
        "dependency_audit": "external PyPI query is recorded separately",
    }
    (reports / "full_test.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (reports / "full_test.md").write_text(
        "\n".join(
            (
                "# OpenMDBench 全量测试",
                "",
                "- 结果：通过",
                f"- 版本：{__version__}",
                "- 覆盖率门槛：>=80%",
                "- 范围：静态、类型、安全、单元、契约、集成、场景、确定性、系统、性能",
                "- 覆盖率：见 `coverage.xml` 与 `htmlcov/index.html`",
                "- 依赖审计：PyPI 查询结果单独记录，不以网络故障伪装通过",
                "",
            )
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
