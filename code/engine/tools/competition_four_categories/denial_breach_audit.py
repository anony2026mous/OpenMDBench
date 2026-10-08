"""Referee-only capture of existing denial score inputs; never engine edits."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from openmdbench.world.factory_v2 import _canonical_evidence_hash
from .build import ROOT
from .calibration_matrix import sha
from .denial_metrics_v1 import DenialMetricV1

_ACTIVE = False


def final_wave(package, intruders):
    scenario = package["scenario"]
    release = {e["id"]: 0 for e in scenario["entities"]}
    for event in scenario["events"]:
        if event["event_type"] != "spawn":
            continue
        entity = event["payload"]["entity"]["id"]
        if entity in release or set(event["trigger"]) != {"tick"}:
            raise ValueError("cohort requires unique entities with explicit one-time spawn ticks")
        tick = event["trigger"]["tick"]
        if type(tick) is not int or tick < 0:
            raise ValueError("invalid declared release tick")
        release[entity] = tick
    if not intruders or not set(intruders) <= set(release):
        raise ValueError("scored intruder release mapping is incomplete")
    release = {i: release[i] for i in sorted(intruders)}
    last = max(release.values())
    return {"definition": "Scored intruders in the final declared spawn wave, not all entities present in a late time window",
            "release_ticks": release, "final_release_tick": last if last > 0 else None,
            "members": sorted(i for i, t in release.items() if t == last) if last > 0 else [],
            "data_status": "declared_final_spawn_wave" if last > 0 else "no_separate_spawn_wave"}


class DenialBreachAudit:
    def __init__(self, path, metric_id="metric.breaches"):
        self.path, self.metric_id, self.rows = Path(path), metric_id, []

    def __enter__(self):
        global _ACTIVE
        if _ACTIVE:
            raise ValueError("breach input observer requires one isolated session")
        self.stream = self.path.open("x", encoding="utf-8")
        original = DenialMetricV1.evaluate
        def evaluate(model, snapshot):
            result = original(model, snapshot)
            p = model.parameters
            if p["metric_id"] == self.metric_id:
                transitions = [t.model_dump(mode="json") for t in snapshot.zone_transitions
                               if t.entity_id in p["intruder_ids"] and t.zone_id in p["zone_ids"]]
                row = {"audience": "referee_only", "scoring_tick": snapshot.tick,
                    "source_fact_hash": None, "source_fact_hash_status": "not_exposed_by_MissionEvaluationSnapshotV2",
                    "parameters": deepcopy(p),
                    "lifecycle": {i: snapshot.entity_states.get(i, {}).get("lifecycle") for i in p["intruder_ids"]},
                    "zone_membership": {i: sorted(snapshot.zone_membership.get(i, ())) for i in p["intruder_ids"]},
                    "zone_transitions": transitions, "native_plugin_output": deepcopy(result)}
                self.stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                self.stream.flush(); self.rows.append(row)
            return result
        self.patcher = patch.object(DenialMetricV1, "evaluate", evaluate)
        self.patcher.start(); _ACTIVE = True
        return self

    def __exit__(self, *exc):
        global _ACTIVE
        self.patcher.stop(); self.stream.close(); _ACTIVE = False
        return False

    def summarize(self, package, state_rows, final_tick):
        if [r["scoring_tick"] for r in self.rows] != list(range(1, final_tick + 1)):
            raise ValueError("breach inputs must cover every native scoring tick")
        parameters = self.rows[0]["parameters"]
        cohort = final_wave(package, parameters["intruder_ids"])
        late = set(cohort["members"])
        states = {r["state"]["last_tick"]: r["state"] for r in state_rows
                  if r["state"]["parameters"]["metric_id"] == self.metric_id}
        counts = {z: 0 for z in parameters["zone_ids"]}
        late_counts = dict(counts); previous = {z: set() for z in counts}
        seen, evidence_payloads, entries = set(), {}, []
        first_runtime = {i: None for i in cohort["members"]}
        for row in self.rows:
            tick = row["scoring_tick"]
            if row["parameters"] != parameters:
                raise ValueError("breach parameters changed during native episode")
            for i in late:
                if row["lifecycle"][i] not in (None, "scheduled"):
                    if tick < cohort["release_ticks"][i]:
                        raise ValueError("late-wave actor present before declared release")
                    if first_runtime[i] is None: first_runtime[i] = tick
            eligible = {i for i, lifecycle in row["lifecycle"].items() if lifecycle in ("active", "degraded")}
            entered = {z: {} for z in counts}
            for event in row["zone_transitions"]:
                payload = {k: v for k, v in event.items() if k != "evidence_hash"}
                digest = event["evidence_hash"]
                if _canonical_evidence_hash(payload) != digest:
                    raise ValueError("native zone transition hash differs")
                if event["tick"] > tick or event["zone_id"] not in counts or event["entity_id"] not in parameters["intruder_ids"]:
                    raise ValueError("zone evidence clock or scope differs")
                if digest in evidence_payloads and evidence_payloads[digest] != event:
                    raise ValueError("native evidence identity changed")
                evidence_payloads[digest] = event
                if (parameters["start_tick"] <= tick < parameters["end_tick"]
                        and parameters["start_tick"] <= event["tick"] <= tick and digest not in seen):
                    seen.add(digest)
                    if event["transition"] == "entered":
                        entered[event["zone_id"]].setdefault(event["entity_id"], []).append(event)
            if parameters["start_tick"] <= tick < parameters["end_tick"]:
                for zone in counts:
                    occupied = {i for i in eligible if zone in row["zone_membership"][i]}
                    new = set(entered[zone]) | (occupied - previous[zone])
                    for entity in sorted(new):
                        counts[zone] += 1; late_counts[zone] += entity in late
                        sources = entered[zone].get(entity, [])
                        entries.append({"scoring_tick": tick, "entity_id": entity, "zone_id": zone,
                            "final_spawn_wave_member": entity in late,
                            "basis": "authoritative_entered_transition" if sources else "new_sampled_occupancy",
                            "native_entered_events": sources})
                    previous[zone] = occupied
            state = states[tick]
            if state["parameters"] != parameters or row["native_plugin_output"] != {self.metric_id: state["last_value"]}:
                raise ValueError("input observation output differs from native score state")
            if any(counts[z] != state["zones"][z]["breaches"] for z in counts):
                raise ValueError("event-derived count differs from existing native candidate counter")
        return {"schema_version": "referee-denial-breach-cohort@1.0", "audience": "referee_only",
            "input_journal": self.path.relative_to(ROOT).as_posix(), "input_journal_sha256": sha(self.path),
            "input_rows": len(self.rows), "all_scoring_ticks_match_existing_counter": True,
            "final_spawn_wave": cohort, "first_runtime_lifecycle_tick": first_runtime,
            "all_intruder_entry_count_by_zone": counts,
            "final_spawn_wave_entry_count_by_zone": late_counts if late else None,
            "entry_records": entries,
            "count_definition": "Distinct entering/newly occupied scored entity per zone and scoring tick, matching existing model; multiple native crossings within one tick remain separate evidence but one model entry",
            "clock_definition": "Native event tick/time_fraction are preserved separately from scoring_tick; lifecycle appearance is not a substituted spawn receipt",
            "native_checkpoint_restoration_proven": False, "competition_accepted": False}
