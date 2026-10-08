"""Gate: speed-convention provenance must be resolved by exactly one rule.

Why this needs its own gate: the failure it guards against is **silent**.  A policy
trained with one speed table and evaluated with the other produces a normal-looking
scorecard -- just a lower number -- and that number is the one an ablation rests on.
Measured once: `theta_rl_legacy2` (trained `legacy_tags`) was evaluated through
`rl_agent.py`'s `catalog` default and the whole batch had to be discarded
(ARM5_LLM_RL_EXECUTOR_DESIGN.md §14.18).

So the precedence is pinned here by test, not by comment:

    argument > checkpoint meta > RL_SPEED_SOURCE > default ("guessed_default")

Usage: python _w1_test_speed_provenance.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ie_rl_policy import (META_KEY, load_theta, pack_meta, read_meta,  # noqa: E402
                          save_theta)
from rl_agent import _resolve_speed_source  # noqa: E402

PASSED = 0
FAILED: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASSED
    if condition:
        PASSED += 1
        print(f"  ok   {name}")
    else:
        FAILED.append(f"{name}: {detail}")
        print(f"  FAIL {name}  {detail}")


def main() -> int:
    saved = os.environ.pop("RL_SPEED_SOURCE", None)
    try:
        print("== 优先级 ==")
        # 1. 显式参数最高
        value, origin = _resolve_speed_source(
            "catalog", {"speed_source": "legacy_tags"}, "legacy_tags")
        check("参数覆盖 meta", (value, origin) == ("catalog", "argument"),
              f"got {(value, origin)}")

        # 2. 没有参数时用 checkpoint meta
        value, origin = _resolve_speed_source(None, {"speed_source": "legacy_tags"},
                                             "catalog")
        check("无参数时用 meta", (value, origin) == ("legacy_tags", "checkpoint_meta"),
              f"got {(value, origin)}")

        # 3. meta 缺失/为 None（老 checkpoint）时用环境变量
        os.environ["RL_SPEED_SOURCE"] = "catalog"
        value, origin = _resolve_speed_source(None, {}, "legacy_tags")
        check("meta 缺失时用环境变量", (value, origin) == ("catalog", "environment"),
              f"got {(value, origin)}")
        value, origin = _resolve_speed_source(None, {"speed_source": None}, "legacy_tags")
        check("meta 里 speed_source=None 视为没有", 
              (value, origin) == ("catalog", "environment"), f"got {(value, origin)}")
        os.environ.pop("RL_SPEED_SOURCE")

        # 4. 都没有 -> 默认值，且必须自报家门为"猜的"
        value, origin = _resolve_speed_source(None, {}, "legacy_tags")
        check("都不给时用默认值并标记 guessed_default",
              (value, origin) == ("legacy_tags", "guessed_default"),
              f"got {(value, origin)}")

        # 5. 非法值必须报错，不能静默当默认
        try:
            _resolve_speed_source("nonsense", {}, "legacy_tags")
            check("非法值抛错", False, "没有抛错")
        except ValueError:
            check("非法值抛错", True)

        print("== checkpoint 里的 meta 往返 ==")
        theta = {"trunk0.w": np.zeros((4, 2), dtype=np.float32),
                 "log_std": np.zeros(3, dtype=np.float32)}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "theta.npz"
            save_theta(path, theta, {"speed_source": "legacy_tags", "obs_dim": 2866})
            back = load_theta(path)
            check("meta 可读回", read_meta(back).get("speed_source") == "legacy_tags",
                  str(read_meta(back)))
            check("权重组未被 meta 破坏",
                  back["trunk0.w"].shape == (4, 2) and back["log_std"].shape == (3,),
                  str(sorted(back)))
            check("meta 不参与前向（键名不撞权重）",
                  all(k in ("trunk0.w", "log_std", META_KEY) for k in back),
                  str(sorted(back)))
        check("没有 meta 时返回空 dict（老 checkpoint 情形）", read_meta(theta) == {},
              str(read_meta(theta)))

        print("== 真实检查点的 provenance ==")
        rl = HERE / "_w1_runs" / "rl"
        for name, expected in (("theta_rl_legacy2.npz", "legacy_tags"),
                               ("theta_rl_legacy.npz", "legacy_tags")):
            path = rl / name
            if not path.is_file():
                check(f"{name} 存在", False, "文件缺失")
                continue
            meta = read_meta(load_theta(path))
            check(f"{name} 记着 {expected}", meta.get("speed_source") == expected,
                  str(meta.get("speed_source")))
            value, origin = _resolve_speed_source(None, meta, "catalog")
            check(f"{name} 解析为 meta 而不是默认 catalog",
                  (value, origin) == (expected, "checkpoint_meta"),
                  f"got {(value, origin)}")

        path = rl / "theta_arm5_rule.npz"
        if path.is_file():
            meta = read_meta(load_theta(path))
            check("arm5_rule 的 speed_source 保持未断言（None）",
                  meta.get("speed_source") is None, str(meta.get("speed_source")))
            check("arm5_rule 只留 hint，不留断言",
                  meta.get("speed_source_hint") in (None, "legacy_tags")
                  and "speed_source_hint_evidence" in meta,
                  str(sorted(meta)))
    finally:
        if saved is not None:
            os.environ["RL_SPEED_SOURCE"] = saved

    print()
    print(f"=== summary ===\n  {PASSED}/{PASSED + len(FAILED)} checks passed")
    for item in FAILED:
        print("  -", item)
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
