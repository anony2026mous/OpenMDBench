"""汇总下层升级后的 A/B 结果，并统计 hybrid 实际使用的 goal_type 分布。"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path("/root/eval_w1_runs/lower_layer_v2")
ARMS = ["rule_easy_v2", "hybrid_easy_v2", "rule_deception_v2", "hybrid_deception_v2"]

print("| 组 | 场景 | Ticks | 终局 | V | 生存 | 歼灭 | 开火 | 真威胁 | 诱饵 | 首开火 |")
print("|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|")
for tag in ARMS:
    path = ROOT / f"{tag}.json"
    if not path.is_file():
        print(f"| {tag} | (missing) | | | | | | | | | |")
        continue
    d = json.loads(path.read_text(encoding="utf-8"))
    m = d.get("layered_metrics") or {}
    term = str(d.get("terminal_result") or "")
    outcome = ("timeout_hold" if d.get("ticks_run", 0) >= 1799 and not term
               else ("intruder_success" if "intruder" in term else "other"))
    print("| {tag} | {sc} | {t} | {o} | {v} | {s} | {n} | {f} | {th} | {de} | {ff} |".format(
        tag=tag, sc=d.get("scenario"), t=d.get("ticks_run"), o=outcome,
        v=m.get("performance_v"), s=m.get("defender_survival_rate"),
        n=m.get("threat_neutralization_rate"), f=d.get("total_fires"),
        th=m.get("fires_threat"), de=m.get("fires_decoy"),
        ff=m.get("first_fire_tick")))

print()
print("== LLM 实际使用的 goal_type（从 plan 日志的 accepted 列表统计）==")
goal_re = re.compile(r"([a-z]+)_\d{3}")
for tag in ("hybrid_easy_v2", "hybrid_deception_v2"):
    log = ROOT / f"{tag}.jsonl"
    if not log.is_file():
        continue
    counter = Counter()
    for line in log.read_text(encoding="utf-8").splitlines():
        if '"plan"' not in line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        for task in (event.get("accepted") or ()):
            match = goal_re.match(str(task))
            if match:
                counter[match.group(1)] += 1
    print(f"{tag}: {dict(counter.most_common())}")
