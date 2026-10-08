"""Open-source readiness audit for the openmd repo.

Read-only. Produces a keep-vs-delete inventory with sizes, grouped by
classification, plus a scan for internal infrastructure strings.
Writes nothing except its own stdout (redirected to a report file).
"""
from __future__ import annotations

import os
import re
import sys
from collections import defaultdict

ROOT = r"C:\Code\source-code\openmd"

DEL_DIRS = {
    "__pycache__", ".pytest_cache", ".ipynb_checkpoints", ".mplcache",
    ".ruff_cache", ".mypy_cache", "htmlcov", ".tox", ".eggs",
}

DEL_EXT = {".pyc", ".pyo", ".pyd", ".log", ".tmp", ".bak", ".orig", ".rej"}

BIG = 20 * 1024 * 1024

# classification buckets -> (list of (path, size))
buckets: dict[str, list[tuple[str, int]]] = defaultdict(list)


def rel(p: str) -> str:
    return os.path.relpath(p, ROOT).replace("\\", "/")


def classify(path: str, size: int) -> str:
    r = rel(path)
    parts = r.split("/")
    name = parts[-1]
    lower = r.lower()
    ext = os.path.splitext(name)[1].lower()

    if any(p in DEL_DIRS for p in parts):
        return "A_cache"
    if ext in DEL_EXT:
        return "A_cache" if ext in {".pyc", ".pyo", ".pyd"} else "B_logs_tmp"
    if re.search(r"\.(bak|backup|old|orig|save)\d*$", name, re.I) or re.search(r"[-_.]backup\d*\.", name, re.I):
        return "B_logs_tmp"
    if name.startswith("_tmp_") or "/_tmp_" in lower:
        return "C_tmp_scripts"
    if re.search(r"\.(pt|pth|npz|ckpt|safetensors|bin|onnx|h5|pkl)$", name, re.I):
        return "D_model_weights"
    if re.search(r"\.(mp4|avi|mov|mkv|gif|png|jpg|jpeg|pdf|svg)$", name, re.I):
        return "E_media"
    if re.search(r"\.(csv|jsonl|parquet|db|sqlite|h5|npy|pkl)$", name, re.I):
        return "F_data_outputs"
    return "Z_keep_other"


for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        fp = os.path.join(dirpath, fn)
        try:
            size = os.path.getsize(fp)
        except OSError:
            continue
        buckets[classify(fp, size)].append((rel(fp), size))

# ---------------------------------------------------------------- dir sizes
dirsize: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # path -> [bytes, files]
for dirpath, dirnames, filenames in os.walk(ROOT):
    r = rel(dirpath)
    for fn in filenames:
        fp = os.path.join(dirpath, fn)
        try:
            size = os.path.getsize(fp)
        except OSError:
            continue
        parts = r.split("/") if r != "." else []
        for i in range(1, min(len(parts), 4) + 1):
            key = "/".join(parts[:i])
            dirsize[key][0] += size
            dirsize[key][1] += 1


def mb(n: int) -> str:
    return f"{n / 1048576:,.1f} MB"


print("=" * 100)
print("SECTION 1  DIRECTORY SIZES (depth<=4, >=1 MB)")
print("=" * 100)
for k, (sz, n) in sorted(dirsize.items(), key=lambda kv: -kv[1][0]):
    if sz >= 1048576:
        print(f"{mb(sz):>12}  {n:>6} files  {k}")

print()
print("=" * 100)
print("SECTION 2  CLASSIFICATION SUMMARY")
print("=" * 100)
total = 0
for k in sorted(buckets):
    sz = sum(s for _, s in buckets[k])
    total += sz
    print(f"{k:<16} files={len(buckets[k]):>5}  size={mb(sz):>14}")
print(f"{'TOTAL':<16} files={sum(len(v) for v in buckets.values()):>5}  size={mb(total):>14}")

print()
print("=" * 100)
print("SECTION 3  BIGGEST FILES (>=20 MB), top 40")
print("=" * 100)
allfiles = sorted(((p, s) for v in buckets.values() for p, s in v), key=lambda x: -x[1])
for p, s in allfiles[:40]:
    print(f"{mb(s):>12}  {p}")
print(f"-- files >=20MB: {sum(1 for _, s in allfiles if s >= BIG)}, "
      f"total {mb(sum(s for _, s in allfiles if s >= BIG))}")

print()
print("=" * 100)
print("SECTION 4  A_cache / B_logs_tmp DETAIL (grouped)")
print("=" * 100)
for key in ("A_cache", "B_logs_tmp"):
    grp: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for p, s in buckets[key]:
        d = "/".join(p.split("/")[:-1])
        grp[d][0] += s
        grp[d][1] += 1
    print(f"-- {key}: {len(buckets[key])} files, {mb(sum(s for _, s in buckets[key]))}")
    for d, (sz, n) in sorted(grp.items(), key=lambda kv: -kv[1][0])[:30]:
        print(f"   {mb(sz):>12}  {n:>4} files  {d}")

print()
print("=" * 100)
print("SECTION 5  code/ LAYOUT")
print("=" * 100)
code = os.path.join(ROOT, "code")
for entry in sorted(os.listdir(code)):
    fp = os.path.join(code, entry)
    if os.path.isdir(fp):
        sz, n = dirsize.get(f"code/{entry}", [0, 0])
        print(f"[DIR ] {mb(sz):>12}  {n:>6} files  code/{entry}")
for entry in sorted(os.listdir(code)):
    fp = os.path.join(code, entry)
    if os.path.isfile(fp):
        print(f"[FILE] {mb(os.path.getsize(fp)):>12}            code/{entry}")

print()
print("=" * 100)
print("SECTION 6  code/eval FILE CLASSES")
print("=" * 100)
ev = [p for v in buckets.values() for p, s in v if p.startswith("code/eval/")]
classes: dict[str, list[int]] = defaultdict(lambda: [0, 0])
for p in ev:
    name = p.split("/")[-1]
    if name.startswith("_w1_"):
        k = "_w1_ work scripts"
    elif name.startswith("_tmp_"):
        k = "_tmp_ *"
    elif name.startswith("LLMRL_") or name.startswith("IE_") or name.startswith("PAPER_"):
        k = "design/audit markdown"
    elif name.endswith(".md"):
        k = "other markdown"
    elif name.endswith(".py"):
        k = "other python"
    else:
        k = "other"
    classes[k][0] += 1
for k, (n, _) in sorted(classes.items(), key=lambda kv: -kv[1][0]):
    print(f"{k:<28} {n:>5} files")
print("-- total files directly in code/eval:",
      len([f for f in os.listdir(os.path.join(code, "eval")) if os.path.isfile(os.path.join(code, "eval", f))]))
print("-- _w1_* count:", len([f for f in os.listdir(os.path.join(code, "eval")) if f.startswith("_w1_")]))
print("-- _tmp_* count:", len([f for f in os.listdir(os.path.join(code, "eval")) if f.startswith("_tmp_")]))

print()
print("=" * 100)
print("SECTION 7  INTERNAL INFRASTRUCTURE STRINGS")
print("=" * 100)
pats = {
    "internal_ip": re.compile(r"\b(?:172\.18|10\.\d+\.\d+|192\.168)\.\d+\.\d+(?::\d+)?"),
    "windows_user_path": re.compile(r"C:\\\\?Users\\\\?(?:沉倚|openmd)"),
    "container_home": re.compile(r"/(?:root|home)/[A-Za-z0-9_.-]+"),
    "gitee_or_gitlab": re.compile(r"(?:gitee\.com|172\.18\.113\.30)"),
    "api_key_like": re.compile(r"\bsk-[A-Za-z0-9]{16,}"),
    "hf_token": re.compile(r"\bhf_[A-Za-z0-9]{20,}"),
}
TEXT_EXT = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini",
            ".sh", ".ps1", ".env", ".html", ".js", ".ts", ".c", ".h", ".cpp", ".cmake", ".rst"}
hits: dict[str, list[str]] = defaultdict(list)
scanned = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in {".venv", "__pycache__", ".git"}]
    for fn in filenames:
        ext = os.path.splitext(fn)[1].lower()
        if ext not in TEXT_EXT and fn not in {".env", "Dockerfile", "Makefile"}:
            continue
        fp = os.path.join(dirpath, fn)
        try:
            if os.path.getsize(fp) > 4 * 1024 * 1024:
                continue
            with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except OSError:
            continue
        scanned += 1
        for label, rx in pats.items():
            if rx.search(text):
                hits[label].append(rel(fp))
print(f"scanned {scanned} text files")
for label in pats:
    lst = hits.get(label, [])
    print(f"-- {label}: {len(lst)} files")
    for p in sorted(lst)[:25]:
        print(f"     {p}")
    if len(lst) > 25:
        print(f"     ... +{len(lst) - 25} more")

sys.stdout.flush()
