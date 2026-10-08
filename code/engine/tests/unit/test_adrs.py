"""M1 architectural-decision acceptance checks."""

from pathlib import Path


def test_required_architecture_decisions_are_accepted() -> None:
    decisions = Path(__file__).resolve().parents[2] / "docs" / "decisions"
    files = sorted(decisions.glob("ADR-*.md"))
    found = {path.name[:7] for path in files}
    assert {f"ADR-{index:03d}" for index in range(1, 11)} <= found
    for path in files:
        assert "Status: Accepted" in path.read_text(encoding="utf-8")
