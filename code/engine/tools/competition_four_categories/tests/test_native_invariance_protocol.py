from copy import deepcopy
from dataclasses import dataclass
import json

import pytest

from tools.competition_four_categories.native_invariance import MODES, matrix_cases, transform_package


def fixture():
    return {"schema_version": "package@2.0", "scenario": {"scenario_id": "original",
        "entities": [{"id": "one"}, {"id": "two"}],
        "events": [{"id": "late", "trigger": {"tick": 20}}, {"id": "early", "trigger": {"tick": 2}}],
        "zones": [{"id": "z1", "coordinates_m": [[0, 0], [1, 0], [0, 1]]}, {"id": "z2"}],
        "scoring": {"metrics": [{"id": "a", "weight": .3}, {"id": "b", "weight": .7}]},
        "route": [{"waypoint": 1}, {"waypoint": 2}],
        "mission_rules": [{"id": "one", "condition": {"sequence": [2, 1]}}]}}


@pytest.mark.parametrize("mode", MODES)
def test_transform_never_mutates_canonical_input(mode):
    original = fixture(); saved = deepcopy(original)
    result, _ = transform_package(original, mode)
    assert original == saved and result is not original


def test_rename_changes_exactly_the_native_scenario_identifier():
    original = fixture(); renamed, changes = transform_package(original, "rename")
    assert changes == ["scenario.scenario_id"]
    assert renamed["scenario"].pop("scenario_id") == "independent.invariance.scenario"
    original["scenario"].pop("scenario_id")
    assert renamed == original


def test_order_probe_preserves_waypoints_geometry_conditions_and_parameter_values():
    original = fixture(); changed, paths = transform_package(original, "declaration_order")
    assert paths == ["scenario.entities", "scenario.events", "scenario.zones", "scenario.scoring.metrics"]
    assert changed["scenario"]["route"] == original["scenario"]["route"]
    assert changed["scenario"]["mission_rules"] == original["scenario"]["mission_rules"]
    reverted, _ = transform_package(changed, "declaration_order")
    assert reverted == original


def test_matrix_covers_28_bases_30_variants_and_separate_transformations():
    cases = matrix_cases(1701)
    assert len(cases) == 150 and len({c["case_id"] for c in cases}) == 150
    assert len({c["scenario_id"] for c in cases}) == 28
    groups = {}
    for case in cases:
        groups.setdefault((case["scenario_id"], case["difficulty"]), []).append(case)
    assert len(groups) == 30
    assert [case["scenario_id"] for case in cases[::len(MODES)][:4]] == [
        "MD-REC-001", "MD-TRK-001", "MD-AD-001", "MD-ER-001"]
    assert all(tuple(c["mode"] for c in group) == MODES for group in groups.values())
    assert all(len({(c["module"], tuple(c["arguments"]), c["expected_policy"]) for c in group}) == 1
               for group in groups.values())


def test_unsupported_transform_fails_closed():
    with pytest.raises(ValueError, match="unknown"):
        transform_package(fixture(), "easier_thresholds")


def test_serializer_preserves_frozen_native_structure_and_rejects_lossy_repr():
    from tools.competition_four_categories.native_invariance import plain
    @dataclass(frozen=True)
    class Frame:
        tick: int
        scores: dict
    assert plain(Frame(2, {"unavailable": None, "zero": 0.})) == {
        "tick": 2, "scores": {"unavailable": None, "zero": 0.}}
    with pytest.raises(TypeError, match="unsupported"):
        plain(object())


@pytest.mark.parametrize("left,right", [(0, 0.), (None, 0.), ([1, 2], [2, 1]),
                                          ({"score": .5}, {"score": .50000000001}),
                                          ({"a": 1}, {"a": 1, "b": 2})])
def test_comparator_never_rounds_values_drops_keys_or_sorts_ordered_data(left, right):
    from tools.competition_four_categories.native_invariance import first_difference
    assert first_difference(left, right) is not None


def test_journal_comparison_detects_a_missing_final_record(tmp_path):
    from tools.competition_four_categories.native_invariance import compare_journals
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    a.write_text('{"tick":0}\n{"tick":1}\n', encoding="utf-8")
    b.write_text('{"tick":0}\n', encoding="utf-8")
    assert compare_journals(a, b) == {"record": 2, "reason": "record count"}


@pytest.mark.parametrize("key,value", [("seed", 1701), ("seeds", [1700, 1701]), ("seed_order", [1701])])
def test_prepare_refuses_seeds_reserved_in_nested_existing_plans(tmp_path, monkeypatch, key, value):
    from tools.competition_four_categories import native_invariance as subject
    monkeypatch.setattr(subject, "RESULTS", tmp_path)
    nested = tmp_path / "previous-study"; nested.mkdir()
    (nested / "plan.json").write_text(json.dumps({key: value}), encoding="utf-8")
    with pytest.raises(ValueError, match="already used"):
        subject.prepare(1701)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["previous-study"]


def test_reference_arguments_cover_every_declared_runner_signature():
    import importlib
    from tools.competition_four_categories.native_invariance import runner_arguments
    for case in matrix_cases(1701)[::len(MODES)]:
        function = importlib.import_module(case["module"]).run
        arguments = runner_arguments(case, function)
        assert arguments["seed"] == 1701
        assert all(key in function.__code__.co_varnames for key in arguments)


def test_read_only_probe_returns_original_objects_and_never_records_authority_token(tmp_path):
    from tools.competition_four_categories.native_invariance import Journal, SessionProbe
    class Native:
        def __init__(self):
            self.world_view = self; self.tick = 0; self.step_receipt = {"tick": 1}
            self.observation = {"tick": 0}; self.submission = {"status": "queued"}
        def presentation_snapshot(self): return {"tick": self.tick}
        def controller_observation(self, **kwargs): return self.observation
        def submit_actions(self, **kwargs):
            assert kwargs["authority_token"] == "private-test-token"
            return self.submission
        def step(self, **kwargs):
            self.tick += 1
            return self.step_receipt
    native = Native(); path = tmp_path / "journal.jsonl"; journal = Journal(path)
    wrapped = SessionProbe(native, journal)
    assert wrapped.world_view.controller_observation(controller_slot_id="own") is native.observation
    assert wrapped.submit_actions(batch={"owned": True}, authority_token="private-test-token") is native.submission
    assert wrapped.step(expected_tick=0) is native.step_receipt
    assert native.tick == 1 and journal.world_ticks == [0, 1]
    journal.close()
    assert "private-test-token" not in path.read_text(encoding="utf-8")
    assert [json.loads(x)["kind"] for x in path.read_text().splitlines()] == [
        "world", "observation", "submission", "step_receipt", "world"]


def test_native_queue_capability_values_are_redacted_without_hiding_scope_or_outcome(tmp_path):
    from tools.competition_four_categories.native_invariance import Journal
    path = tmp_path / "queue.jsonl"; journal = Journal(path)
    journal.write({"kind": "world", "frame": {"tick": 0, "event_state": {"command_queue": [
        {"authority_token": "private-native-capability", "entity_id": "own.1", "status": "queued"}]}}})
    journal.close(); data = json.loads(path.read_text())
    assert "private-native-capability" not in path.read_text()
    assert data["frame"]["event_state"]["command_queue"] == [
        {"authority_token": "<redacted-authority-token>", "entity_id": "own.1", "status": "queued"}]


def test_only_explicit_observation_metadata_identity_can_be_neutralized():
    from tools.competition_four_categories.native_invariance import metadata_neutral, first_difference
    a = {"kind": "observation", "observation": {"metadata": {"resolved_hash": "a"}, "own_entities": [{"health": 1.}]}}
    b = deepcopy(a); b["observation"]["metadata"]["resolved_hash"] = "b"
    assert first_difference(a, b) and not first_difference(metadata_neutral(a), metadata_neutral(b))
    b["observation"]["own_entities"][0]["health"] = .99
    assert first_difference(metadata_neutral(a), metadata_neutral(b))
    a = {"kind": "world", "frame": {"event_state": {"shared_contact_queue": [{"loss_sample": .1}]}}}
    b = deepcopy(a); b["frame"]["event_state"]["shared_contact_queue"][0]["loss_sample"] = .2
    assert first_difference(metadata_neutral(a), metadata_neutral(b))


def test_reversed_catalog_is_frozen_and_preserves_resources_and_resolved_definitions():
    from tools.competition_four_categories import runtime
    from tools.competition_four_categories.build import reconnaissance
    from tools.competition_four_categories.native_invariance import reversed_catalog, plain
    package = reconnaissance("easy")[0]
    original, catalog = runtime.compile_package(package)
    reordered = reversed_catalog(catalog)
    resolved = runtime.ScenarioCompilerV2(catalog=reordered).compile(runtime.ScenarioPackageV2.from_mapping(package))
    assert plain(catalog.snapshot()) == plain(reordered.snapshot())
    assert plain(catalog.model_registry.snapshot()) == plain(reordered.model_registry.snapshot())
    assert resolved.resolved_hash == original.resolved_hash
    assert resolved.catalog_hash == original.catalog_hash
    assert resolved.model_registry_hash == original.model_registry_hash
