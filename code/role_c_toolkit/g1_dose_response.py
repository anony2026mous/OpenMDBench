"""G1 pilot analysis: dose-response of layer-attributed fault impact.

Reads the pilot tree produced by ``g1_pilot.sh``:

    <root>/clean/seed-<s>/episode.json                      clean baseline (v0)
    <root>/<case>/seed-<s>/dose-<d>/episode.json            injected run at that tier
    <root>/counterfactual/seed-<s>/result.json              reference improvements
    <root>/<case>/seed-<s>/dose-<d>/fault_events.json       layer-tagged injected events

Reported per fault class and dose tier:

* mean dV = V(injected) - V(clean), with a seed-bootstrap 95% CI
* the same for a continuous carrier (steps, alive counts) because V is coarse
* monotonicity of the tier profile per the checklist criterion
* opportunity counts (injected events) per tier, which bound what a tier can express
* layer localisation: every injected event must be tagged with its own layer
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import d2_headroom  # noqa: E402  (project bootstrap convention)

DEFAULT_ROOT = Path("/mnt/QTJC/chenyi-codex/experiments/g1-fault-dose/pilot")
DOSES = ("0.05", "0.10", "0.20", "0.40", "0.60")
CASES = ("planner_wrong_contact", "action_hold")
CARRIERS = ("V", "blue_score", "steps", "fuel_consumed", "red_intercepted",
            "lock_maintenance_ratio", "ammo_efficiency")


def read_episode(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    metrics = payload.get("metrics") or {}
    return {
        "V": payload.get("V"),
        "blue_score": metrics.get("blue_score"),
        "steps": payload.get("steps"),
        "done": payload.get("done"),
        "aborted": payload.get("aborted"),
        "replay_exact": (payload.get("replay_check") or {}).get("exact_match"),
        "fault_events": (payload.get("fault_injection") or {}).get("fault_event_count"),
        "mission_success": metrics.get("mission_success"),
    }


def fault_layers(path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not path.is_file():
        return counts
    try:
        events = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return counts
    for event in events if isinstance(events, list) else []:
        layer = str(event.get("layer", "?"))
        counts[layer] = counts.get(layer, 0) + 1
    return counts


def monotonic(values: list[float]) -> tuple[int, int]:
    """Return (consistent, total) adjacent-pair counts for the increasing direction."""
    pairs = list(zip(values, values[1:]))
    consistent = sum(1 for a, b in pairs if b > a)
    return consistent, len(pairs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    out_path = args.out or (args.root / "dose_response.json")
    root = args.root
    if not root.is_dir():
        raise SystemExit(f"pilot root not found: {root}")

    clean: dict[int, dict] = {}
    for seed_dir in sorted((root / "clean").glob("seed-*")):
        try:
            seed = int(seed_dir.name.split("-")[-1])
        except ValueError:
            continue
        episode = read_episode(seed_dir / "episode.json")
        if episode:
            clean[seed] = episode
    print(f"=== clean 基线（{len(clean)} 个 seed）===")
    for seed, episode in sorted(clean.items()):
        print(f"  seed {seed}: V={episode['V']} blue_score={episode['blue_score']} "
              f"steps={episode['steps']} success={episode['mission_success']}")

    report: dict = {"schema": "g1-pilot-analysis@1", "root": str(root),
                    "clean": {str(k): v for k, v in clean.items()}, "cases": {}}

    for case in CASES:
        case_dir = root / case
        if not case_dir.is_dir():
            continue
        print(f"\n=== {case} ===")
        per_tier: dict[str, dict] = {}
        seeds_seen: list[int] = []
        for seed_dir in sorted(case_dir.glob("seed-*")):
            try:
                seed = int(seed_dir.name.split("-")[-1])
            except ValueError:
                continue
            if seed not in clean:
                continue
            seeds_seen.append(seed)
            for dose_dir in sorted(seed_dir.glob("dose-*")):
                dose = dose_dir.name.replace("dose-", "")
                episode = read_episode(dose_dir / "episode.json")
                if not episode:
                    continue
                layers = fault_layers(dose_dir / "fault_events.json")
                entry = per_tier.setdefault(dose, {"per_seed": {}})
                entry["per_seed"][seed] = {
                    "V": episode["V"],
                    "blue_score": episode["blue_score"],
                    "steps": episode["steps"],
                    "dV": (episode["V"] - clean[seed]["V"]
                           if isinstance(episode["V"], (int, float))
                           and isinstance(clean[seed]["V"], (int, float)) else None),
                    "d_blue_score": (episode["blue_score"] - clean[seed]["blue_score"]
                                     if isinstance(episode["blue_score"], (int, float))
                                     and isinstance(clean[seed]["blue_score"], (int, float))
                                     else None),
                    "d_steps": (episode["steps"] - clean[seed]["steps"]
                                if isinstance(episode["steps"], (int, float))
                                and isinstance(clean[seed]["steps"], (int, float)) else None),
                    "fault_events": episode["fault_events"],
                    "layers": layers,
                }

        header = f"  {'dose':>6} {'n':>3} {'V均值':>9} {'dV均值':>9} {'dV 95%CI':>20} " \
                 f"{'dSteps':>8} {'事件数':>7} {'层':>10}"
        print(header)
        for dose in DOSES:
            entry = per_tier.get(dose)
            if not entry:
                print(f"  {dose:>6} {'—':>3}  （无数据）")
                continue
            seeds = sorted(entry["per_seed"])
            dvs = [entry["per_seed"][s]["dV"] for s in seeds
                   if entry["per_seed"][s]["dV"] is not None]
            dsteps = [entry["per_seed"][s]["d_steps"] for s in seeds
                      if entry["per_seed"][s]["d_steps"] is not None]
            vs = [entry["per_seed"][s]["V"] for s in seeds
                  if entry["per_seed"][s]["V"] is not None]
            events = [entry["per_seed"][s]["fault_events"] for s in seeds
                      if entry["per_seed"][s]["fault_events"] is not None]
            ci = d2_headroom.bootstrap_ci(dvs) if dvs else [None, None]
            layers: dict[str, int] = {}
            for seed in seeds:
                for layer, count in entry["per_seed"][seed]["layers"].items():
                    layers[layer] = layers.get(layer, 0) + count
            entry["dose"] = dose
            entry["dV_mean"] = round(sum(dvs) / len(dvs), 4) if dvs else None
            entry["dV_ci"] = [round(ci[0], 4) if ci[0] is not None else None,
                              round(ci[1], 4) if ci[1] is not None else None]
            entry["d_steps_mean"] = round(sum(dsteps) / len(dsteps), 2) if dsteps else None
            entry["events_mean"] = round(sum(events) / len(events), 2) if events else None
            entry["layers_total"] = layers
            print(f"  {dose:>6} {len(seeds):>3} "
                  f"{(sum(vs)/len(vs) if vs else float('nan')):>9.3f} "
                  f"{(entry['dV_mean'] if entry['dV_mean'] is not None else float('nan')):>9.3f} "
                  f"{'[' + format(ci[0], '.3f') + ',' + format(ci[1], '.3f') + ']' if ci[0] is not None else '—':>20} "
                  f"{(entry['d_steps_mean'] if entry['d_steps_mean'] is not None else float('nan')):>8.1f} "
                  f"{(entry['events_mean'] if entry['events_mean'] is not None else float('nan')):>7.1f} "
                  f"{str(layers)[:10]:>10}")

        # monotonicity on dV and on d_steps
        profile_v = [per_tier[d]["dV_mean"] for d in DOSES
                     if d in per_tier and per_tier[d].get("dV_mean") is not None]
        profile_s = [per_tier[d]["d_steps_mean"] for d in DOSES
                     if d in per_tier and per_tier[d].get("d_steps_mean") is not None]
        # For a fault, "dose-response" means the damage grows: dV decreases, so monotone here is
        # measured on -dV (increasing damage).
        cons_v, tot_v = monotonic([-v for v in profile_v])
        cons_s, tot_s = monotonic(profile_s)
        print(f"  → 单调性（损伤递增方向）: dV {cons_v}/{tot_v} 对一致; dSteps {cons_s}/{tot_s} 对一致")
        report["cases"][case] = {
            "tiers": per_tier,
            "seeds": seeds_seen,
            "monotonicity_dV": {"consistent": cons_v, "total": tot_v},
            "monotonicity_dSteps": {"consistent": cons_s, "total": tot_s},
            "dV_profile": profile_v,
            "dSteps_profile": profile_s,
        }

    # counterfactual reference improvements
    cf_dir = root / "counterfactual"
    if cf_dir.is_dir():
        print("\n=== 反事实参考（每 seed）===")
        refs = {}
        for seed_dir in sorted(cf_dir.glob("seed-*")):
            result = seed_dir / "result.json"
            if not result.is_file():
                continue
            payload = json.loads(result.read_text(encoding="utf-8", errors="replace"))
            seed = seed_dir.name.split("-")[-1]
            refs[seed] = payload
            print(f"  seed {seed}: dP={payload.get('reference_improvement_planning'):+.4f} "
                  f"dE={payload.get('reference_improvement_execution'):+.4f} "
                  f"nonadd={payload.get('reference_nonadditivity'):+.4f} "
                  f"self_replay={payload.get('self_replay_gate')}")
        report["counterfactual"] = refs

    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nwritten {out_path}")


if __name__ == "__main__":
    main()
