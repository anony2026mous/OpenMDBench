"""Versioned candidate-only picket control mapping with explicit evidence."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from .candidate_geometry import SURFACE_SHAPE_REF

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = Path(__file__).with_name("surface_parameters.json")
DYNAMICS_REF = "dynamics.competition-picket-usv@1.0.0"
PLATFORM_REF = "platform.competition-picket-usv@1.1.0"


def read_profile():
    p = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    if (p.get("schema_version") != "surface-navigation-profile@1.0"
        or p.get("status") != "native_proxy_straight_speed_mapping_validated"
        or p.get("holdout_all_passed") is not True or p.get("fidelity") != "UNVALIDATED_REAL_WORLD"):
        raise ValueError("candidate surface profile is not supported by the required evidence")
    if any(type(p.get(k)) not in (int, float) or not math.isfinite(p[k]) or p[k] <= 0
           for k in ("maximum_speed_mps", "maximum_nps", "nps_per_mps")):
        raise ValueError("surface profile parameters must be finite positive values")
    if p["maximum_speed_mps"] > 18 or p["maximum_nps"] > 240 or not math.isclose(
        p["maximum_nps"], p["maximum_speed_mps"]*p["nps_per_mps"], rel_tol=0., abs_tol=1e-10):
        raise ValueError("surface profile exceeds trusted bounds or has inconsistent units")
    if set(p.get("evidence", {})) != {"reference", "holdout", "maneuver"}:
        raise ValueError("complete calibration evidence set required")
    reports = {}
    for label, evidence in p["evidence"].items():
        path = (ROOT / evidence["path"]).resolve()
        if not path.is_relative_to(ROOT / "artifacts/competition_four_categories"):
            raise ValueError("calibration evidence is outside the candidate artifact scope")
        if hashlib.sha256(path.read_bytes()).hexdigest() != evidence["sha256"]:
            raise ValueError("surface calibration evidence hash mismatch")
        reports[label] = json.loads(path.read_text(encoding="utf-8"))
    reference, holdout, maneuver = (reports[k] for k in ("reference", "holdout", "maneuver"))
    rows = reference["summaries"]
    gain = sum(r["requested_speed_mps"]*r["settled_speed_mps"] for r in rows)/sum(r["requested_speed_mps"]**2 for r in rows)
    expected_ratio = reference["ratio_nps_per_mps"]/gain
    if (not math.isclose(p["nps_per_mps"], expected_ratio, rel_tol=0., abs_tol=1e-10)
        or holdout["ratio_nps_per_mps"] != p["nps_per_mps"] or maneuver["ratio_nps_per_mps"] != p["nps_per_mps"]
        or holdout["maximum_speed_mps"] != p["maximum_speed_mps"] or holdout["maximum_nps"] != p["maximum_nps"]
        or holdout["tolerances"] != p["tolerances"]
        or [r["requested_speed_mps"] for r in rows] != p["fit_speeds_mps"]
        or [r["requested_speed_mps"] for r in holdout["summaries"]] != p["holdout_speeds_mps"]):
        raise ValueError("profile parameters do not match measured calibration and holdout inputs")
    t = p["tolerances"]
    def passed(row):
        return (row["relative_error"] <= t["relative_speed_error"] and row["absolute_error_mps"] <= t["absolute_speed_error_mps"]
            and row["settling_span_mps"] <= t["settling_window_span_mps"]
            and row["heading_error_deg"] <= t["straight_heading_error_deg"] and row["lifecycle"] == "active")
    if not all(passed(r) for r in holdout["summaries"]):
        raise ValueError("native holdout measurements did not pass the declared tolerances")
    if (p["speed_reduction_passed"] != passed(maneuver["summaries"][0])
        or p["turn_full_steady_tolerances_passed"] != passed(maneuver["summaries"][1])
        or p["turn_characterization"] != maneuver["summaries"][1]):
        raise ValueError("maneuver status differs from native evidence")
    return p


def resources(templates):
    p = read_profile()
    dynamic = deepcopy(templates["dynamics.picket-usv"])
    dynamic.update(id=DYNAMICS_REF.split("@")[0], version="1.0.0")
    dynamic["content"].update(max_speed_mps=p["maximum_speed_mps"], max_nps=p["maximum_nps"])
    platform = deepcopy(templates["platform.picket-usv"])
    platform.update(id=PLATFORM_REF.split("@")[0], version="1.0.0")
    platform["content"]["allowed_dynamics"] = [DYNAMICS_REF]
    supported = deepcopy(platform)
    supported["version"] = "1.1.0"
    supported["content"]["collision_shape_ref"] = SURFACE_SHAPE_REF
    return [dynamic, platform, supported]
