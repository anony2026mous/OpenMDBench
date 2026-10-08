"""Release container and user-documentation contracts."""

from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_container_is_non_root_and_health_checked() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text()
    compose = (ROOT / "compose.yaml").read_text()
    assert dockerfile.startswith("FROM python:3.11.15-slim\n")
    assert "USER 10001:10001" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "/health/ready" in dockerfile
    assert "no-new-privileges:true" in compose
    assert "cap_drop:" in compose


def test_release_guides_are_linked() -> None:
    readme = (ROOT / "README.md").read_text()
    for name in (
        "OpenMDBench_用户操作手册与场景智能体开发指南.md",
        "OpenMDBench_当前支持实体武器挂载与事件清单.md",
        "OpenMDBench_Platform_Refactor_Service_Requirements.md",
        "OpenMDBench_Platform_Refactor_Implementation_Test_Review_Plan.md",
    ):
        assert name in readme
        assert (ROOT / "docs" / name).stat().st_size > 100
    assert (ROOT / "CHANGELOG.md").stat().st_size > 100
