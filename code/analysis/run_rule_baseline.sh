#!/bin/bash
# 同代码、同 seed 的 rule 基线条（前置模块对照实验参照）
cd /root/source_codes_linux/eval_w1 || exit 1
export PYTHONPATH=/root/source_codes_linux/source_codes
export MPLCONFIGDIR=/tmp/openmdbench-mpl
PY=/root/source_codes_linux/source_codes/.venv/bin/python
OUT=/root/eval_w1_runs/frontend_ablation
mkdir -p "$OUT"

"$PY" run_episode.py --scenario MD-AD-002-EASY --planner rule --seed 7 \
    --max-ticks 1800 --output "$OUT/rule_easy.json" --log "$OUT/rule_easy.jsonl"
echo "=== RULE EASY DONE"
"$PY" run_episode.py --scenario MD-AD-004-DECEPTION --planner rule --seed 7 \
    --max-ticks 1800 --output "$OUT/rule_deception.json" --log "$OUT/rule_deception.jsonl"
echo "=== RULE DECEPTION DONE"
