"""Architecture check: every IE scenario must work with all three method arms.

This is the gate that has to pass BEFORE any expensive episode runs.  For each
member of the IE set and each planner it:

1. builds the session (world construction, terrain deployment, controller slots),
2. builds the defender stack for that planner (weapon-policy/tag matching,
   objective, event timeline, interception-graph wiring),
3. drives ``N`` ticks through the real main loop with the attack driver,
4. reports the first failure with its chained cause.

The LLM arms use a STUB client, so no API call is made and no 40-minute episode is
spent: what is verified is the architecture (prompt construction, command
validation, goal submission, executor loop), not model quality.

Usage:
    python _w1_ie_arch_check.py [--ticks N] [--scenarios ID ...]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from types import SimpleNamespace

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
EVAL = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(EVAL))

IE_SET = [
    "IE-01-SINGLE-TARGET",
    "IE-02-DUAL-THREAT",
    "IE-03-SURFACE-RAID",
    "IE-04-COMBINED-ARMS",
    "IE-05-MULTI-AXIS",
    "IE-06-DECOY-MIXED",
    "IE-07-CROSS-DOMAIN",
    "IE-08-ISLAND-STRIKE",
]
PLANNERS = ("rule", "llm", "pure-llm")

EMPTY_PLAN = '{"goal_commands": [], "reasoning": "architecture check"}'


class _StubLLM:
    """Records prompts and returns an empty plan, so the rule fallback drives."""

    def __init__(self, *args, **kwargs) -> None:
        self.calls = 0
        self.last_prompt = ""
        self.last_system = ""

    def chat(self, system, user, max_tokens=None, temperature=None, **kwargs):
        self.calls += 1
        self.last_system = system
        self.last_prompt = user
        return EMPTY_PLAN


def _args_for(planner: str, ticks: int) -> SimpleNamespace:
    return SimpleNamespace(
        scenario="", planner=planner, plan_interval=10, llm_max_tokens=256,
        llm_base_url=None, llm_model=None, frontend="graph",
        rule_fire_policy="salvo", rule_fire_policy_urgent=None,
        rule_fire_policy_urgent_eta=240, fire_doctrine="assess",
        lead_pursuit=True, patrol_sweep=True, deconflict_fire=True,
        retreat_when_dry=True, goal_granularity=None, no_lead_pursuit=False,
        no_patrol_sweep=False, no_deconflict=False, no_retreat_when_dry=False,
        max_ticks=ticks, seed=7,
    )


def _cause_chain(error: BaseException) -> str:
    parts = []
    current: BaseException | None = error
    depth = 0
    while current is not None and depth < 6:
        code = getattr(current, "code", None)
        path = getattr(current, "path", None)
        label = type(current).__name__ + (f"[{code}]" if code else "")
        if path:
            label += f" at {path}"
        parts.append(label)
        current = current.__cause__ or current.__context__
        depth += 1
    return " <- ".join(parts)


def check(scenario: str, planner: str, ticks: int) -> tuple[bool, str]:
    import llm_client_hifi
    import run_episode
    from openmdbench.sessions.formal_v2 import create_formal_session_v2

    llm_client_hifi.LLMClient = _StubLLM  # no API traffic

    profile = run_episode.load_attack_profile_data(scenario)
    args = _args_for(planner, ticks)
    args.scenario = scenario
    try:
        session = create_formal_session_v2(scenario, session_id="audit.arch", seed=7)
        session.load().start()
        attack = run_episode.AttackProfileDriverV2(scenario, seed=7)
        defender = run_episode._build_defender(profile, args)
        fires = 0
        for _ in range(ticks):
            attack(session)
            result = defender(session)
            session.step(operation_id=f"audit.arch.{session.world_view.tick:08d}",
                         expected_tick=session.world_view.tick)
            fires += len(result.get("executor", {}).get("fires", ()) or ())
        live = len(session.world_view.entities_stable())
        session.stop()
        session.close()
        return True, f"ticks={ticks} live={live} fire_attempts={fires}"
    except Exception as error:  # noqa: BLE001 - report, do not mask
        return False, _cause_chain(error)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=12)
    parser.add_argument("--scenarios", nargs="*", default=None)
    args = parser.parse_args()

    scenarios = args.scenarios or IE_SET
    failures = 0
    total = 0
    for scenario in scenarios:
        print(f"=== {scenario}")
        for planner in PLANNERS:
            total += 1
            ok, detail = check(scenario, planner, args.ticks)
            mark = "ok  " if ok else "FAIL"
            print(f"  [{mark}] {planner:<9} {detail}")
            if not ok:
                failures += 1
        print()
    print(f"  {total - failures}/{total} scenario x planner combinations pass")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
