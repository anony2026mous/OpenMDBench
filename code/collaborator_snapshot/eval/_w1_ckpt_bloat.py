"""Measure checkpoint JSON bloat: which keys dominate the 5.9 GB."""
import json
import os

CK = r"C:\Code\source-code\openmd\code\eval\_w1_runs\checkpoints"

files = sorted(os.listdir(CK))
print("checkpoint count:", len(files))
tot = sum(os.path.getsize(os.path.join(CK, f)) for f in files)
print(f"total {tot / 2**30:.2f} GiB")

p = os.path.join(CK, [f for f in files if f.endswith(".ckpt.json")][0])
print("\n== structure of", os.path.basename(p), "==")
with open(p, encoding="utf-8") as fh:
    txt = fh.read()
print("raw chars:", len(txt))
d = json.loads(txt)
print("top keys:", list(d.keys()))


def walk(node, prefix="", depth=0, budget=6):
    if depth > budget:
        return
    if isinstance(node, dict):
        for k, v in list(node.items())[:40]:
            s = len(json.dumps(v))
            if s > 4096:
                print(f"  {prefix}{k:<28} {type(v).__name__:<6} bytes~{s:>12,}")
                walk(v, prefix + k + ".", depth + 1, budget)
    elif isinstance(node, list) and node:
        s = len(json.dumps(node))
        if s > 4096:
            print(f"  {prefix}[0] of {len(node):<6} {type(node[0]).__name__:<6} bytes~{s:>12,}")
            walk(node[0], prefix + "0.", depth + 1, budget)


walk(d)

# key-level byte attribution on the raw text
print("\n== top-level byte attribution ==")
for k, v in d.items():
    print(f"  {k:<28} {len(json.dumps(v)):>14,}")

# legacy vs new package version fingerprint
print("\n== ISLAND-STRIKE legacy vs IE-08 metadata ==")
for name in ("MD-AD-006-ISLAND-STRIKE_7.ckpt.json", "IE-08-ISLAND-STRIKE_7.ckpt.json"):
    fp = os.path.join(CK, name)
    if not os.path.exists(fp):
        continue
    with open(fp, encoding="utf-8") as fh:
        dd = json.load(fh)
    print(f"-- {name}: {os.path.getsize(fp) / 2**20:.1f} MB")
    for k in ("scenario_id", "scenario", "resolved_hash", "seed", "session_id", "meta"):
        if k in dd:
            print(f"     {k} = {str(dd[k])[:160]}")
    print("     all keys:", list(dd.keys()))
