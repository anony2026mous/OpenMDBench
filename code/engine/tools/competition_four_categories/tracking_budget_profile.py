"""Versioned, data-only reference budget transformation; loaders never write packages.

DEF-P3 follows task_settings_v2.0_parameterized.md section3.1: two UAVs,
two-to-three USVs and multiple shore sensors. Positions remain explicitly
UNVALIDATED deployment assumptions for a controlled native feasibility study.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import yaml

from .build import PACKAGES, entity, selector

PROFILES = ("current", "DEF-P3", "legacy-four-observers")
REFERENCE = Path("C:/Users/沉倚/Downloads/task_settings_v2.0_parameterized.md")
ADDITIONS = (
    ("unit.r05", "surface", [250., -100., 0.]),
    ("unit.r06", "surface", [300., 100., 0.]),
    ("unit.r07", "shore", [600., 300., 0.]),
)


def load_profile(number=8, profile="current"):
    if number != 8 or profile not in PROFILES:
        raise ValueError("budget calibration is scoped to TRK008 and declared profiles")
    path = PACKAGES/f"md_trk_{number:03d}_standard"
    package = yaml.safe_load((path/"scenario.yaml").read_text(encoding="utf-8"))
    brief = json.loads((path/"public_brief.json").read_text(encoding="utf-8"))
    opponent = json.loads((path/"scripted_blue_policy.json").read_text(encoding="utf-8"))
    provenance = {"profile": profile, "canonical_package": path.as_posix(),
        "canonical_file_hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.iterdir() if p.is_file()},
        "calibration_only": True, "competition_accepted": False}
    if profile == "legacy-four-observers":
        from .tracking import tracking
        package, brief, _, opponent = tracking(8, asset_profile="legacy")
        provenance["input_factory"] = "tracking(8, asset_profile=legacy); historical four-observer design"
        return package, brief, opponent, provenance
    if profile == "current":
        return package, brief, opponent, provenance
    provenance.update(reference_path=str(REFERENCE), reference_sha256=hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
        reference_section="3.1 DEF-P3: 2 UAV, 2-3 USV, multiple shore sensors",
        declared_additions=[{"entity_id": i, "domain": d, "position_m": p} for i, d, p in ADDITIONS],
        deployment_status="UNVALIDATED initial deployment; not real-world force design")
    apply_def_p3(package, brief, status="calibration_only_not_promoted")
    brief["difficulty"] = "calibration-def-p3"
    return package, brief, opponent, provenance


def apply_def_p3(package, brief, *, status="candidate_reference_budget"):
    """Apply the declared additions, or verify an already-applied exact profile.

This mutates only the supplied in-memory document. It never changes a file,
target plan, event, threshold, time window or original entity definition.
"""
    s = package["scenario"]
    existing = {e["id"]: e for e in s["entities"]}
    declared = {i for i, _, _ in ADDITIONS}
    present = declared & set(existing)
    if present and present != declared:
        raise ValueError("partial DEF-P3 additions are not a valid profile")
    templates = {d: next(e for e in s["entities"] if e["id"] in brief["observers"]
                         and brief["observer_domains"][e["id"]] == d) for d in ("surface", "shore")}
    for identifier, domain, position in ADDITIONS:
        template = templates[domain]
        sensor = next(ref for ref in template["component_refs"] if ref.startswith("sensor."))
        added = entity(identifier, brief["evaluated_side"], domain, list(position), sensor)
        added["component_refs"] = deepcopy(template["component_refs"])
        control = deepcopy(next(c for c in s["controller_slots"] if c["id"] == template["controller_slot"]))
        control.update(id=added["controller_slot"], controller_id=f"agent.{identifier}",
                       controller_endpoint_ref=identifier, selector=selector([identifier]))
        if present:
            actual_control = next((c for c in s["controller_slots"] if c["id"] == control["id"]), None)
            if existing[identifier] != added or brief["observer_domains"].get(identifier) != domain or actual_control != control:
                raise ValueError("existing DEF-P3 asset differs from its declared definition")
            continue
        s["entities"].append(added)
        s["controller_slots"].append(control)
        brief["observers"].append(identifier)
        brief["observer_domains"][identifier] = domain
        if domain != "shore":
            brief["mobile_observers"].append(identifier)
    counts = {d: sum(brief["observer_domains"].get(i) == d for i in brief["observers"]) for d in ("air", "surface", "shore")}
    if counts != {"air": 2, "surface": 3, "shore": 2}:
        raise ValueError("DEF-P3 observer roster must be two air, three surface and two shore")
    if {e["id"] for e in s["entities"] if e["faction_id"] == brief["evaluated_side"]} != set(brief["observers"]):
        raise ValueError("DEF-P3 brief and actual friendly entities differ")
    reporters = [i for i in brief["observers"] if brief["observer_domains"][i] != "shore"]
    if brief["mobile_observers"] != reporters:
        raise ValueError("DEF-P3 mobile roster differs from actual domains")
    brief["track_reporting"]["reporter_ids"] = reporters
    for metric in s["scoring"]["metrics"]:
        metric["selector"] = selector(brief["observers"])
        params = metric["plugin_parameters"]
        if "observer_ids" in params:
            params["observer_ids"] = list(brief["observers"])
            params["observer_groups"] = [{"group_id": domain, "observer_ids": [i for i in brief["observers"]
                if brief["observer_domains"][i] == domain]} for domain in ("air", "surface", "shore")]
        if "reporter_ids" in params:
            params["reporter_ids"] = reporters
    brief["asset_profile"] = {"name": "DEF-P3", "air": 2, "surface": 3, "shore": 2,
                                "status": status}
