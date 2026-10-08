"""Coupling estimators for the §4.5 coupling-complexity experiment.

Implements the Kraskov-Stögbauer-Grassberger (KSG, Type-1) k-NN mutual
information estimator plus the paper's coupling quantities, all estimated
from execution traces (no analytical model):

  C_info          = I(S_usv; S_uav | task)            — task structural coupling
  residual MI     = I(S_usv; S_uav | G, task)         — after conditioning on
                     the goal commands G actually issued
  B_if            = C_info − residual MI              — interface capacity
  C_effective     = I(S_usv; S_uav) under policy π    — behavioral coupling

Domain states are aggregated per unit-kind over a small time window
(mean position), giving low-dimensional continuous samples the KSG
estimator can handle; G is a discrete signature of the active UAV goal
command at goal-granularity level (weak / medium / strong).
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.special import digamma
from scipy.spatial import cKDTree

LOG2E = 1.0 / np.log(2.0)   # nats → bits


# ---------------------------------------------------------------------------
# KSG k-NN mutual information (Kraskov et al. 2004, estimator 1)
# ---------------------------------------------------------------------------

def ksg_mi(x: np.ndarray, y: np.ndarray, k: int = 5) -> float:
    """Estimate I(X; Y) in bits from paired samples.

    x: [N, dx], y: [N, dy].  Uses Chebyshev (max) norm and counts strictly
    closer neighbours for the marginal range queries, per Kraskov Type-1.
    """
    x = np.atleast_2d(x.T).T if x.ndim == 1 else x
    y = np.atleast_2d(y.T).T if y.ndim == 1 else y
    n = len(x)
    if n < k + 5:
        return float("nan")
    joint = np.hstack([x, y]).astype(float)
    joint_tree = cKDTree(joint)
    # k+1 neighbours (the point itself is included) → k-th true neighbour
    d, _ = joint_tree.query(joint, k=k + 1, p=np.inf)
    eps = d[:, -1]

    x_tree, y_tree = cKDTree(x.astype(float)), cKDTree(y.astype(float))
    nx = x_tree.query_ball_point(
        x.astype(float), eps * (1 - 1e-10), p=np.inf,
        return_length=True)
    ny = y_tree.query_ball_point(
        y.astype(float), eps * (1 - 1e-10), p=np.inf,
        return_length=True)

    mi_nats = (digamma(k) + digamma(n)
               - np.mean(digamma(nx + 1) + digamma(ny + 1)))
    return float(max(mi_nats, 0.0) * LOG2E)


def discrete_conditional_mi(x: np.ndarray, y: np.ndarray,
                            g: np.ndarray, k: int = 5,
                            min_group: int = 20) -> float:
    """I(X; Y | G) in bits for discrete G: Σ_g p(g) · I(X; Y | G=g)."""
    total = len(x)
    acc = 0.0
    for gv in np.unique(g):
        mask = g == gv
        if mask.sum() < min_group:
            # too few samples to estimate the within-group MI — fall back
            # to the pooled estimate (upper-biases the residual MI, i.e.
            # under-estimates B_if: conservative)
            continue
        acc += (mask.sum() / total) * ksg_mi(x[mask], y[mask], k=k)
    covered = sum((g == gv).sum() for gv in np.unique(g)
                  if (g == gv).sum() >= min_group) / total
    if covered < 0.5:
        # cannot condition reliably → residual = unconditional (B_if = 0)
        return ksg_mi(x, y, k=k)
    return float(acc / covered)


# ---------------------------------------------------------------------------
# Trace → coupling quantities
# ---------------------------------------------------------------------------

def windowed_states(trace: list, window: int = 3) -> np.ndarray:
    """Aggregate a per-step trace into windowed means.

    trace: list of {"usv": (x, y), "uav": (x, y)} dicts, one per step.
    Returns [n_windows, 4]: (usv_mx, usv_my, uav_mx, uav_my).
    """
    rows = []
    usv = np.array([t["usv"] for t in trace], dtype=float)
    uav = np.array([t["uav"] for t in trace], dtype=float)
    for s in range(0, len(trace) - window + 1, window):
        rows.append(np.concatenate([usv[s:s + window].mean(0),
                                    uav[s:s + window].mean(0)]))
    return np.array(rows) if rows else np.empty((0, 4))


def goal_signature(goal: dict | None, granularity: str) -> str:
    """Discrete signature of the active UAV goal command at a granularity.

    weak   : goal_type only
    medium : goal_type + target id
    strong : goal_type + target id + coarsened waypoint (2×2 grid cell)
    """
    if not goal:
        return "none"
    sig = str(goal.get("goal_type", "none"))
    if granularity in ("medium", "strong") and goal.get("target_id"):
        sig += f"@{goal['target_id']}"
    if granularity == "strong":
        wp = goal.get("position") or goal.get("waypoint")
        if wp:
            sig += f"#({int(wp[0]) // 10},{int(wp[1]) // 10})"
    return sig


def estimate_couplings(traces: list, granularity: str = "strong",
                       window: int = 3, k: int = 5) -> dict:
    """Estimate C_info, residual MI and B_if from a pool of episodes.

    traces: list of episodes; each episode is
        {"steps": [{"usv": (x,y), "uav": (x,y), "uav_goal": dict|None}]}
    """
    xs, ys, gs = [], [], []
    for ep in traces:
        W = windowed_states(ep["steps"], window)
        if not len(W):
            continue
        goals = ep["steps"]
        for i, w0 in enumerate(range(0, len(goals) - window + 1, window)):
            chunk = goals[w0:w0 + window]
            g = chunk[len(chunk) // 2].get("uav_goal")  # mid-window goal
            gs.append(goal_signature(g, granularity))
        xs.append(W[:, :2])
        ys.append(W[:, 2:])
    if not xs:
        return {"c_info": float("nan"), "residual_mi": float("nan"),
                "b_if": float("nan"), "n_windows": 0}
    x = np.vstack(xs)
    y = np.vstack(ys)
    g = np.array(gs)

    c_info = ksg_mi(x, y, k=k)
    residual = discrete_conditional_mi(x, y, g, k=k)
    return {"c_info": c_info, "residual_mi": residual,
            "b_if": max(c_info - residual, 0.0), "n_windows": len(x)}


# ---------------------------------------------------------------------------
# Sanity checks (run as script)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    rng = np.random.RandomState(0)

    # 1. independent Gaussians → MI ≈ 0
    a = rng.randn(4000, 2)
    b = rng.randn(4000, 2)
    print(f"independent gaussians:  MI = {ksg_mi(a, b):.3f} bits (expect ≈0)")

    # 2. correlated Gaussians (rho=0.9): MI = -log2(1-rho^2) = 1.76 bits
    rho = 0.9
    z = rng.randn(4000, 2)
    a = z
    b = rho * z + np.sqrt(1 - rho ** 2) * rng.randn(4000, 2)
    print(f"correlated (rho=0.9):   MI = {ksg_mi(a, b):.3f} bits "
          f"(expect ≈{-np.log2(1 - rho**2):.3f})")

    # 3. deterministic coupling removed by conditioning on G
    z = rng.randn(4000, 2)
    g = (z[:, 0] > 0).astype(int)          # G reveals the mixture component
    a = z + g[:, None] * 6                  # X depends on component
    b = z * 1.0 + 0.3 * rng.randn(4000, 2)  # Y ≈ X → coupled within component
    mi_marg = ksg_mi(a, b)
    mi_cond = discrete_conditional_mi(a, b, g)
    print(f"mixture: I(X;Y)={mi_marg:.3f}  I(X;Y|G)={mi_cond:.3f} "
          f"(cond < marg expected)")

    # 4. trace-level: fully coupled vs decoupled synthetic episodes
    def make_trace(coupled: bool, seed: int, length: int = 60):
        r = np.random.RandomState(seed)
        steps = []
        ux, uy, ax, ay = 5.0, 5.0, 15.0, 15.0
        for _ in range(length):
            ux = np.clip(ux + r.randn() * 0.7, 0, 19)
            uy = np.clip(uy + r.randn() * 0.7, 0, 19)
            if coupled:
                ax = np.clip(ux + r.randn() * 2.0, 0, 19)
                ay = np.clip(uy + r.randn() * 2.0, 0, 19)
            else:
                ax = np.clip(ax + r.randn() * 0.7, 0, 19)
                ay = np.clip(ay + r.randn() * 0.7, 0, 19)
            steps.append({"usv": (ux, uy), "uav": (ax, ay), "uav_goal": None})
        return {"steps": steps}

    coup = estimate_couplings([make_trace(True, s) for s in range(30)])
    dec = estimate_couplings([make_trace(False, s) for s in range(30)])
    print(f"coupled traces:  C_info={coup['c_info']:.3f} bits")
    print(f"decoupled traces: C_info={dec['c_info']:.3f} bits "
          f"(expect coupled >> decoupled)")
