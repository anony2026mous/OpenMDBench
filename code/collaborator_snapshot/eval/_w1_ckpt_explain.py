"""Explain what the checkpoint files are, by reading them.

Answers, from the artefacts rather than from memory:
  * when each checkpoint was written (tick),
  * which episode wrote it (session_id encodes the seed),
  * whether the naming scheme can collide between arms.
"""
from __future__ import annotations

import glob
import json
import os
import re
from collections import Counter

CK = r"C:\Code\source-code\openmd\code\eval\_w1_runs\checkpoints"

files = sorted(glob.glob(os.path.join(CK, "*.ckpt.json")))
print(f"  checkpoint 文件: {len(files)} 个")
print()

ticks = Counter()
seeds = Counter()
hash_present = 0
for p in files:
    d = json.load(open(p, encoding="utf-8"))
    ticks[d.get("world_checkpoint", {}).get("tick")] += 1
    seeds[d.get("seed")] += 1
    if d.get("checkpoint_hash"):
        hash_present += 1

print("  存档 tick 分布:", dict(ticks))
print("  按 seed:", dict(sorted(seeds.items(), key=lambda kv: kv[0] or 0)))
print(f"  含 checkpoint_hash 的: {hash_present}/{len(files)}")
print()

print("  文件名格式: <SCENARIO>_<seed>.ckpt.json")
print("  => 同一场景、同一种子的 3 个臂会写到同一个路径，互相覆盖。")
print(f"  => 每个 (场景,种子) 组合只保留最后写入的那一份。")
print()

# 逐场景统计：14 场景 x 每场景应有几个种子
per_scen = Counter()
for p in files:
    stem = os.path.basename(p)[: -len(".ckpt.json")]
    sc, _, _sd = stem.rpartition("_")
    per_scen[sc] += 1
print("  逐场景 checkpoint 数（若为 6，说明 6 个种子各留 1 份）:")
for sc, n in sorted(per_scen.items()):
    print(f"    {sc:<30} {n}")
print()

sample = files[0]
d = json.load(open(sample, encoding="utf-8"))
print(f"  样本内容摘要（{os.path.basename(sample)}）:")
print(f"    session_id            = {d.get('session_id')}")
print(f"    seed                  = {d.get('seed')}")
print(f"    session_state         = {d.get('session_state')}")
print(f"    world tick            = {d.get('world_checkpoint', {}).get('tick')}")
print(f"    world_checkpoint 键   = {list((d.get('world_checkpoint') or {}).keys())}")
print(f"    rng_state_hash        = {d.get('rng_state_hash')}")
print(f"    checkpoint_hash       = {d.get('checkpoint_hash')}")
print(f"    含 planner 内部状态?  ", "planner" in json.dumps(d).lower())
