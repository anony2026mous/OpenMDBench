#!/bin/bash
# auto-chain after grid-info: merge results -> A3 complex (heuristic
# executor) -> P0-D two-role tournament. Launched 8/28 while the two
# grid-info LLM processes (2-concurrency cap) were still running.
cd /home/<user>/zrz/test_jidi/openMD/code
PY=/home/<user>/anaconda3/envs/jidi/bin/python
export OPENAI_BASE_URL=http://172.18.116.170:8000/v1
export LLM_DEFAULT_MODEL=Qwen3.8-27B

# 1. wait for both grid-info processes to exit
while kill -0 75574 2>/dev/null || kill -0 75722 2>/dev/null; do
  sleep 60
done
echo "grid-info done at $(date +%m-%d\ %H:%M)" >> logs/auto_chain.log

# 2. merge a+b with paired bootstrap contrasts
$PY - <<'EOF'
import json
import numpy as np
a = json.load(open('results/grid_info_a.json'))['systems']
b = json.load(open('results/grid_info_b.json'))['systems']
systems = {**a, **b}
rng = np.random.RandomState(0)
contrasts = {}
for x, y in [("hybrid_intel", "hybrid_heuristic"),
             ("hybrid_intel", "rule_heuristic"),
             ("hybrid_intel", "rule_intel"),
             ("rule_intel", "rule_heuristic")]:
    if x in systems and y in systems:
        d = np.array(systems[x]["sr_list"]) - np.array(systems[y]["sr_list"])
        boots = [float(np.mean(rng.choice(d, len(d))))
                 for _ in range(1000)]
        contrasts[f"{x} - {y}"] = {
            "delta_SR": round(float(np.mean(d)), 4),
            "ci95": [round(float(np.percentile(boots, 2.5)), 4),
                     round(float(np.percentile(boots, 97.5)), 4)]}
out = {"config": json.load(open('results/grid_info_a.json'))["config"],
       "systems": systems, "contrasts": contrasts}
json.dump(out, open('results/grid_info_experiment.json', 'w'),
          indent=1, default=str)
print({k: v["SR"] for k, v in systems.items()})
for k, v in contrasts.items():
    print(f"  {k}: dSR={v['delta_SR']:+.2f} CI=[{v['ci95'][0]:+.2f},{v['ci95'][1]:+.2f}]")
EOF
echo "merged at $(date +%m-%d\ %H:%M)" >> logs/auto_chain.log

# 3. A3 complex: interface ablation with the heuristic executor backend
#    (MAPPO complex is an SR=0 floor — it would mask any nl/json gap)
$PY ablation_nl_json.py --difficulties complex --episodes 45 --seed0 200 \
   --executor heuristic --out results/ablation_nl_json_complex45.json \
   >> logs/ablation_complex45.log 2>&1
echo "A3 complex done at $(date +%m-%d\ %H:%M)" >> logs/auto_chain.log

# 4. P0-D: two-role round-robin tournament, default lineup, 5 eps/pair
$PY run_tournament.py --difficulties simple medium complex --episodes 5 \
   >> logs/tournament_v214.log 2>&1
echo "tournament done at $(date +%m-%d\ %H:%M)" >> logs/auto_chain.log
