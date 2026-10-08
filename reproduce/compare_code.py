"""Compare the local code against the co-author's delivered snapshot.

Run from the release root: `python reproduce/compare_code.py`.

Two things make a naive comparison misleading, and this script handles both:

1. **Layout differs.** Ours nests the harness under `code/analysis/` and the platform
   under `code/engine/`; theirs ships a flat `code/` with `eval/`, `evaluation/` and
   `scripts/`. Matching on relative path therefore finds almost no overlap. Filename is
   the meaningful key.

2. **Same name does not mean same file.** `metrics.py` exists in both trees but is a
   different module (theirs: tournament/Elo evaluation; ours: the strategy scorecard),
   and several `__init__.py` / `validate.py` collisions are unrelated. Comparing those
   by name produces alarming, meaningless "similarity 0.01" results.

Differences are then classified: a changed absolute path or an added `os.environ` lookup
is plumbing, not behaviour, and should not be reported as a divergence in the science.
"""
from __future__ import annotations

import difflib
import hashlib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
MINE_ROOTS = [CODE / "analysis", CODE / "engine"]
THEIRS_ROOT = CODE / "collaborator_snapshot"

# Baseline names that exist in both trees but are DIFFERENT modules. Comparing them
# yields a huge diff that says nothing about agreement.
NAME_COLLISIONS = {"metrics.py", "validate.py", "__init__.py"}

COSMETIC_MARKERS = (
    "C:\\Code", "C:\\Users", "OPENMD_SRC_ROOT", "OPENMD_RELEASE_DIR",
    "Path(__file__)", "_ROOT", "_HERE", "os.environ",
)


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def by_name(roots) -> dict[str, list[Path]]:
    out: dict[str, list[Path]] = defaultdict(list)
    for r in roots:
        if r.is_dir():
            for p in r.rglob("*.py"):
                out[p.name].append(p)
    return out


def main() -> int:
    if not THEIRS_ROOT.is_dir():
        print(f"  co-author snapshot not present: {THEIRS_ROOT}")
        return 0
    mine, theirs = by_name(MINE_ROOTS), by_name([THEIRS_ROOT])
    shared = sorted(set(mine) & set(theirs))

    print("=" * 92)
    print("LOCAL CODE  vs  CO-AUTHOR SNAPSHOT   (matched by filename)")
    print("=" * 92)
    print(f"  our distinct .py names   : {len(mine)}")
    print(f"  their distinct .py names : {len(theirs)}")
    print(f"  shared names             : {len(shared)}")

    classes: dict[str, list] = defaultdict(list)
    for n in shared:
        a, b = mine[n][0], theirs[n][0]
        if digest(a) == digest(b):
            classes["identical"].append(n)
            continue
        al = a.read_text(encoding="utf-8", errors="replace").splitlines()
        bl = b.read_text(encoding="utf-8", errors="replace").splitlines()
        sm = difflib.SequenceMatcher(None, al, bl)
        changed = cosmetic = 0
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            for ln in al[i1:i2] + bl[j1:j2]:
                changed += 1
                if any(m in ln for m in COSMETIC_MARKERS):
                    cosmetic += 1
        share = cosmetic / changed if changed else 0.0
        ratio = sm.ratio()
        if n in NAME_COLLISIONS:
            classes["same name, different module"].append((n, ratio, changed, cosmetic))
        elif ratio > 0.98 or share > 0.6:
            classes["differs, paths/plumbing only"].append((n, ratio, changed, cosmetic))
        elif ratio > 0.90:
            classes["differs, moderate edits"].append((n, ratio, changed, cosmetic))
        else:
            classes["differs, substantial"].append((n, ratio, changed, cosmetic))

    for k in ("identical", "differs, paths/plumbing only", "differs, moderate edits",
              "differs, substantial", "same name, different module"):
        print(f"\n  {k:<34} {len(classes[k])}")
        for entry in sorted(classes[k])[:12]:
            if isinstance(entry, tuple):
                n, ratio, changed, cosmetic = entry
                print(f"      {n:<42} similarity={ratio:.2f} changed={changed}")
            else:
                print(f"      {entry}")

    # The analysis harness, which is what the earlier narrower comparison looked at.
    w1 = [n for n in shared if n.startswith("_w1_")]
    w1_same = [n for n in w1 if digest(mine[n][0]) == digest(theirs[n][0])]
    print(f"\n  --- analysis harness (_w1_*.py) ---")
    print(f"  shared {len(w1)}   identical {len(w1_same)}   different {len(w1) - len(w1_same)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
