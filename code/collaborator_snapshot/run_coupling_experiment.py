"""Section 4.5 coupling-complexity experiment (grid-only).

Factorial design: C_info tier (task_mode: independent/sequential/continuous)
× B_if level (goal granularity: weak/medium/strong) on the complex tier.

Per cell:
  monolithic = MAPPO trained with --no-goals (unconditioned policy)
  layered    = LLM planner emitting goal commands at the given granularity
               + goal-conditioned MAPPO executor (the tm-{mode}_goals ckpt)
  ΔV = V_layered − V_monolithic at equal sample budget N
  C_info / B_if estimated from execution traces via KSG k-NN MI

Validation (paper criteria):
  (i)   Spearman ρ(ΔV, exp(B_if)) > 0.7
  (ii)  95% CI of ΔV at B_if ≈ 0 includes 0
  (iii) exponential model beats linear on BIC
  (+b)  slope b increases with C_info
  (+R)  sample-efficiency ratio R = N_mono / N_layered grows with B_if
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grid_env.grid_env import GridEnv, MAX_STEPS
from grid_env.goai import GOAIBroker, GOAIExecutor, GoalCommand
from grid_env.agents.llm_client import LLMClient
from grid_env.agents.mappo_agent import MAPPOAgent, encode_unit_obs
from coupling_mi import estimate_couplings

TASK_MODES = ("independent", "sequential", "continuous")
GRANULARITIES = ("weak", "medium", "strong")

# prompt suffix per granularity (the only B_if manipulation)
GRAN_INSTRUCTION = {
    "weak": ("Issue ONLY the goal_type per unit (waypoint/patrol/track/"
             "intercept/hold/return/loiter). Omit all parameters."),
    "medium": ("Issue goal_type plus coarse parameters: target_id for "
               "track/intercept, sector-centre coordinates for waypoint."),
    "strong": ("Issue goal_type plus fine-grained parameters: exact "
               "waypoint (x, y), target_id, speed hint, constraints "
               "(fuel_reserve, standoff), and a deadline in steps."),
}


# ---------------------------------------------------------------------------
# Planners
# ---------------------------------------------------------------------------

class _ClippedPlanner:
    """Wrap a non-LLM planner and clip its goal granularity (dry runs)."""

    def __init__(self, base, granularity: str):
        self.base = base
        self.interval = base.interval
        self.granularity = granularity
        self._seq = 0

    def _tid(self):
        self._seq += 1
        return f"cpl_{self._seq:03d}"

    def plan(self, obs, env, step):
        cmds = self.base.plan(obs, env, step)
        keep = {"unit_id"}
        if self.granularity in ("medium", "strong"):
            keep |= {"target_id"}
        if self.granularity == "strong":
            keep |= {"position", "radius", "speed", "pattern"}
        out = []
        for c in cmds:
            out.append(GoalCommand(
                task_id=self._tid(), goal_type=c.goal_type,
                parameters={k: v for k, v in (c.parameters or {}).items()
                            if k in keep},
                priority=c.priority,
                constraints=(c.constraints if self.granularity == "strong"
                             else [])))
        return out


class GranularLLMPlanner:
    """LLM planner whose goal-command granularity is the B_if lever."""

    def __init__(self, client, granularity: str, seed: int = 42,
                 interval: int = 10):
        from grid_env.agents.hybrid_agent import HybridAgent
        self._agent = HybridAgent(role="blue", seed=seed, llm_client=client)
        self.interval = interval
        self.granularity = granularity
        self._seq = 0
        self._last_raw = []

    def _tid(self):
        self._seq += 1
        return f"cpl_{self._seq:03d}"

    def plan(self, obs, env, step):
        self._agent.step_count = step
        prompt = self._agent._build_planner_prompt(obs)
        prompt += "\n\nOUTPUT FORMAT REQUIREMENT: " + GRAN_INSTRUCTION[
            self.granularity]
        response = self._agent._call_planner_llm(prompt)
        plan = self._agent._parse_plan(response)
        cmds = (self._agent._plan_to_goal_commands(plan, obs) if plan
                else self._agent._fallback_goal_commands(obs))
        return self._clip_granularity(cmds)

    def _clip_granularity(self, cmds):
        """Strip parameters down to the active granularity level."""
        out = []
        for c in cmds:
            params = dict(c.parameters)
            keep = {"unit_id"}
            if self.granularity in ("medium", "strong"):
                keep |= {"target_id"}
            if self.granularity == "strong":
                keep |= {"position", "radius", "speed", "pattern",
                         "fuel_reserve"}
            clipped = {k: v for k, v in params.items() if k in keep}
            out.append(GoalCommand(
                task_id=self._tid(), goal_type=c.goal_type,
                parameters=clipped, priority=c.priority,
                constraints=(c.constraints if self.granularity == "strong"
                             else [])))
        return out


# ---------------------------------------------------------------------------
# Runners (episode + trace recording)
# ---------------------------------------------------------------------------

DIFFICULTY = "complex"   # set from --difficulty in main(); see migration note below
TRACE_DUMP = None        # set from --dump-traces in main(): jsonl sink for
                         # per-episode metrics + step traces (offline MI /
                         # metric recomputation without re-running)


def _dump_trace(rec: dict):
    if TRACE_DUMP:
        with open(TRACE_DUMP, "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")


def _checkpoint(task_mode: str, layered: bool, seed: int = 42) -> str:
    # train_mappo._ckpt naming: continuous + goal-conditioned keeps the
    # canonical name (no _tm- tag); continuous + --no-goals is "_mono".
    # Both must map correctly here or the continuous cells assert-fail.
    #
    # v2.1.4 migration: the experiment moved to --difficulty medium. On the
    # complex tier the MAPPO executor is at SR=0 (criterion2 2x2, frozen-env
    # retrain x3 seeds), so ΔV collapses to ±0.03 floor and the B_if
    # estimator returns 0 everywhere — goal granularity has no behavioural
    # effect to measure. Medium-tier executors (SR 95-100%) respond to goals,
    # giving both ΔV and B_if variance. v214/ (aligned) checkpoints take
    # precedence over legacy root-dir ones.
    if layered:
        name = (f"checkpoints/mappo_{DIFFICULTY}_s{seed}_best.pt"
                if task_mode == "continuous"
                else f"checkpoints/mappo_{DIFFICULTY}_tm-{task_mode}_s{seed}_best.pt")
    else:
        name = (f"checkpoints/mappo_{DIFFICULTY}_mono_s{seed}_best.pt"
                if task_mode == "continuous"
                else f"checkpoints/mappo_{DIFFICULTY}_tm-{task_mode}_mono_s{seed}_best.pt")
    # v214/ (aligned) checkpoints take precedence over legacy root-dir ones;
    # `name` already starts with "checkpoints/", so splice v214/ after it
    for cand in (name.replace("checkpoints/", "checkpoints/v214/"), name):
        if os.path.exists(cand):
            return cand
        alt = cand.replace("_best", "_final")
        if os.path.exists(alt):
            return alt
    return None


def run_episode(task_mode: str, seed: int, planner=None, ckpt: str = None,
                trace_goals: bool = True):
    """One episode; returns (metrics, trace-steps with uav_goal)."""
    env = GridEnv(difficulty=DIFFICULTY, seed=seed, task_mode=task_mode)
    broker = GOAIBroker()
    ex = GOAIExecutor(broker, blue_units=list(env.blue_units))
    agent = None
    if ckpt:
        agent = MAPPOAgent(role="blue", seed=seed, checkpoint_path=ckpt)

        from grid_env.agents.mappo_agent import make_goai_controller
        ex.controller = make_goai_controller(agent)

    step, last_plan = 0, -(10 ** 9)
    trace = []
    while not env.done and step < MAX_STEPS:
        step += 1
        uav_goal = None
        if planner is not None and step - last_plan >= planner.interval:
            obs = env._get_observation("blue")
            broker.submit_goals(planner.plan(obs, env, step), step=step)
            last_plan = step
        # record the active UAV goal for the B_if estimation
        if trace_goals:
            for st in broker.active.values():
                if st.terminal:
                    continue
                c = st.command
                if c.unit_id == env.uav_id:
                    uav_goal = {"goal_type": c.goal_type,
                                "target_id": c.parameters.get("target_id"),
                                "position": c.parameters.get("position")}
                    break
        acts = ex.act(env, step)
        env.step(acts, None)
        env.compute_reward("blue")
        uav = env.entities.get(env.uav_id)
        usv0 = env.entities.get(env.usv_units[0]) if env.usv_units else None
        trace.append({
            "usv": (usv0.x, usv0.y) if usv0 else (0, 0),
            "uav": (uav.x, uav.y) if uav and uav.alive else (0, 0),
            "uav_goal": uav_goal,
        })
    return env.get_episode_metrics(), trace


def run_monolithic(task_mode: str, seed: int):
    """Unconditioned MAPPO — direct act() loop, no planner."""
    env = GridEnv(difficulty=DIFFICULTY, seed=seed, task_mode=task_mode)
    agent = MAPPOAgent(role="blue", seed=seed,
                       checkpoint_path=_checkpoint(task_mode, layered=False))
    step = 0
    trace = []
    while not env.done and step < MAX_STEPS:
        obs = env._get_observation("blue")
        env.step(agent.act(obs, env), None)
        env.compute_reward("blue")
        step += 1
        uav = env.entities.get(env.uav_id)
        usv0 = env.entities.get(env.usv_units[0]) if env.usv_units else None
        trace.append({
            "usv": (usv0.x, usv0.y) if usv0 else (0, 0),
            "uav": (uav.x, uav.y) if uav and uav.alive else (0, 0),
            "uav_goal": None,
        })
    return env.get_episode_metrics(), trace


# ---------------------------------------------------------------------------
# Experiment driver
# ---------------------------------------------------------------------------

def run_cell(task_mode: str, granularity: str, seeds, client=None,
             use_llm: bool = True):
    """One (C_info tier × B_if level) cell → dict of results."""
    mono_ck = _checkpoint(task_mode, layered=False)
    layer_ck = _checkpoint(task_mode, layered=True)
    assert mono_ck and layer_ck, \
        f"missing checkpoints for task_mode={task_mode}"

    V_m, V_l = [], []
    traces_layered = []
    for i, seed in enumerate(seeds):
        # monolithic: same env seed, unconditioned policy
        m, tr_mono = run_monolithic(task_mode, seed)
        V_m.append(m["blue_score"])
        _dump_trace({"task_mode": task_mode, "granularity": granularity,
                     "seed": seed, "variant": "mono",
                     "metrics": m, "trace": tr_mono})

        # layered: planner at this granularity + goal-cond executor
        planner = None
        if use_llm:
            planner = GranularLLMPlanner(client, granularity, seed=seed)
        else:
            # dry-run substitute: the rule planner (no LLM dependency);
            # granularity still clips the emitted parameters
            from attribution import RulePlanner
            base = RulePlanner(seed=seed)
            planner = _ClippedPlanner(base, granularity)
        lm, tr = run_episode(task_mode, seed, planner=planner,
                             ckpt=layer_ck)
        V_l.append(lm["blue_score"])
        traces_layered.append({"steps": tr})
        _dump_trace({"task_mode": task_mode, "granularity": granularity,
                     "seed": seed, "variant": "layered",
                     "metrics": lm, "trace": tr})

    couplings = estimate_couplings(
        traces_layered, granularity=granularity)
    dV = np.array(V_l) - np.array(V_m)
    rng = np.random.RandomState(0)
    boots = [float(np.mean(rng.choice(dV, len(dV)))) for _ in range(1000)]
    return {
        "task_mode": task_mode, "granularity": granularity,
        "V_monolithic": float(np.mean(V_m)),
        "V_layered": float(np.mean(V_l)),
        "delta_V": float(np.mean(dV)),
        "delta_V_ci95": [float(np.percentile(boots, 2.5)),
                         float(np.percentile(boots, 97.5))],
        "c_info": couplings["c_info"], "b_if": couplings["b_if"],
        "residual_mi": couplings["residual_mi"],
        "n_windows": couplings["n_windows"],
        "n_seeds": len(seeds),
        "_traces": traces_layered,
    }


# ---------------------------------------------------------------------------
# Analysis: fit ΔV = a·(exp(b·B_if) − 1) and validation criteria
# ---------------------------------------------------------------------------

def fit_models(cells):
    b = np.array([c["b_if"] for c in cells])
    dv = np.array([c["delta_V"] for c in cells])

    def nll(pred):
        resid = dv - pred
        sigma = max(float(np.std(resid)), 1e-6)
        return 0.5 * len(dv) * (np.log(2 * np.pi * sigma ** 2) + 1) \
            + np.sum(resid ** 2) / (2 * sigma ** 2)

    # degenerate case: every cell has B_if = 0 (estimator underpowered) —
    # the exponential basis exp(b·0)−1 ≡ 0 cannot be fit
    if np.all(b <= 1e-9):
        a_lin = 0.0
        return {"a": 0.0, "b": 0.0, "bic_exp": 0.0, "bic_linear": 0.0,
                "a_linear": 0.0, "degenerate": True}

    # exponential: grid + refine on (a, b)
    best = None
    for b0 in np.linspace(0.05, 5.0, 100):
        x = np.exp(b0 * b) - 1
        if x.max() <= 0:
            continue
        a0 = float(np.dot(x, dv) / max(np.dot(x, x), 1e-9))
        obj = nll(a0 * x)
        if best is None or obj < best[0]:
            best = (obj, a0, b0)
    nll_exp, a_hat, b_hat = best

    # linear: dv = a·b
    a_lin = float(np.dot(b, dv) / max(np.dot(b, b), 1e-9))
    nll_lin = nll(a_lin * b)

    k = 3  # params + sigma for both models
    bic_exp = k * np.log(len(dv)) + 2 * nll_exp
    bic_lin = k * np.log(len(dv)) + 2 * nll_lin

    return {"a": a_hat, "b": b_hat, "bic_exp": float(bic_exp),
            "bic_linear": float(bic_lin), "a_linear": a_lin}


def validate(cells, fit):
    b = np.array([c["b_if"] for c in cells])
    dv = np.array([c["delta_V"] for c in cells])

    # (i) Spearman ρ(ΔV, exp(B_if))
    exp_b = np.exp(b) - 1
    ranks_x = np.argsort(np.argsort(exp_b)).astype(float)
    ranks_y = np.argsort(np.argsort(dv)).astype(float)
    rho = float(np.corrcoef(ranks_x, ranks_y)[0, 1])

    # (ii) CI at the weakest B_if cell includes 0
    weakest = cells[int(np.argmin(b))]
    ci_includes_zero = (weakest["delta_V_ci95"][0] <= 0
                        <= weakest["delta_V_ci95"][1])

    # (iii) exponential beats linear on BIC
    bic_ok = fit["bic_exp"] < fit["bic_linear"]

    # (b) slope b increases with C_info: per-tier fits
    tier_slopes = {}
    for tm in TASK_MODES:
        sub = [c for c in cells if c["task_mode"] == tm]
        if len(sub) >= 2:
            bb = np.array([c["b_if"] for c in sub])
            dd = np.array([c["delta_V"] for c in sub])
            x = np.exp(bb) - 1
            tier_slopes[tm] = float(np.dot(x, dd) / max(np.dot(x, x), 1e-9))
    slopes_sorted = all(
        tier_slopes[TASK_MODES[i]] <= tier_slopes[TASK_MODES[i + 1]]
        for i in range(len(TASK_MODES) - 1)
        if TASK_MODES[i] in tier_slopes and TASK_MODES[i + 1] in tier_slopes)

    return {
        "spearman_rho_deltaV_expBif": rho,
        "criterion_i_rho_gt_0.7": rho > 0.7,
        "weakest_cell_ci": weakest["delta_V_ci95"],
        "criterion_ii_ci_includes_zero": bool(ci_includes_zero),
        "criterion_iii_exp_bic_better": bool(bic_ok),
        "tier_slopes": tier_slopes,
        "criterion_b_slope_monotone_in_Cinfo": bool(slopes_sorted),
        "b_hat": fit["b"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--difficulty", default="complex",
                    choices=["simple", "medium", "complex"],
                    help="v2.1.4 migration: medium is the valid tier for this "
                         "experiment (complex executors are SR=0; see "
                         "_checkpoint note)")
    ap.add_argument("--seeds", type=int, nargs="+",
                    default=[100, 101, 102, 103, 104, 105])
    ap.add_argument("--granularities", nargs="+",
                    default=list(GRANULARITIES))
    ap.add_argument("--task_modes", nargs="+", default=list(TASK_MODES))
    ap.add_argument("--no-llm", action="store_true",
                    help="dry run with oracle-like rule planner (CI check)")
    ap.add_argument("--output", default="results/coupling_experiment.json")
    ap.add_argument("--dump-traces", default=None, metavar="JSONL",
                    help="dump per-episode metrics + step traces to this "
                         "jsonl (append); enables offline recomputation of "
                         "MI / new metrics without re-running")
    args = ap.parse_args()

    global DIFFICULTY, TRACE_DUMP
    DIFFICULTY = args.difficulty
    TRACE_DUMP = args.dump_traces

    client = None
    if not args.no_llm:
        client = LLMClient()

    cells = []
    pooled_traces = defaultdict(list)   # task_mode → traces (for C_info)
    for tm in args.task_modes:
        for gr in args.granularities:
            print(f"\n=== cell: task_mode={tm} granularity={gr} ===",
                  flush=True)
            cell = run_cell(tm, gr, args.seeds, client=client,
                            use_llm=not args.no_llm)
            cells.append(cell)
            pooled_traces[tm].extend(cell.pop("_traces", []))
            print(f"  C_info(cell)={cell['c_info']:.3f} "
                  f"B_if={cell['b_if']:.3f} "
                  f"ΔV={cell['delta_V']:+.3f} "
                  f"CI=[{cell['delta_V_ci95'][0]:+.3f}, "
                  f"{cell['delta_V_ci95'][1]:+.3f}]", flush=True)

    # C_info is a TASK property: pool all granularities per task_mode and
    # overwrite the per-cell estimates (which conflate policy behaviour)
    for tm, trs in pooled_traces.items():
        pooled = estimate_couplings(trs, granularity="strong")
        for c in cells:
            if c["task_mode"] == tm:
                c["c_info"] = pooled["c_info"]
                c["c_info_pooled_n_windows"] = pooled["n_windows"]

    fit = fit_models(cells)
    report = {
        "cells": cells,
        "fit": fit,
        "validation": validate(cells, fit),
        "config": {"seeds": args.seeds,
                   "granularities": args.granularities,
                   "task_modes": args.task_modes,
                   "llm": not args.no_llm},
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    v = report["validation"]
    print("\n=== validation ===")
    print(f"(i)   Spearman ρ(ΔV, exp(B_if)) = "
          f"{v['spearman_rho_deltaV_expBif']:.3f} "
          f"{'PASS' if v['criterion_i_rho_gt_0.7'] else 'FAIL'} (need >0.7)")
    print(f"(ii)  weakest-cell CI includes 0: "
          f"{'PASS' if v['criterion_ii_ci_includes_zero'] else 'FAIL'} "
          f"({v['weakest_cell_ci']})")
    print(f"(iii) BIC exp={fit['bic_exp']:.1f} vs lin={fit['bic_linear']:.1f} "
          f"{'PASS' if v['criterion_iii_exp_bic_better'] else 'FAIL'}")
    print(f"(b)   tier slopes {v['tier_slopes']} monotone in C_info: "
          f"{'PASS' if v['criterion_b_slope_monotone_in_Cinfo'] else 'FAIL'}")
    if fit.get("degenerate"):
        print("NOTE: all B_if ≈ 0 (estimator underpowered / dry run) — "
              "fit degenerate")
    print(f"\nSaved {args.output}")


if __name__ == "__main__":
    main()
