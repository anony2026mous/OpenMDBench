"""Rebuild the high-fidelity results table from per-episode JSON reports."""
from __future__ import annotations

import json
from pathlib import Path

DUR = {
    "MD-AD-002-EASY": 1800,
    "MD-AD-002-MEDIUM": 1800,
    "MD-AD-002-HARD": 1800,
    "MD-AD-004-DECEPTION": 1800,
}


def normalize(d: dict) -> dict:
    m = dict(d.get("layered_metrics") or {})
    scenario = d.get("scenario")
    dur = int(DUR.get(scenario, 1500))
    ticks = int(d.get("ticks_run") or 0)
    states = " ".join(str(s) for s in (d.get("mission_states") or ()))
    term = str(d.get("terminal_result") or "")
    aborted = d.get("aborted")
    surv = float(m.get("defender_survival_rate") or 0.0)
    neut = float(m.get("threat_neutralization_rate") or 0.0)
    if "intruder_success" in term or "breach-failure" in states:
        outcome, success = "intruder_success", False
    elif "defender_success" in term or "defence-success" in states or "raiders-neutralized" in states:
        outcome, success = "defender_success", True
    elif ticks >= dur - 2 and "breach" not in states:
        outcome, success = "timeout_hold", True
    elif aborted:
        outcome, success = "aborted", False
    else:
        outcome, success = str(m.get("outcome") or "horizon_end"), False
    sr = 1.0 if success else 0.0
    return {
        "planner": d.get("planner"),
        "scenario": scenario,
        "duration_ticks": dur,
        "ticks_run": ticks,
        "outcome": outcome,
        "mission_success": success,
        "performance_v": round(0.6 * sr + 0.2 * neut + 0.2 * surv, 4),
        "defender_survival_rate": surv,
        "threat_neutralization_rate": neut,
        "total_fires": d.get("total_fires", m.get("total_fires")),
        "first_fire_tick": m.get("first_fire_tick"),
        "fires_threat": m.get("fires_threat"),
        "fires_decoy": m.get("fires_decoy"),
        "fires_civilian": m.get("fires_civilian"),
        "ammo_efficiency": m.get("ammo_efficiency"),
        "parse_failures": m.get("parse_failures"),
        "fallback_count": m.get("fallback_count"),
        "aborted": aborted,
    }


def main() -> int:
    root = Path(__file__).resolve().parent.parent / "results" / "hifi_full"
    rows = [normalize(json.loads(p.read_text(encoding="utf-8")))
            for p in sorted(root.glob("*_seed7.json"))]
    (root / "normalized.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    header = (
        "| Planner | Scenario | Ticks | Outcome | Success | V | Survival | "
        "Neutralize | Fires | ThreatF | DecoyF | CivF | FirstFire |"
    )
    sep = "|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    lines = [header, sep]
    order_p = {"rule": 0, "llm": 1, "pure-llm": 2}
    rows.sort(key=lambda r: (r["scenario"] or "", order_p.get(r["planner"], 9)))
    for r in rows:
        lines.append(
            "| {planner} | {scenario} | {ticks_run} | {outcome} | {mission_success} | "
            "{performance_v} | {defender_survival_rate} | {threat_neutralization_rate} | "
            "{total_fires} | {fires_threat} | {fires_decoy} | {fires_civilian} | {first_fire_tick} |".format(**r)
        )
    text = "\n".join(lines) + "\n"
    (root / "table.md").write_text(text, encoding="utf-8")
    print(text)
    print("rows", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
