"""Conformance check: can the trained RL checkpoint be used on this scenario?

Answers, for one scenario, every condition the RL wrapper actually depends on --
as PASS / WARN / FAIL with the exact limit that produced the verdict, rather than
leaving a reader to infer it from the documentation.

The distinctions that matter:
  * FAIL  -- the environment cannot run it at all (raises, or nothing to control);
  * WARN  -- it runs, but outside the range the checkpoint has ever been trained
             or tested on, so the score is an extrapolation;
  * ok    -- inside the demonstrated envelope.

Usage:
    python _w1_rl_scenario_check.py [SCENARIO ...]
    python _w1_rl_scenario_check.py            # checks the 8 known scenarios
"""
from __future__ import annotations

import collections
import os
import sys
from pathlib import Path

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

DEFAULT_SCENARIOS = [
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

# Envelope the checkpoint has actually been trained and tested on.  These are
# measurements, not design intent -- see RL_MODEL_SCENARIO_SUPPORT.md.
DEMONSTRATED_UNITS = (5, 12)       # own controllable units
DEMONSTRATED_RAIDERS = (3, 17)     # intruders, any lifecycle


def terminal_rules(public_id: str) -> list[tuple[str, str]]:
    """(rule_id, outcome) pairs declared as terminal by the scenario."""
    try:
        import yaml
        from openmdbench.scenarios.formal_v2 import formal_scenario_registry_v2
        entry = formal_scenario_registry_v2()[public_id]
        payload = yaml.safe_load(
            (entry.package_root / "scenario.yaml").read_text(encoding="utf-8"))
        scenario = payload.get("scenario") or payload
    except Exception as error:  # noqa: BLE001
        return [("unreadable", f"{type(error).__name__}: {error}")]
    out: list[tuple[str, str]] = []
    for rule in scenario.get("mission_rules") or scenario.get("rules") or ():
        if not isinstance(rule, dict):
            continue
        outcome = rule.get("outcome") or {}
        if isinstance(outcome, dict) and outcome.get("terminal"):
            out.append((str(rule.get("id")), str(outcome.get("result"))))
    return out


def check_scenario(public_id: str) -> bool:
    from ie_rl_env import (MAX_CONTACTS, MAX_UNITS, SPEED_BY_CLASS,
                           _weapon_profile_for, _ammo_total)
    from v2_agent import FIXED_DYNAMICS_MODEL
    from ie_rl_env import IERlEnv

    print(f"== {public_id}")
    env = IERlEnv(public_id, seed=1000, decision_interval=5, max_ticks=60)
    failures = []
    warnings = []
    try:
        try:
            env.reset()
        except Exception as error:  # noqa: BLE001
            print(f"   [FAIL] cannot start a session: {type(error).__name__}: {error}")
            return False

        # ---- controllable roster -----------------------------------------
        own = len(env._slots)
        fixed = 0
        for entity in env._session.world_view.entities_stable():
            if str(entity.faction_id) != env.defender_faction:
                continue
            bindings = (getattr(getattr(entity, "definition", None),
                                "resource_bindings", None) or {}).get("dynamics", ())
            if bindings and all(getattr(b, "model_ref", "") == FIXED_DYNAMICS_MODEL
                                for b in bindings):
                fixed += 1
        verdict = ("ok" if own <= MAX_UNITS else "FAIL")
        if own > MAX_UNITS:
            failures.append("roster")
        elif not (DEMONSTRATED_UNITS[0] <= own <= DEMONSTRATED_UNITS[1]):
            warnings.append("roster")
            verdict = "WARN"
        print(f"   [{verdict:<4}] controllable units = {own} (MAX_UNITS={MAX_UNITS}, "
              f"demonstrated {DEMONSTRATED_UNITS[0]}-{DEMONSTRATED_UNITS[1]}); "
              f"{fixed} fixed asset(s) correctly excluded")
        if own == 0:
            failures.append("roster")
            print("   [FAIL] no controllable mobile friendly units")

        # ---- intruders ---------------------------------------------------
        # A scenario whose raiders arrive via spawn events has none alive at reset
        # (MD-AD-006 declares its whole raid that way), so the live snapshot alone
        # reports 0 and produces a spurious warning.  Take the larger of the live
        # count and the declared raid size.
        raiders = env._snapshot()["raiders"]
        declared = int(env.engagement_onsets().get("raiders") or 0)
        n_raid = max(len(raiders), declared)
        verdict = "ok"
        if n_raid > MAX_CONTACTS:
            verdict = "WARN"
            warnings.append("raiders")
        elif not (DEMONSTRATED_RAIDERS[0] <= n_raid <= DEMONSTRATED_RAIDERS[1]):
            verdict = "WARN"
            warnings.append("raiders")
        print(f"   [{verdict:<4}] intruders = {n_raid} "
              f"(alive at reset {len(raiders)}, declared {declared}; "
              f"MAX_CONTACTS={MAX_CONTACTS}, demonstrated "
              f"{DEMONSTRATED_RAIDERS[0]}-{DEMONSTRATED_RAIDERS[1]})")
        if n_raid == 0:
            warnings.append("raiders")
            print("   [WARN] no intruders declared: nothing to score against")

        # ---- platform classification -------------------------------------
        classes = collections.Counter()
        unknown_speed = 0
        for slot in env._slots:
            classes[slot.klass] += 1
            if slot.klass not in SPEED_BY_CLASS:
                unknown_speed += 1
        print(f"   [{'ok' if not unknown_speed else 'WARN':<4}] domain classes: "
              f"{dict(classes)} (SPEED_BY_CLASS keys {sorted(SPEED_BY_CLASS)})")

        # ---- weapons: a unit with no resolvable envelope can never fire ----
        armed, unarmed = [], []
        for slot in env._slots:
            entity = next((e for e in env._session.world_view.entities_stable()
                           if str(e.id) == slot.entity_id), None)
            ref, lo, hi, domains = _weapon_profile_for(entity) if entity else (
                None, 0.0, 0.0, ())
            if ref and hi > lo and _ammo_total(entity) > 0:
                armed.append(f"{slot.entity_id}:{lo:.0f}-{hi:.0f}/{','.join(domains) or 'any'}")
            else:
                unarmed.append(slot.entity_id)
        verdict = "ok" if not unarmed else "WARN"
        if unarmed:
            warnings.append("unarmed")
        print(f"   [{verdict:<4}] armed units {len(armed)}/{own}"
              + (f"; CANNOT FIRE: {unarmed}" if unarmed else ""))

        # ---- horizon + engagement onset ----------------------------------
        onsets = env.engagement_onsets()
        print(f"   [ok  ] engagement onset t{onsets['earliest']}..{onsets['latest']} "
              f"over a {env._max_ticks}-tick horizon"
              f"{'  [WARN] truncation would cut the engagement' if env._max_ticks <= onsets['latest'] else ''}")

        # ---- observation / action contract -------------------------------
        print(f"   [ok  ] observation_size={env.observation_size} "
              f"(pair_width={env.pair_width}), action = heading_xy(16,2) "
              f"speed(16,) fire(16,{env.num_fire_choices})")

        # ---- terminal rules ----------------------------------------------
        rules = terminal_rules(public_id)
        names = {outcome for _rid, outcome in rules}
        known = {"defender_success", "intruder_success"}
        verdict = "ok" if names & known else "WARN"
        if not (names & known):
            warnings.append("terminal")
        print(f"   [{verdict:<4}] terminal rules: {rules}")
        if not (names & known):
            print("   [WARN] no defender_success/intruder_success terminal rule: the "
                  "terminal reward term can never fire")
    finally:
        env.close()

    if failures:
        print(f"   => NOT USABLE: {sorted(set(failures))}")
        return False
    if warnings:
        print(f"   => USABLE, OUTSIDE THE DEMONSTRATED ENVELOPE: {sorted(set(warnings))}")
        return True
    print("   => USABLE, inside the demonstrated envelope")
    return True


def main() -> int:
    scenarios = sys.argv[1:] or DEFAULT_SCENARIOS
    ok = True
    for name in scenarios:
        ok = check_scenario(name) and ok
        print()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
