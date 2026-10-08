#!/bin/bash
# 前置模块消融：pure-llm 有/无 GraphBuilder 前置模块（同一代码、同一 seed）
cd /root/source_codes_linux/eval_w1 || exit 1
export PYTHONPATH=/root/source_codes_linux/source_codes
export MPLCONFIGDIR=/tmp/openmdbench-mpl
PY=/root/source_codes_linux/source_codes/.venv/bin/python
OUT=/root/eval_w1_runs/frontend_ablation
mkdir -p "$OUT"

run() {
  planner="$1"; scenario="$2"; frontend="$3"; tag="$4"
  echo "=== START $tag ($planner / $scenario / frontend=$frontend) $(date +%H:%M:%S)"
  "$PY" run_episode.py --scenario "$scenario" --planner "$planner" --seed 7 \
      --max-ticks 1800 --frontend "$frontend" --step-timeout 90 \
      --wall-limit 2400 --output "$OUT/$tag.json" --log "$OUT/$tag.jsonl"
  echo "=== DONE $tag $(date +%H:%M:%S)"
}

run pure-llm MD-AD-002-EASY        graph pll_easy_graph
run pure-llm MD-AD-002-EASY        raw   pll_easy_raw
run pure-llm MD-AD-004-DECEPTION   graph pll_deception_graph
run pure-llm MD-AD-004-DECEPTION   raw   pll_deception_raw
echo ALL_ARMS_DONE
