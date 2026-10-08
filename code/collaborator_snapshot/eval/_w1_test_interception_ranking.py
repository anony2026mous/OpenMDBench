"""Unit test for the interception-graph candidate ranking (③ 的整改复测).

The defect being pinned down
----------------------------
``InterceptionGraph._top_k`` used to rank candidates with

    0.45 * threat + 0.25 * (1 - range_ratio/2) + 0.30 * (1 - eta/scale) + 0.15*can_intercept

where ``threat`` rises as the raider gets *closer to the protected zone*.  Both of
the two largest terms therefore **reward a raider for already being close**: the
frontend systematically preferred targets the defender had let slip deep, and
penalised meeting the same raider far out.  Measured consequence: the hybrid-LLM
arm's mean interception depth was 10.8 km against the rule arm's 18.3 km (see
recorded run notes, s1 experiment §7).

The fix adds an explicit ``intercept_depth_m`` (how far from the zone the two
sides would actually meet if the defender launched now) and gives it real weight,
while keeping urgency via a reduced ``threat`` term.

These tests are pure-function: they build synthetic edge lists, so they need no
episode, no engine session and no LLM endpoint.  That matters because the LLM
endpoint is currently unreachable and the three-arm comparison is blocked on it.

Usage:
    python _w1_test_interception_ranking.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
EVAL = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(EVAL))

from interception_graph import GraphBuilder, GraphConfig  # noqa: E402


class _Bound:
    """Stub that carries only ``config`` so the real ``GraphBuilder._top_k`` runs."""

    def __init__(self, config: GraphConfig) -> None:
        self.config = config

    _top_k = GraphBuilder._top_k


def edge(target: str, *, distance: float, range_m: float, distance_to_zone: float,
         threat: float, eta: float = 0.0, speed_mps: float = 43.0,
         intruder_speed_mps: float = 43.0, domain_ok: bool = True,
         can_intercept: bool = True) -> dict:
    """One candidate edge with intercept_depth derived the same way the graph does."""
    meet_ticks = distance / (speed_mps + intruder_speed_mps)
    depth = distance_to_zone - intruder_speed_mps * meet_ticks
    return {
        "target": target,
        "distance": distance,
        "range_ratio": distance / range_m,
        "eta": eta,
        "feasible_eta_ticks": max(0.0, distance - range_m) / speed_mps,
        "feasible": True,
        "intercept_depth_m": round(depth, 1),
        "target_class": "air",
        "domain_ok": domain_ok,
        "can_intercept": can_intercept,
        "threat": threat,
        "bearing": 90.0,
        "distance_to_zone": distance_to_zone,
        "observed_by": "site.shore-radar",
        "observer_count": 1,
    }


def graph(top_k: int = 1) -> "_Bound":
    """Bind the real ``GraphBuilder._top_k`` to a minimal stub.

    ``GraphBuilder.__init__`` builds weapon policies and speed tables, but
    ``_top_k`` reads only ``self.config``.  Binding the unbound method to a stub
    therefore exercises **the production ranking code** without standing up a
    builder; no ranking logic is duplicated in the test.
    """
    return _Bound(GraphConfig(top_k=top_k))


def test_depth_field_is_monotone_in_geometry():
    """远的目标、且我方离得近 ⇒ 预计拦截纵深更大。"""
    near_zone = edge("a", distance=6000.0, range_m=8000.0, distance_to_zone=4000.0,
                     threat=0.89)
    far_out = edge("b", distance=9000.0, range_m=8000.0, distance_to_zone=30000.0,
                   threat=0.14)
    assert far_out["intercept_depth_m"] > near_zone["intercept_depth_m"]
    # 来袭者已经贴到保护区边缘时，纵深可以算成负值（= 现在出发来不及）
    desperate = edge("c", distance=25000.0, range_m=8000.0,
                     distance_to_zone=500.0, threat=0.99)
    assert desperate["intercept_depth_m"] < 0.0


def test_depth_participates_in_the_ordering():
    """纵深项确实进入排序：其余字段完全相同、只有纵深不同时，纵深大者胜出。

    **刻意不去断言"远的应胜过近的"**。第 14 轮先按那个假设写了测试，结果失败；
    复查后发现假设本身是错的：距保护区 3.5 km 的来袭者已经落在 8 km 打击半径内、
    随时可投放，优先打它是**正确**的。紧迫性本就该压过纵深。

    另外，纵深与既有的 `range_ratio` / `eta` 项在几何上高度同向
    （depth = distance_to_zone − v_来袭 × distance/(v_我+v_来袭)，同一
    distance_to_zone 下 distance 越小纵深越大，而 range_ratio 也越小），
    所以纵深项对排序的实际作用是**在与紧迫性可比的目标之间打破平局**，
    以及**给规划器/LLM 提供"现在出发能在多远拦住它"的显式依据** ——
    这才是 ③ 里真正缺的信息。
    """
    base = dict(distance=6000.0, range_m=8000.0, threat=0.5, eta=200.0)
    shallow = edge("shallow", distance_to_zone=9000.0, **base)
    deep = edge("deep", distance_to_zone=9000.0, **base)
    deep["intercept_depth_m"] = 6000.0     # 同一切其他字段，仅纵深不同
    shallow["intercept_depth_m"] = 200.0
    ranked = graph(top_k=2)._top_k([shallow, deep])
    assert ranked[0]["target"] == "deep", [r["target"] for r in ranked]


def test_urgency_still_dominates_the_depth_term():
    """紧迫性必须压过纵深：已贴近保护区的目标不会被一个"纵深更大"的远目标顶掉。"""
    about_to_strike = edge("strike", distance=3000.0, range_m=8000.0,
                           distance_to_zone=3500.0, threat=0.90, eta=80.0)
    far_out = edge("far", distance=9000.0, range_m=8000.0,
                   distance_to_zone=31000.0, threat=0.11, eta=700.0)
    assert far_out["intercept_depth_m"] > about_to_strike["intercept_depth_m"]
    ranked = graph(top_k=1)._top_k([about_to_strike, far_out])
    assert ranked[0]["target"] == "strike"


def test_ranking_still_engages_the_only_urgent_target():
    """紧迫性不能丢：只有一个已逼近的目标时，必须仍然选它。"""
    urgent = edge("urgent", distance=2500.0, range_m=8000.0,
                  distance_to_zone=900.0, threat=0.97, eta=25.0)
    ranked = graph(top_k=1)._top_k([urgent])
    assert ranked[0]["target"] == "urgent"


def test_domain_unavailable_edges_never_win_the_top_k():
    """域不匹配的边必须排在可用边之后（既有不变量，防止回归）。"""
    wrong_domain = edge("boat", distance=1200.0, range_m=8000.0,
                        distance_to_zone=2000.0, threat=0.95, domain_ok=False)
    usable = edge("uav", distance=9000.0, range_m=8000.0,
                  distance_to_zone=28000.0, threat=0.20)
    ranked = graph(top_k=1)._top_k([wrong_domain, usable])
    assert ranked[0]["target"] == "uav"


def test_deep_term_does_not_override_weapon_domain_rules():
    """纵深项只是加分，不能让"打不到"的边反超"打得到"的边。"""
    cannot = edge("cannot", distance=40000.0, range_m=8000.0,
                  distance_to_zone=45000.0, threat=0.0, can_intercept=False)
    can = edge("can", distance=8000.0, range_m=8000.0,
               distance_to_zone=12000.0, threat=0.5, can_intercept=True)
    scored = {e["target"]: e for e in graph(top_k=2)._top_k([cannot, can])}
    assert set(scored) == {"cannot", "can"}
    top = graph(top_k=1)._top_k([cannot, can])
    assert top[0]["target"] == "can"


def main() -> int:
    tests = [(name, value) for name, value in sorted(globals().items())
             if name.startswith("test_") and callable(value)]
    failures = 0
    for name, function in tests:
        try:
            function()
            print(f"  PASS {name}")
        except AssertionError as error:
            failures += 1
            print(f"  FAIL {name}: {error}")
        except Exception as error:  # noqa: BLE001
            failures += 1
            print(f"  ERROR {name}: {type(error).__name__}: {error}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
