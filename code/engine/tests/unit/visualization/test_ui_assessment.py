"""T6.1 assessment deliverable guard."""

from pathlib import Path


def test_existing_ui_assessment_covers_required_topics() -> None:
    path = Path(__file__).parents[3] / "docs/visualization_existing_ui_assessment.md"
    content = path.read_text(encoding="utf-8")
    topics = (
        "入口与数据来源",
        "Artist 生命周期",
        "播放控制与线程模型",
        "已有地图",
        "复用项",
        "必要适配点",
    )
    for topic in topics:
        assert topic in content
    assert "没有可运行的 Matplotlib GUI" in content
