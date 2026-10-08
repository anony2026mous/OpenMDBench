"""Backfill training provenance into checkpoints that predate it.

Why a script rather than hand-editing: the numbers in ``_meta`` are a *claim* about
how a file was produced, so each one needs a traceable source.  The table below is
that source.  Nothing here touches the weights -- the file is rewritten from the
arrays it already contains plus the metadata, and the result is verified by
reloading and comparing every weight array bit-for-bit.

``speed_source=None`` means **unknown** and is deliberately not guessed: the
evaluation side must then be told explicitly which convention to use, because a
wrong guess is silent (see ARM5_LLM_RL_EXECUTOR_DESIGN.md §14.18).

Usage:
    python _w1_backfill_theta_meta.py            # dry run, prints what it would do
    python _w1_backfill_theta_meta.py --apply
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ie_rl_policy import META_KEY, load_theta, pack_meta, read_meta  # noqa: E402

RL = Path(__file__).resolve().parent / "_w1_runs" / "rl"

# name -> (speed_source, evidence)
PROVENANCE: dict[str, tuple[str | None, str]] = {
    "theta_rl_legacy.npz": (
        "legacy_tags",
        "由历史恢复入口记录的续训命令得出：`--speed-source legacy_tags`"
        "（tag 名 rl_legacy 亦为此约定）"),
    "theta_rl_legacy2.npz": (
        "legacy_tags",
        "训练命令存档：`... --resume theta_rl_legacy.npz --tag rl_legacy2 "
        "--speed-source legacy_tags`（本次会话启动的后台作业 pwsh-2）"),
    "theta_arm5_rule.npz": (
        None,
        "**无据可查（训练侧）**：train_arm5_rule.jsonl 与 rollout npz 都没有存 "
        "speed_source，启动命令未留档 ⇒ meta 里 speed_source 保持 None，"
        "评测侧必须显式给 --rl-speed-source，否则报 guessed_default。"),
}
#: 只能"推断"、不能"断言"的提示：单列一个字段，绝不写进 speed_source。
#: 把推断值写进 speed_source 会让 guessed 警告消失 —— 那正是要保留的信息。
SPEED_HINTS: dict[str, tuple[str, str]] = {
    "theta_arm5_rule.npz": (
        "legacy_tags",
        "训练侧的 goal-features 探针请求存档 `_w1_runs/rl/_probe_goal.jsonl` 里"
        "写着 `\"speed_source\": \"legacy_tags\", \"goal_features\": true`，"
        "而该字段由 `ie_rl_train.py` 从 `args.speed_source` 填入"
        "（探针代码第 648 行）⇒ 当时这族第五臂训练确实带 "
        "`--speed-source legacy_tags`。但存档只覆盖 arm5_smoke 那次"
        "（09-22 20:40），arm5_rule 主训练（23:05）的启动命令没留档，"
        "所以只能作为**提示**，不作为断言。"),
}
# 这两个是架构自带的，与约定无关，可以直接记
COMMON = {"goal_features": None,  # 由 obs_dim 推出，见下
          "decision_interval": 5,
          "num_units": 16,
          "log_std_init": -1.5}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="已有 meta 也重写（用于补充 hint/evidence 字段；权重仍逐数组校验）")
    args = parser.parse_args()

    for name, (speed_source, evidence) in PROVENANCE.items():
        path = RL / name
        if not path.is_file():
            print(f"-- {name}: 不存在，跳过")
            continue
        theta = load_theta(path)
        existing = read_meta(theta)
        obs_dim = int(theta["trunk0.w"].shape[0])
        # goal block 是否参与：三个已知布局 2226 / 2866(+lead) / 3250(+24/unit goal)
        goal_features = obs_dim >= 3000
        meta = {
            "speed_source": speed_source,
            "goal_features": bool(goal_features),
            "obs_dim": obs_dim,
            "decision_interval": COMMON["decision_interval"],
            "num_units": COMMON["num_units"],
            "log_std_init": COMMON["log_std_init"],
            "provenance": "backfilled",
            "evidence": evidence,
        }
        hint = SPEED_HINTS.get(name)
        if hint:
            meta["speed_source_hint"], meta["speed_source_hint_evidence"] = hint
        print(f"== {name}")
        print(f"   obs_dim={obs_dim} goal_features={goal_features} "
              f"speed_source={speed_source!r}"
              + (f" hint={hint[0]!r}" if hint else ""))
        print(f"   依据：{evidence}")
        if existing and not args.force:
            print(f"   已有 meta，跳过：{existing}")
            continue
        if not args.apply:
            print("   (dry run)")
            continue
        payload = {k: v for k, v in theta.items() if k != META_KEY}
        payload[META_KEY] = pack_meta(meta)
        # np.savez 会给不以 .npz 结尾的路径**自动补 .npz**，所以临时名必须以
        # .npz 结尾，否则随后的读回比对会 FileNotFoundError
        # （而原文件此时还没被替换 —— 失败是安全的，这点很重要）。
        tmp = path.with_name(path.stem + ".tmp.npz")
        np.savez(tmp, **payload)
        # 逐数组比对，任何差异都拒绝替换
        reloaded = load_theta(tmp)
        for key, value in theta.items():
            if key == META_KEY:
                continue
            if not np.array_equal(np.asarray(reloaded[key]), np.asarray(value)):
                tmp.unlink()
                raise SystemExit(f"!! {name}: {key} 重写后不一致，已放弃")
        tmp.replace(path)
        print(f"   已写入 meta；权重逐数组比对一致；读回 = {read_meta(load_theta(path))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
