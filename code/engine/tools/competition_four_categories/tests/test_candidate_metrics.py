from copy import deepcopy
from types import SimpleNamespace
import json

import pytest

from openmdbench.missions.engine_v2 import MissionContactFactV2
from tools.competition_four_categories.build import ROOT, PACKAGES, reconnaissance
from tools.competition_four_categories.metrics_v1 import ObservationMetricV1
from tools.competition_four_categories.runtime import compile_candidate, load_candidate_catalog


def plugin(kind="contact_recall", items=("target.one", "target.two"), start=1):
    value = ObservationMetricV1()
    value.bind_session(session_id="test", seed=1, parameters={
        "metric_id": "metric.test", "kind": kind, "observer_ids": ["own.one", "own.two"],
        "item_ids": list(items), "start_tick": start, "end_tick": 10,
        "maximum_age_ticks": 1, "unit": "1"})
    return value

def fact(target="target.one", owner="own.one", tick=1, confidence=1.):
    return MissionContactFactV2(evidence_id=f"contact.{owner}.{target}", owner_entity_id=owner,
        target_entity_id=target, observed_tick=tick, max_age_ticks=5, confidence=confidence,
        minimum_confidence=.5, selector_id="selector.test")

def snap(tick=1, facts=(), zones=None, activation=None, states=None):
    return SimpleNamespace(tick=tick, contact_facts=tuple(facts),
        entity_states=states or {"own.one": {"lifecycle": "active"},
                                 "own.two": {"lifecycle": "active"}},
        zone_membership=zones or {}, zone_activation=activation or {})

def test_contact_recall_deduplicates_targets_across_sensors():
    p = plugin()
    assert p.evaluate(snap(facts=[fact(), fact(owner="own.two")])) == {"metric.test": .5}
    assert p.evaluate(snap(2, [fact("target.two", tick=2)])) == {"metric.test": 1.}

def test_stale_unauthorized_low_confidence_and_unassigned_contacts_do_not_count():
    p = plugin()
    assert p.evaluate(snap(facts=[fact(tick=0, confidence=.1), fact(owner="enemy.one"),
                                     fact("unassigned")]))["metric.test"] == 0.
    assert p.evaluate(snap(2, [fact(tick=0)]))["metric.test"] == 0.

def test_continuity_requires_every_target_and_every_tick():
    p = plugin("contact_fraction")
    assert p.evaluate(snap(facts=[fact(), fact("target.two")]))["metric.test"] == 1.
    assert p.evaluate(snap(2, [fact(tick=2)]))["metric.test"] == .5
    with pytest.raises(ValueError, match="every authoritative tick"):
        p.evaluate(snap(4))

def test_missing_time_window_is_na_not_zero():
    p = plugin(start=3)
    assert p.evaluate(snap(1)) == {"metric.test": None}
    assert p.evaluate(snap(2)) == {"metric.test": None}
    assert p.evaluate(snap(3)) == {"metric.test": 0.}

def test_zone_visits_ignore_inactive_zones_and_destroyed_observers():
    p = plugin("zone_visits", ("z1", "z2"))
    assert p.evaluate(snap(zones={"own.one": ("z1", "z2")},
                                 activation={"z2": False}))["metric.test"] == .5
    assert p.evaluate(snap(2, zones={"own.one": ("z2",)},
                                 states={"own.one": {"lifecycle": "destroyed"}}))["metric.test"] == .5

def test_checkpoint_resume_and_tick_idempotency():
    a, b = plugin(), plugin()
    first = snap(facts=[fact()])
    a.evaluate(first)
    state = deepcopy(a.snapshot())
    a.evaluate(first)
    assert a.snapshot() == state
    b.restore(state)
    second = snap(2, [fact("target.two", tick=2)])
    assert a.evaluate(second) == b.evaluate(second)
    assert a.snapshot() == b.snapshot()
    with pytest.raises(ValueError, match="conflicting"):
        b.evaluate(snap(2))

def test_plugin_does_not_share_session_state():
    a, b = plugin(), plugin()
    a.evaluate(snap(facts=[fact()]))
    assert b.snapshot()["seen"] == []

def test_production_registration_fails_closed():
    with pytest.raises(ValueError, match="not released"):
        load_candidate_catalog()

def test_all_28_contracts_preserve_required_scope_and_are_distinct():
    path = ROOT.parents[1] / "doc/competition_four_categories/SCENARIO_CONTRACTS.json"
    rows = json.loads(path.read_text(encoding="utf-8"))["scenarios"]
    expected = {f"MD-{group}-{n:03d}" for group, count in
                (("REC", 8), ("TRK", 8), ("AD", 6), ("ER", 6)) for n in range(1, count+1)}
    assert len(rows) == 28
    assert {row["id"] for row in rows} == expected
    assert len({row["challenge"] for row in rows}) == 28
    assert len({tuple(row["mechanisms"]) for row in rows}) == 28
    assert all(row["metrics"] and row["success"] for row in rows)

@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_candidate_compiles_and_contains_live_bound_metrics(difficulty):
    resolved, _ = compile_candidate(PACKAGES / f"md_rec_001_{difficulty}")
    assert len(resolved.scoring.metrics) == 2
    for metric in resolved.scoring.metrics:
        assert metric.plugin_evidence.artifact_sha256.startswith("sha256:")
        assert metric.plugin_parameters.kind in {"contact_recall", "zone_visits"}
    assert len(resolved.entities) == 3 + {"easy": 1, "medium": 2, "hard": 3}[difficulty]

def test_difficulty_changes_executable_pressure_not_only_names():
    packages = [reconnaissance(level)[0]["scenario"] for level in ("easy", "medium", "hard")]
    assert [p["world"]["duration_ticks"] for p in packages] == [181, 161, 141]
    assert [len(p["entities"]) for p in packages] == [4, 5, 6]
    assert len({p["entities"][0]["component_refs"][1] for p in packages}) == 3

def test_score_window_freezes_after_deadline():
    p = plugin()
    for tick in range(1, 10):
        p.evaluate(snap(tick))
    assert p.evaluate(snap(10, [fact(tick=10), fact("target.two", tick=10)]))["metric.test"] == 0.
    assert p.snapshot()["samples"] == 9

def test_deadline_score_gets_a_non_scoring_adjudication_tick():
    package, brief = reconnaissance("easy")
    scenario = package["scenario"]
    assert scenario["world"]["duration_ticks"] == brief["scoring_deadline_tick"]+1
    assert scenario["mission_rules"][1]["condition"]["parameters"]["tick"] == brief["adjudication_tick"]
    assert all(m["plugin_parameters"]["end_tick"] == brief["adjudication_tick"]
               for m in scenario["scoring"]["metrics"])
