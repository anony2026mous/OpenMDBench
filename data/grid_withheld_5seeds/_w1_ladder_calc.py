"""Difficulty-ladder calculator: predict each IE scenario's engagement balance
from the *declared* forces and the catalog envelopes, without running an episode.

Why this exists
---------------
Rounds 9-10 tried to build a monotone difficulty ladder by trial and error
(counts up, ingress distance down).  That calibration was invalid: the attacker
had no fire policy at all (see recorded run notes, s1 experiment §8), so every
measurement was taken on a model where the threat never shoots back.

This script replaces the guessing with closed-form bookkeeping over the same
numbers the engine uses:

    hits to neutralise a target   = ceil(1.0 / (magnitude * health_scale))
    rounds needed per neutralise  = hits / hit_probability
    attacker damage per round     = magnitude * health_scale

Measured effect facts (catalog/v2/ie_set.yaml):

    weapon.loitering-munition      effect.loitering-hit     0.6 x 0.5 = 0.30 / hit
                                   hit_probability 0.75, range 500-8000 m
    weapon.air-interceptor-munition effect.loitering-hit    0.30 / hit
                                   hit_probability 0.75, range 500-8000 m
    weapon.surface-missile         effect.surface-missile-hit 1.0 / hit
                                   hit_probability 0.50, range 0-3000 m
    weapon.suicide-warhead         effect.suicide-detonation  1.0 / hit
                                   hit_probability ?, range 0-30 m

Consequences that the old calibration got wrong:

  * ``kinetic-partial`` has ``health_scale 0.5`` and ``disabled_threshold 0.5``,
    so a loitering round does 0.30 health: **2 hits disable, 4 hits destroy**.
    Nothing about this weapon is one-shot.
  * A facility only counts as "lost" when ``destroyed``, so a strike package
    must land **4 hits on one facility** to trigger ``rule.assets-lost``.
  * One blue air-interceptor round cannot even disable a raider on its own
    (1 x 0.3 = 0.3 < 0.5 threshold).  ``blue_ammo=1`` therefore makes each
    defender UAV worth only ~0.375 neutralisations, which is why the old
    pressure table's ``blue_ammo=1`` rows were quietly disarming the defence.

Usage:
    python _w1_ladder_calc.py [--tag p11]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
EVAL = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

FORMAL = ROOT / "scenarios" / "formal"
RUNS = EVAL / "_w1_runs"

# ---- measured effect/envelope facts (kept as a table so drift is visible) ----
#
# 第 11 轮实测更正：**只有 `magnitude` 生效**。
# `openmdbench/combat/damage_v2.py` 第 440 行是
#     entity.health = max(0.0, entity.health - magnitude)
# 而失能/摧毁阈值在第 441/444 行是**硬编码常量** 0.0 / 0.5。
# catalog 里 `damage.*` 资源的 `health_scale` / `disabled_threshold` /
# `destroyed_threshold` 三个字段在整个引擎 Python 里**没有任何读取点**
# （`health_scale` 全仓库 0 命中）—— 是与 `reference_depth_m` 同类的死参数。
# 因此实际毁伤链是：
#   effect.loitering-hit      magnitude 0.6 → 1 发失能(0.4≤0.5)、2 发摧毁
#   effect.collision-impact   magnitude 0.5 → 1 发失能(0.5≤0.5)、2 发摧毁
#   effect.surface-missile-hit / suicide-detonation / interceptor-hit
#                             magnitude 1.0 → 1 发即摧毁
# 这条实测结论推翻了本脚本先前按 0.6×0.5=0.3/发 推出的"2 发失能、4 发摧毁"：
# 真实是 **1 发失能、2 发摧毁**，即一个设施只要被命中 2 发就被摧毁
# （p11 的 IE-01 实测 `shots_taken: 2` + `lifecycle: destroyed` 正好吻合）。
WEAPON_FACTS = {
    "weapon.loitering-munition@2.0.0": {
        "hit_probability": 0.75, "damage_per_hit": 0.60,
        "min_range_m": 500.0, "max_range_m": 8000.0,
    },
    "weapon.air-interceptor-munition@2.0.0": {
        "hit_probability": 0.75, "damage_per_hit": 0.60,
        "min_range_m": 500.0, "max_range_m": 8000.0,
    },
    "weapon.surface-missile@2.0.0": {
        "hit_probability": 0.50, "damage_per_hit": 1.00,
        "min_range_m": 0.0, "max_range_m": 3000.0,
    },
    "weapon.suicide-warhead@2.0.0": {
        "hit_probability": 0.95, "damage_per_hit": 1.00,
        "min_range_m": 0.0, "max_range_m": 30.0,
    },
}
# Engine constants, not catalog values (see the note above).
DISABLED_THRESHOLD = 0.5
FACILITY_HEALTH = 1.0

AMMO_TO_WEAPON = {
    "ammunition.loitering-munition@2.0.0": "weapon.loitering-munition@2.0.0",
    "ammunition.air-interceptor-munition@2.0.0": "weapon.air-interceptor-munition@2.0.0",
    "ammunition.surface-missile@2.0.0": "weapon.surface-missile@2.0.0",
    "ammunition.suicide-warhead@2.0.0": "weapon.suicide-warhead@2.0.0",
}

SCENARIOS = [
    "IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
    "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
    "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE",
    "IE-09-STAGGERED-WAVES",
    "IE-10-DUAL-AXIS-PINCER",
    "IE-11-DECOY-SCREEN",
    "IE-12-FOG-ONSET",
    "IE-13-DEEP-STRIKE",
    "IE-14-SATURATION-THREE-WAVE",
]


def hits_to_disable(damage_per_hit: float) -> int:
    """Hits needed to cross ``disabled_threshold`` (health 1.0 -> <= 0.5)."""
    if damage_per_hit <= 0.0:
        return 10**9
    remaining = FACILITY_HEALTH - DISABLED_THRESHOLD
    return max(1, int(-(-remaining // damage_per_hit)))


def hits_to_destroy(damage_per_hit: float) -> int:
    if damage_per_hit <= 0.0:
        return 10**9
    return max(1, int(-(-FACILITY_HEALTH // damage_per_hit)))


def package_for(public_id: str) -> Path | None:
    """Map a public id to its package directory.

    The generator names each package after the public id (``IE-01-SINGLE-TARGET``
    -> ``ie_01_single_target``); ``scenario_id`` inside the YAML is a different
    string (``ie-01-single-target.v1``), so it is only used as a fallback.
    """
    direct = FORMAL / public_id.lower().replace("-", "_")
    if (direct / "scenario.yaml").is_file():
        return direct
    for package in sorted(FORMAL.iterdir()):
        if not (package / "scenario.yaml").is_file():
            continue
        payload = yaml.safe_load((package / "scenario.yaml").read_text(encoding="utf-8"))
        scenario_id = str((payload.get("scenario") or {}).get("scenario_id") or "")
        if scenario_id.lower().startswith(public_id.lower()):
            return package
    return None


def entities_of(scenario: dict) -> list[dict]:
    found = list(scenario["entities"])
    for event in scenario.get("events") or ():
        if event.get("event_type") != "spawn":
            continue
        blueprint = (event.get("payload") or {}).get("entity")
        if isinstance(blueprint, dict):
            found.append(blueprint)
    return found


def force_profile(package: Path) -> dict:
    scenario = yaml.safe_load(
        (package / "scenario.yaml").read_text(encoding="utf-8"))["scenario"]
    agents = yaml.safe_load((package / "agents.yaml").read_text(encoding="utf-8"))

    def is_armed_raider(entity: dict) -> bool:
        tags = {str(tag) for tag in entity.get("tags") or ()}
        return (entity.get("faction_id") == "coalition.intruder"
                and any(tag.startswith("target.") for tag in tags)
                and bool(entity.get("ammunition")))

    raiders = [e for e in entities_of(scenario) if is_armed_raider(e)]
    defenders = [e for e in entities_of(scenario)
                 if e.get("faction_id") == "coalition.defender"
                 and bool(e.get("ammunition"))]

    def rounds(pool: list[dict]) -> dict[str, int]:
        out: dict[str, int] = {}
        for entity in pool:
            for ammo_ref, count in (entity.get("ammunition") or {}).items():
                weapon = AMMO_TO_WEAPON.get(str(ammo_ref))
                if weapon is None:
                    continue
                out[weapon] = out.get(weapon, 0) + int(count)
        return out

    return {
        "scenario": scenario,
        "agents": agents,
        "raiders": raiders,
        "defenders": defenders,
        "red_rounds": rounds(raiders),
        "blue_rounds": rounds(defenders),
        "red_uav_count": sum(1 for e in raiders if "boat" not in (e.get("tags") or ())),
        "red_boat_count": sum(1 for e in raiders if "boat" in (e.get("tags") or ())),
        "blue_uav_count": sum(1 for e in defenders
                              if "usv" not in (e.get("tags") or ())),
        "blue_usv_count": sum(1 for e in defenders
                              if "usv" in (e.get("tags") or ())),
        "duration": int(scenario["world"]["duration_ticks"]),
    }


def neutralisation_capacity(rounds: dict[str, int], weapon: str) -> float:
    facts = WEAPON_FACTS[weapon]
    per_neutralise = hits_to_disable(facts["damage_per_hit"]) / facts["hit_probability"]
    return rounds.get(weapon, 0) / per_neutralise


def report(tag: str | None) -> int:
    scores: dict[str, dict] = {}
    if tag:
        path = RUNS / f"ie_set_results_{tag}.json"
        if path.is_file():
            rows = json.loads(path.read_text(encoding="utf-8"))["rows"]
            scores = {row["scenario"]: row for row in rows if row["arm"] == "rule"}

    header = (f"{'scenario':<28}{'红机':>4}{'红船':>4}{'蓝机':>4}{'蓝船':>4}"
              f"{'蓝弹/机':>8}{'红弹/机':>8}{'蓝可拦':>7}{'预计突防':>8}"
              f"{'红期望命中':>10}  判定")
    print(header)
    print("-" * len(header))
    verdicts = []
    for public_id in SCENARIOS:
        package = package_for(public_id)
        if package is None:
            print(f"{public_id:<28} MISSING")
            continue
        profile = force_profile(package)
        blue_rounds = profile["blue_rounds"]
        red_rounds = profile["red_rounds"]
        blue_air = neutralisation_capacity(blue_rounds,
                                          "weapon.air-interceptor-munition@2.0.0")
        raiders = profile["red_uav_count"]
        lfm = WEAPON_FACTS["weapon.loitering-munition@2.0.0"]
        # 每架红机的载弹（1 发/架时单架突防最多只能给设施 1 发命中）
        rounds_per_raider = (red_rounds.get("weapon.loitering-munition@2.0.0", 0)
                             / max(1, raiders))
        # 突防架数：我方对空可拦架数之外剩下的那些
        leakers = max(0.0, raiders - blue_air)
        red_hits_on_facility = leakers * rounds_per_raider * lfm["hit_probability"]
        need_destroy = hits_to_destroy(lfm["damage_per_hit"])
        need_disable = hits_to_disable(lfm["damage_per_hit"])
        if red_hits_on_facility < need_disable:
            band = "设施完好（偏易）"
        elif red_hits_on_facility < need_destroy:
            band = "设施失能（刚好守住）"
        else:
            band = "设施可能被毁（失守）"
        ratio = (raiders / blue_air) if blue_air > 0 else float("inf")
        blue_ammo_per_uav = (blue_rounds.get("weapon.air-interceptor-munition@2.0.0", 0)
                             / max(1, profile["blue_uav_count"]))
        print(f"{public_id:<28}{raiders:>4}{profile['red_boat_count']:>4}"
              f"{profile['blue_uav_count']:>4}{profile['blue_usv_count']:>4}"
              f"{blue_ammo_per_uav:>8.1f}{rounds_per_raider:>8.1f}"
              f"{blue_air:>7.2f}{leakers:>7.1f}"
              f"{red_hits_on_facility:>9.2f}  {band}")
        verdicts.append({
            "scenario": public_id,
            "raiders": raiders,
            "red_boat_count": profile["red_boat_count"],
            "blue_air_capacity": round(blue_air, 2),
            "expected_leakers": round(leakers, 2),
            "critical_ratio": round(ratio, 2),
            "red_expected_facility_hits": round(red_hits_on_facility, 2),
            "hits_to_disable_facility": need_disable,
            "hits_to_destroy_facility": need_destroy,
            "predicted_band": band,
            "observed_score": (scores.get(public_id) or {}).get("defender_score"),
            "observed_outcome": (scores.get(public_id) or {}).get("outcome"),
        })

    print()
    print("解读：")
    print("  蓝可拦   = 我方对空弹药期望能失能的红机数（1 发命中即失能，命中率 0.75）")
    print("  预计突防 = 红机数 − 蓝可拦（能突防到投弹距离的架数）")
    print("  红期望命中 = 突防架数 × 每架载弹 × 命中率")
    print("  判定分级：命中 < 1 → 设施完好；1 ≤ 命中 < 2 → 设施失能（刚好守住）；")
    print("            命中 ≥ 2 → 设施被摧毁（失守）。阈值 1/2 来自实测毁伤链，")
    print("            不是 catalog 声明的 health_scale（该字段是死参数）。")
    print()
    for row in verdicts:
        tail = ""
        if row["observed_score"] is not None:
            tail = (f"  实测 score={row['observed_score']}"
                    f" ({row['observed_outcome']})")
        print(f"  {row['scenario']:<28} 突防={row['expected_leakers']:>5}"
              f"  红期望命中={row['red_expected_facility_hits']:>5}"
              f"  {row['predicted_band']}{tail}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default=None,
                        help="同时对照该 tag 的 rule 实测结果")
    args = parser.parse_args()
    return report(args.tag)


if __name__ == "__main__":
    raise SystemExit(main())
