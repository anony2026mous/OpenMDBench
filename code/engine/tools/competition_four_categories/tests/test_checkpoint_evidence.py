"""A failed native checkpoint must stay failed, with actionable provenance."""
from types import SimpleNamespace

import pytest

from openmdbench.world.checkpoint_v2 import CheckpointErrorV2
from tools.competition_four_categories.validate_recon import referee_checkpoint_evidence
from tools.competition_four_categories.audit import checkpoint_record_evidence, checkpoint_test_gates


@pytest.mark.parametrize("reason", [
    "plugin score input lacks authoritative output evidence",
    "terminal result differs from selection receipt",
])
def test_failed_checkpoint_preserves_native_cause_and_never_fabricates_state(reason):
    def rejected_checkpoint():
        try:
            raise ValueError(reason)
        except ValueError as cause:
            raise CheckpointErrorV2("checkpoint mission scoring state is invalid") from cause

    session = SimpleNamespace(world_view=SimpleNamespace(checkpoint=rejected_checkpoint))
    evidence, states = referee_checkpoint_evidence(session)
    assert evidence["status"] == "FAILED_CHECKPOINT_GATE"
    assert states is None
    assert evidence["causes"] == [{"type": "ValueError", "error": reason}]
    assert "checkpoint.integrity_invalid" in evidence["error"]


def test_valid_checkpoint_extraction_does_not_claim_restore_equivalence():
    checkpoint = SimpleNamespace(checkpoint_hash="sha256:fixture",
        mission_scoring_checkpoint={"plugin_states": []})
    session = SimpleNamespace(world_view=SimpleNamespace(checkpoint=lambda: checkpoint))
    evidence, states = referee_checkpoint_evidence(session)
    assert evidence == {"status": "available_not_full_restore_equivalence",
                        "world_checkpoint_hash": "sha256:fixture"}
    assert states == []


@pytest.mark.parametrize("version", ["current", "stale", "unrecorded"])
def test_semantic_restore_evidence_never_claims_byte_exact_hash_equivalence(version):
    tests = {"source_version_status": version, "failed_test_names": [],
        "passed_test_names": [
            "test_native_dispatch_checkpoint_preserves_partial_dwell_and_weather",
            "test_native_delivered_dwell_checkpoint_preserves_exact_plugin_state",
            "test_native_tracking_checkpoint_preserves_nonzero_per_target_history"]}
    gates = checkpoint_test_gates(tests)
    assert gates["checkpoint_full_hash_gate"] == "not_proven"
    expected = "passed_targeted_fixture_only" if version == "current" else "not_proven"
    assert gates["checkpoint_semantic_restore_gate"] == expected


def test_missing_and_failed_restore_tests_cannot_count_as_passed():
    assert checkpoint_test_gates(None)["checkpoint_semantic_restore_gate"] == "not_proven"
    tests = {"source_version_status": "current", "passed_test_names": [],
        "failed_test_names": ["test_native_tracking_checkpoint_preserves_nonzero_per_target_history"]}
    gates = checkpoint_test_gates(tests)
    assert gates["checkpoint_semantic_restore_gate"] == "FAILED"
    assert gates["checkpoint_missing_plugin_evidence_gate"] == "FAILED"


def test_ad_native_checkpoint_failure_is_not_hidden_by_an_alias_or_successful_task():
    raw = {"status": "FAILED", "cause": "plugin score input lacks authoritative output evidence"}
    record = {"status": "candidate_validation_not_release", "failure": None,
              "native_terminal_checkpoint_gate": raw}
    gate = checkpoint_record_evidence(record)
    assert gate["status"] == "FAILED_CHECKPOINT_GATE"
    assert gate["source_field"] == "native_terminal_checkpoint_gate"
    assert gate["raw_evidence"] == raw
    assert record["failure"] is None


@pytest.mark.parametrize("field,status", [
    ("native_terminal_checkpoint_gate", "read_passed_not_restore_acceptance"),
    ("native_checkpoint_evidence", "available_not_full_restore_equivalence"),
])
def test_successful_extraction_does_not_establish_restoration(field, status):
    gate = checkpoint_record_evidence({field: {"status": status}})
    assert gate["status"] == status
    assert gate["restoration_equivalence_proven"] is False


def test_failed_alias_takes_precedence_and_absent_evidence_stays_unrecorded():
    gate = checkpoint_record_evidence({"native_checkpoint_evidence": {"status": "available_not_full_restore_equivalence"},
        "native_terminal_checkpoint_gate": {"status": "FAILED", "error": "native rejection"}})
    assert gate["status"] == "FAILED_CHECKPOINT_GATE"
    assert checkpoint_record_evidence({})["status"] == "not_recorded"
