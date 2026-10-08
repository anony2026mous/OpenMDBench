"""Fingerprint the analysis outputs, so a before/after comparison is exact.

Hashes every withheld episode's (file, seed, arm, score, ticks) plus the rendered
documents.  Two runs that differ in ANY of these produce different digests, so this
is a real check rather than a proxy.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

EVAL = Path(r"C:\Code\source-code\openmd\code\eval")
RUNS = EVAL / "_w1_runs"

# 1. every withheld episode report: path + size + mtime is too weak; hash content
h = hashlib.sha256()
files = sorted(p for p in RUNS.glob("*_n3*.json"))
for p in files:
    h.update(p.name.encode())
    h.update(p.read_bytes())

rows = 0
table = []
for p in files:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    rows += 1
    table.append((p.name, d.get("seed"), d.get("planner"),
                  (d.get("strategy_scorecard") or {}).get("defender_score"),
                  d.get("ticks_run")))

# 2. rendered documents
doc_h = {}
for name in ("DATASET_5SEEDS.csv", "DATASET_5SEEDS.json", "DATASET_5SEEDS.md",
             "THE_WITHHELD_RESULTS.md", "LLMRL_WITHHELD_TABLE.md"):
    p = EVAL / name
    doc_h[name] = hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "MISSING"

src = hashlib.sha256(json.dumps(sorted(map(str, table)), ensure_ascii=False)
                     .encode()).hexdigest()

print(f"  withheld report files : {len(files)}")
print(f"  parsed episodes       : {rows}")
print(f"  content digest        : {h.hexdigest()[:24]}")
print(f"  parsed-table digest   : {src[:24]}")
print("  documents:")
for k, v in doc_h.items():
    print(f"    {k:<28} {v}")

(Path(r"C:\Code\source-code\openmd\code\eval\_w1_fingerprint.json")).write_text(
    json.dumps({"files": len(files), "rows": rows,
                "content": h.hexdigest(), "table": src, "docs": doc_h},
               indent=1), encoding="utf-8")
