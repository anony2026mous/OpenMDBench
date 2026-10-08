"""Audit the ammunition ledger: declared rounds vs shots actually executed.

The requirement questioned the missile count reported for IE-08 ("40+ UAV
missiles — where do that many missiles come from?").  This probe answers it with
evidence: for every shooter it compares

  * the ammunition declared in the scenario package, and
  * the shots that the engine actually executed (from the episode's JSONL log),

and flags any shooter that fired more than it was issued, plus the totals by
side and weapon.

Usage:
    python _w1_ammo_audit.py --log rule_seed7_1789893167.jsonl --package ie_08_island_strike
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

import yaml

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
LOG_DIR = Path(os.environ.get("OPENMDBENCH_LOG_DIR")
               or Path.home() / "eval_w1_runs" / "logs")


def scenario_from_log(log_path: Path) -> str | None:
    """Read the scenario public id from the log's own ``start`` event.

    The audit needs the *matching* scenario package to resolve declared
    ammunition.  Passing a mismatched package silently produces false
    "OVER BUDGET" rows (every shooter looks undeclared, faction resolves to
    ``?``), which is exactly the kind of fabricated evidence this audit exists
    to prevent -- so the package is taken from the log itself and ``--package``
    only serves as an override.
    """
    text = log_path.read_text(encoding="utf-8", errors="replace")
    for line in text.split("\n")[:20]:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            item = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if item.get("t") == "start" and item.get("scenario"):
            return str(item["scenario"])
    return None


def package_for(public_id: str) -> str | None:
    """Map a public scenario id to its package directory name."""
    formal = ROOT / "scenarios" / "formal"
    direct = formal / public_id.lower().replace("-", "_")
    if (direct / "scenario.yaml").is_file():
        return direct.name
    for package in sorted(formal.iterdir()):
        if not (package / "scenario.yaml").is_file():
            continue
        payload = yaml.safe_load((package / "scenario.yaml").read_text(encoding="utf-8"))
        sid = str((payload.get("scenario") or {}).get("scenario_id") or "")
        if sid.lower().startswith(public_id.lower()):
            return package.name
    return None


def load_entities(package: str) -> dict[str, dict]:
    base = ROOT / "scenarios" / "formal" / package
    scenario = yaml.safe_load((base / "scenario.yaml").read_text(encoding="utf-8"))
    scenario = scenario.get("scenario") or scenario
    found: dict[str, dict] = {}
    for entity in scenario.get("entities", ()) or ():
        if isinstance(entity, dict):
            found[str(entity["id"])] = entity
    for event in scenario.get("events", ()) or ():
        if isinstance(event, dict) and event.get("event_type") == "spawn":
            blueprint = (event.get("payload") or {}).get("entity")
            if isinstance(blueprint, dict):
                found[str(blueprint["id"])] = blueprint
    return found


def read_fires(log_path: Path) -> list[dict]:
    fires: list[dict] = []
    text = log_path.read_text(encoding="utf-8", errors="replace")
    for line in text.split("\n"):
        line = line.strip()
        if not line.startswith("{"):
            continue
        # 日志写入没有保证换行，可能把多个对象粘在一起
        for chunk in line.replace("}{", "}\n{").split("\n"):
            chunk = chunk.strip()
            if not chunk.startswith("{"):
                continue
            if not chunk.endswith("}"):
                chunk += "}"
            try:
                item = json.loads(chunk)
            except Exception:  # noqa: BLE001
                continue
            if item.get("t") == "fire":
                fires.append(item)
    return fires


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True)
    parser.add_argument("--package", default=None,
                        help="覆盖包名；默认由日志自身的 start 事件推导")
    args = parser.parse_args()

    log_path = LOG_DIR / args.log
    if not log_path.exists():
        print(f"log not found: {log_path}")
        return 2
    package = args.package
    if package is None:
        public_id = scenario_from_log(log_path)
        if public_id is None:
            print(f"!! 无法从日志推导场景（{args.log} 没有 start 事件），请用 --package 指定")
            return 2
        package = package_for(public_id)
        if package is None:
            print(f"!! 日志声明场景 {public_id}，但找不到对应场景包")
            return 2
        print(f"场景（取自日志 start 事件）: {public_id}  -> 包 {package}")

    entities = load_entities(package)
    fires = read_fires(log_path)
    executed = [f for f in fires if f.get("executed")]
    print(f"log = {log_path.name}")
    print(f"fire events = {len(fires)}  (executed = {len(executed)}, "
          f"rejected = {len(fires) - len(executed)})\n")

    shots = collections.Counter(str(f.get("entity_id")) for f in executed)
    # ---- 先剔除"旧日志"--------------------------------------------------
    # 射手不在当前场景包的名册里 ⇒ 这条日志是用**另一版场景**跑出来的，
    # 拿它和当前申报弹药比对只会得到假的"超预算"。实测踩到过：IE-02 的旧日志里
    # 有 defender.usv-03 / intruder.boat-93（当前包已无此编成），IE-01 的旧日志里
    # 红机打了 3 发（当前包只申报 1 发）—— 两条都是陈旧日志，不是真缺陷。
    unknown = sorted({e for e in shots if e not in entities})
    if unknown:
        print(f"!! 日志与当前场景包不一致：射手 {unknown} 不在名册内。")
        print("   该日志是用旧版场景跑出来的，弹药申报已变，不能据此判定超预算。")
        print("   请对**当前配置**重跑后再审计。")
        return 3
    # 名册相同并不代表申报相同（改的是 ammunition 数量时实体 id 不变），
    # 所以用更强的判据：**日志必须晚于场景包的最后一次生成**。
    package_yaml = ROOT / "scenarios" / "formal" / package / "scenario.yaml"
    if package_yaml.is_file() and log_path.stat().st_mtime < package_yaml.stat().st_mtime:
        print("!! 日志早于当前场景包的最后一次生成 —— 该日志属于旧配置。")
        print(f"   log      {log_path.stat().st_mtime:.0f}")
        print(f"   package  {package_yaml.stat().st_mtime:.0f}")
        print("   请对当前配置重跑后再审计，否则申报量对不上。")
        return 3

    declared_total = 0
    overruns = []
    print(f"{'shooter':<30}{'faction':<10}{'declared':>9}{'fired':>7}  verdict")
    print("-" * 74)
    for entity_id in sorted(shots, key=lambda k: (-shots[k], k)):
        entity = entities.get(entity_id, {})
        ammo = entity.get("ammunition") or {}
        declared = sum(int(v) for v in ammo.values())
        declared_total += declared
        fired = shots[entity_id]
        verdict = "ok" if fired <= declared else "OVER BUDGET"
        if fired > declared:
            overruns.append((entity_id, declared, fired))
        print(f"{entity_id:<30}{str(entity.get('faction_id', '?')):<10}"
              f"{declared:>9}{fired:>7}  {verdict}")

    print(f"\n射击过的单位数 = {len(shots)}  其申报弹药合计 = {declared_total}")
    print(f"全场景申报弹药合计 = "
          f"{sum(sum(int(v) for v in (e.get('ammunition') or {}).values()) for e in entities.values())}")

    by_side = collections.Counter()
    by_weapon = collections.Counter()
    for fire in executed:
        entity = entities.get(str(fire.get("entity_id")), {})
        by_side[str(entity.get("faction_id", "?"))] += 1
        by_weapon[str(fire.get("weapon_ref"))] += 1
    print("\n按阵营：" + "  ".join(f"{k}={v}" for k, v in sorted(by_side.items())))
    print("按武器：" + "  ".join(f"{k}={v}" for k, v in sorted(by_weapon.items())))

    if overruns:
        print(f"\n!! {len(overruns)} 个单位超出申报弹药：{overruns}")
        return 1
    print("\n每个射手都在申报弹药预算内。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
