"""
OpenMDBench v2 — Attribution framework (§3.5.1, Algorithms 1 & 2, A10).

Layer-wise Shapley-style attribution for hybrid LLM+RL systems:

- Algorithm 1 (pairwise cross-attribution, oracle-free): leverages the
  standardized GOAI interface (goai.py) to interchange deliberation and
  execution layers across systems; per-system relative bottlenecks
  ΔP_i / ΔE_i and layer-matching matrix M_ij.
- Algorithm 2 (oracle counterfactual replay, Mode B default): decomposes
  a system's gap to the oracle upper bound into ΔP, ΔE, decision-stack
  coupling β, ΔE_corrected = ΔE + β and synergy ΔI, with 1000-resample
  bootstrap CIs and a paired Wilcoxon dominant-bottleneck test.
- A10 ground-truth injection: random planner / degraded executor (random
  action probability p ∈ {0.1, 0.3, 0.5}) / balanced — validates that
  attribution accuracy > 85% and severity calibration ρ > 0.7.

Grid-world oracle implementations:
- π_e*: planning-style controller with ground-truth targets — predictive
  intercept points (leads the target toward the port), standoff-first
  engagement under an active lock, dynamic-obstacle-aware routing.
- π_d*: exhaustive assignment search over ≤3 blue units with ground-truth
  red state (permutation search; ≤6 hostiles ⇒ ≤36 assignments).
- π_d^{π_e*} (re-matched planner): base planner adapted to the upgraded
  executor — grid approximation maps random→rule, rule→oracle,
  oracle→oracle while preserving the base decision interval.

Reference: paper §3.5.1, §4.6 (ablation 9 / A10), Appendix H.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grid_env.grid_env import (
    GridEnv, Direction, MAX_STEPS, GRID_SIZE, EntityType,
    RESUPPLY_POINTS, OBSTACLE_SET, STANDOFF_RANGE,
)
from grid_env.goai import GOAIBroker, GOAIExecutor, GoalCommand

try:
    from scipy.stats import wilcoxon as _wilcoxon, spearmanr as _spearman
    _HAVE_SCIPY = True
except ImportError:  # pragma: no cover — fallbacks keep the framework usable
    _HAVE_SCIPY = False

PORT_X, PORT_Y = 1, 18


# ===========================================================================
# Performance functional
# ===========================================================================

def performance_of(metrics: dict) -> float:
    """Scalar performance V ∈ [0, 1] for attribution.

    blue_score = 0.6·mission_success + 0.2·red-neutralized + 0.2·blue-alive
    — continuous (avoids success-rate saturation) and already normalized.
    """
    return float(metrics.get("blue_score", 0.0))


# ===========================================================================
# Planners (deliberation layer π_d — all emit GOAI goal commands)
# ===========================================================================

class BasePlanner:
    """Interface: every `interval` steps, emit GOAI goal commands."""

    interval: int = 10

    def plan(self, obs: dict, env: GridEnv, step: int) -> List[GoalCommand]:
        raise NotImplementedError


class RulePlanner(BasePlanner):
    """Wraps RuleAgent's rule policy as a standalone planner."""

    def __init__(self, seed: int = 42, interval: int = 5):
        from grid_env.agents.rule_agent import RuleAgent
        self._agent = RuleAgent(role="blue", seed=seed)
        self.interval = interval

    def plan(self, obs, env, step):
        return self._agent._rule_goal_commands(obs)


class LLMPlanner(BasePlanner):
    """Wraps HybridAgent's LLM planning path (GOAI goal commands)."""

    def __init__(self, llm_client, seed: int = 42, interval: int = 10):
        from grid_env.agents.hybrid_agent import HybridAgent
        self._agent = HybridAgent(role="blue", seed=seed, llm_client=llm_client)
        self.interval = interval

    def plan(self, obs, env, step):
        self._agent.step_count = step
        prompt = self._agent._build_planner_prompt(obs)
        response = self._agent._call_planner_llm(prompt)
        plan = self._agent._parse_plan(response)
        if plan is None:
            return self._agent._fallback_goal_commands(obs)
        return self._agent._plan_to_goal_commands(plan, obs)


class RandomPlanner(BasePlanner):
    """A10 (a): deliberately suboptimal — random task allocation."""

    def __init__(self, seed: int = 42, interval: int = 5):
        self.rng = np.random.RandomState(seed)
        self.interval = interval
        self._seq = 0

    def _tid(self, pfx):
        self._seq += 1
        return f"{pfx}_{self._seq:03d}"

    def plan(self, obs, env, step):
        sit = obs.get("situational_data", {})
        friendly = sit.get("friendly_assets", [])
        contacts = sit.get("detected_contacts", []) or []
        commands = []
        for a in friendly:
            uid = a["id"]
            is_uav = a.get("unit") == "uav"
            gtype = self.rng.choice(
                ["waypoint", "patrol", "track", "hold", "loiter"]
                + ([] if is_uav else ["intercept"]))
            params = {"unit_id": uid}
            if gtype in ("waypoint", "patrol", "loiter"):
                params["position"] = [int(self.rng.randint(0, GRID_SIZE)),
                                      int(self.rng.randint(0, GRID_SIZE))]
            elif gtype in ("track", "intercept"):
                if contacts:
                    c = contacts[self.rng.randint(len(contacts))]
                    params["target_id"] = c["id"]
                else:
                    gtype, params = "hold", {"unit_id": uid, "duration": 20}
            elif gtype == "hold":
                params["duration"] = int(self.rng.randint(5, 30))
            commands.append(GoalCommand(
                task_id=self._tid(gtype), goal_type=str(gtype),
                parameters=params,
                priority=float(round(self.rng.uniform(0.2, 0.9), 2)),
            ))
        return commands


def _oracle_intercept_point(env: GridEnv, tx: int, ty: int) -> Tuple[int, int]:
    """Predictive intercept point: lead the hostile toward the port."""
    dx = PORT_X - tx
    dy = PORT_Y - ty
    lead = 3 if (abs(dx) + abs(dy)) > 8 else 1
    n = max(abs(dx) + abs(dy), 1)
    px = int(round(tx + lead * dx / n))
    py = int(round(ty + lead * dy / n))
    px = max(0, min(GRID_SIZE - 1, px))
    py = max(0, min(GRID_SIZE - 1, py))
    if (px, py) in OBSTACLE_SET:
        for r in range(1, 4):
            for ax in range(px - r, px + r + 1):
                for ay in range(py - r, py + r + 1):
                    if (0 <= ax < GRID_SIZE and 0 <= ay < GRID_SIZE
                            and (ax, ay) not in OBSTACLE_SET):
                        return ax, ay
    return px, py


class OraclePlanner(BasePlanner):
    """π_d*: ground-truth exhaustive assignment (≤3 blue units)."""

    def __init__(self, seed: int = 42, interval: int = 5):
        self.interval = interval
        self._seq = 0

    def _tid(self, pfx):
        self._seq += 1
        return f"{pfx}_{self._seq:03d}"

    def plan(self, obs, env, step):
        usvs = [uid for uid in env.blue_units
                if env.entities[uid].unit_kind == "usv"
                and env.entities[uid].alive]
        uav = env.blue_units[-1] if env.blue_units else None
        hostiles = [e for e in env.entities.values()
                    if e.alive and e.team == "red"
                    and e.entity_type == EntityType.RED_COMBATANT]
        # sort by port threat
        hostiles.sort(key=lambda e: abs(e.x - PORT_X) + abs(e.y - PORT_Y))

        commands: List[GoalCommand] = []

        # fuel management first (units below 25 head to resupply)
        dry = {uid for uid in env.blue_units
               if env.entities[uid].alive and env.entities[uid].fuel < 25}
        for uid in dry:
            commands.append(GoalCommand(
                task_id=self._tid("return"), goal_type="return",
                parameters={"unit_id": uid}, priority=0.95))

        free_usvs = [u for u in usvs if u not in dry]

        # exhaustive assignment: minimize Σ dist(usv, lead point) — cap the
        # permutation search at the 6 most threatening hostiles
        targets = hostiles[:6]
        best: Optional[Tuple[float, Dict[str, str]]] = None
        if targets and free_usvs:
            for perm in itertools.permutations(
                    range(len(targets)), min(len(free_usvs), len(targets))):
                assign = {}
                cost = 0.0
                for ui, ti in zip(range(len(free_usvs)), perm):
                    t = targets[ti]
                    px, py = _oracle_intercept_point(env, t.x, t.y)
                    u = env.entities[free_usvs[ui]]
                    cost += (abs(u.x - px) + abs(u.y - py)
                             + 0.15 * (abs(px - PORT_X) + abs(py - PORT_Y)))
                    assign[free_usvs[ui]] = t.id
                if best is None or cost < best[0]:
                    best = (cost, assign)
            if best is not None:
                for uid, tid in best[1].items():
                    commands.append(GoalCommand(
                        task_id=self._tid("intercept"), goal_type="intercept",
                        parameters={"unit_id": uid, "target_id": tid},
                        priority=0.85))
                free_usvs = [u for u in free_usvs if u not in best[1]]

        # UAV: lock the most threatening hostile (standoff prerequisite)
        if (uav and env.entities[uav].alive and uav not in dry and hostiles):
            commands.append(GoalCommand(
                task_id=self._tid("track"), goal_type="track",
                parameters={"unit_id": uav, "target_id": hostiles[0].id},
                priority=0.8))

        # leftover USVs: hold near the port approach
        for uid in free_usvs:
            commands.append(GoalCommand(
                task_id=self._tid("patrol"), goal_type="patrol",
                parameters={"unit_id": uid, "position": [6, 15]},
                priority=0.3))
        return commands


class RematchedPlanner(BasePlanner):
    """π_d^{π_e*}: base planner adapted to the upgraded executor.

    Grid approximation of prompt adaptation — the SAME planner family,
    with its decisions informed that the executor is now π_e*:
    - random → random: a random allocator cannot adapt (β ≈ 0 — no
      deliberation-execution coordination to exploit)
    - rule → oracle: the rule policy's adaptation ceiling (same decision
      tempo, ground-truth-quality assignments)
    - oracle → oracle: already matched (β = 0)
    The decision interval always stays that of the base planner, so β
    isolates decision-layer adaptation rather than tempo change.
    """

    _UPGRADE = {"random": "random", "rule": "oracle", "oracle": "oracle"}

    def __init__(self, base_kind: str, seed: int = 42, interval: int = 5):
        self.interval = interval
        kind = self._UPGRADE.get(base_kind, "oracle")
        if kind == "rule":
            self._inner = RulePlanner(seed=seed, interval=interval)
        elif kind == "random":
            self._inner = RandomPlanner(seed=seed, interval=interval)
        else:
            self._inner = OraclePlanner(seed=seed, interval=interval)

    def plan(self, obs, env, step):
        return self._inner.plan(obs, env, step)


# ===========================================================================
# Executors (execution layer π_e)
# ===========================================================================

def _oracle_bfs_step(env: GridEnv, uid: str, goal_cell: Tuple[int, int],
                     stop_cheb: int = 0) -> Optional[int]:
    """BFS step toward a goal cell, avoiding static AND dynamic obstacles.

    stop_cheb: stop when within this Chebyshev distance (0 = enter cell).
    """
    e = env.entities[uid]
    if max(abs(e.x - goal_cell[0]), abs(e.y - goal_cell[1])) <= stop_cheb:
        return Direction.STAY.value

    dyn = {(d.x, d.y) for d in env.dynamic_obstacles}
    blocked = OBSTACLE_SET | dyn
    occupied = {(o.x, o.y) for o in env.entities.values()
                if o.alive and o.team == "blue" and o.id != uid}

    from collections import deque
    start = (e.x, e.y)
    q = deque([(start, None)])
    seen = {start}
    first_move: Dict[Tuple[int, int], int] = {}
    while q:
        (x, y), _ = q.popleft()
        for d, (dx, dy) in ((Direction.UP.value, (0, 1)),
                            (Direction.DOWN.value, (0, -1)),
                            (Direction.LEFT.value, (-1, 0)),
                            (Direction.RIGHT.value, (1, 0))):
            nxt = (x + dx, y + dy)
            if not (0 <= nxt[0] < GRID_SIZE and 0 <= nxt[1] < GRID_SIZE):
                continue
            if nxt in seen:
                continue
            seen.add(nxt)
            if start == (x, y):
                first_move[nxt] = d
            else:
                first_move[nxt] = first_move.get((x, y), d)
            if nxt == goal_cell:
                return first_move[nxt]
            # passable cells for routing (goal cell may be occupied by red)
            if nxt in blocked or nxt in occupied:
                continue
            q.append((nxt, None))
    return None


def make_oracle_controller():
    """π_e*: ground-truth, predictive, obstacle-aware executor.

    controller(env, unit_id, goal_state) -> Optional[int] (None → the
    GOAIExecutor's built-in heuristic handles it).
    """

    def controller(env: GridEnv, unit_id: str, goal_state):
        try:
            e = env.entities.get(unit_id)
            if e is None or not e.alive:
                return None
            cmd = goal_state.command
            params = cmd.parameters or {}

            # critical fuel override (oracle self-preservation)
            if e.fuel < 15 and cmd.goal_type != "return":
                sp = min(RESUPPLY_POINTS,
                         key=lambda p: abs(p[0] - e.x) + abs(p[1] - e.y))
                return _oracle_bfs_step(env, unit_id, sp, stop_cheb=0)

            if cmd.goal_type == "intercept":
                t = env.entities.get(params.get("target_id"))
                if t is None or not t.alive:
                    return None
                d = max(abs(e.x - t.x), abs(e.y - t.y))
                # standoff-first under an active lock (cheb ≤ 4 fires)
                if d <= 1 or (d <= STANDOFF_RANGE and env.lock
                              and env.lock.acquired
                              and env.lock.target_id == t.id):
                    return Direction.INTERCEPT.value
                px, py = _oracle_intercept_point(env, t.x, t.y)
                return _oracle_bfs_step(env, unit_id, (px, py))

            if cmd.goal_type == "track":
                t = env.entities.get(params.get("target_id"))
                if t is None or not t.alive:
                    return None
                # keep inside UAV vision (8) with margin, away from jammers
                for other in env.entities.values():
                    if (other.alive and other.team == "red"
                            and other.entity_type == EntityType.RED_COMBATANT
                            and max(abs(e.x - other.x), abs(e.y - other.y)) <= 2):
                        away = (2 * int(np.sign(e.x - other.x)) or 1,
                                2 * int(np.sign(e.y - other.y)) or 1)
                        return _oracle_bfs_step(
                            env, unit_id,
                            (max(0, min(GRID_SIZE - 1, e.x + away[0])),
                             max(0, min(GRID_SIZE - 1, e.y + away[1]))))
                d = max(abs(e.x - t.x), abs(e.y - t.y))
                if d <= 6:
                    return Direction.STAY.value
                return _oracle_bfs_step(env, unit_id, (t.x, t.y), stop_cheb=6)

            if cmd.goal_type == "return":
                sp = min(RESUPPLY_POINTS,
                         key=lambda p: abs(p[0] - e.x) + abs(p[1] - e.y))
                return _oracle_bfs_step(env, unit_id, sp, stop_cheb=0)

            pos = params.get("position")
            if pos:
                return _oracle_bfs_step(env, unit_id,
                                        (int(pos[0]), int(pos[1])), stop_cheb=1)
            return None
        except Exception:
            return None

    return controller


# ===========================================================================
# System runner (GOAI broker assembles any planner × executor pair)
# ===========================================================================

def run_system(difficulty: str, seed: int, planner: BasePlanner,
               executor: str = "heuristic",
               mappo_checkpoint: Optional[str] = None,
               degraded_p: float = 0.0) -> dict:
    """Run one episode of (π_d = planner, π_e = executor config).

    executor: "heuristic" (GOAIExecutor built-in) | "mappo" |
              "oracle" (π_e*).  degraded_p > 0 randomizes the executor's
    action with that probability (A10 execution-bottleneck injection).
    """
    env = GridEnv(difficulty=difficulty, seed=seed)
    broker = GOAIBroker()
    ex = GOAIExecutor(broker, blue_units=list(env.blue_units))

    if executor == "oracle":
        ex.controller = make_oracle_controller()
    elif executor == "mappo" and mappo_checkpoint:
        from grid_env.agents.mappo_agent import MAPPOAgent, make_goai_controller
        mappo = MAPPOAgent(role="blue", seed=seed,
                           checkpoint_path=mappo_checkpoint)
        ex.controller = make_goai_controller(mappo)

    rng = np.random.RandomState(seed * 7919 + 13)
    step = 0
    last_plan = -(10 ** 9)
    while not env.done and step < MAX_STEPS:
        step += 1
        if (step - last_plan) >= planner.interval:
            obs = env._get_observation("blue")
            cmds = planner.plan(obs, env, step)
            broker.submit_goals(cmds, step=step)
            last_plan = step
        acts = ex.act(env, step)
        if degraded_p > 0:
            for uid in list(acts):
                ent = env.entities.get(uid)
                if ent is None:
                    continue
                if rng.rand() < degraded_p:
                    hi = 4 if ent.unit_kind == "uav" else 5
                    acts[uid] = int(rng.randint(0, hi + 1))
        env.step(acts, None)
        env.compute_reward("blue")

    metrics = env.get_episode_metrics()
    return {"V": performance_of(metrics),
            "success": bool(metrics.get("mission_success", False)),
            "steps": metrics.get("steps", step),
            "metrics": metrics}


def run_config_v(difficulty: str, seeds: List[int],
                  planner_factory: Optional[callable] = None,
                  planner: Optional[BasePlanner] = None,
                  **kwargs) -> np.ndarray:
    """Run one configuration over seeds → array of V values.

    planner_factory(seed) is invoked per seed so that stateful planners
    (e.g. LLMPlanner dialogue history) never leak across episodes.
    """
    if planner_factory is None:
        planner_factory = (lambda _s: planner)
    return np.array(
        [run_system(difficulty, s, planner=planner_factory(s), **kwargs)["V"]
         for s in seeds], dtype=float)

# ===========================================================================
# Statistics
# ===========================================================================

def bootstrap_ci(values: np.ndarray, n_resamples: int = 1000,
                 ci: float = 0.95, seed: int = 0) -> Tuple[float, float, float]:
    """Mean with percentile bootstrap CI → (mean, lo, hi)."""
    values = np.asarray(values, dtype=float)
    rng = np.random.RandomState(seed)
    n = len(values)
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    idx = rng.randint(0, n, size=(n_resamples, n))
    means = values[idx].mean(axis=1)
    lo = float(np.percentile(means, (1 - ci) / 2 * 100))
    hi = float(np.percentile(means, (1 + ci) / 2 * 100))
    return (float(values.mean()), lo, hi)


def paired_wilcoxon(a: np.ndarray, b: np.ndarray) -> Tuple[float, float]:
    """Paired Wilcoxon signed-rank test → (statistic, p). Zero-diff safe."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = a - b
    if np.allclose(d, 0):
        return (0.0, 1.0)
    if _HAVE_SCIPY:
        try:
            res = _wilcoxon(a, b)
            return (float(res.statistic), float(res.pvalue))
        except ValueError:
            return (0.0, 1.0)
    # sign-test fallback
    pos = int((d > 0).sum())
    n = int((d != 0).sum())
    from math import comb
    p = sum(comb(n, k) for k in range(pos + 1)) / 2 ** n
    return (float(pos), float(min(p, 1 - p)) * 2)


def cliffs_delta(a: np.ndarray, b: np.ndarray) -> float:
    """Cliff's delta effect size (0 = no difference)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) == 0 or len(b) == 0:
        return 0.0
    gt = sum(int(x > y) for x in a for y in b)
    lt = sum(int(x < y) for x in a for y in b)
    return (gt - lt) / (len(a) * len(b))


# ===========================================================================
# Algorithm 1: pairwise cross-attribution (oracle-free)
# ===========================================================================

@dataclass
class SystemSpec:
    """A named (π_d factory, π_e config) pair — layers interchangeable."""
    name: str
    planner_factory: callable          # (seed) -> BasePlanner
    executor: str = "heuristic"        # heuristic | mappo | oracle
    mappo_checkpoint: Optional[str] = None
    degraded_p: float = 0.0


def pairwise_cross_attribution(systems: List[SystemSpec], difficulty: str,
                               seeds: List[int], verbose: bool = True
                               ) -> dict:
    """Algorithm 1: 4 configurations per pair, per-system ΔP/ΔE + M."""
    N = len(systems)
    # V_ii diagonal first
    V = {}
    for i, s in enumerate(systems):
        V[(i, i)] = run_config_v(
            difficulty, seeds,
            planner_factory=s.planner_factory, executor=s.executor,
            mappo_checkpoint=s.mappo_checkpoint, degraded_p=s.degraded_p)

    dE = {i: [] for i in range(N)}     # ΔE_i(j) samples across (j, seed)
    dP = {i: [] for i in range(N)}
    M = {i: [] for i in range(N)}
    pair_records = []

    for i in range(N):
        for j in range(i + 1, N):
            Vij = run_config_v(
                difficulty, seeds,
                planner_factory=systems[i].planner_factory,
                executor=systems[j].executor,
                mappo_checkpoint=systems[j].mappo_checkpoint,
                degraded_p=systems[j].degraded_p)
            Vji = run_config_v(
                difficulty, seeds,
                planner_factory=systems[j].planner_factory,
                executor=systems[i].executor,
                mappo_checkpoint=systems[i].mappo_checkpoint,
                degraded_p=systems[i].degraded_p)
            for k in range(len(seeds)):
                dE[i].append(Vij[k] - V[(i, i)][k])       # ΔE_i(j) = V_ij − V_ii
                dP[i].append(Vji[k] - V[(i, i)][k])       # ΔP_i(j) = V_ji − V_ii
                dE[j].append(Vji[k] - V[(j, j)][k])       # ΔE_j(i) = V_ji − V_jj
                dP[j].append(Vij[k] - V[(j, j)][k])       # ΔP_j(i) = V_ij − V_jj
                M[i].append(V[(i, i)][k] + V[(j, j)][k] - Vij[k] - Vji[k])
                M[j].append(M[i][-1])
            pair_records.append({
                "pair": f"{systems[i].name}|{systems[j].name}",
                "V_ii": float(V[(i, i)].mean()), "V_jj": float(V[(j, j)].mean()),
                "V_ij": float(Vij.mean()), "V_ji": float(Vji.mean()),
                "M_ij": float(np.mean(M[i][-len(seeds):])),
            })
            if verbose:
                print(f"  pair {systems[i].name} × {systems[j].name}: "
                      f"V_ii={V[(i, i)].mean():.3f} V_jj={V[(j, j)].mean():.3f} "
                      f"V_ij={Vij.mean():.3f} V_ji={Vji.mean():.3f} "
                      f"M={pair_records[-1]['M_ij']:+.3f}")

    report = {"pairs": pair_records, "systems": {}}
    for i, s in enumerate(systems):
        dE_i, dP_i = np.array(dE[i]), np.array(dP[i])
        # dominant bottleneck via paired Wilcoxon
        stat, p = paired_wilcoxon(dP_i, dE_i)
        dominant = "planning" if dP_i.mean() > dE_i.mean() else "execution"
        if p >= 0.05:
            dominant = "inconclusive"
        report["systems"][s.name] = {
            "V_own": float(V[(i, i)].mean()),
            "delta_P": float(dP_i.mean()), "delta_E": float(dE_i.mean()),
            "beta_M": float(np.mean(M[i])),
            "dominant_bottleneck": dominant,
            "wilcoxon_p": float(p),
            "cliffs_delta": cliffs_delta(dP_i, dE_i),
        }
    return report


# ===========================================================================
# Algorithm 2: oracle counterfactual replay (Mode B default)
# ===========================================================================

def oracle_counterfactual_replay(planner_factory: callable,
                                 base_kind: str,
                                 executor: str = "heuristic",
                                 difficulty: str = "complex",
                                 seeds: List[int] = None,
                                 mappo_checkpoint: Optional[str] = None,
                                 degraded_p: float = 0.0,
                                 n_bootstrap: int = 1000,
                                 verbose: bool = True) -> dict:
    """Algorithm 2, Mode B (policy replacement).

    Five configurations per seed:
      V0      = V(π_d, π_e)          — original system
      V_E     = V(π_d, π_e*)         — frozen planner, oracle executor
      V_re    = V(π_d^{π_e*}, π_e*)  — re-matched planner, oracle executor
      V_P     = V(π_d*, π_e)         — oracle planner, original executor
      V_full  = V(π_d*, π_e*)        — oracle upper bound
    Per-seed: ΔE, β = V_re − V_E, ΔE_corr = ΔE + β, ΔP, ΔI.
    """
    seeds = seeds or list(range(10))
    rematch_interval = planner_factory(seeds[0]).interval

    V0 = run_config_v(difficulty, seeds, planner_factory=planner_factory,
                      executor=executor, mappo_checkpoint=mappo_checkpoint,
                      degraded_p=degraded_p)
    V_E = run_config_v(difficulty, seeds, planner_factory=planner_factory,
                       executor="oracle")
    V_re = run_config_v(
        difficulty, seeds,
        planner_factory=lambda _s: RematchedPlanner(base_kind,
                                                    interval=rematch_interval),
        executor="oracle")
    V_P = run_config_v(difficulty, seeds,
                       planner_factory=lambda _s: OraclePlanner(
                           interval=rematch_interval),
                       executor=executor, mappo_checkpoint=mappo_checkpoint,
                       degraded_p=degraded_p)
    V_full = run_config_v(difficulty, seeds,
                          planner_factory=lambda _s: OraclePlanner(
                              interval=rematch_interval),
                          executor="oracle")

    dE = V_E - V0
    beta = V_re - V_E
    dE_corr = dE + beta                # = V_re − V0
    dP = V_P - V0
    dI = V_full - V_P - V_E + V0       # synergy (paper definition)
    # genuine coupling gain via the re-matched planner: closes the identity
    #   ΔP + ΔE_corrected + ΔI_genuine = V_full − V0  (residual ≡ 0)
    dI_genuine = V_full - V_P - V_re + V0
    identity_residual = (dP + dE_corr + dI_genuine) - (V_full - V0)

    _, p_w = paired_wilcoxon(dP, dE_corr)
    result = {
        "config": {"executor": executor, "degraded_p": degraded_p,
                   "difficulty": difficulty, "mode": "B",
                   "n_seeds": len(seeds)},
        "V0": bootstrap_ci(V0, n_bootstrap),
        "V_oracle_exec": bootstrap_ci(V_E, n_bootstrap),
        "V_rematch": bootstrap_ci(V_re, n_bootstrap),
        "V_oracle_plan": bootstrap_ci(V_P, n_bootstrap),
        "V_full": bootstrap_ci(V_full, n_bootstrap),
        "delta_E": bootstrap_ci(dE, n_bootstrap),
        "beta": bootstrap_ci(beta, n_bootstrap),
        "delta_E_corrected": bootstrap_ci(dE_corr, n_bootstrap),
        "delta_P": bootstrap_ci(dP, n_bootstrap),
        "delta_I": bootstrap_ci(dI, n_bootstrap),
        "delta_I_genuine": bootstrap_ci(dI_genuine, n_bootstrap),
        "identity_residual": float(np.abs(identity_residual).max()),
        "dominant_bottleneck": ("planning" if dP.mean() > dE_corr.mean()
                                else "execution"),
        "dominant_wilcoxon_p": float(p_w),
        "dominant_cliffs_delta": cliffs_delta(dP, dE_corr),
        "delta_I_significant": bool(
            bootstrap_ci(dI, n_bootstrap)[1] > 0
            or bootstrap_ci(dI, n_bootstrap)[2] < 0),
    }
    # replay-consistency validity check: re-run V0 configuration
    V0_check = run_config_v(difficulty, seeds[:3],
                            planner_factory=planner_factory,
                            executor=executor,
                            mappo_checkpoint=mappo_checkpoint,
                            degraded_p=degraded_p)
    result["replay_consistency"] = float(
        np.abs(V0_check - V0[:3]).max())
    if verbose:
        print(f"  ΔP={result['delta_P'][0]:+.3f} "
              f"ΔE={result['delta_E'][0]:+.3f} "
              f"β={result['beta'][0]:+.3f} "
              f"ΔE_corr={result['delta_E_corrected'][0]:+.3f} "
              f"ΔI={result['delta_I'][0]:+.3f} "
              f"→ {result['dominant_bottleneck']} (p={p_w:.4f})")
    return result


# ===========================================================================
# A10: ground-truth bottleneck injection validation
# ===========================================================================

def a10_injection_validation(difficulty: str = "complex",
                             seeds: List[int] = None,
                             verbose: bool = True) -> dict:
    """A10 §4.6: inject known bottlenecks, verify attribution recovers them.

    (a) planning bottleneck: RandomPlanner + oracle executor
        → expect ΔP > ΔE_corrected
    (b) execution bottleneck: OraclePlanner + degraded executor
        (random-action p ∈ {0.1, 0.3, 0.5}) → expect ΔE_corrected > ΔP,
        magnitude scaling with p (Spearman ρ > 0.7)
    (c) balanced: RulePlanner + heuristic executor → ΔP ≈ ΔE_corrected
    """
    seeds = seeds or list(range(10))
    cases = []
    n_correct = 0
    n_argmax_cases = 0

    # --- (a) planning bottleneck ---
    if verbose:
        print("[A10 (a)] planning bottleneck: random planner + oracle executor")
    res_a = oracle_counterfactual_replay(
        lambda s: RandomPlanner(seed=s, interval=5), base_kind="random",
        executor="oracle", difficulty=difficulty, seeds=seeds, verbose=verbose)
    ok_a = res_a["dominant_bottleneck"] == "planning"
    n_correct += int(ok_a)
    n_argmax_cases += 1
    cases.append({"case": "a_planning", "expected": "planning",
                  "identified": res_a["dominant_bottleneck"],
                  "correct": ok_a,
                  "delta_P": res_a["delta_P"][0],
                  "delta_E_corrected": res_a["delta_E_corrected"][0]})

    # --- (b) execution bottleneck at three severities ---
    severities = [0.1, 0.3, 0.5]
    b_results = []
    for p in severities:
        if verbose:
            print(f"[A10 (b)] execution bottleneck: oracle planner + "
                  f"degraded executor p={p}")
        res_b = oracle_counterfactual_replay(
            lambda s, _p=p: OraclePlanner(seed=s, interval=5),
            base_kind="oracle", executor="heuristic", degraded_p=p,
            difficulty=difficulty, seeds=seeds, verbose=verbose)
        ok_b = res_b["dominant_bottleneck"] == "execution"
        n_correct += int(ok_b)
        n_argmax_cases += 1
        b_results.append({"case": f"b_execution_p{p}", "expected": "execution",
                          "identified": res_b["dominant_bottleneck"],
                          "correct": ok_b, "severity": p,
                          "delta_P": res_b["delta_P"][0],
                          "delta_E_corrected": res_b["delta_E_corrected"][0]})

    # severity calibration: Spearman between injected p and ΔE_corrected
    if _HAVE_SCIPY:
        rho, rho_p = _spearman([b["severity"] for b in b_results],
                               [b["delta_E_corrected"] for b in b_results])
    else:
        xs = np.argsort([b["severity"] for b in b_results]).argsort()
        ys = np.argsort([b["delta_E_corrected"] for b in b_results]).argsort()
        rho = float(np.corrcoef(xs, ys)[0, 1])
        rho_p = float("nan")
    cases.extend(b_results)

    # --- (c) balanced ---
    if verbose:
        print("[A10 (c)] balanced: rule planner + heuristic executor")
    res_c = oracle_counterfactual_replay(
        lambda s: RulePlanner(seed=s, interval=5), base_kind="rule",
        executor="heuristic", difficulty=difficulty, seeds=seeds, verbose=verbose)
    gap_c = abs(res_c["delta_P"][0] - res_c["delta_E_corrected"][0])
    cases.append({"case": "c_balanced", "expected": "balanced",
                  "identified": res_c["dominant_bottleneck"],
                  "correct": gap_c < 0.15,
                  "gap": gap_c,
                  "delta_P": res_c["delta_P"][0],
                  "delta_E_corrected": res_c["delta_E_corrected"][0]})

    accuracy = n_correct / n_argmax_cases
    report = {
        "difficulty": difficulty,
        "n_seeds": len(seeds),
        "cases": cases,
        "attribution_accuracy": accuracy,
        "severity_calibration_spearman": float(rho),
        "severity_calibration_p": float(rho_p),
        "acceptance": {
            "accuracy_gt_85pct": accuracy > 0.85,
            "severity_rho_gt_0.7": float(rho) > 0.7,
        },
    }
    if verbose:
        print(f"\n[A10] attribution accuracy = {accuracy:.0%} "
              f"(need >85%: {'PASS' if accuracy > 0.85 else 'FAIL'})")
        print(f"[A10] severity calibration ρ = {rho:.3f} "
              f"(need >0.7: {'PASS' if rho > 0.7 else 'FAIL'})")
    return report


# ===========================================================================
# CLI
# ===========================================================================

def main():
    ap = argparse.ArgumentParser(description="Attribution framework (§3.5.1)")
    ap.add_argument("--mode", default="a10", choices=["a10", "algo1", "algo2"])
    ap.add_argument("--difficulty", default="complex")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--output", default="results/attribution_a10.json")
    args = ap.parse_args()

    seeds = list(range(42, 42 + args.seeds))
    t0 = time.time()

    if args.mode == "a10":
        report = a10_injection_validation(args.difficulty, seeds)
    elif args.mode == "algo1":
        systems = [
            SystemSpec("rule+heur", lambda s: RulePlanner(seed=s)),
            SystemSpec("oracle+heur", lambda s: OraclePlanner(seed=s)),
            SystemSpec("random+oracle",
                       lambda s: RandomPlanner(seed=s), executor="oracle"),
            SystemSpec("oracle+degraded30",
                       lambda s: OraclePlanner(seed=s), degraded_p=0.3),
        ]
        report = pairwise_cross_attribution(systems, args.difficulty, seeds)
    else:
        report = oracle_counterfactual_replay(
            lambda s: RulePlanner(seed=s), base_kind="rule",
            executor="heuristic", difficulty=args.difficulty, seeds=seeds)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nSaved {args.output} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
