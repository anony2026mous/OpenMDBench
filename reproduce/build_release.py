"""Build the submission release folder.

Design rules, learned from what is actually on disk:

  * GitHub-hostile sizes are kept OUT of the repo tree and described by a manifest
    instead.  `artifacts/` alone is 11.5 GB of engine-run evidence and the HF
    campaigns are 18 GB of tick-by-tick traces; neither belongs in git history.
  * Nothing is ever moved or deleted from the source trees.  The release is a copy.
  * Credentials are never copied: private keys, tokens, `.env`, `.huairou` caches and
    the SSH material are excluded by an explicit deny-list, and the build reports
    every exclusion so the choice is auditable.
  * The script is idempotent: re-running rebuilds the release from scratch.

Run:  python build_release.py [--dest <dir>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SRC_ROOT = Path(os.environ.get("OPENMD_SRC_ROOT", r"C:\Code\source-code"))
ENGINE = SRC_ROOT / "openmd" / "source-code" / "source_codes"
EVAL = SRC_ROOT / "openmd" / "code" / "eval"
# The manuscript normally lives outside the source checkout; override per machine.
PAPER = Path(os.environ.get("OPENMD_PAPER_DIR",
                            SRC_ROOT.parent / "openmd-paper" / "openmd-paper"))
EXPERIMENTS = SRC_ROOT / "server-experiments"

DEFAULT_DEST = SRC_ROOT / "release" / "OpenMDBench-Release"

# ---------------------------------------------------------------- deny-lists
SECRET_NAME_PATTERNS = (
    "id_rsa", "id_ed25519", "private", "credential", "credentials",
    "token", "apikey", "api_key", "secret", "password", ".env", ".netrc",
    "sshkey", "jianwei_li", "cookie", "session_key",
)
SECRET_DIR_NAMES = {".huairou", ".ssh", ".gnupg", ".cao", ".claude-scratch"}

# directories that must never be copied (size or noise)
JUNK_DIR_NAMES = {
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".ipynb_checkpoints", ".mplcache", "artifacts", ".venv", "venv",
    "node_modules", ".git", "snapshots", "checkpoints",
    # LaTeX build cache that ships inside the manuscript folder: ~30 MB of Tectonic
    # format files and download cache, regenerated on any local compile.
    ".home",
}

# Stray run logs are not release material, and they leak the authoring machine's
# absolute home paths (measured: 69 occurrences, mostly in these files).
#
# Only `.console.txt` and lock files are dropped by SUFFIX. `.jsonl` and `.log` are not,
# because the same suffix names both disposable logs and real evidence: g1-fault-dose
# stores per-tick traces as .jsonl (76 MB), and the e1-2x2 batch's SHA-256 manifest
# accounts for 594 files including 220 .log files. Excluding those two by suffix silently
# dropped evidence twice, so they are filtered by PATH instead (see is_junk), and the
# home paths that motivated the suffix rule in the first place are rewritten afterwards
# by sanitize_data_paths().
JUNK_FILE_SUFFIXES = (".console.txt", ".log.lock")

# Suffixes that are never release material wherever they appear. These are editor and
# build leftovers with no directory to filter on: the engine scenario tree shipped four
# `scenario.yaml.bak` files, and a stray `__pycache__` reappears whenever a shipped
# script is compiled during verification.
JUNK_FILE_EXTENSIONS = {
    ".bak", ".orig", ".rej", ".swp", ".swo", ".tmp", ".pyc", ".pyo", ".pyd",
    ".pem", ".key", ".ppk", ".p12", ".pfx",
}

# Directories whose .jsonl/.log contents are logs rather than data.
LOG_DIR_NAMES = {"logs", "log", "_w1_runs"}

# Files that must NEVER be published, with the reason recorded in the build report.
# `KEY_DO_NOT_SHARE.json` is the blind-annotation answer key: the appendix's kappa
# statistic depends on the human annotators not having seen the machine labels, so
# publishing the key would invalidate the very measurement it supports. Its parent
# directory (`e5_easy/`) is therefore excluded wholesale rather than filtered.
NEVER_PUBLISH_NAMES = {"key_do_not_share.json"}

# Scripts that read inputs from OUTSIDE this repository (a co-author's figure export,
# a planning note). Their absolute paths are useless to a reader, so they are rewritten
# to read from an environment variable and fall back to a documented relative path.
SANITIZE_TARGETS = {
    "code/role_c_toolkit/e5_figA4_verify.py": "OPENMD_FIGA4_DATA_DIR",
    "code/role_c_toolkit/e5_figA4_raw_audit.py": "OPENMD_FIGA4_DATA_DIR",
    "code/role_c_toolkit/e4_exp2_blockers_doc.py": "OPENMD_EXP2_BRIEF_MD",
}
_HOME_LEAK_RE = re.compile(r'r?"[A-Za-z]:\\Users\\[^"\r\n]{1,200}"')

# ---------------------------------------------------------------- helpers
copied_log: list[tuple[str, int, int]] = []      # (relpath, files, bytes)
excluded_log: list[tuple[str, str]] = []         # (relpath, reason)


def is_secret(p: Path) -> str | None:
    low = p.name.lower()
    if low in NEVER_PUBLISH_NAMES:
        return f"withheld by policy ({p.name}): blind-annotation answer key"
    for pat in SECRET_NAME_PATTERNS:
        if pat in low:
            return f"credential-like name ({pat})"
    for part in p.parts:
        if part.lower() in SECRET_DIR_NAMES:
            return f"credential-like directory ({part})"
    return None


def is_junk(p: Path) -> str | None:
    if p.name.lower().endswith(JUNK_FILE_SUFFIXES):
        return f"stray run log ({p.suffix})"
    for part in p.parts:
        if part.lower() in JUNK_DIR_NAMES:
            return f"excluded dir ({part})"
    # .jsonl and .log are kept or dropped by LOCATION: the same suffix names both
    # per-episode console logs (drop) and real batch evidence (keep).
    if p.suffix in (".jsonl", ".log"):
        if any(part.lower() in LOG_DIR_NAMES for part in p.parts[:-1]):
            return f"run log ({p.suffix} under a log directory)"
        if re.search(r"\.console\.(jsonl|log)$", p.name, re.I):
            return f"run log (.console{p.suffix})"
    if p.suffix.lower() in JUNK_FILE_EXTENSIONS:
        return f"editor/build leftover ({p.suffix})"
    if p.suffix in (".so", ".log.lock"):
        return f"build artifact ({p.suffix})"
    return None


def copy_tree(src: Path, dst: Path, *, label: str, max_mb: float | None = None) -> None:
    """Copy a tree wholesale, applying the deny-lists, and record what happened."""
    if not src.exists():
        excluded_log.append((label, "SOURCE MISSING"))
        return
    files = 0
    size = 0
    for root, dirs, names in os.walk(src):
        rp = Path(root)
        # prune junk dirs in-place so os.walk does not descend
        keep_dirs = []
        for d in dirs:
            if d.lower() in JUNK_DIR_NAMES:
                excluded_log.append((str(rp / d), f"excluded dir ({d})"))
            else:
                keep_dirs.append(d)
        dirs[:] = keep_dirs

        for n in names:
            sp = rp / n
            reason = is_secret(sp) or is_junk(sp)
            if reason:
                excluded_log.append((str(sp), reason))
                continue
            rel = sp.relative_to(src)
            tp = dst / rel
            tp.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(sp, tp)
            except Exception as exc:  # noqa: BLE001
                excluded_log.append((str(sp), f"copy failed: {exc}"))
                continue
            files += 1
            size += sp.stat().st_size
    copied_log.append((label, files, size))


def sha256(path: Path, limit: int | None = None) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        left = limit
        while True:
            chunk = fh.read(1 << 20 if left is None else min(1 << 20, left))
            if not chunk:
                break
            h.update(chunk)
            if left is not None:
                left -= len(chunk)
                if left <= 0:
                    break
    return h.hexdigest()


def survey(path: Path) -> dict:
    """Count and size a tree without copying it (for the external-data manifest)."""
    if not path.exists():
        return {"exists": False}
    files = 0
    size = 0
    for root, dirs, names in os.walk(path):
        dirs[:] = [d for d in dirs if d.lower() not in JUNK_DIR_NAMES]
        for n in names:
            p = Path(root) / n
            files += 1
            try:
                size += p.stat().st_size
            except OSError:
                pass
    return {"exists": True, "files": files, "bytes": size,
            "mb": round(size / 1e6, 1), "gb": round(size / 1e9, 2)}


def sanitize_data_paths(dest: Path) -> None:
    """Generalise authoring-machine home paths inside shipped prose data.

    Handoff notes and result documents sometimes reference where a deliverable was
    written. That leaks one machine's account name without helping any reader, so the
    prefix is rewritten to a portable form that still reads correctly.
    """
    target = re.compile(r"[A-Za-z]:\\Users\\[^\\\r\n`\"']{1,40}")
    for p in (dest / "data").rglob("*"):
        if not p.is_file() or p.suffix.lower() not in (
                ".md", ".txt", ".json", ".csv", ".yaml", ".yml"):
            continue
        try:
            src = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        new, n = target.subn("$HOME", src)
        if n:
            p.write_text(new, encoding="utf-8")
            excluded_log.append((str(p.relative_to(dest)),
                                 f"sanitized {n} home path(s) in prose"))


def sanitize_external_paths(dest: Path) -> None:
    """Rewrite co-author input paths in shipped scripts to read an env var.

    These scripts read data that lives outside this repository. Their absolute paths
    both leak the authoring machine's account name and are useless to a reader, so the
    path is replaced with a lookup that fails with a clear message instead.
    """
    for rel, envvar in SANITIZE_TARGETS.items():
        p = dest / rel
        if not p.is_file():
            continue
        src = p.read_text(encoding="utf-8")
        new, n = _HOME_LEAK_RE.subn(f'os.environ.get("{envvar}", "")', src)
        if n:
            if "import os" not in new:
                new = new.replace("from pathlib import Path",
                                  "import os\nfrom pathlib import Path", 1)
            p.write_text(new, encoding="utf-8")
            excluded_log.append((rel, f"sanitized {n} external absolute path(s)"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=str(DEFAULT_DEST))
    args = ap.parse_args()
    dest = Path(args.dest)

    if dest.exists():
        # Wipe the contents but PRESERVE `.git`. Destroying it silently turns the bundle
        # into an ordinary subdirectory of whatever repository encloses it, after which
        # any `git` command run inside the bundle operates on the PARENT repo. That
        # happened once and committed the whole bundle into the parent's history.
        print(f"clearing existing {dest} (preserving .git)")
        for child in dest.iterdir():
            if child.name == ".git":
                continue
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                try:
                    child.unlink()
                except OSError:
                    pass
    dest.mkdir(parents=True, exist_ok=True)

    # Guard: refuse to build into a directory governed by an OUTER repository, because
    # every later git operation would then target that outer repo.
    try:
        probe = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                               cwd=str(dest), capture_output=True, text=True,
                               timeout=30)
        top = (probe.stdout or "").strip()
        if probe.returncode == 0 and top:
            top_p = Path(top).resolve()
            if top_p != dest.resolve():
                print(f"\n  !! WARNING: `git` inside the destination resolves to {top_p}")
                print( "     which is NOT the bundle. Run `git init` in the bundle, or the")
                print( "     ignored/untracked state of the parent repo will be affected.\n")
    except Exception:  # noqa: BLE001
        pass

    print("=" * 92)
    print(f"BUILDING RELEASE  ->  {dest}")
    print("=" * 92)

    # ---- 1. paper (sources + built PDFs + figure sources)
    print("\n[1/7] paper")
    copy_tree(PAPER, dest / "paper", label="paper")

    # ---- 2. engine source (no artifacts, no venv)
    print("[2/7] engine source")
    copy_tree(ENGINE, dest / "code" / "engine", label="engine")

    # ---- 3. analysis layer
    print("[3/7] analysis layer (eval/)")
    copy_tree(EVAL, dest / "code" / "analysis", label="analysis")

    # ---- 4. tooling that the paper's reproducibility claims rely on
    print("[4/7] tooling")
    copy_tree(SRC_ROOT / "tools", dest / "code" / "tools", label="tools")

    # ---- 5. role_c_toolkit (analysis toolchain + its tests)
    print("[5/7] role_c_toolkit")
    copy_tree(SRC_ROOT / "role_c_toolkit", dest / "code" / "role_c_toolkit",
              label="role_c_toolkit")

    # ---- 6. small data that fits in git
    print("[6/7] small data")
    small = {
        "tables": (PAPER / "tables", dest / "paper" / "tables"),
        "figures": (PAPER / "figures", dest / "paper" / "figures"),
        "figsrc": (PAPER / "figsrc", dest / "paper" / "figsrc"),
    }
    for label, (s, d) in small.items():
        copy_tree(s, d, label=f"paper/{label}")

    data_small = {
        "e5-annotation-final": EXPERIMENTS / "e5-annotation-final-20261002T1230Z",
        "e5-hifi-attribution-r3": EXPERIMENTS / "e5-hifi-attribution-r3-20261002T0620Z",
        "e5-hifi-attribution-r3b": EXPERIMENTS / "e5-hifi-attribution-r3b-20261002T0715Z",
        "e5-hifi-record-validation": EXPERIMENTS / "e5-hifi-record-validation-20261001",
        "paper-e5-e7-priority": EXPERIMENTS / "paper-e5-e7-priority-20261001T155743Z",
        "e6-model-invariance": EXPERIMENTS / "e6-model-invariance-20261002T1330Z",
        "e5-grid-natural-failures": EXPERIMENTS / "e5-grid-natural-failures-20261002T0640Z",
    }
    for label, s in data_small.items():
        copy_tree(s, dest / "data" / "campaigns" / label, label=f"data/{label}")

    # E5 conclusion documents and their supporting data tables. The appendix cites these
    # by name (`e1_2x2_option1.json`, `D1prime_FROZEN.json`, `E5_consolidated.md`), so
    # omitting the directory leaves cited artefacts unresolvable in the release.
    print("      E5 results documents")
    copy_tree(SRC_ROOT / "e5_ascii", dest / "data" / "e5", label="data/e5")

    # Co-author's run data (grid + LLM-channel batches), delivered as a tarball and
    # verified file-by-file against their container. Staged as an asset rather than read
    # from the delivery path so a rebuild does not depend on a WeChat download folder.
    print("      collaborator run data")
    copy_tree(SRC_ROOT / "release_assets" / "collaborator_runs",
              dest / "data" / "collaborator_runs",
              label="data/collaborator_runs")

    # The co-author's code snapshot that PRODUCED those runs, so the data stays
    # attributable. Frozen historical copy; the shipped analysis is the newer one.
    print("      collaborator code snapshot")
    copy_tree(SRC_ROOT / "release_assets" / "collaborator_code",
              dest / "code" / "collaborator_snapshot",
              label="code/collaborator_snapshot")

    # Anchored critical-fault validation batch (appendix I.4). Lives only on this
    # machine -- absent from both servers -- so it must travel with the release.
    # Compact attribution records behind appendix I.5's per-case table. The raw batches
    # are ~9 GB of replay evidence; these 17 records (~47 KB) are the part carrying the
    # printed numbers, so only they travel.
    # E6's two source batches (dense Qwen + third-party MiniMax MoE). The release
    # previously carried only campaigns/e6-model-invariance, i.e. the dense half, and
    # reported the MoE half as missing; both batches live under role_c_toolkit/artifacts/
    # in the co-author's tarball.
    print("      E6 source batches (four models)")
    copy_tree(SRC_ROOT / "release_assets" / "e6-sources",
              dest / "data" / "e6-sources", label="data/e6-sources")
    # Appendix G "Experiment 2" -- the headroom-manipulation feasibility probe. The paper
    # cites it as e1_2x2_option1/2.json and "Study 2 batch SHA-256-manifested (594 files)";
    # this is that batch (594 files). It was on disk but outside the bundle.
    print("      E1/Exp2 2x2 headroom probe (appendix G)")
    copy_tree(SRC_ROOT / "release_assets" / "e4-headroom-2x2",
              dest / "data" / "e4-headroom-2x2", label="data/e4-headroom-2x2")
    # The two appendix tables that had a script but no archived output: the A3
    # NL-vs-JSON interface ablation (tab:interface) and the complex-tier four-system
    # intervention study (tab:intervention). Both result sets live in one directory on
    # the authoring machine and were outside the bundle.
    print("      platform experiment results (tab:interface, tab:intervention)")
    copy_tree(SRC_ROOT / "release_assets" / "platform-results",
              dest / "data" / "platform-results", label="data/platform-results")
    copy_tree(SRC_ROOT / "release_assets" / "platform-experiments",
              dest / "data" / "platform-experiments", label="data/platform-experiments")
    print("      e5 attribution records (appendix I.5)")
    copy_tree(SRC_ROOT / "release_assets" / "e5-attribution",
              dest / "data" / "e5-attribution", label="data/e5-attribution")
    print("      g1 fault-dose batch (appendix I.4)")
    copy_tree(SRC_ROOT / "release_assets" / "g1-fault-dose",
              dest / "data" / "g1-fault-dose",
              label="data/g1-fault-dose")

    # the withheld grid dataset: OUR analysis outputs, scripts and result documents.
    # These live in EVAL itself (not in _w1_runs), which is why an earlier version of
    # this script shipped the per-episode reports but silently omitted every table,
    # script and document that the paper's no-intelligence claim depends on.
    print("      withheld grid reports + analysis outputs")
    wd = dest / "data" / "grid_withheld_5seeds"
    wd.mkdir(parents=True, exist_ok=True)
    n = 0
    size = 0
    for pat in ("DATASET_5SEEDS.*", "THE_WITHHELD_RESULTS.md",
                "LLMRL_WITHHELD_TABLE.md", "WITHHELD_BRIEFING_EVIDENCE.md",
                "PAPER_CONCLUSIONS_CN.md", "_w1_*.py", "_w1_*.ps1",
                "GATE_LOG_20260927.txt"):
        for p in sorted(EVAL.glob(pat)):
            if not p.is_file():
                continue
            shutil.copy2(p, wd / p.name)
            n += 1
            size += p.stat().st_size
    copied_log.append(("data/grid_withheld_5seeds (analysis+docs)", n, size))

    # the raw per-episode reports of the withheld grid, so every table is recomputable
    raw = wd / "episodes"
    raw.mkdir(parents=True, exist_ok=True)
    srcruns = EVAL / "_w1_runs"
    n = 0
    size = 0
    if srcruns.exists():
        for p in sorted(srcruns.glob("*_n3*.json")):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                excluded_log.append((str(p), "unparseable report"))
                continue
            if d.get("aborted") or int(d.get("ticks_run") or 0) <= 0:
                excluded_log.append((str(p), "aborted episode (not data)"))
                continue
            shutil.copy2(p, raw / p.name)
            n += 1
            size += p.stat().st_size
    copied_log.append(("data/grid_withheld_5seeds/episodes", n, size))

    # ---- 7. external-data manifest (the parts that must not go into git)
    print("[7/7] external-data manifest")
    external = {
        "engine/artifacts": ENGINE / "artifacts",
        "campaigns/five-seed-fill (HF CSS/ULHA)":
            EXPERIMENTS / "five-seed-fill-20260930T153924Z",
        "campaigns/e4-headroom-2x2-P1": EXPERIMENTS / "e4-headroom-2x2-P1",
        "campaigns/e5-hifi-natural-failures": EXPERIMENTS / "e5-hifi-natural-failures-20261002T1920Z",
        "campaigns/e5-hifi-natural-failures-r2":
            EXPERIMENTS / "e5-hifi-natural-failures-r2-20261002T0220Z",
        "campaigns/g1-fault-dose": EXPERIMENTS / "g1-fault-dose",
        "server-artifacts": SRC_ROOT / "server-artifacts",
        "grid_withheld_5seeds/logs": srcruns / "logs",
    }
    manifest = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "note": ("Large evidence trees are NOT in this repository. They are described "
                 "here so a reviewer can request or re-derive them, and so the "
                 "reproduction guide can state exactly what is missing."),
        "external": {k: survey(v) for k, v in external.items()},
    }
    (dest / "data" / "EXTERNAL_DATA_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---- 8. authored assets: docs, portable scripts, supporting records.
    # Everything comes from `release_assets/`, so a rebuild reproduces the release
    # deterministically instead of depending on what a previous run left on disk.
    print("[8/9] authored assets")
    assets = SRC_ROOT / "release_assets"
    if not assets.is_dir():
        excluded_log.append((str(assets), "release_assets/ missing - docs NOT emitted"))
    else:
        rep = dest / "reproduce"
        rep.mkdir(parents=True, exist_ok=True)
        # Root-level metadata: dotfiles must be copied explicitly by name.
        # NOTE: PAPER_COVERAGE.md is intentionally NOT emitted (withheld by request).
        for name in ("README.md", "REPRODUCE.md", "LICENSE.md", "CITATION.md",
                     "PAPER_PROVENANCE.md", "GAP_OWNERS.md",
                     "E6_G1_SOURCES.md",
                     "SERVER_SEARCH_RECORD.md",
                     "CODE_COMPARISON.md", ".gitignore", ".gitattributes"):
            s = assets / name
            if s.is_file():
                shutil.copy2(s, dest / name)
                copied_log.append((f"asset {name}", 1, s.stat().st_size))
            else:
                excluded_log.append((f"release_assets/{name}",
                                     "document missing from release_assets"))
        s = assets / "PENDING.md"
        if s.is_file():
            shutil.copy2(s, dest / "data" / "PENDING.md")
            copied_log.append(("asset data/PENDING.md", 1, s.stat().st_size))
        n = size = 0
        for name in ("verify_paper_table.py", "verify_p1_grid.py", "verify_p2_dose.py",
                     "verify_sixarm.py", "verify_replanning.py", "verify_i4_fault.py",
                     "verify_p3a.py",
                     "verify_complex_tier.py", "verify_model_invariance.py", "verify_legacy_arm.py",
                     "verify_e6_four_models.py", "verify_g1_deltas.py",
                     "verify_e5pilot.py", "verify_e2_2x2.py", "verify_e6b_minimax.py", "verify_modality.py", "verify_intervention.py",
                     "verify_legacy_arm.py",
                     "compare_code.py",
                     "scan_for_secrets.py",
                     "build_dataset.py", "_w1_common.py", "build_release.py",
                     "extract_paper_refs.py"):
            s = assets / name
            if s.is_file():
                shutil.copy2(s, rep / name)
                n += 1
                size += s.stat().st_size
        # NOTE: verification output (*_VERIFICATION.txt, SECRET_SCAN.txt) is deliberately
        # NOT published. Those are internal audit records, not release material: the
        # scripts in this directory regenerate them on demand, and the release should
        # carry evidence plus tooling rather than transcribed self-checks.
        copied_log.append(("asset reproduce/", n, size))

    # ---- 9. strip authoring-machine paths out of shipped scripts and prose
    print("[9/9] sanitizing external absolute paths")
    sanitize_external_paths(dest)
    sanitize_data_paths(dest)

    # ---- provenance: hashes of the things the paper pins
    print("\n  recording provenance hashes ...")
    prov = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "items": {}}

    def add_hash(label: str, p: Path) -> None:
        if p.is_file():
            prov["items"][label] = {"path": str(p), "sha256": sha256(p),
                                    "bytes": p.stat().st_size}

    add_hash("rl checkpoints / theta_rl_legacy2.npz",
             EVAL / "_w1_runs" / "rl" / "theta_rl_legacy2.npz")
    add_hash("rl checkpoints / theta_arm5_llm_reward_v9.npz",
             EVAL / "_w1_runs" / "rl" / "theta_arm5_llm_reward_v9.npz")
    add_hash("dataset / DATASET_5SEEDS.csv", EVAL / "DATASET_5SEEDS.csv")
    add_hash("dataset / DATASET_5SEEDS.json", EVAL / "DATASET_5SEEDS.json")

    plan = EXPERIMENTS / "five-seed-fill-20260930T153924Z" / "plan.json"
    if plan.is_file():
        d = json.loads(plan.read_text(encoding="utf-8"))
        prov["five_seed_fill_plan"] = {
            "campaign_id": d.get("campaign_id"),
            "model": d.get("model"),
            "endpoints": d.get("endpoints"),
            "weights_sha256": d.get("weights_sha256"),
            "recorder_sha256": d.get("recorder_sha256"),
            "parameters": d.get("parameters"),
            "n_cases": len(d.get("cases") or []),
            "engine_pin": {k: v for k, v in (d.get("engine_pin") or {}).items()
                           if k in ("reference_commit", "reference_branch", "snapshot",
                                    "scope_manifest_sha256")},
        }
    (dest / "PROVENANCE.json").write_text(
        json.dumps(prov, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---- build report
    print("\n" + "=" * 92)
    print("COPY SUMMARY")
    print("=" * 92)
    total_f = total_b = 0
    for label, f, b in copied_log:
        total_f += f
        total_b += b
        print(f"  {label:<40}{f:>8} files{b / 1e6:>10.1f} MB")
    print(f"  {'TOTAL':<40}{total_f:>8} files{total_b / 1e6:>10.1f} MB")

    if excluded_log:
        print(f"\n  excluded/denied: {len(excluded_log)} entries; by reason:")
        from collections import Counter
        c = Counter(r for _p, r in excluded_log)
        for reason, n in c.most_common(20):
            print(f"    {reason:<52}{n:>7}")

    # The copy summary is printed for the operator rather than written into the release.
    # A BUILD_REPORT.json in the published tree would be an internal audit record, and
    # this repository carries evidence and tooling, not transcribed self-checks.
    print(f"\n  release at: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())









