"""Verify the delivered P1 episodes reproduce tab_p1_seedgrid cell by cell."""
from __future__ import annotations

import json
import re
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent if (_HERE.parent / "data").is_dir() else _HERE


RAW = (_ROOT / "data" / "collaborator_runs"
           r"\e2-delivery-20261003\raw\P1__six_arm__s501-510__main__v1")
TABLE = Path(r"C:\Code\source-code\release\OpenMDBench-Release\paper\tables"
             r"\tab_p1_seedgrid.tex")

txt = TABLE.read_text(encoding="utf-8")
rows = re.findall(r"^(\d{3})\s+&(.+?)\\\\", txt, re.M)
ORDER = ["Rule+Rule", "LLM+Rule", "Rule+RL", "LLM+RL", "Pure RL", "Pure LLM"]
ARM_OF = {
    "Rule+Rule": "rule-rule", "LLM+Rule": "llm-rule", "Rule+RL": "rule-rl",
    "LLM+RL": "llm-rl", "Pure RL": "rl", "Pure LLM": "pure-llm",
}
paper = {int(s): [float(v.strip()) for v in rest.split("&")] for s, rest in rows}

got: dict[tuple[int, str], float] = {}
for p in sorted(RAW.rglob("episode.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    cfg, met = d.get("config", {}), d.get("metrics", {})
    m = re.search(r"_s(\d+)_", p.parent.name)
    seed = cfg.get("seed") or (int(m.group(1)) if m else None)
    got[(seed, cfg.get("arm"))] = met.get("blue_score")

print("=" * 92)
print("tab_p1_seedgrid  vs  delivered P1 batch")
print("=" * 92)
print(f"  {'seed':<6}" + "".join(f"{a:>12}" for a in ORDER))
exact = near = miss = diff = 0
for seed in sorted(paper):
    line = f"  {seed:<6}"
    for i, label in enumerate(ORDER):
        v = got.get((seed, ARM_OF[label]))
        pv = paper[seed][i]
        if v is None:
            line += f"{'--':>12}"
            miss += 1
        elif abs(v - pv) < 1e-9:
            line += f"{v:>12.3f}"
            exact += 1
        elif abs(v - pv) <= 0.005:
            line += f"{v:>11.3f}~"
            near += 1
        else:
            line += f"{pv:>7.2f}/{v:<4.2f}"
            diff += 1
    print(line)

print(f"\n  cells exact : {exact}/60")
print(f"  cells ~round: {near}/60")
print(f"  cells DIFFER: {diff}/60")
print(f"  cells missing: {miss}/60")
