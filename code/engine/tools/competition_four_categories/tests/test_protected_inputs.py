import json

import pytest

from tools.competition_four_categories.protected_inputs import ANCHOR, BASELINE, capture, verify


@pytest.fixture
def frozen_tree(tmp_path):
    for name in ("openmdbench/core.py", "scenarios/formal/ie_14/scenario.yaml", "catalog/v2/base.yaml"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("original\n", encoding="utf-8")
    capture(tmp_path)
    return tmp_path


def test_unchanged_tree_and_candidate_only_edits_are_allowed(frozen_tree):
    candidate = frozen_tree / "catalog/v2/competition_four_categories.yaml"
    candidate.write_text("new candidate only\n", encoding="utf-8")
    assert verify(frozen_tree)["file_count"] == 3


@pytest.mark.parametrize("change", ["modify", "delete", "add"])
def test_protected_changes_fail_closed_without_rewriting_baseline(frozen_tree, change):
    before = (frozen_tree / BASELINE).read_bytes()
    path = frozen_tree / "openmdbench/core.py"
    if change == "modify":
        path.write_text("changed\n", encoding="utf-8")
    elif change == "delete":
        path.unlink()
    else:
        path.with_name("another.py").write_text("new mechanism\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Protected inputs changed"):
        verify(frozen_tree)
    assert (frozen_tree / BASELINE).read_bytes() == before


def test_existing_baseline_cannot_be_recaptured(frozen_tree):
    with pytest.raises(FileExistsError):
        capture(frozen_tree)


def test_missing_baseline_and_empty_inventory_fail_closed(tmp_path):
    with pytest.raises(FileNotFoundError):
        verify(tmp_path)
    with pytest.raises(ValueError, match="empty baseline"):
        capture(tmp_path)


def test_first_capture_respects_preexisting_engine_anchor(tmp_path):
    path = tmp_path / "openmdbench/core.py"
    path.parent.mkdir(parents=True)
    path.write_text("changed", encoding="utf-8")
    anchor = tmp_path / ANCHOR
    anchor.parent.mkdir(parents=True)
    anchor.write_text(json.dumps({"files": [{"path": "openmdbench/core.py", "working_tree_sha256": "0" * 64}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="Original engine freeze changed"):
        capture(tmp_path)
    assert not (tmp_path / BASELINE).exists()


def test_candidate_catalog_verifies_freeze_before_loading(monkeypatch):
    from tools.competition_four_categories import runtime
    def deny():
        raise ValueError("Protected inputs changed")
    def should_not_load(*args, **kwargs):
        pytest.fail("Native catalog loaded before the integrity gate")
    monkeypatch.setattr(runtime, "verify_protected_inputs", deny)
    monkeypatch.setattr(runtime, "load_catalog_bundle_v2", should_not_load)
    with pytest.raises(ValueError, match="Protected inputs changed"):
        runtime.load_candidate_catalog(allow_candidate=True)
