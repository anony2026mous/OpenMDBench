from copy import deepcopy
import pytest

from openmdbench.missions.engine_v2 import MissionEvaluationSnapshotV2, ZoneTransitionEvidenceV2
from openmdbench.world.factory_v2 import _canonical_evidence_hash
from tools.competition_four_categories import denial_breach_audit as audit
from tools.competition_four_categories.denial_metrics_v1 import DenialMetricV1
from tools.competition_four_categories.tests.test_denial_metrics import plugin, snap


def package():
    return {"scenario": {"entities": [{"id": "target.a"}], "events": [{
        "event_type": "spawn", "trigger": {"tick": 3}, "payload": {"entity": {"id": "target.b"}}}]}}


def transition(entity, tick, kind="entered"):
    fields = {"entity_id": entity, "zone_id": "zone.a", "transition": kind, "tick": tick, "time_fraction": .5}
    return ZoneTransitionEvidenceV2(**fields, evidence_hash=_canonical_evidence_hash(fields))


def evaluation_snapshot(source):
    result = MissionEvaluationSnapshotV2(tick=source.tick, entity_states=source.entity_states,
        zone_membership={k: tuple(v) for k, v in source.zone_membership.items()},
        event_ids=(), mission_states=(), contacts={}, communications=(), resources={}, scores={},
        zone_transitions=tuple(source.zone_transitions), zone_activation=source.zone_activation)
    assert not hasattr(result, "fact_hash")
    return result


def collect(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    model = plugin("breach_free"); states = []
    transitions = [transition("target.a", 3), transition("target.b", 3), transition("target.b", 3, "left")]
    with audit.DenialBreachAudit(tmp_path / "inputs.jsonl", "metric.test") as observer:
        for tick in range(1, 7):
            snapshot = snap(tick, transitions=transitions if tick >= 4 else ())
            if tick >= 3: snapshot.entity_states["target.b"]["lifecycle"] = "destroyed" if tick >= 4 else "active"
            model.evaluate(evaluation_snapshot(snapshot)); states.append({"state": model.snapshot()})
    return observer, states


def test_last_wave_members_come_from_declared_release_not_time_window():
    result = audit.final_wave(package(), ["target.a", "target.b"])
    assert result["members"] == ["target.b"] and result["final_release_tick"] == 3
    assert audit.final_wave(package(), ["target.a"])["data_status"] == "no_separate_spawn_wave"
    with pytest.raises(ValueError): audit.final_wave(package(), ["missing"])


def test_early_and_late_intruders_in_same_tick_are_counted_separately(tmp_path, monkeypatch):
    observer, states = collect(tmp_path, monkeypatch)
    result = observer.summarize(package(), states, 6)
    assert result["all_intruder_entry_count_by_zone"]["zone.a"] == 2
    assert result["final_spawn_wave_entry_count_by_zone"]["zone.a"] == 1
    late = next(x for x in result["entry_records"] if x["final_spawn_wave_member"])
    assert late["scoring_tick"] == 4 and late["native_entered_events"][0]["tick"] == 3
    assert late["native_entered_events"][0]["time_fraction"] == .5
    assert result["all_scoring_ticks_match_existing_counter"] is True
    assert all(row["source_fact_hash"] is None for row in observer.rows)
    assert all(row["source_fact_hash_status"] == "not_exposed_by_MissionEvaluationSnapshotV2" for row in observer.rows)


@pytest.mark.parametrize("change,message", [("gap", "every native scoring tick"), ("event", "hash differs"), ("counter", "count differs"), ("early", "before declared release")])
def test_inconsistent_evidence_is_rejected(tmp_path, monkeypatch, change, message):
    observer, states = collect(tmp_path, monkeypatch)
    if change == "gap": observer.rows.pop(0)
    elif change == "event": observer.rows[3]["zone_transitions"][0]["time_fraction"] = .7
    elif change == "counter": states[3]["state"]["zones"]["zone.a"]["breaches"] = 0
    else: observer.rows[0]["lifecycle"]["target.b"] = "active"
    with pytest.raises(ValueError, match=message): observer.summarize(package(), states, 6)


def test_observer_returns_original_output_and_restores_method(tmp_path, monkeypatch):
    original = DenialMetricV1.evaluate; returned = []
    def tracked(model, snapshot):
        value = original(model, snapshot); returned.append(value); return value
    monkeypatch.setattr(DenialMetricV1, "evaluate", tracked)
    model = plugin(); control = plugin(); snapshot = evaluation_snapshot(snap(1))
    expected = control.evaluate(snapshot); before = control.snapshot()
    with audit.DenialBreachAudit(tmp_path / "input.jsonl", "metric.test"):
        output = model.evaluate(snapshot)
        assert output is returned[-1] and output == expected and model.snapshot() == before
    assert DenialMetricV1.evaluate is tracked
    with pytest.raises(RuntimeError):
        with audit.DenialBreachAudit(tmp_path / "error.jsonl", "metric.test"):
            raise RuntimeError("fixture failure")
    assert DenialMetricV1.evaluate is tracked
