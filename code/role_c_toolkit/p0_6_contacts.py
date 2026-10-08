"""Trace real 6.0 IE-11 defender observations without altering the engine."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from toolkit_paths import PROJECT, ENGINE, EVAL


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ticks", type=int, default=170)
    args = parser.parse_args()
    os.environ["OPENMDBENCH_ROOT"] = str(ENGINE)
    sys.path.insert(0, str(ENGINE))
    sys.path.insert(0, str(EVAL))
    import openmdbench
    from openmdbench.sessions.formal_v2 import create_formal_session_v2
    from attack_driver import AttackProfileDriverV2, load_attack_profile_data
    from run_episode import _build_defender, _receipt_terminal, build_parser

    actual = Path(openmdbench.__file__).resolve().parent
    if actual != (ENGINE / "openmdbench").resolve():
        raise RuntimeError(f"Wrong engine: {actual}")
    scenario, seed = "IE-11-DECOY-SCREEN", 9901
    session = create_formal_session_v2(scenario, session_id="rolec.p0.6.ie11", seed=seed)
    session.load().start()
    profile = load_attack_profile_data(scenario)
    run_args = build_parser().parse_args(
        ["--scenario", scenario, "--seed", str(seed), "--planner", "rule",
         "--max-ticks", str(args.ticks)])
    defender = _build_defender(profile, run_args)
    attack = AttackProfileDriverV2(scenario, seed=seed)
    first_seen: dict[str, int] = {}
    selected: dict[str, list[dict]] = {}
    fields: set[str] = set()
    terminal = None
    target_ticks = {0, 1, 2, 10, 50, 100, 149, 150, 151, 160, 169}
    try:
        for _ in range(args.ticks):
            tick = session.world_view.tick
            attack(session)
            obs = session.world_view.observation(observer_faction_id=defender.faction_id)
            contacts = [dict(row) for row in obs.contacts_by_faction.get(defender.faction_id, ())]
            for row in contacts:
                fields.update(row)
                first_seen.setdefault(str(row.get("contact_id")), tick)
            if tick in target_ticks:
                selected[str(tick)] = contacts
            defender(session)
            receipt = session.step(operation_id=f"rolec.p0.6.ie11.{tick:08d}",
                                   expected_tick=tick)
            terminal = _receipt_terminal(receipt)
            if terminal is not None:
                break
        internal_ids = sorted(str(row.id) for row in session.world_view.entities_stable())
        result = {
            "scenario": scenario, "seed": seed, "engine": str(actual),
            "ticks_requested": args.ticks, "ticks_run": session.world_view.tick,
            "terminal": terminal is not None,
            "observation_fields": sorted(obs.model_fields),
            "contact_fields": sorted(fields),
            "first_seen_tick_by_contact": first_seen,
            "selected_tick_contacts": selected,
            "internal_decoy_ids_present": sorted(x for x in internal_ids if "decoy" in x.lower()),
            "public_contact_ids_contain_decoy": any("decoy" in x.lower() for x in first_seen),
            "public_contact_rows_contain_decoy": any(
                "decoy" in json.dumps(rows, ensure_ascii=False).lower()
                for rows in selected.values()),
        }
    finally:
        if session.state.value in {"running", "loaded", "paused"}:
            session.stop()
        session.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n",
                           encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "ticks_run", "terminal", "contact_fields", "internal_decoy_ids_present",
        "public_contact_ids_contain_decoy", "public_contact_rows_contain_decoy")},
        ensure_ascii=False))


if __name__ == "__main__":
    main()
