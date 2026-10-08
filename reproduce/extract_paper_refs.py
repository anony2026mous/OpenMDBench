"""Extract every data/code reference from the paper's LaTeX sources.

The .tex files are the authoritative source (the PDFs are compiled from them), so
this parses those rather than trying to read the PDFs.  Goal: a checklist of
artefacts the release must contain for the paper to be reproducible.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

# Default to the shipped copy inside this repository, so the script works after a clone.
D = Path(os.environ.get("OPENMD_PAPER_DIR",
                        Path(__file__).resolve().parent.parent / "paper"))

PATTERNS = {
    "includegraphics": re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}"),
    "input/include": re.compile(r"\\(?:input|include)\{([^}]+)\}"),
    "texttt": re.compile(r"\\texttt\{([^}]+)\}"),
    "filename-like": re.compile(r"\b[\w./-]+\.(?:json|csv|py|npz|yaml|yml|tex|md|txt|sha256|pdf|pdb)\b"),
    "hash": re.compile(r"\b(?:sha256:)?[0-9a-f]{16,64}\b"),
    "seeds": re.compile(r"seeds?\s+(?:\$?\\?[^.]{0,20}?\$?\s*)?(\d{3,6})", re.I),
}

for name in ("main.tex", "appendix.tex"):
    p = D / name
    if not p.exists():
        print(f"!! {name} missing")
        continue
    src = p.read_text(encoding="utf-8", errors="replace")
    print("=" * 100)
    print(f"{name}   ({len(src.splitlines())} lines)")
    print("=" * 100)

    for label, rx in PATTERNS.items():
        hits = rx.findall(src)
        seen: list[str] = []
        for h in hits:
            h = h.strip()
            if h and h not in seen:
                seen.append(h)
        if not seen:
            continue
        print(f"\n--- {label} ({len(seen)} distinct) ---")
        for h in seen[:60]:
            print(f"    {h}")
        if len(seen) > 60:
            print(f"    ... (+{len(seen) - 60} more)")

    # section headings, to see which appendix covers what
    print("\n--- sections ---")
    for m in re.finditer(r"\\(?:sub)?section\{([^}]+)\}", src):
        print(f"    {m.group(1)[:110]}")
