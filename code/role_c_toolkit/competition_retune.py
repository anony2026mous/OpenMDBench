"""Retune competition scenario difficulty (the E4 / D2 headroom calibration).

Why this is allowed now: the four new scenario categories are this reviewer's own scope, and
the user authorised tightening them.  The simulation kernel, the catalog and the fourteen
interception packages are NOT touched - only the competition packages' declared parameters,
which is exactly the "scenario declares" side of the architecture boundary.

What it tunes (all declared, no kernel change):

* ``horizon`` - the scoring deadline.  Both the metric window and the success rule use it, so
  compressing it makes the observation task strictly harder.
* metric ``plugin_parameters``: ``maximum_age_ticks`` / ``maximum_gap_ticks`` (how stale a
  contact may be, how long an outage is tolerated).
* success-rule thresholds: how much continuity / freshness the objective demands.

Deterministic and idempotent: the same profile applied twice yields the same bytes, and a
JSON report records every changed value with its before/after so the change is auditable and
reversible from the backup manifest.

Usage:
    python competition_retune.py --tree <competition_v1> --profile <name> [--dry-run]
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import yaml

# Each profile lists, per scenario package, the declared changes to apply.  Values are
# absolute targets, never deltas, so re-running cannot compound.
PROFILES = {
    # v1 (bounds only): keep the declared horizon and the public brief's tick fields in step,
    # and tighten only what the metrics tolerate plus what the objective demands.  A horizon
    # change also has to be mirrored into public_brief.json, so it is a separate, heavier lever.
    "trk-tighten-v1": {
        "md_trk_001_standard": {"maximum_gap_ticks": 8, "maximum_age_ticks": 1,
                                "thresholds": {"metric.continuity": 0.8}},
        "md_trk_002_standard": {"maximum_gap_ticks": 8, "maximum_age_ticks": 1,
                                "thresholds": {"metric.continuity": 0.8}},
        "md_trk_003_standard": {"maximum_gap_ticks": 8, "maximum_age_ticks": 1,
                                "thresholds": {"metric.continuity": 0.75,
                                               "metric.handover": 1.0}},
        "md_trk_004_standard": {"maximum_gap_ticks": 8, "maximum_age_ticks": 1,
                                "thresholds": {"metric.continuity": 0.8,
                                               "metric.after_turn1": 0.75,
                                               "metric.after_turn2": 0.75}},
        "md_trk_005_standard": {"maximum_gap_ticks": 10, "maximum_age_ticks": 1,
                                "thresholds": {"metric.continuity": 0.75,
                                               "metric.after_fog": 0.7}},
        "md_trk_006_standard": {"maximum_gap_ticks": 8, "maximum_age_ticks": 1,
                                "thresholds": {"metric.continuity": 0.8,
                                               "metric.reacquisition": 1.0}},
    },
    "ad-tighten-v1": {
        "md_ad_001_standard": {"thresholds": {"metric.protection": 0.95}},
        "md_ad_002_standard": {"thresholds": {"metric.protection": 0.95}},
        "md_ad_003_standard": {"thresholds": {"metric.protection": 0.95,
                                              "metric.protected_integrity": 1.0}},
        "md_ad_004_standard": {"thresholds": {"metric.protection": 0.9}},
        "md_ad_005_standard": {"thresholds": {"metric.protection": 0.95,
                                              "metric.breaches": 1.0}},
    },
    # v2 for area denial: the success thresholds are already at their ceiling, so the task is
    # made harder structurally - each protected zone is translated toward the intruder's
    # approach axis, which shortens the intercept window without removing any asset.
    "ad-tighten-v2": {
        "md_ad_001_standard": {"zone_shifts": {"zone.protected01": [90.0, 0.0]}},
        "md_ad_002_standard": {"zone_shifts": {"zone.protected01": [90.0, 0.0],
                                               "zone.protected02": [90.0, 0.0]}},
        "md_ad_003_standard": {"zone_shifts": {"zone.protected01": [90.0, 0.0]}},
        "md_ad_004_standard": {"zone_shifts": {"zone.protected01": [70.0, 0.0]}},
        "md_ad_005_standard": {"zone_shifts": {"zone.protected01": [90.0, 0.0]}},
    },
    # v3 for area denial - the calibration that actually lands in the window.  Measured on
    # AD-001 with the guard baseline: zone_x 0/90/300 -> composite 1.000, 300 -> 1.000, 500 ->
    # 0.492, 700 -> 0.467, 900 -> 0.440.  Each package's protected zone is therefore placed at
    # a measured point on that curve rather than at the authored origin.
    "ad-calibrate-v1": {
        "md_ad_001_standard": {"zone_centroids": {"zone.protected01": 900.0}},
        "md_ad_002_standard": {"zone_centroids": {"zone.protected01": 900.0,
                                                  "zone.protected02": 900.0}},
        "md_ad_003_standard": {"zone_centroids": {"zone.protected01": 520.0}},
        "md_ad_004_standard": {"zone_centroids": {"zone.protected01": 900.0}},
        "md_ad_005_standard": {"zone_centroids": {"zone.protected01": 900.0}},
    },
    # v2 for tracking - the calibration that lands three packages in the window.  Measured on
    # TRK-001 with the follow baseline: standoff 0/300 m -> 1.000, 650 m -> 0.475 (but 650 m
    # sits ON the cliff: a replay of the same setting produced gap=1.0, i.e. 0.975, so 1000 m
    # is used for a robust margin instead), 1000 m -> 0.432.  TRK-002 at 1000 m -> 0.396;
    # TRK-006 at 300 m -> 0.687; TRK-004 with the contact pushed 200 m ahead -> 0.448.
    # Second lever (contact start position) is used where the standoff lever has a
    # two-policy fork that no value satisfies: TRK-004's follow baseline stays above 0.95 for
    # every standoff up to 480 m, while the cooperative baseline drops below 0.40 from 440 m.
    # TRK-003/005/007/008 answer differently again (003 and 005 are already below the window
    # with the authored layout, 007/008 use a different metric plugin), so they are
    # deliberately NOT part of this profile.
    "trk-calibrate-v1": {
        "md_trk_001_standard": {"anchor_shifts": {
            "unit.r01": [0.0, -1000.0], "unit.r02": [0.0, -1000.0], "unit.r03": [150.0, -850.0],
            "unit.r04": [600.0, -400.0]}},
        "md_trk_002_standard": {"anchor_shifts": {
            "unit.r01": [0.0, -1000.0], "unit.r02": [0.0, -1000.0], "unit.r03": [150.0, -850.0],
            "unit.r04": [600.0, -400.0]}},
        "md_trk_004_standard": {"anchor_shifts": {
            "unit.x01": [300.0, 500.0], "unit.x02": [300.0, 500.0]}},
        "md_trk_006_standard": {"anchor_shifts": {
            "unit.r01": [0.0, -300.0], "unit.r02": [0.0, -300.0], "unit.r03": [150.0, -150.0],
            "unit.r04": [1000.0, 700.0]}},
        "md_trk_005_standard": {"anchor_shifts": {
            "unit.x01": [300.0, 550.0]}},
    },
    # ER calibration: the dominant metric is arrival_fraction, and pushing the response zones
    # away turns "arrive at all" into a scheduling problem.  Measured on ER-003 with the naive
    # baseline: +0 m -> 0.896, +60 m -> 0.914, +70 m -> 0.601 (floor control idle = 0.553).
    "er-calibrate-v1": {
        "md_er_003_standard": {"zone_shift_m": 70.0},
        "md_er_005_standard": {"zone_shift_m": 70.0},
    },
    # v3 for area denial: declare a defence-capability loss using the engine's own
    # component-suppression mechanism (the one TRK-008 already uses).  Kept for the record:
    # on its own it did NOT move the composite once the zone was back at its authored place.
    "ad-tighten-v3": {
        "md_ad_001_standard": {"suppressions": [{
            "id": "event.retune-air-sensor-suppression", "target_entity_id": "unit.r01",
            "component_ref": "sensor.competition-denial-air@1.0.0", "tick": 1,
            "duration_ticks": 60}]},
        "md_ad_002_standard": {"suppressions": [{
            "id": "event.retune-air-sensor-suppression", "target_entity_id": "unit.r01",
            "component_ref": "sensor.competition-denial-air@1.0.0", "tick": 1,
            "duration_ticks": 60}]},
        "md_ad_003_standard": {"suppressions": [{
            "id": "event.retune-air-sensor-suppression", "target_entity_id": "unit.r01",
            "component_ref": "sensor.competition-denial-air@1.0.0", "tick": 1,
            "duration_ticks": 60}]},
        "md_ad_004_standard": {"suppressions": [{
            "id": "event.retune-air-sensor-suppression", "target_entity_id": "unit.r01",
            "component_ref": "sensor.competition-denial-air@1.0.0", "tick": 1,
            "duration_ticks": 45}]},
        "md_ad_005_standard": {"suppressions": [{
            "id": "event.retune-air-sensor-suppression", "target_entity_id": "unit.r01",
            "component_ref": "sensor.competition-denial-air@1.0.0", "tick": 1,
            "duration_ticks": 60}]},
    },
    # v2 (escalation, only if v1 leaves a scenario above the window): also compress the
    # horizon, which requires the public brief's tick fields to move with it.
    "trk-tighten-v2": {
        "md_trk_001_standard": {"horizon": 181, "maximum_gap_ticks": 8,
                                "maximum_age_ticks": 1,
                                "thresholds": {"metric.continuity": 0.85}},
        "md_trk_002_standard": {"horizon": 181, "maximum_gap_ticks": 8,
                                "maximum_age_ticks": 1,
                                "thresholds": {"metric.continuity": 0.85}},
        "md_trk_003_standard": {"horizon": 181, "maximum_gap_ticks": 8,
                                "maximum_age_ticks": 1,
                                "thresholds": {"metric.continuity": 0.8,
                                               "metric.handover": 1.0}},
        "md_trk_004_standard": {"horizon": 181, "maximum_gap_ticks": 8,
                                "maximum_age_ticks": 1,
                                "thresholds": {"metric.continuity": 0.85,
                                               "metric.after_turn1": 0.8,
                                               "metric.after_turn2": 0.8}},
        "md_trk_005_standard": {"horizon": 181, "maximum_gap_ticks": 10,
                                "maximum_age_ticks": 1,
                                "thresholds": {"metric.continuity": 0.8,
                                               "metric.after_fog": 0.75}},
        "md_trk_006_standard": {"horizon": 181, "maximum_gap_ticks": 8,
                                "maximum_age_ticks": 1,
                                "thresholds": {"metric.continuity": 0.85,
                                               "metric.reacquisition": 1.0}},
    },
}
# Tracking metrics that carry the tunable staleness/outage bounds.
TRACKING_METRIC_IDS = ("metric.continuity", "metric.gap", "metric.handover",
                       "metric.reacquisition", "metric.freshness", "metric.after_turn1",
                       "metric.after_turn2", "metric.after_fog")


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump_yaml(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, default_flow_style=False,
                                   width=1000, sort_keys=False), encoding="utf-8")


def horizon_of(scenario: dict) -> int:
    """The scenario's scoring deadline, read from the timeout rule it declares."""
    for rule in scenario.get("mission_rules") or []:
        condition = rule.get("condition") or {}
        if condition.get("operator") == "time":
            tick = (condition.get("parameters") or {}).get("tick")
            if isinstance(tick, int):
                return tick
    raise ValueError("scenario declares no time-based deadline")


def apply_horizon(payload: dict, horizon: int) -> list[dict]:
    scenario = payload["scenario"]
    changes = []
    world = scenario.setdefault("world", {})
    if world.get("duration_ticks") != horizon:
        changes.append({"field": "world.duration_ticks",
                        "before": world.get("duration_ticks"), "after": horizon})
        world["duration_ticks"] = horizon
    for rule in scenario.get("mission_rules") or []:
        condition = rule.get("condition") or {}
        if condition.get("operator") == "time":
            parameters = condition.setdefault("parameters", {})
            if parameters.get("tick") != horizon:
                changes.append({"field": f"mission_rules[{rule.get('id')}].tick",
                                "before": parameters.get("tick"), "after": horizon})
                parameters["tick"] = horizon
    for event in scenario.get("events") or []:
        trigger = event.get("trigger") or {}
        if isinstance(trigger.get("tick"), int) and trigger["tick"] > horizon:
            changes.append({"field": f"events[{event.get('id')}].trigger.tick",
                            "before": trigger["tick"], "after": horizon})
            trigger["tick"] = horizon
    return changes


def apply_metric_bounds(payload: dict, maximum_gap_ticks: int | None,
                        maximum_age_ticks: int | None) -> list[dict]:
    changes = []
    metrics = ((payload["scenario"].get("scoring") or {}).get("metrics")) or []
    for metric in metrics:
        if metric.get("id") not in TRACKING_METRIC_IDS:
            continue
        parameters = metric.setdefault("plugin_parameters", {})
        if maximum_gap_ticks is not None and parameters.get("maximum_gap_ticks") != maximum_gap_ticks:
            changes.append({"field": f"{metric['id']}.maximum_gap_ticks",
                            "before": parameters.get("maximum_gap_ticks"),
                            "after": maximum_gap_ticks})
            parameters["maximum_gap_ticks"] = maximum_gap_ticks
        if maximum_age_ticks is not None and parameters.get("maximum_age_ticks") != maximum_age_ticks:
            changes.append({"field": f"{metric['id']}.maximum_age_ticks",
                            "before": parameters.get("maximum_age_ticks"),
                            "after": maximum_age_ticks})
            parameters["maximum_age_ticks"] = maximum_age_ticks
    return changes


def apply_thresholds(payload: dict, thresholds: dict) -> list[dict]:
    """Raise the success-rule thresholds the scoring metrics must reach."""
    changes = []
    for rule in payload["scenario"].get("mission_rules") or []:
        outcome = rule.get("outcome") or {}
        if outcome.get("result") != "objective_complete":
            continue
        condition = rule.get("condition") or {}
        if condition.get("operator") != "all":
            continue
        for sub in (condition.get("parameters") or {}).get("conditions") or []:
            if sub.get("operator") != "score":
                continue
            parameters = sub.setdefault("parameters", {})
            target = thresholds.get(parameters.get("metric_id"))
            if target is None:
                continue
            if parameters.get("value") != target:
                changes.append({"field": f"success.{parameters.get('metric_id')}.value",
                                "before": parameters.get("value"), "after": target})
                parameters["value"] = target
    return changes


def apply_zone_shift(payload: dict, shifts: dict, baseline: dict | None = None) -> list[dict]:
    """Translate a declared protected zone (metres, +x toward the intruder approach axis).

    This is a structural difficulty lever: the intruder reaches the zone earlier, so the
    defenders have a shorter intercept window, while every unit keeps its assets and the zone
    keeps its size.

    The zone schema is closed (an extra key is a ``CompilerErrorV2``), so no provenance field
    is written into the package.  Idempotence therefore comes from an explicit ``baseline``
    map of original centroids: the target is always ``baseline + shift``, so replaying a
    profile on an already-shifted file is a no-op rather than a compounding move.
    """
    changes = []
    zones = ((payload["scenario"].get("world") or {}).get("zones")) or []
    for zone in zones:
        shift = shifts.get(zone.get("id"))
        if not shift:
            continue
        coordinates = zone.get("coordinates_m") or []
        if not coordinates:
            continue
        current = [round(sum(point[index] for point in coordinates) / len(coordinates), 3)
                   for index in (0, 1)]
        origin = (baseline or {}).get(zone.get("id"), current)
        target = [round(origin[0] + shift[0], 3), round(origin[1] + shift[1], 3)]
        if current == target:
            continue
        delta = [target[0] - current[0], target[1] - current[1]]
        zone["coordinates_m"] = [[round(point[0] + delta[0], 3), round(point[1] + delta[1], 3)]
                                 for point in coordinates]
        changes.append({"field": f"zone[{zone.get('id')}].centroid",
                        "before": current, "after": target})
    return changes


def apply_contact_shift(payload: dict, shift: float, faction: str = "blue") -> list[dict]:
    """Move a faction's units along +x by ``shift`` metres, including spawn-event payloads."""
    changes = []
    for entity in payload["scenario"].get("entities") or []:
        if entity.get("faction_id") != faction:
            continue
        state = entity.get("initial_state") or {}
        position = state.get("position_m")
        if not isinstance(position, list) or len(position) != 3:
            continue
        state["position_m"] = [round(position[0] + shift, 3), position[1], position[2]]
        changes.append({"field": f"{entity['id']}.position_m.x", "before": position[0],
                        "after": state["position_m"][0]})
    for event in payload["scenario"].get("events") or []:
        spawned = (event.get("payload") or {}).get("entity")
        if not isinstance(spawned, dict) or spawned.get("faction_id") != faction:
            continue
        state = spawned.get("initial_state") or {}
        position = state.get("position_m")
        if not isinstance(position, list) or len(position) != 3:
            continue
        state["position_m"] = [round(position[0] + shift, 3), position[1], position[2]]
        changes.append({"field": f"{event.get('id')}:{spawned.get('id')}.position_m.x",
                        "before": position[0], "after": state["position_m"][0]})
    return changes


def apply_anchor_shift(payload: dict, shifts: dict) -> list[dict]:
    """Move named units so they sit at an absolute x (metres), keeping y and z.

    Each entry is ``entity_id: [authored_x, target_x]``.  The authored x is a schema-internal
    reference (it is what the package declares), so the operation is idempotent without writing
    any provenance field into the closed package schema: a replay finds the current x already
    equal to the target and does nothing, and a unit the profile never touched (still at its
    authored x) is moved exactly once.
    """
    changes = []
    for entity in payload["scenario"].get("entities") or []:
        entry = shifts.get(entity.get("id"))
        if not entry:
            continue
        authored, target = float(entry[0]), float(entry[1])
        state = entity.get("initial_state") or {}
        position = state.get("position_m")
        if not isinstance(position, list) or len(position) != 3:
            continue
        current = position[0]
        if current in (target, authored):
            if current == authored:
                state["position_m"] = [target, position[1], position[2]]
                changes.append({"field": f"{entity['id']}.position_m.x",
                                "before": current, "after": target})
            continue
        raise ValueError(f"{entity.get('id')} is at x={current}, expected the authored {authored} "
                         f"or the calibrated {target}; refusing to guess")
    return changes


def apply_standoff(payload: dict, back: float, faction: str = "red") -> list[dict]:
    """Move a faction's units back along -x by ``back`` metres.

    Kept for the record and for one-shot use; the profile below uses ``anchor_shifts`` instead,
    which is idempotent by construction (this one compounds if replayed, which drove TRK-001 to
    a 2000 m standoff and a 0.000 composite during calibration).
    """
    changes = []
    for entity in payload["scenario"].get("entities") or []:
        if entity.get("faction_id") != faction:
            continue
        state = entity.get("initial_state") or {}
        position = state.get("position_m")
        if not isinstance(position, list) or len(position) != 3:
            continue
        state["position_m"] = [round(position[0] - back, 3), position[1], position[2]]
        changes.append({"field": f"{entity['id']}.position_m.x",
                        "before": position[0], "after": state["position_m"][0]})
    return changes


def apply_zone_translation(payload: dict, shift: float | list) -> list[dict]:
    """Translate every declared zone by a fixed offset (all protected and warning zones alike).

    Used by the emergency-response calibration, where the dominant metric is arrival_fraction:
    moving the response zones away from the responders turns "arrive at all" into a scheduling
    problem.  Measured on ER-003 with the naive baseline: +0 m -> 0.896, +70 m -> 0.601.
    """
    dx, dy = (shift, 0.0) if not isinstance(shift, (list, tuple)) else (shift[0], shift[1])
    changes = []
    for zone in ((payload["scenario"].get("world") or {}).get("zones")) or []:
        coordinates = zone.get("coordinates_m") or []
        if not coordinates:
            continue
        zone["coordinates_m"] = [[round(point[0] + dx, 3), round(point[1] + dy, 3)]
                                 for point in coordinates]
        centroid = [round(sum(point[0] for point in coordinates) / len(coordinates), 3),
                    round(sum(point[1] for point in coordinates) / len(coordinates), 3)]
        changes.append({"field": f"zone[{zone.get('id')}].centroid",
                        "before": centroid,
                        "after": [round(centroid[0] + dx, 3), round(centroid[1] + dy, 3)]})
    return changes


def apply_zone_centroid(payload: dict, targets: dict, baseline: dict | None = None) -> list[dict]:
    """Move a declared protected zone to an absolute centroid x (metres).

    The zone position is the lever that actually moved the area-denial composite: the
    intruder reaches a forward zone earlier, so the defenders' intercept window shrinks.  The
    target is absolute, so replaying a profile never compounds a shift.
    """
    changes = []
    zones = ((payload["scenario"].get("world") or {}).get("zones")) or []
    for zone in zones:
        target = targets.get(zone.get("id"))
        if target is None:
            continue
        coordinates = zone.get("coordinates_m") or []
        if not coordinates:
            continue
        current = [round(sum(point[index] for point in coordinates) / len(coordinates), 3)
                   for index in (0, 1)]
        goal = [float(target), current[1]] if not isinstance(target, (list, tuple)) \
            else [float(target[0]), float(target[1])]
        if current == goal:
            continue
        delta = [goal[0] - current[0], goal[1] - current[1]]
        zone["coordinates_m"] = [[round(point[0] + delta[0], 3), round(point[1] + delta[1], 3)]
                                 for point in coordinates]
        changes.append({"field": f"zone[{zone.get('id')}].centroid",
                        "before": current, "after": goal})
    return changes


def apply_suppression(payload: dict, entries: list[dict]) -> list[dict]:
    """Declare a component-suppression event (the engine's own mechanism, used by TRK-008).

    Weakening a defender's capability is a structural difficulty lever: the policy must still
    cover the same protected area with fewer working components, which is pressure the metric
    parameters cannot create on their own.
    """
    changes = []
    events = payload["scenario"].setdefault("events", [])
    existing = {event.get("id") for event in events}
    for entry in entries:
        if entry["id"] in existing:
            continue
        events.append({
            "schema_version": "2.0", "id": entry["id"], "event_type": "component_suppression",
            "trigger": {"tick": entry.get("tick", 1)},
            "payload": {"target_entity_id": entry["target_entity_id"],
                        "component_ref": entry["component_ref"],
                        "duration_ticks": entry["duration_ticks"]},
        })
        changes.append({"field": f"event[{entry['id']}]",
                        "before": None,
                        "after": f"suppress {entry['component_ref']} on "
                                 f"{entry['target_entity_id']} for "
                                 f"{entry['duration_ticks']} ticks"})
    return changes


def tune(tree: Path, profile_name: str, dry_run: bool = False) -> dict:
    if profile_name not in PROFILES:
        raise ValueError(f"unknown profile {profile_name}; known: {sorted(PROFILES)}")
    report = {"schema": "competition-retune@1", "profile": profile_name, "tree": str(tree),
              "dry_run": dry_run, "scenarios": []}
    for package, spec in PROFILES[profile_name].items():
        path = tree / package / "scenario.yaml"
        if not path.is_file():
            report["scenarios"].append({"package": package, "status": "missing"})
            continue
        payload = load_yaml(path)
        before = copy.deepcopy(payload)
        changes = []
        if "horizon" in spec:
            changes += apply_horizon(payload, spec["horizon"])
        changes += apply_metric_bounds(payload, spec.get("maximum_gap_ticks"),
                                       spec.get("maximum_age_ticks"))
        if spec.get("zone_shift_m"):
            changes += apply_zone_translation(payload, spec["zone_shift_m"])
        if spec.get("zone_centroids"):
            changes += apply_zone_centroid(payload, spec["zone_centroids"])
        if spec.get("anchor_shifts"):
            changes += apply_anchor_shift(payload, spec["anchor_shifts"])
        if spec.get("standoff_m"):
            changes += apply_standoff(payload, spec["standoff_m"], spec.get("standoff_faction",
                                                                           "red"))
        if spec.get("contact_shift_m"):
            changes += apply_contact_shift(payload, spec["contact_shift_m"],
                                           spec.get("contact_faction", "blue"))
        if spec.get("zone_shifts"):
            changes += apply_zone_shift(payload, spec["zone_shifts"],
                                        spec.get("zone_baseline_centroids"))
        if spec.get("suppressions"):
            changes += apply_suppression(payload, spec["suppressions"])
        if spec.get("thresholds"):
            changes += apply_thresholds(payload, spec["thresholds"])
        if changes and not dry_run:
            dump_yaml(path, payload)
        report["scenarios"].append({
            "package": package, "status": "changed" if changes else "unchanged",
            "changes": changes, "change_count": len(changes),
            "horizon_before": horizon_of(before["scenario"]),
            "horizon_after": horizon_of(payload["scenario"]),
        })
    report["changed_packages"] = sum(1 for row in report["scenarios"]
                                     if row["status"] == "changed")
    report["total_changes"] = sum(row.get("change_count", 0) for row in report["scenarios"])
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    report = tune(args.tree, args.profile, args.dry_run)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    print(json.dumps({"profile": report["profile"], "changed": report["changed_packages"],
                      "changes": report["total_changes"], "dry_run": report["dry_run"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
