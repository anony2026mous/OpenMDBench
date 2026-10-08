"""D1' task-attribute annotation helper (read-only, design inputs only).

Checklist v9 asks for D1' as a *prior* task property: six dimensions scored 1-3 from the
task design, before any result is looked at.  This module therefore:

* reads only design inputs (scenario packages, the competition design contracts, the grid
  environment reference);
* refuses to consume any result artifact or any result-bearing field, so an annotation
  cannot silently become an ex-post description;
* keeps the six scores human-owned - it collects the design signals and the rubric, and
  compiles whatever the annotator wrote, but never invents a score.

Usage:
    python d1prime_annotation.py extract --source <source_codes> --grid-doc <md> \
        --contracts <json> --output <worksheet.json>
    python d1prime_annotation.py compile --worksheet <worksheet.json> \
        --annotations <annotations.json> --output <table.md> [--csv <table.csv>] \
        [--frozen <frozen.json>]
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

# The six dimensions and their verbatim rubric bands from checklist v9 section 1.2.
DIMENSIONS = {
    "a_decision_form": {
        "label": "D1′-a 决策形态主导",
        "bands": {1: "连续控制/几何拦截为主", 2: "混合", 3: "分配/调度/意图推断为主"},
    },
    "b_goal_openness": {
        "label": "D1′-b 目标开放性",
        "bands": {1: "目标是固定几何位置/数量", 2: "半开放（有限候选目标）",
                  3: "目标需要语义理解/自然语言描述"},
    },
    "c_state_space": {
        "label": "D1′-c 状态空间主导",
        "bands": {1: "连续高维物理状态为主", 2: "混合", 3: "语义/离散/关系状态为主"},
    },
    "d_time_scale": {
        "label": "D1′-d 决策时间尺度",
        "bands": {1: "毫秒级实时控制为主", 2: "混合", 3: "秒级以上 deliberation 为主"},
    },
    "e_opponent_diversity": {
        "label": "D1′-e 对手策略多样性",
        "bands": {1: "固定脚本/可预测模式", 2: "有限策略切换",
                  3: "需要意图推断/欺骗识别/自适应"},
    },
    "f_rule_complexity": {
        "label": "D1′-f 规则/协议复杂度",
        "bands": {1: "无规则约束", 2: "简单规则", 3: "复杂交互规则/交战约束/合规要求"},
    },
}
# Result-bearing field names, matched as whole tokens so a design field such as
# ``velocity_mps`` or ``return_to_base`` cannot trip the guard by substring accident.
RESULT_FIELD_TOKENS = frozenset({
    "score", "scores", "score_total", "outcome", "reward", "rewards", "winner", "elo",
    "composite", "success_rate", "delta", "dv", "dp", "de", "di", "blue_score",
    "defender_score", "reference_planner", "reference_executor", "reference_full"})
# Keys that legitimately contain a guarded token but are design-side declarations.
DESIGN_ALLOWED_KEYS = frozenset({"score_metrics", "score_state", "scoring", "score_windows"})
RESULT_KEYS = re.compile(r"[^a-z0-9]+")
DESIGN_FIELDS = ("schema_version", "scenario_id", "display_name", "factions", "relationships",
                 "entities", "formations", "events", "world", "mission_states", "mission_rules",
                 "scoring", "controller_slots", "controller_policy", "score_metrics")


class DesignOnlyViolation(RuntimeError):
    """Raised when an input looks like a result artifact rather than a design document."""


# A design document is read from an allowed location; a result artifact never is.
RESULT_PATH_PATTERNS = (re.compile(r"artifacts/"), re.compile(r"/results?/"),
                        re.compile(r"experiments/"), re.compile(r"\.ckpt\.json$"))


def assert_design_path(path: Path) -> None:
    text = str(path).replace("\\", "/")
    for pattern in RESULT_PATH_PATTERNS:
        if pattern.search(text):
            raise DesignOnlyViolation(
                f"refusing to read a result artifact while annotating a prior property: {text}")


def assert_design_value(value, where: str = "value") -> None:
    """Reject result-bearing tokens anywhere in a payload the tool is about to compile."""
    if isinstance(value, dict):
        for key, item in value.items():
            name = str(key)
            if name not in DESIGN_ALLOWED_KEYS:
                tokens = {token for token in RESULT_KEYS.split(name.lower()) if token}
                if tokens & RESULT_FIELD_TOKENS:
                    raise DesignOnlyViolation(
                        f"field '{name}' at {where} looks like a result quantity")
            assert_design_value(item, f"{where}.{name}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            assert_design_value(item, f"{where}[{index}]")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scenario_design(package_dir: Path) -> dict:
    path = package_dir / "scenario.yaml"
    assert_design_path(path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    scenario = payload.get("scenario") or {}
    # Only the design envelope is read out of the package; mission rules legitimately
    # declare win/lose *conditions* (a design statement), so the token guard is applied to
    # the extracted facts, never to a declared rule's own vocabulary.
    return {key: scenario[key] for key in DESIGN_FIELDS if key in scenario}


def metric_names(scoring: dict) -> list[str]:
    """Scoring metric names, tolerating both the dict and list-of-records package shapes."""
    raw = scoring.get("metrics") or []
    if isinstance(raw, dict):
        return sorted(str(key) for key in raw)
    names = []
    for item in raw:
        if isinstance(item, dict):
            names.append(str(item.get("id") or item.get("metric") or item.get("name") or "?"))
        else:
            names.append(str(item))
    return sorted(set(names))


def summarize(scenario: dict) -> dict:
    """Design-side facts an annotator needs, with no result quantity anywhere."""
    entities = scenario.get("entities") or []
    events = scenario.get("events") or []
    rules = scenario.get("mission_rules") or []
    scoring = scenario.get("scoring") or {}
    worlds = scenario.get("world") or {}
    facts = {
        "display_name": scenario.get("display_name"),
        "factions": [f.get("id") for f in (scenario.get("factions") or [])],
        "entity_count": len(entities),
        "entity_platforms": sorted({e.get("platform_ref", "") for e in entities
                                    if isinstance(e, dict)}),
        "entity_kinds": sorted({str(e.get("id", "")).split(".")[0] for e in entities
                                if isinstance(e, dict)}),
        "formation_count": len(scenario.get("formations") or []),
        "event_count": len(events),
        "event_types": sorted({e.get("event_type") or e.get("type") for e in events
                               if isinstance(e, dict) and (e.get("event_type") or e.get("type"))}),
        "mission_rule_count": len(rules),
        "mission_rule_kinds": sorted({str((r or {}).get("condition", {}).get("operator")
                                       or (r or {}).get("operator") or "")
                                      for r in rules if isinstance(r, dict)})[:12],
        "scoring_metrics": metric_names(scoring),
        "scoring_aggregation": scoring.get("aggregation"),
        "world_keys": sorted(worlds.keys()) if isinstance(worlds, dict) else [],
        "controller_policy_present": bool(scenario.get("controller_policy")),
        "controller_slots": len(scenario.get("controller_slots") or []),
    }
    assert_design_value(facts, "facts")
    return facts


def collect_signals(facts: dict, extra: dict | None = None) -> dict:
    """Point each dimension at the design fields that bear on it (no scoring)."""
    signals = {
        "a_decision_form": ["entity_platforms", "entity_count", "mission_rule_kinds",
                            "scoring_metrics"],
        "b_goal_openness": ["mission_rule_kinds", "mission_rule_count", "world_keys",
                            "display_name"],
        "c_state_space": ["world_keys", "event_types", "controller_slots"],
        "d_time_scale": ["world_keys", "controller_policy_present", "event_types"],
        "e_opponent_diversity": ["event_types", "formation_count", "display_name"],
        "f_rule_complexity": ["mission_rule_kinds", "mission_rule_count", "scoring_metrics"],
    }
    if extra:
        signals = {name: fields + list(extra.get(name, [])) for name, fields in signals.items()}
    return {name: {field: facts.get(field) for field in fields} for name, fields in signals.items()}


def load_contracts(path: Path) -> dict:
    assert_design_path(path)
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    rows = {}
    for scenario in payload.get("scenarios", []):
        identity = scenario.get("id")
        if not identity:
            continue
        rows[identity] = {key: scenario.get(key) for key in
                          ("id", "template", "name", "challenge", "mechanisms", "metrics",
                           "success", "replacement")}
    return rows


# ---------------------------------------------------------------------------
# Derivation for the 28 competition scenarios.
#
# Their design is declared as mechanism tags plus a contract sentence, not as a parameter
# table, so the annotation is derived from a documented per-family baseline raised by
# dimension floors.  Every contribution is recorded in the row's evidence, and a human
# override file can replace any value.  This keeps the annotation reproducible instead of
# being 28 independent judgement calls.
# ---------------------------------------------------------------------------
FAMILY_BASELINES = {
    "REC": {"a_decision_form": 3, "b_goal_openness": 2, "c_state_space": 2,
            "d_time_scale": 2, "e_opponent_diversity": 2, "f_rule_complexity": 2},
    "TRK": {"a_decision_form": 2, "b_goal_openness": 1, "c_state_space": 1,
            "d_time_scale": 2, "e_opponent_diversity": 1, "f_rule_complexity": 2},
    "AD": {"a_decision_form": 1, "b_goal_openness": 1, "c_state_space": 1,
           "d_time_scale": 1, "e_opponent_diversity": 2, "f_rule_complexity": 2},
    "ER": {"a_decision_form": 3, "b_goal_openness": 1, "c_state_space": 1,
           "d_time_scale": 1, "e_opponent_diversity": 1, "f_rule_complexity": 2},
}
MECHANISM_FLOORS = {
    # task structure that pushes the core difficulty into scheduling / deliberation
    "multiple_sectors": {"a_decision_form": 3, "c_state_space": 2},
    "disjoint_search_sectors": {"a_decision_form": 3, "c_state_space": 2},
    "limited_parallel_assets": {"a_decision_form": 3, "c_state_space": 2},
    "distributed_observers": {"a_decision_form": 3, "c_state_space": 3},
    "communication_delay": {"c_state_space": 2, "d_time_scale": 3},
    "delayed_contact_spawn": {"d_time_scale": 3},
    "multiple_waves": {"a_decision_form": 3, "d_time_scale": 2},
    "staggered_waves": {"a_decision_form": 3, "d_time_scale": 2},
    "concurrent_arrivals": {"a_decision_form": 3},
    "multiple_public_alerts": {"a_decision_form": 3, "d_time_scale": 2},
    "delayed_public_confirmation": {"a_decision_form": 3, "d_time_scale": 3},
    "priority_weighted_arrival_fraction": {"a_decision_form": 3},
    "finite_resources": {"a_decision_form": 3},
    # state-space character
    "opaque_identifiers": {"c_state_space": 3},
    "crossing_tracks": {"c_state_space": 3, "e_opponent_diversity": 3},
    "piecewise_waypoint_motion": {"c_state_space": 2, "e_opponent_diversity": 2},
    "weather_change": {"c_state_space": 2},
    "sensor_degradation": {"c_state_space": 2},
    "reduced_sensor_footprint": {"c_state_space": 2},
    "intermittent_sensor_availability": {"c_state_space": 2, "d_time_scale": 3},
    "jamming_interval": {"c_state_space": 3, "e_opponent_diversity": 3},
    "air_surface_contacts": {"c_state_space": 3},
    # deception / intent inference
    "diversion_routes": {"e_opponent_diversity": 3, "b_goal_openness": 2},
    "protected_neutral_traffic": {"e_opponent_diversity": 3, "f_rule_complexity": 3},
    "delayed_public_message": {"e_opponent_diversity": 2, "f_rule_complexity": 3},
    # rules and compliance
    "zone_activation": {"f_rule_complexity": 3},
    "hazard_exposure": {"f_rule_complexity": 3},
    "preissued_route": {"f_rule_complexity": 3},
    "alternate_route": {"f_rule_complexity": 3},
    "component_suppression": {"f_rule_complexity": 2, "a_decision_form": 3},
    "alternate_responder": {"f_rule_complexity": 2, "a_decision_form": 3},
    "priority_destination": {"f_rule_complexity": 3, "a_decision_form": 3},
    "moving_surface_contact": {"d_time_scale": 2},
    "moving_contacts": {"d_time_scale": 2},
    "diverging_contacts": {"a_decision_form": 3},
    "air_surface_observer_handover": {"a_decision_form": 3, "c_state_space": 3},
    "sensor_availability_windows": {"c_state_space": 2},
    "air_surface_shore_relay": {"a_decision_form": 3, "c_state_space": 3},
    "one_search_sector": {"c_state_space": 1},
    "shore_sensor_gap": {"c_state_space": 2},
    "separated_search_cells": {"c_state_space": 2},
    "one_protected_zone": {"a_decision_form": 1},
    "two_protected_zones": {"a_decision_form": 3},
    "outer_inner_zones": {"a_decision_form": 2, "f_rule_complexity": 3},
    "multiple_protected_zones": {"a_decision_form": 3},
}


def derive_competition_scores(contract: dict) -> tuple[dict, dict]:
    """Return (scores, evidence) for one competition scenario from its design tags."""
    family = None
    for candidate in FAMILY_BASELINES:
        if str(contract.get("id", "")).upper().startswith("MD-" + candidate):
            family = candidate
            break
    if family is None:
        raise ValueError("no family baseline for " + str(contract.get("id")))
    scores = dict(FAMILY_BASELINES[family])
    evidence = {name: [f"family baseline {family}"] for name in DIMENSIONS}
    for mechanism in contract.get("mechanisms") or []:
        floors = MECHANISM_FLOORS.get(mechanism)
        if not floors:
            continue
        for name, floor in floors.items():
            if floor > scores[name]:
                scores[name] = floor
                evidence[name].append(f"mechanism '{mechanism}' -> floor {floor}")
    return scores, {name: "; ".join(items) for name, items in evidence.items()}


def merge_override(scores: dict, override: dict | None) -> dict:
    if not override:
        return scores
    merged = dict(scores)
    for name, value in override.items():
        if name not in DIMENSIONS:
            raise ValueError(f"override names an unknown dimension: {name}")
        if value not in (1, 2, 3):
            raise ValueError(f"override for {name} must be 1, 2 or 3")
        merged[name] = value
    return merged


GRID_TIERS = ("simple", "medium", "complex")
# The IE scenario generators carry the authoritative design statements (axis, purpose,
# timeline, notes) for each HF scenario.  They are read with ``ast`` - never executed - and
# only the declared design strings are taken.
IE_DESIGN_DOCS = ("openmd/code/eval/_gen_ie_set.py", "openmd/code/eval/_gen_ie_set_ext.py")
TIMELINE_FIELDS = frozenset({"label", "spawn_tick", "count", "axis", "behavior"})


def _literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return None


def _arg_count(node) -> int:
    """Count declared entities in an argument that may be a list literal or a call.

    ``red_uavs=[...]`` is a literal, but the first scenarios build it through helpers such
    as ``red_uav_force([(x, y, alt, heading)], target)``; counting the inner list keeps the
    force composition visible without evaluating the generator.
    """
    if node is None:
        return 0
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return len(node.elts)
    if isinstance(node, ast.Call):
        return sum(_arg_count(arg) for arg in node.args if isinstance(arg, (ast.List, ast.Tuple)))
    return 0


def _keywords(call) -> dict:
    out = {}
    for keyword in call.keywords or []:
        if keyword.arg is None:
            continue
        out[keyword.arg] = _literal(keyword.value)
        out[f"__count__{keyword.arg}"] = _arg_count(keyword.value)
    return out


def _timeline(value) -> list[dict]:
    """Keep only design-declared timeline fields; drop keys whose tokens look like results."""
    rows = []
    for item in value or []:
        if not isinstance(item, dict):
            continue
        row = {key: item[key] for key in TIMELINE_FIELDS if key in item}
        if row:
            rows.append(row)
    return rows


def ie_design_statements(root: Path) -> dict:
    """Map ``IE-nn`` to its declared design statement, parsed from the generators."""
    statements = {}
    for relative in IE_DESIGN_DOCS:
        path = root / relative
        if not path.is_file():
            continue
        assert_design_path(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        pending_comments = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                    and isinstance(node.value.value, str) and node.lineno < 200:
                pending_comments.append(node.value.value)
            if not isinstance(node, ast.Call) or not _is_spec_call(node):
                continue
            arguments = [_literal(arg) for arg in node.args]
            keywords = _keywords(node)
            strings = [arg for arg in arguments if isinstance(arg, str)]
            public_id = next((arg for arg in strings if arg.startswith("IE-")), None)
            if not public_id:
                continue
            zh = strings[strings.index(public_id) + 1] if strings.index(public_id) + 1 < len(strings) else None
            statements[public_id[:5]] = {
                "public_id": public_id,
                "display_name_zh": zh,
                "timeline": _timeline(keywords.get("timeline")),
                "notes": keywords.get("notes"),
                "red_uavs": keywords.get("__count__red_uavs", 0),
                "red_boats": keywords.get("__count__red_boats", 0),
                "decoys": keywords.get("__count__decoys", 0),
                "blue_uavs": keywords.get("blue_uavs"),
                "blue_usvs": keywords.get("blue_usvs"),
                "protected": keywords.get("protected"),
                "duration_ticks": keywords.get("duration"),
                "spawn_ticks": sorted((keywords.get("spawn_ticks") or {}).values()),
                "source": relative,
            }
    return statements


def _is_spec_call(node: ast.Call) -> bool:
    """Both ``spec(...)`` and ``base.spec(...)`` declare an IE scenario."""
    target = node.func
    if isinstance(target, ast.Name):
        return target.id == "spec"
    return (isinstance(target, ast.Attribute) and target.attr == "spec"
            and isinstance(target.value, ast.Name) and target.value.id == "base")


def grid_tier_designs(doc_path: Path) -> dict:
    """Pull the three difficulty tiers' parameter table out of the grid reference doc."""
    assert_design_path(doc_path)
    text = Path(doc_path).read_text(encoding="utf-8")
    start = text.find("| 参数（遗留字段名） |")
    if start < 0:
        raise ValueError("grid difficulty parameter table not found in " + str(doc_path))
    block = text[start:].split("\n\n", 1)[0].splitlines()
    header = [cell.strip() for cell in block[0].strip("|").split("|")]
    tiers = {}
    for line in block[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != len(header):
            continue
        parameter = cells[0]
        for index, tier in enumerate(header[1:], start=1):
            if tier in GRID_TIERS:
                tiers.setdefault(tier, {"parameters": {}})
                tiers[tier]["parameters"][parameter] = cells[index]
    if set(tiers) != set(GRID_TIERS):
        raise ValueError(f"expected all three grid tiers, found {sorted(tiers)}")
    for tier in GRID_TIERS:
        params = tiers[tier]["parameters"]
        tiers[tier]["scenario_id"] = f"GRID-{tier.upper()}"
        tiers[tier]["display_name"] = (f"grid 20x20 港防（{tier} 档）")
        tiers[tier]["facts"] = {
            "instructions": params.get("instructions"),
            "wave_count": params.get("wave_count"),
            "anomaly_probability": params.get("anomaly 概率/步"),
            "comm_delay_steps": params.get("comm_delay（步）"),
            "comm_loss": params.get("comm_loss"),
            "action_noise": params.get("action_noise"),
            "initial_ammo_per_usv": params.get("initial_ammo（/USV）"),
            "dynamic_obstacles": params.get("dynamic_obstacles"),
            "deceptive_transports": params.get("进攻方 transports（num_red_transports）"),
            "attacker_hunts_uav": params.get("进攻方 hunts_uav（red_hunts_uav）"),
        }
    return tiers


def extract(source_root: Path, grid_doc: Path, contracts_path: Path,
            design_root: Path | None = None) -> dict:
    formal = source_root / "scenarios" / "formal"
    registry = yaml.safe_load((formal / "registry.yaml").read_text(encoding="utf-8"))
    inputs = {"registry.yaml": sha256_file(formal / "registry.yaml"),
              str(contracts_path): sha256_file(contracts_path),
              str(grid_doc): sha256_file(grid_doc)}
    statements = ie_design_statements(design_root or source_root.parents[1])
    for relative in IE_DESIGN_DOCS:
        path = (design_root or source_root.parents[1]) / relative
        if path.is_file():
            inputs[relative] = sha256_file(path)
    records = []
    for entry in registry["scenarios"]:
        public_id = entry["public_id"]
        if not public_id.startswith("IE-"):
            continue
        package_dir = formal / entry["package"]
        design = scenario_design(package_dir)
        facts = summarize(design)
        inputs[str(package_dir / "scenario.yaml")] = sha256_file(package_dir / "scenario.yaml")
        record = {"group": "hf_ie", "public_id": public_id, "package": entry["package"],
                  "facts": facts, "signals": collect_signals(facts),
                  "design_fields": sorted(design.keys())}
        statement = statements.get(public_id[:5])
        if statement:
            assert_design_value(statement, public_id)
            record["design_statement"] = statement
            record["signals"] = collect_signals(
                facts, {"a_decision_form": ["statement.timeline", "statement.notes"],
                        "b_goal_openness": ["statement.protected"],
                        "e_opponent_diversity": ["statement.decoys", "statement.notes"],
                        "f_rule_complexity": ["statement.notes"]})
        records.append(record)
    competition = source_root / "scenarios" / "competition_v1"
    contracts = load_contracts(contracts_path)
    for package_dir in sorted(item for item in competition.iterdir() if item.is_dir()):
        design = scenario_design(package_dir)
        facts = summarize(design)
        contract = contracts.get(package_dir.name.upper().replace("_", "-"))
        if contract is None:
            contract_id = "-".join(package_dir.name.upper().split("_")[:3])
            contract = contracts.get(contract_id)
        extra = {"a_decision_form": ["contract.mechanisms"], "b_goal_openness": ["contract.success"],
                 "e_opponent_diversity": ["contract.mechanisms"],
                 "f_rule_complexity": ["contract.metrics"]} if contract else {}
        record = {"group": "competition_v1",
                  "public_id": package_dir.name.upper().replace("_", "-"),
                  "package": package_dir.name, "facts": facts,
                  "signals": collect_signals(facts, extra),
                  "design_fields": sorted(design.keys())}
        if contract:
            record["contract"] = contract
            scores, evidence = derive_competition_scores(contract)
            record["derived_scores"] = scores
            record["derived_evidence"] = evidence
            record["derivation"] = ("family baseline + mechanism floors; every contribution "
                                    "listed in derived_evidence")
            inputs[str(contracts_path) + "#" + contract["id"]] = sha256_file(contracts_path)
        inputs[str(package_dir / "scenario.yaml")] = sha256_file(package_dir / "scenario.yaml")
        records.append(record)
    for tier, payload in grid_tier_designs(grid_doc).items():
        records.append({"group": "grid",
                        "public_id": payload["scenario_id"],
                        "package": f"grid_env ({tier})",
                        "facts": payload["facts"],
                        "signals": collect_signals(payload["facts"],
                                                   {"a_decision_form": ["instructions", "wave_count"],
                                                    "d_time_scale": ["instructions"],
                                                    "e_opponent_diversity": ["deceptive_transports"],
                                                    "f_rule_complexity": ["instructions"]}),
                        "design_fields": ["grid_environment_reference.md 参数表"]})
    return {"schema": "d1prime-worksheet@1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "rubric": DIMENSIONS,
            "rubric_source": "checklist v9 section 1.2 (verbatim bands)",
            "design_inputs_sha256": inputs,
            "scenario_count": len(records),
            "scenarios": records}


def compile_payload(worksheet: dict, annotations: dict, overrides: dict | None = None) -> dict:
    """Merge scores with the worksheet; refuse to invent a score that has no basis.

    A scenario either carries a human annotation, or it carries derived scores from the
    competition mechanism table.  Anything else is an error rather than a default.
    """
    rows = []
    missing = []
    overrides = overrides or {}
    for record in worksheet["scenarios"]:
        public_id = record["public_id"]
        annotation = annotations.get(public_id) or {}
        override = overrides.get(public_id)
        if annotation:
            scores = annotation.get("scores") or {}
            evidence = annotation.get("evidence") or {}
            note = annotation.get("note") or ""
            uncertain = annotation.get("uncertain") or []
            source = "annotated"
        elif record.get("derived_scores"):
            scores = record["derived_scores"]
            evidence = record.get("derived_evidence") or {}
            note = record.get("derivation") or ""
            uncertain = []
            source = "derived-from-contract"
        else:
            missing.append(public_id)
            continue
        scores = merge_override(scores, override)
        if override:
            note = (note + f"；人工覆盖 {override}").strip("；")
            source = source + "+override"
        gaps = [name for name in DIMENSIONS if not isinstance(scores.get(name), int)
                or scores[name] not in (1, 2, 3)]
        if gaps:
            raise ValueError(f"{public_id} has invalid scores for {gaps}")
        values = [scores[name] for name in DIMENSIONS]
        rows.append({
            "public_id": public_id,
            "group": record["group"],
            "scores": {name: scores[name] for name in DIMENSIONS},
            "prior_score": round(sum(values) / len(values), 3),
            "score_sum": sum(values),
            "evidence": evidence,
            "uncertain": uncertain,
            "note": note,
            "source": source,
        })
    if missing:
        raise ValueError(f"no score basis for {len(missing)} scenarios: {missing[:5]}")
    strong = sum(1 for row in rows if row["prior_score"] >= 2.0)
    return {"schema": "d1prime-table@1",
            "compiled_utc": datetime.now(timezone.utc).isoformat(),
            "weighting": "equal weight over the six dimensions (weighted variant needs the "
                         "analyst's weights and must be issued as a separate version)",
            "dimensions": DIMENSIONS,
            "design_inputs_sha256": worksheet["design_inputs_sha256"],
            "scenario_count": len(rows),
            "rows": rows,
            "by_group": {group: sum(1 for row in rows if row["group"] == group)
                         for group in sorted({row["group"] for row in rows})},
            "by_source": {source: sum(1 for row in rows if row["source"].startswith(source))
                          for source in ("annotated", "derived-from-contract")},
            "summary": {"llm_strong_side_count": strong, "total": len(rows)}}


def render_markdown(table: dict) -> str:
    header = ["场景", "组"] + [meta["label"] for meta in DIMENSIONS.values()] + ["先验得分", "不确定维", "依据/备注"]
    lines = ["# D1′ 任务属性先验标注表", "",
             "> 依据：任务设计声明（scenario.yaml / SCENARIO_CONTRACTS.json / "
             "grid_environment_reference.md 参数表）。**不含任何实验结果**。",
             "> 计分：6 维等权均值（1–3 分）。",
             "",
             "| " + " | ".join(header) + " |",
             "|" + "---|" * len(header)]
    for row in table["rows"]:
        evidence = "；".join(f"{name}={value}" for name, value in (row["evidence"] or {}).items())
        note = " ".join(filter(None, [evidence, row["note"]]))
        lines.append("| " + " | ".join(
            [row["public_id"], row["group"]]
            + [str(row["scores"][name]) for name in DIMENSIONS]
            + [f"{row['prior_score']:.2f}",
               "、".join(row["uncertain"]) or "—",
               note.replace("|", "/")]) + " |")
    lines += ["", "## 维度定义（引自清单 v9 §1.2）", ""]
    for name, meta in DIMENSIONS.items():
        bands = "；".join(f"{point} 分 = {text}" for point, text in meta["bands"].items())
        lines.append(f"- **{meta['label']}**：{bands}")
    return "\n".join(lines) + "\n"


def write_csv(table: dict, path: Path) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["public_id", "group"] + list(DIMENSIONS) + ["prior_score", "score_sum",
                                                                    "uncertain", "note"])
        for row in table["rows"]:
            writer.writerow([row["public_id"], row["group"]]
                            + [row["scores"][name] for name in DIMENSIONS]
                            + [row["prior_score"], row["score_sum"],
                               "|".join(row["uncertain"]), row["note"]])


def freeze(table: dict, annotations_path: Path, out_path: Path) -> dict:
    payload = {
        "schema": "d1prime-frozen@1",
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "reason": ("锁定先验标注，供第二标注人独立标注与 κ 计算；相关性与结果分析必须在此"
                   "文件生成之后进行。"),
        "annotations_sha256": sha256_file(annotations_path),
        "design_inputs_sha256": table["design_inputs_sha256"],
        "rows": [{"public_id": row["public_id"], "scores": row["scores"],
                  "prior_score": row["prior_score"]} for row in table["rows"]],
    }
    payload["content_sha256"] = hashlib.sha256(
        json.dumps(payload["rows"], sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    Path(out_path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    extract_cmd = sub.add_parser("extract", help="collect design signals into a worksheet")
    extract_cmd.add_argument("--source", type=Path, required=True)
    extract_cmd.add_argument("--grid-doc", type=Path, required=True)
    extract_cmd.add_argument("--contracts", type=Path, required=True)
    extract_cmd.add_argument("--design-root", type=Path,
                             help="project root holding openmd/code/eval generators")
    extract_cmd.add_argument("--output", type=Path, required=True)

    compile_cmd = sub.add_parser("compile", help="merge human scores and render the table")
    compile_cmd.add_argument("--worksheet", type=Path, required=True)
    compile_cmd.add_argument("--annotations", type=Path, required=True)
    compile_cmd.add_argument("--output", type=Path, required=True)
    compile_cmd.add_argument("--csv", type=Path)
    compile_cmd.add_argument("--table-json", type=Path,
                             help="machine-readable compiled table for the ledger merge")
    compile_cmd.add_argument("--frozen", type=Path)

    args = parser.parse_args()
    if args.command == "extract":
        payload = extract(args.source, args.grid_doc, args.contracts, args.design_root)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
        print(json.dumps({"scenarios": payload["scenario_count"],
                          "design_inputs": len(payload["design_inputs_sha256"])},
                         ensure_ascii=False))
        return
    worksheet = json.loads(args.worksheet.read_text(encoding="utf-8"))
    annotations = json.loads(args.annotations.read_text(encoding="utf-8"))
    table = compile_payload(worksheet, annotations)
    args.output.write_text(render_markdown(table), encoding="utf-8")
    if args.csv:
        write_csv(table, args.csv)
    if args.table_json:
        Path(args.table_json).write_text(
            json.dumps(table, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.frozen:
        freeze(table, args.annotations, args.frozen)
    print(json.dumps({"rows": table["scenario_count"], "summary": table["summary"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
