"""Shared loading rules for the withheld experiment. One place, so no script can
quietly reintroduce a口径/基线 error.

Every previous analysis bug in this project came from a filtering or metric
convention that was re-implemented per script and drifted:

  * reading the briefing from only `defender.briefing`, which silently reported
    "no provenance" for correctly tagged llm-rule / llm-rl episodes (the field is
    under `defender.planner.briefing` for those arms);
  * dividing `defender_score` by `scored_weight` - the score is ALREADY the
    normalised weighted mean, so this inflated 0.90 into 1.00;
  * averaging the `rl` baseline across several checkpoints, producing a number
    belonging to no actual policy;
  * accepting an episode whose report exists but whose run aborted at tick 0.

This module centralises those decisions and validates them.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

def _first_existing(*candidates: Path) -> Path:
    """Return the first candidate that exists, else the first.

    Lets the same analysis run in the authoring checkout (episodes sit directly in
    `_w1_runs`) and in the published release (episodes sit under
    `data/grid_withheld_5seeds/episodes`) with no per-environment edits.
    """
    for cand in candidates:
        if cand.exists():
            return cand
    return candidates[0]


_HERE = Path(__file__).resolve().parent
# Repository root: one level up in the release layout, itself in the checkout.
_ROOT = _HERE.parent if (_HERE.parent / "code").exists() else _HERE

# Withheld grid episodes.
RUNS = _first_existing(
    _ROOT / "data" / "grid_withheld_5seeds" / "episodes",
    _HERE / "_w1_runs",
)

# Baseline episodes (rule-rule, RL). The release carries its own copy, so the private
# archive is NOT required: verified to yield identical scenario means
# (rule-rule 0.723, RL 0.632). The archive remains only as a checkout fallback.
SNAP = _first_existing(
    _ROOT / "code" / "analysis" / "_w1_runs",
    Path(os.path.expanduser("~")) / "openmd_private_archive"
    / "declared_briefing_snapshot_20260927_1419" / "results",
)

FORMAL = _first_existing(
    _ROOT / "code" / "engine" / "scenarios" / "formal",
    Path(r"C:\Code\source-code\openmd\source-code\source_codes\scenarios\formal"),
)

IE = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
      "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
      "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
      "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
      "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]
ALIAS = {"MD-AD-006-ISLAND-STRIKE": "IE-08-ISLAND-STRIKE"}

LLM_ARMS = ["llm-rule", "llm-rl", "pure-llm"]
BASE_ARMS = ["rule-rule", "rl"]
ARMS = LLM_ARMS + BASE_ARMS
LABEL = {"llm-rule": "LLM+rule", "llm-rl": "LLM+RL", "pure-llm": "pure-LLM",
         "rule-rule": "rule+rule", "rl": "RL"}

# The single-architecture baselines are REUSED from the archive, never re-run.
# `rl` is a family of checkpoints, so the analysis pins ONE policy identity: the
# only partition that records its training provenance and matches the training
# decision interval. See `_w1_baseline_partition.py`.
#
# NOTE the archive is a SNAPSHOT of `_w1_runs`, so the same episode exists in both
# places. Always read baselines from ONE source - summing the two directories
# double-counts every baseline episode (this inflated an rl count from 64 to 118).
RL_THETA = "theta_rl_legacy2.npz"
RL_SPEED_SOURCE = "legacy_tags"
RL_DECISION_INTERVAL = "5"
RL_OBS_DIM = 2866


def _declared_speeds() -> dict[str, float]:
    import yaml
    out = {}
    for d in sorted(os.listdir(FORMAL)):
        ap = FORMAL / d / "agents.yaml"
        if ap.exists():
            y = yaml.safe_load(ap.read_text(encoding="utf-8")) or {}
            v = (y.get("defence") or {}).get("intercept_speed_mps")
            if v is not None:
                out[d] = float(v)
    return out


DECLARED_SPEED = _declared_speeds()


def recomp(card: dict) -> float | None:
    """Independent recomputation of the headline statistic from the layer breakdown.

    Mirrors strategy_metrics.py:
        scored_weight  = sum(w[k] for applicable k)
        defender_score = sum(layers[k]*w[k] for applicable k) / scored_weight
    Agreement proves the offline read kept the applicability mask.
    """
    layers = card.get("layers") or {}
    wts = card.get("layer_weights") or {}
    app = card.get("layer_applicability") or {}
    num = sum(float(layers[k]) * float(wts[k]) for k in wts
              if app.get(k, True) and k in layers)
    den = sum(float(wts[k]) for k in wts if app.get(k, True))
    return (num / den) if den else None


def briefing_of(d: dict) -> str | None:
    """Read the情报口径 from whichever of the two places the arm records it."""
    de = d.get("defender") or {}
    if not isinstance(de, dict):
        return None
    b = de.get("briefing")
    if isinstance(b, str):
        return b
    pl = de.get("planner")
    if isinstance(pl, dict) and isinstance(pl.get("briefing"), str):
        return pl["briefing"]
    return None


def checkpoint_meta_of(d: dict) -> dict:
    """First non-empty checkpoint_meta, checking executor then planner.

    The rl arm records it under `defender.planner`; llm-rl records it under
    `defender.executor`. Reading only one of the two silently drops an arm.
    """
    de = d.get("defender") or {}
    for blk in ("executor", "planner"):
        b = de.get(blk)
        if isinstance(b, dict):
            m = b.get("checkpoint_meta")
            if isinstance(m, dict) and m:
                return m
    return {}


def theta_name_of(d: dict) -> str:
    de = d.get("defender") or {}
    for blk in ("executor", "planner"):
        b = de.get(blk)
        if isinstance(b, dict) and b.get("theta"):
            return Path(str(b["theta"])).name
    m = checkpoint_meta_of(d)
    return Path(str(m.get("theta"))).name if m.get("theta") else ""


def scenario_of(d: dict) -> str:
    raw = str(d.get("scenario") or "").upper().strip()
    return ALIAS.get(raw, raw)


def is_usable(d) -> tuple[bool, str]:
    """A report exists; does it represent a real, scoreable episode?"""
    if not isinstance(d, dict):
        return False, "not a report"
    card = d.get("strategy_scorecard") or {}
    if int(d.get("ticks_run") or 0) <= 0:
        return False, "ticks=0"
    if d.get("aborted"):
        return False, f"aborted: {str(d['aborted'])[:60]}"
    if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        return False, "no terminal outcome"
    if card.get("defender_score") is None:
        return False, "no defender_score"
    rc = recomp(card)
    if rc is None:
        return False, "layer breakdown unusable"
    if abs(float(card["defender_score"]) - rc) > 5e-4:
        return False, "scorecard not reproducible from layers"
    if not isinstance(d.get("seed"), int):
        return False, "no integer seed"
    return True, f"ticks={d['ticks_run']} score={card['defender_score']}"


def arm_of(d: dict, *, allow_briefing: str | None = "withheld",
           strict_arms: bool = True) -> tuple[str | None, str]:
    """Resolve which arm an episode belongs to, enforcing arm-specific provenance."""
    pl = str(d.get("planner") or "").lower()
    de = d.get("defender") or {}
    if pl == "llm":
        arm = "llm-rule"
    elif pl == "llm-rl":
        arm = "llm-rl"
        tag = str(checkpoint_meta_of(d).get("tag") or "")
        if tag and tag != "arm5_llm_reward_v9":
            return None, f"llm-rl policy tag={tag}"
    elif pl == "pure-llm":
        arm = "pure-llm"
        env = de.get("speed_max_by_tag") if isinstance(de, dict) else None
        if not isinstance(env, dict):
            return None, "pure-llm: no envelope record"
        want = DECLARED_SPEED.get(scenario_of(d).lower().replace("-", "_"), 43.0)
        if abs(float(env.get("uav", -1)) - want) > 1e-6:
            return None, f"pure-llm envelope {env.get('uav')} != declared {want}"
    elif pl == "rule":
        arm = "rule-rule"
    elif pl == "rl":
        arm = "rl"
        if strict_arms:
            if checkpoint_meta_of(d).get("obs_dim") != RL_OBS_DIM:
                return None, "rl obs_dim mismatch"
            if theta_name_of(d) != RL_THETA:
                return None, f"rl policy={theta_name_of(d) or '?'} (pinned {RL_THETA})"
    else:
        return None, f"unknown planner {pl!r}"

    if allow_briefing is not None and arm in LLM_ARMS:
        b = briefing_of(d)
        if not isinstance(b, str):
            return None, f"{arm}: no briefing provenance"
        if b != allow_briefing:
            return None, f"{arm}: briefing={b} (wanted {allow_briefing})"
    return arm, "ok"


def load_dir(root: Path, pattern: str = "*.json", *, skip_underscore: bool = True):
    """Yield (path, report) for parseable dict reports under `root`."""
    for p in sorted(root.glob(pattern)):
        if skip_underscore and p.name.startswith("_"):
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if isinstance(d, dict):
            yield p, d


def collect(root: Path, pattern: str = "*.json", *, briefing: str | None = "withheld",
            strict_arms: bool = True, reasons: dict | None = None,
            provenance: str = "required"):
    """Return {(scenario, arm): {seed: [score, ...]}} plus a drop-reason tally.

    `provenance` controls what to do when an LLM-arm episode records NO briefing:
      "required" (default) - drop it.  An episode that cannot be attributed to a口径
        must not be silently assigned to one.
      "legacy-ok" - keep it.  Needed for the ARCHIVED declared episodes: the
        `briefing` field was introduced together with the switch, so every
        pre-2026-09-27 episode predates it.  Dropping them would empty the declared
        column entirely and make the with/without comparison impossible.  The
        justification for treating an unlabelled archived LLM episode as `declared`
        is that the switch did not exist before that date, and `declared` is defined
        as the historical behaviour - it is not an inference about the episode.
    """
    from collections import defaultdict
    by: dict[tuple[str, str], dict[int, list[float]]] = defaultdict(
        lambda: defaultdict(list))
    for _p, d in load_dir(root, pattern):
        sc = scenario_of(d)
        if sc not in IE:
            continue
        ok, why = is_usable(d)
        if not ok:
            if reasons is not None:
                reasons[f"unusable: {why}"] += 1
            continue
        arm = None
        if provenance == "legacy-ok":
            arm, why = arm_of(d, allow_briefing=None, strict_arms=strict_arms)
            if arm in LLM_ARMS:
                b = briefing_of(d)
                if isinstance(b, str) and b != (briefing or b):
                    if reasons is not None:
                        reasons[f"{arm}: briefing={b} (wanted {briefing})"] += 1
                    continue
        else:
            arm, why = arm_of(d, allow_briefing=briefing, strict_arms=strict_arms)
        if arm is None:
            if reasons is not None:
                reasons[why] += 1
            continue
        by[(sc, arm)][int(d["seed"])].append(float(d["strategy_scorecard"]["defender_score"]))
    return by


def vals(by, sc: str, arm: str) -> list[float]:
    return [x for v in by.get((sc, arm), {}).values() for x in v]


def seeds(by, sc: str, arm: str) -> int:
    return len(by.get((sc, arm), {}))
