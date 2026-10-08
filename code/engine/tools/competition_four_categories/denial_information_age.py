"""Offline descriptive information-age metrics from frozen public observations.

No simulation, controller, score, or original record is changed. Source-contact
streams are not true-target identities; missing contact data is never age zero.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics

import yaml

from .build import ROOT, PACKAGES
from .calibration_matrix import frozen_inputs, sha
from .protected_inputs import verify

SCHEMA = "public-contact-information-age@1.0"
CHANNELS = ("organic", "shared", "freshest_public_source")


def distribution(values, dt):
    values = sorted(values)
    if not values:
        return {"sample_count": 0, "data_status": "no_visible_contact_samples",
                "ticks": None, "seconds": None}
    ticks = {"minimum": values[0], "mean": statistics.fmean(values),
             "median": statistics.median(values),
             "p95_nearest_rank": values[math.ceil(.95 * len(values)) - 1], "maximum": values[-1]}
    return {"sample_count": len(values), "data_status": "observed",
            "ticks": ticks, "seconds": {k: v * dt for k, v in ticks.items()}}


def _integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(name + " must be a nonnegative integer")
    return value


def _contacts(rows, channel, tick):
    if not isinstance(rows, list):
        raise ValueError("public contact channel must be a list")
    selected = {}
    for row in rows:
        source = row["contact_id" if channel == "organic" else "source_contact_id"]
        owner = row["observer_entity_id"]
        if any(not isinstance(x, str) or not x for x in (source, owner)):
            raise ValueError("public source-contact identity is missing")
        measured = _integer(row["observed_tick"], "observed_tick")
        reported = _integer(row["age_ticks"], "age_ticks")
        if measured > tick:
            raise ValueError("measurement occurs after the public observation")
        item = {"source_contact_id": source, "source_observer_entity_id": owner,
                "measurement_tick": measured, "measurement_age_ticks": tick - measured,
                "reported_age_ticks": reported, "delivered_tick": None, "delivery_lag_ticks": None}
        if channel == "shared":
            delivered = _integer(row["delivered_tick"], "delivered_tick")
            if not measured <= delivered <= tick:
                raise ValueError("shared delivery clock is inconsistent")
            item.update(delivered_tick=delivered, delivery_lag_ticks=delivered - measured)
        key = (owner, source)
        old = selected.get(key)
        # One freshest public measurement per stream and recipient/tick. For
        # repeated delivery of that same sample retain its earliest visible copy.
        if old is None or measured > old["measurement_tick"] or (
                measured == old["measurement_tick"] and channel == "shared"
                and item["delivered_tick"] < old["delivered_tick"]):
            selected[key] = item
    return selected


def audit(result, brief, outage_window=None):
    dt = brief["physics_dt_seconds"]
    if type(dt) not in (int, float) or not math.isfinite(dt) or dt <= 0:
        raise ValueError("positive finite physics tick duration required")
    end = _integer(brief["scoring_deadline_tick"], "scoring deadline") + 1
    final_tick = _integer(result["final_tick"], "final tick")
    if result["scenario_id"] != brief["scenario_id"] or final_tick < end - 1 or not result["terminal"]:
        raise ValueError("result must be the matching complete natural episode")
    trace = result["trace"]
    if [f["tick"] for f in trace] != list(range(1, final_tick + 1)):
        raise ValueError("native observation trace is not contiguous")
    if trace[-1]["terminal"] != result["terminal"]:
        raise ValueError("final native terminal differs from trace")
    slots = brief["defenders"]
    if len(set(slots)) != len(slots) or not slots:
        raise ValueError("unique evaluated controllers required")
    if outage_window is None:
        windows = {"whole_window": [1, end]}
    else:
        first, last = (_integer(x, "outage boundary") for x in outage_window)
        if not 1 < first < last < end:
            raise ValueError("outage must have nonempty pre/during/post phases")
        windows = {"before_outage": [1, first], "during_outage": [first, last],
                   "after_outage": [last, end]}
    buckets, timeline, delivery_seen = {}, [], set()
    jamming_ticks = {phase: [] for phase in windows}
    recovery = {slot: {"first_visible_shared_delivery_tick": None,
                       "first_visible_post_outage_measurement_tick": None} for slot in slots}
    def bucket(phase, slot, channel):
        return buckets.setdefault((phase, slot, channel), {"ages": [], "observation_samples": 0,
            "without_contacts": 0, "reported_age_disagreements": 0, "new_delivery_lags": []})
    for frame in trace:
        tick = frame["tick"]
        if tick >= end:
            continue
        phase = next(name for name, (a, b) in windows.items() if a <= tick < b)
        if frame["referee_event_evidence"]["active_jamming_sessions"]:
            jamming_ticks[phase].append(tick)
        observations = frame["controller_observations"]
        if set(observations) != set(slots):
            raise ValueError("controller observations are missing or unexpected")
        for slot in slots:
            obs = observations[slot]
            if obs["tick"] != tick:
                raise ValueError("public observation tick differs from native frame")
            organic = _contacts(obs["organic_contacts"], "organic", tick)
            shared = _contacts(obs["shared_contacts"], "shared", tick)
            freshest = dict(shared)
            for key, item in organic.items():
                if key not in freshest or item["measurement_tick"] >= freshest[key]["measurement_tick"]:
                    freshest[key] = item
            channels = dict(zip(CHANNELS, (organic, shared, freshest)))
            timeline.append({"tick": tick, "controller_entity_id": slot, "phase": phase,
                "channels": {c: [rows[k] for k in sorted(rows)] for c, rows in channels.items()}})
            new_lags = []
            for key, item in shared.items():
                identity = (slot, *key, item["measurement_tick"], item["delivered_tick"])
                if identity not in delivery_seen:
                    delivery_seen.add(identity); new_lags.append(item["delivery_lag_ticks"])
                if outage_window is not None and tick >= outage_window[1]:
                    for field, clock in [("first_visible_shared_delivery_tick", "delivered_tick"),
                                         ("first_visible_post_outage_measurement_tick", "measurement_tick")]:
                        if item[clock] >= outage_window[1] and recovery[slot][field] is None:
                            recovery[slot][field] = tick
            for channel, rows in channels.items():
                for recipient in (slot, "ALL_CONTROLLERS"):
                    b = bucket(phase, recipient, channel)
                    b["observation_samples"] += 1
                    b["without_contacts"] += not rows
                    b["ages"].extend(item["measurement_age_ticks"] for item in rows.values())
                    b["reported_age_disagreements"] += sum(item["reported_age_ticks"] != item["measurement_age_ticks"] for item in rows.values())
                    if channel == "shared":
                        b["new_delivery_lags"].extend(new_lags)
    summaries = []
    for (phase, slot, channel), b in sorted(buckets.items()):
        summaries.append({"phase": phase, "controller_entity_id": slot, "channel": channel,
            "observation_samples": b["observation_samples"], "observations_without_contacts": b["without_contacts"],
            "measurement_age": distribution(b["ages"], dt),
            "reported_age_field_disagreements": b["reported_age_disagreements"],
            "newly_visible_selected_delivery_lag": distribution(b["new_delivery_lags"], dt) if channel == "shared" else None})
    report = {"schema_version": SCHEMA, "scenario_id": brief["scenario_id"],
        "seed": result["seed"], "policy": result["policy"], "physics_dt_seconds": dt,
        "windows_start_inclusive_end_exclusive": windows, "summaries": summaries,
        "native_jamming_active_observation_ticks": jamming_ticks,
        "post_outage_shared_recovery": recovery if outage_window is not None else None,
        "definitions": {
            "measurement_age": "public observation tick minus public observed_tick; reported age_ticks is retained, not rewritten or assumed equivalent",
            "weighting": "One freshest visible sample per public source-contact stream, recipient and observation tick; pooled stats weight these exposures, not true targets or episodes",
            "identity": "Exact public observer/source-contact IDs only; no parsing hidden target IDs or merging different sensor streams as the same target",
            "delivery_lag": "Public delivered_tick minus measured observed_tick; deduplicated selected delivery copies first seen in each phase, not all network packets",
            "recovery": "First public observation exposing a post-outage delivery or measurement; null means not observed, not zero delay or proven failure",
            "missing": "No visible contact is unknown freshness; absence is counted separately and does not become zero age",
            "scope": "Descriptive frozen-trace supplement, not a native score change, causal outage experiment, loss-rate estimate, policy input or competition acceptance"},
        "native_results_changed": False, "competition_accepted": False}
    return report, timeline


def run(result_path, number):
    before, protected = frozen_inputs(), verify()
    result_path = Path(result_path).resolve(); input_sha = sha(result_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if hashlib.sha256(json.dumps(result["trace"], sort_keys=True).encode()).hexdigest() != result["trace_sha256"]:
        raise ValueError("native trace hash differs")
    package = PACKAGES / f"md_ad_{number:03d}_standard"
    brief_path, scenario_path = package / "public_brief.json", package / "scenario.yaml"
    binding = result["referee_metric_state_audit_provenance"]["source_inputs"]["input_hashes"]
    for path in (brief_path, scenario_path):
        if sha(path) != binding[path.relative_to(ROOT).as_posix()]:
            raise ValueError("scenario or brief differs from original frozen input")
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    windows = []
    def visit(value):
        if isinstance(value, dict):
            p = value.get("plugin_parameters", {})
            if p.get("metric_id") == "metric.outage_protection":
                windows.append((p["start_tick"], p["end_tick"]))
            for child in value.values(): visit(child)
        elif isinstance(value, list):
            for child in value: visit(child)
    visit(yaml.safe_load(scenario_path.read_text(encoding="utf-8")))
    if len(windows) > 1:
        raise ValueError("ambiguous outage scoring window")
    report, timeline = audit(result, brief, windows[0] if windows else None)
    directory = ROOT / "artifacts/competition_four_categories" / (
        f"denial-information-age-{number:03d}-{result['seed']}-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    directory.mkdir(parents=True, exist_ok=False)
    journal = directory / "public-information-age.jsonl"
    with journal.open("x", encoding="utf-8") as stream:
        for row in timeline: stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    if sha(result_path) != input_sha or frozen_inputs() != before:
        raise RuntimeError("input or postprocessor source changed during analysis")
    report["provenance"] = {"native_result": result_path.relative_to(ROOT).as_posix(),
        "native_result_sha256": input_sha, "source_inputs": before, "input_binding_verified": True,
        "protected_before": protected, "protected_after": verify(), "observer_source_sha256": sha(Path(__file__)),
        "timeline": journal.relative_to(ROOT).as_posix(), "timeline_sha256": sha(journal), "timeline_rows": len(timeline)}
    path = directory / "report.json"
    with path.open("x", encoding="utf-8") as stream: json.dump(report, stream, indent=2, allow_nan=False)
    print("evidence=" + path.relative_to(ROOT).as_posix(), flush=True)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--scenario", type=int, choices=range(1, 7), required=True)
    args = parser.parse_args()
    run(args.result, args.scenario)
