#!/bin/bash
# 下层战术升级后的 A/B：rule 与 hybrid 在同一新下层上对比
cd /root/source_codes_linux/eval_w1 || exit 1
export PYTHONPATH=/root/source_codes_linux/source_codes
export MPLCONFIGDIR=/tmp/openmdbench-mpl
PY=/root/source_codes_linux/source_codes/.venv/bin/python
OUT=/root/eval_w1_runs/lower_layer_v2
mkdir -p "$OUT"

run() {
  planner="$1"; scenario="$2"; tag="$3"
  echo "=== START $tag ($planner/$scenario) $(date +%H:%M:%S)"
  "$PY" run_episode.py --scenario "$scenario" --planner "$planner" --seed 7 \
      --max-ticks 1800 --plan-interval 10 --step-timeout 90 --wall-limit 2400 \
      --output "$OUT/$tag.json" --log "$OUT/$tag.jsonl"
  echo "=== DONE $tag $(date +%H:%M:%S)"
}

run rule      MD-AD-002-EASY       rule_easy_v2
run rule      MD-AD-004-DECEPTION  rule_deception_v2
run llm       MD-AD-002-EASY       hybrid_easy_v2
run llm       MD-AD-004-DECEPTION  hybrid_deception_v2
echo ALL_LOWER_LAYER_ARMS_DONE
