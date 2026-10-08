#!/usr/bin/env python
"""grid-info: D1 causal injection test — does information asymmetry at the
deliberation layer produce a hybrid gain? (conditional-H1 mechanism check)

Background: on grid the hybrid architecture never beat the rule planner
(LLM 5% vs rule 65% on complex) and §4.5 showed ΔV<0 almost everywhere —
consistent with C_info≈0 (the LLM reads the same state-derived report as
the rule; there is nothing exclusive to exploit). That is an *ex post*
interpretation. This experiment makes it causal: inject a controlled
information asymmetry — an exclusive intel channel for the planner layer
only — and re-run the anchor matrix on paired seeds.

Systems (complex, seeds 100-119, executor=heuristic for all):
  rule_heuristic   hand-written rule planner (65% anchor, re-run paired)
  rule_intel       same rule + feint-discrimination post-filter
                   (compressibility control: the same information as
                   ~10 lines of geometry — if this matches hybrid_intel,
                   the intel is numerically compressible and the LLM has
                   no semantic edge)
  hybrid_heuristic LLM planner (5% anchor, re-run paired)
  hybrid_intel     LLM planner + kinetic annex (heading history rendered
                   into the prompt; the cue is in the observation dict
                   but the stock prompt builder omits it) + exclusive
                   intel brief (deception mechanics below)

Verified deception mechanics (v2.1.4 env, see grid_env.py):
  - feint transports hold ~50% of steps and otherwise drift laterally;
    genuine transports/combatants close on the port area (~(1,18));
    observable through repeated contacts only, never through the local
    grid encoding — by design (v2.1 deception notes)
  - firing on a feint is an own-goal (neutral_intercepted, no credit)
  - anomaly relabeling ('unknown' / '?') corrupts type labels;
    kinematics remain valid
  - comm jam drops contact confidence to 0.3
"""
import argparse
import json
import os

import numpy as np

from attribution import BasePlanner, RulePlanner, LLMPlanner, run_system
from grid_env.agents.llm_client import LLMClient

PORT = (1, 18)

INTEL_BRIEF = """

INTEL BRIEF (exclusive to you, the deliberation layer — the execution
layer cannot see this):
1. Deception: roughly half of transport contacts are FEINTS. Feints hold
   position about half the time and otherwise drift LATERALLY along
   their spawn edge; they NEVER close on the port. Genuine threat
   transports and combatants make steady progress toward the port area
   around (1,18).
2. Firing on a feint is an OWN-GOAL: it wastes an interceptor and earns
   no interception credit. Commit interceptors only to contacts whose
   observed heading history consistently closes on the port.
3. Anomaly relabeling: 'false intel' events can show a genuine contact
   as type 'unknown'; 'unknown entity' events show '?'. TYPE LABELS CAN
   LIE; KINEMATICS DO NOT. Reclassify ambiguous contacts by their heading
   history in the kinetic annex.
4. When communications are jammed (contact confidence 0.3), labels are
   even less reliable — trust the kinetic annex over instantaneous
   labels.
5. Scouts never run at the port (lateral harassment only); engaging them
   wastes ammo. Hunters may chase your UAV to hold it inside jamming
   range.
6. Never intercept civilian vessels (rule violation).
"""


def _iter_contacts(obs):
    sit = obs.get("situational_data", {})
    yield from (sit.get("detected_contacts") or [])
    yield from (obs.get("unknown_contacts")
                or sit.get("unknown_contacts") or [])


class InformedLLMPlanner(BasePlanner):
    """LLM planner + exclusive intel channel (agent-side; env frozen).

    (i) kinetic annex: renders each contact's observed heading plus the
        heading history recorded at previous replans (the stock prompt
        builder omits the cue entirely);
    (ii) intel brief: the deception mechanics above.
    """

    def __init__(self, llm_client, seed: int = 42, interval: int = 10):
        from grid_env.agents.hybrid_agent import HybridAgent
        self._agent = HybridAgent(role="blue", seed=seed,
                                  llm_client=llm_client)
        self.interval = interval
        self._hist = {}          # contact_id -> [heading, ...] per replan

    def _annex(self, obs) -> str:
        lines = ["", "KINETIC ANNEX (observed step-deltas; port area at "
                  "(1,18). closing = moving toward (1,18); lateral drift "
                  "away from it = feint signature; (0,0) = holding):"]
        for c in _iter_contacts(obs):
            h = c.get("heading")
            hist = self._hist.setdefault(c["id"], [])
            if h is not None:
                hist.append(tuple(h))
            trail = " ".join(f"({a},{b})" for a, b in hist[-8:])
            lines.append(f"  {c['id']}: type={c.get('type', '?')} "
                         f"heading={tuple(h) if h else 'n/a'} trail=[{trail}]")
        return "\n".join(lines) + "\n"

    def plan(self, obs, env, step):
        self._agent.step_count = step
        prompt = (self._agent._build_planner_prompt(obs)
                  + self._annex(obs) + INTEL_BRIEF)
        response = self._agent._call_planner_llm(prompt)
        plan = self._agent._parse_plan(response)
        if plan is None:
            return self._agent._fallback_goal_commands(obs)
        return self._agent._plan_to_goal_commands(plan, obs)


class RuleIntelPlanner(BasePlanner):
    """Rule planner + feint-discrimination post-filter.

    Compressibility control: encodes the same discrimination rule the
    intel brief gives the LLM as pure geometry — a contact whose net
    progress toward the port over >=3 replans is <2 cells is treated as
    a feint and its intercept commands are dropped.
    """

    def __init__(self, seed: int = 42, interval: int = 5):
        from grid_env.agents.rule_agent import RuleAgent
        self._agent = RuleAgent(role="blue", seed=seed)
        self.interval = interval
        self._pos = {}           # contact_id -> [(x, y), ...]
        self._types = {}         # contact_id -> confirmed label
        self._feints = set()

    def _classify(self, obs):
        for c in _iter_contacts(obs):
            self._pos.setdefault(c["id"], []).append(
                tuple(c["position"]))
        for cid, hist in self._pos.items():
            if len(hist) < 3:
                continue
            # only transport-type contacts: the intel is about transport
            # feints; classifying combatants/unknowns from hold-in-place
            # kinematics misfires (anomaly-stunned combatants hold too)
            if self._types.get(cid) != "red_transport":
                continue
            d0 = abs(hist[0][0] - PORT[0]) + abs(hist[0][1] - PORT[1])
            d1 = abs(hist[-1][0] - PORT[0]) + abs(hist[-1][1] - PORT[1])
            if d0 - d1 < 2:            # no net progress toward port
                self._feints.add(cid)

    def plan(self, obs, env, step):
        sit = obs.get("situational_data", {})
        for c in (sit.get("detected_contacts") or []):
            # only confirmed labels enter the type map; anomaly-relabeled
            # 'unknown' is NOT treated as transport (may be a combatant)
            if c.get("type") == "red_transport":
                self._types[c["id"]] = "red_transport"
        self._classify(obs)
        cmds = self._agent._rule_goal_commands(obs)
        return [c for c in cmds
                if not (c.goal_type == "intercept"
                        and c.parameters.get("target_id") in self._feints)]


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--difficulty", default="complex")
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--seed0", type=int, default=100)
    ap.add_argument("--systems", default="rule_heuristic,rule_intel,"
                                        "hybrid_heuristic,hybrid_intel")
    ap.add_argument("--out", default="results/grid_info_experiment.json")
    ap.add_argument("--append_to", default=None,
                    help="merge finished systems into this json")
    args = ap.parse_args()

    def rule_heuristic(seed):
        return run_system(args.difficulty, seed, RulePlanner(seed=seed),
                          executor="heuristic")["metrics"]

    def rule_intel(seed):
        return run_system(args.difficulty, seed,
                          RuleIntelPlanner(seed=seed),
                          executor="heuristic")["metrics"]

    def hybrid_heuristic(seed):
        return run_system(args.difficulty, seed,
                          LLMPlanner(LLMClient(), seed=seed, interval=10),
                          executor="heuristic")["metrics"]

    def hybrid_intel(seed):
        return run_system(args.difficulty, seed,
                          InformedLLMPlanner(LLMClient(), seed=seed,
                                             interval=10),
                          executor="heuristic")["metrics"]

    systems = {
        "rule_heuristic": rule_heuristic,
        "rule_intel": rule_intel,
        "hybrid_heuristic": hybrid_heuristic,
        "hybrid_intel": hybrid_intel,
    }

    results = {}
    if args.append_to and os.path.exists(args.append_to):
        with open(args.append_to) as f:
            results = json.load(f).get("systems", {})

    for name in args.systems.split(","):
        fn = systems[name]
        sr, waste, eps = [], [], []
        for i in range(args.episodes):
            seed = args.seed0 + i
            m = fn(seed)
            sr.append(float(m["mission_success"]))
            # feint own-goals are not exposed in episode metrics and
            # ammo_used double-counts the standoff path, so report clean
            # diagnostics directly: civilian hits + ammo per kill
            waste.append(float(m["civilian_intercepted"]))
            eps.append(m)          # full L1 metrics (recompute-safe)
            print(f"  [{name} ep{i}] ok={int(m['mission_success'])} "
                  f"score={m['blue_score']:.2f} "
                  f"civ_hits={waste[-1]:.0f} "
                  f"ammo/kill={m['ammo_used'] / max(m['red_intercepted'], 1):.1f}",
                  flush=True)
        results[name] = {
            "SR": round(float(np.mean(sr)), 4),
            "blue_score": round(float(
                np.mean([e["blue_score"] for e in eps])), 4),
            "civ_hits_per_ep": round(float(np.mean(waste)), 2),
            "ammo_per_kill": round(float(np.mean(
                [e["ammo_used"] / max(e["red_intercepted"], 1)
                 for e in eps])), 2),
            "sr_list": sr,
            "episodes": eps,
        }
        print(f"== {name}: SR={np.mean(sr):.0%} "
              f"civ_hits/ep={np.mean(waste):.2f}\n", flush=True)

    # paired contrasts (same env seeds across systems)
    contrasts = {}
    rng = np.random.RandomState(0)

    def paired(a, b):
        if a not in results or b not in results:
            return None
        da = np.array(results[a]["sr_list"])
        db = np.array(results[b]["sr_list"])
        d = da - db
        boots = [float(np.mean(rng.choice(d, len(d))))
                 for _ in range(1000)]
        return {
            "delta_SR": round(float(np.mean(d)), 4),
            "ci95": [round(float(np.percentile(boots, 2.5)), 4),
                     round(float(np.percentile(boots, 97.5)), 4)],
        }

    for a, b in [("hybrid_intel", "hybrid_heuristic"),
                 ("hybrid_intel", "rule_heuristic"),
                 ("hybrid_intel", "rule_intel"),
                 ("rule_intel", "rule_heuristic")]:
        c = paired(a, b)
        if c:
            contrasts[f"{a} - {b}"] = c

    out = {"config": {
               "difficulty": args.difficulty, "episodes": args.episodes,
               "seed0": args.seed0,
               "note": "D1 causal injection: exclusive intel channel "
                       "(agent-side prompt additions, env v2.1.4 frozen)"},
           "systems": results, "contrasts": contrasts}
    path = args.append_to or args.out
    with open(path, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"Saved {path}")
    for k, v in contrasts.items():
        print(f"  {k}: ΔSR={v['delta_SR']:+.2f} "
              f"CI95=[{v['ci95'][0]:+.2f},{v['ci95'][1]:+.2f}]")


if __name__ == "__main__":
    main()
