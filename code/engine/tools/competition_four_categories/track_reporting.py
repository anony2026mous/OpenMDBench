"""Declarative report contract added to selected candidate tracking packages.

No original engine/catalog file is changed. Private target bindings stay in the
referee scoring parameters; the public brief contains only designation labels,
friendly endpoints, message fields and provisional scoring thresholds.
"""
from copy import deepcopy

from .track_report_metrics_v1 import MODEL_REF, PROTOCOL

REPORT_METRICS = (
    ("metric.report_coverage", "delivered_coverage", "maximize", ">=", .70),
    ("metric.report_identity", "identity_accuracy", "maximize", ">=", .95),
    ("metric.report_switch_rate", "identity_switch_rate", "minimize", "<=", .05),
    ("metric.report_freshness", "delivered_freshness", "maximize", ">=", .40),
)


def attach_reporting_contract(package, brief, acceptance, scored_targets):
    s = package["scenario"]
    labels = [r["id"] for r in brief["initial_designation_regions"]]
    if len(labels) != len(scored_targets) or not labels:
        raise ValueError("one private binding per public initial designation required")
    sinks = [i for i in brief["observers"] if brief["observer_domains"][i] == "shore"]
    if not sinks:
        raise ValueError("actual declared receiver required")
    sink = sinks[0]
    reporters = list(brief["mobile_observers"])
    if sink in reporters:
        raise ValueError("report sink cannot be its own source")
    metrics = s["scoring"]["metrics"]
    if any(m.get("plugin_ref") == MODEL_REF for m in metrics):
        raise ValueError("report contract already attached")
    weight = sum(m["weight"] for m in metrics)
    if weight <= 0:
        raise ValueError("existing score requires positive weight")
    for metric in metrics:
        metric["weight"] *= .5/weight
    success = [r for r in s["mission_rules"] if r["outcome"].get("result") == "objective_complete"]
    if len(success) != 1 or success[0]["condition"]["operator"] != "all":
        raise ValueError("one explicit conjunctive success rule required")
    public_scoring = []
    for identifier, kind, direction, comparison, threshold in REPORT_METRICS:
        parameters = {"metric_id": identifier, "kind": kind,
            "tracks": [{"track_id": label, "target_entity_id": target} for label, target in zip(labels, scored_targets)],
            "reporter_ids": reporters, "recipient_entity_id": sink, "recipient_controller_slot": f"slot.{sink}",
            "start_tick": brief["scoring_start_tick"], "end_tick": brief["scoring_deadline_tick"]+1,
            "maximum_age_ticks": 12, "unit": "1"}
        metrics.append({"id": identifier, "selector": deepcopy(metrics[0]["selector"]),
            "aggregation": "mean", "unit": "1", "direction": direction, "weight": .5/len(REPORT_METRICS),
            "available": True, "value": 0., "required": True,
            "normalization": {"lower_bound": 0., "upper_bound": 1.},
            "plugin_ref": MODEL_REF, "plugin_parameters": parameters})
        # The unchanged engine exposes utility-v1 values to mission rules,
        # while metric receipts retain raw values. Low switch rate therefore
        # means HIGH utility; do not compare raw <=.05 to native utility.
        utility_minimize = s["scoring"].get("aggregation_version") == "utility-v1" and direction == "minimize"
        gate_comparison, gate_value = (">=", 1.-threshold) if utility_minimize else (comparison, threshold)
        success[0]["condition"]["parameters"]["conditions"].append({"operator": "score",
            "parameters": {"metric_id": identifier, "comparison": gate_comparison, "value": gate_value}})
        public_scoring.append({"metric_id": identifier, "kind": kind, "comparison": comparison,
            "threshold": threshold, "native_condition": {"comparison": gate_comparison, "value": gate_value}})
    brief["track_reporting"] = {"schema_version": PROTOCOL, "track_ids": labels,
        "recipient_entity_id": sink, "recipient_controller_slot": f"slot.{sink}",
        "reporter_ids": reporters, "suggested_interval_ticks": 4, "maximum_age_ticks": 12,
        "message_fields": {"schema_version": PROTOCOL, "track_id": "a public initial-designation ID",
            "contact_id": "an unchanged opaque organic contact ID from this reporter",
            "observed_tick": "the exact native sample tick", "reported_tick": "the native send tick"},
        "scoring": public_scoring,
        "score_window": {"start_tick_inclusive": brief["scoring_start_tick"],
                         "end_tick_exclusive": brief["scoring_deadline_tick"]+1},
        "score_weight": .5,
        "calibration": "UNVALIDATED candidate thresholds declared before report experiments",
        "scope": "Identity reports must actually arrive at the named endpoint; sensor detection alone is insufficient.",
        "limitations": ["Organic references only; shared-only sample receiver proof is absent from the native mission snapshot.",
                        "True-position error is not computed by this protocol."]}
    brief["task"] += " Maintain public designation identity and send track-report@1.0 messages to the declared receiver."
    old = {"agent track-report identity-switch/position-error scoring not yet implemented",
           "freshness metric uses sensor facts, not yet communication-delivered information age"}
    acceptance["unmet_gates"] = [g for g in acceptance["unmet_gates"] if g not in old]
    acceptance["unmet_gates"] += ["native report identity and information-age metrics require adversarial and cross-seed validation",
        "true-position RMSE remains unavailable in the native mission snapshot",
        "shared-only contact report provenance not supported by this version",
        "new report thresholds and score weights remain uncalibrated competition candidates"]
