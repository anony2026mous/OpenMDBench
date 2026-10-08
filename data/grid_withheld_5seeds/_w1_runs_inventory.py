"""Inventory _w1_runs: compact result JSONs vs bulk checkpoint blobs."""
import os
import re
from collections import defaultdict

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"

groups = defaultdict(lambda: [0, 0])
for dirpath, dirnames, filenames in os.walk(RUNS):
    for fn in filenames:
        fp = os.path.join(dirpath, fn)
        rel = os.path.relpath(fp, RUNS).replace("\\", "/")
        try:
            size = os.path.getsize(fp)
        except OSError:
            continue
        top = rel.split("/")[0]
        if rel.startswith("checkpoints/"):
            key = "checkpoints/  (full-episode blobs)"
        elif rel.startswith("rl/"):
            key = "rl/  (weights+runs)"
        elif rel.startswith("logs/"):
            key = "logs/"
        else:
            key = "top-level results"
        groups[key][0] += 1
        groups[key][1] += size

print("== _w1_runs groups ==")
for k, (n, s) in sorted(groups.items(), key=lambda kv: -kv[1][1]):
    print(f"  {k:<38} {n:>5} files  {s/2**20:>10,.1f} MB")

print("\n== top-level result files by name pattern ==")
pat = defaultdict(lambda: [0, 0])
for fn in os.listdir(RUNS):
    fp = os.path.join(RUNS, fn)
    if not os.path.isfile(fp):
        continue
    base = re.sub(r"[0-9]{4,}", "#", fn)
    base = re.sub(r"_(?:seed)?\d+", "_N", base)
    if base.endswith(".json"):
        kind = "episode result json"
    elif base.endswith((".md",)):
        kind = "report md"
    elif base.endswith((".csv",)):
        kind = "table csv"
    elif base.endswith((".txt",)):
        kind = "txt"
    elif base.endswith((".bak",)):
        kind = "BACKUP files (.bak)"
    elif base.endswith((".jsonl",)):
        kind = "jsonl logs"
    else:
        kind = base.rsplit(".", 1)[-1]
    pat[kind][0] += 1
    pat[kind][1] += os.path.getsize(fp)
for k, (n, s) in sorted(pat.items(), key=lambda kv: -kv[1][1]):
    print(f"  {k:<38} {n:>5} files  {s/2**20:>10,.1f} MB")

print("\n== non-episode top-level files (md/txt/csv/bak) ==")
for fn in sorted(os.listdir(RUNS)):
    fp = os.path.join(RUNS, fn)
    if os.path.isfile(fp) and not fn.endswith(".json"):
        print(f"  {os.path.getsize(fp)/1024:>8,.1f} KB  {fn}")

print("\n== a sample episode result json (compact?) ==")
cands = [f for f in os.listdir(RUNS) if f.endswith(".json")]
cands.sort(key=lambda f: -os.path.getsize(os.path.join(RUNS, f)))
for f in cands[:3] + cands[-3:]:
    print(f"  {os.path.getsize(os.path.join(RUNS, f))/1024:>10,.1f} KB  {f}")
