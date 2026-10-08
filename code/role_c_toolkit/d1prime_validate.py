"""D1' prior-score validation: rank correlation between the frozen prior and observed layering gain.

Checklist v9 asks for Spearman ρ > 0.5 (p < 0.05) between a scenario's D1' prior score and its
*observed* layering advantage (hybrid composite − best pure baseline composite).  The prior
table is frozen before any result is read (`d1prime_FROZEN.json`), and this script is the only
place where the two are joined, so the join is auditable in one file.

`scipy` is not assumed to exist: the correlation is computed directly and the p-value comes
from a seeded permutation test, which also works for the small scenario counts here.

Usage:
    python d1prime_validate.py --frozen <d1prime_FROZEN.json> --scores <scores.json|csv> \
        --output <d1prime_validation.json> [--min-scenarios 6]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

# The checklist's success criterion, quoted rather than chosen here.
RHO_THRESHOLD = 0.5
P_THRESHOLD = 0.05
MIN_SCENARIOS = 6


def rank(values: list[float]) -> list[float]:
    """Average ranks, so ties do not distort the correlation."""
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index
        while end + 1 < len(order) and values[order[end + 1]] == values[order[index]]:
            end += 1
        average = (index + end) / 2 + 1
        for position in range(index, end + 1):
            ranks[order[position]] = average
        index = end + 1
    return ranks


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = (sum((x - mean_x) ** 2 for x in xs) * sum((y - mean_y) ** 2 for y in ys)) ** 0.5
    return numerator / denominator if denominator else 0.0


def spearman(xs: list[float], ys: list[float]) -> float:
    return pearson(rank(xs), rank(ys))


def permutation_p(xs: list[float], ys: list[float], draws: int = 20000,
                  seed: int = 20261003) -> float:
    observed = abs(spearman(xs, ys))
    rng = random.Random(seed)
    shuffled = list(ys)
    hits = 0
    for _ in range(draws):
        rng.shuffle(shuffled)
        if abs(spearman(xs, shuffled)) >= observed:
            hits += 1
    return hits / draws


def load_scores(path: Path) -> dict:
    """Accept either JSON (``{scenario: number}`` or ``{scenario: {composite: number}}``) or CSV."""
    if path.suffix.lower() == ".csv":
        scores = {}
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                key = row.get("scenario") or row.get("public_id") or row.get("scenario_id")
                value = row.get("composite") or row.get("layering_gain") or row.get("delta")
                if key and value not in (None, ""):
                    scores[key] = float(value)
        return scores
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and "scenarios" in payload and isinstance(
            payload["scenarios"], list):
        scores = {}
        for row in payload["scenarios"]:
            key = row.get("scenario") or row.get("public_id")
            value = row.get("layering_gain", row.get("composite"))
            if key and value is not None:
                scores[key] = float(value)
        return scores
    scores = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            for field in ("layering_gain", "composite", "delta"):
                if isinstance(value.get(field), (int, float)):
                    scores[key] = float(value[field])
                    break
        elif isinstance(value, (int, float)):
            scores[key] = float(value)
    return scores


def resolve(key: str, candidates) -> str | None:
    """Match a short scenario key ("IE-03") to its frozen public id ("IE-03-SURFACE-RAID")."""
    if key in candidates:
        return key
    prefix = key.upper() + "-"
    matches = [candidate for candidate in candidates if candidate.upper().startswith(prefix)]
    return matches[0] if len(matches) == 1 else None


def validate(frozen: dict, scores: dict, min_scenarios: int = MIN_SCENARIOS) -> dict:
    known = [row["public_id"] for row in frozen["rows"]]
    rows, missing, unmatched = [], [], []
    for key, value in scores.items():
        resolved = resolve(key, known)
        if resolved is None:
            unmatched.append(key)
            continue
        rows.append({"public_id": resolved, "matched_key": key, "observed": float(value)})
    by_id = {row["public_id"]: row for row in frozen["rows"]}
    for row in rows:
        row["prior_score"] = by_id[row["public_id"]]["prior_score"]
    covered = {row["public_id"] for row in rows}
    missing = [identifier for identifier in known if identifier not in covered]
    if len(rows) < min_scenarios:
        return {"schema": "d1prime-validation@1",
                "status": "insufficient_coverage",
                "note": (f"only {len(rows)} scenarios carry both a frozen prior and an observed "
                         f"value; at least {min_scenarios} are needed before any correlation is "
                         "reported, and a scenario subset must not be presented as the family"),
                "paired_scenarios": len(rows), "missing_observed": missing,
                "unmatched_keys": unmatched,
                "rows": rows,
                "criterion": {"spearman_rho_min": RHO_THRESHOLD, "p_max": P_THRESHOLD}}
    priors = [row["prior_score"] for row in rows]
    observed = [row["observed"] for row in rows]
    rho = spearman(priors, observed)
    p_value = permutation_p(priors, observed)
    passed = rho > RHO_THRESHOLD and p_value < P_THRESHOLD and rho > 0
    return {"schema": "d1prime-validation@1",
            "status": "reported",
            "criterion": {"spearman_rho_min": RHO_THRESHOLD, "p_max": P_THRESHOLD,
                          "source": "checklist v9 section 1.2"},
            "method": ("Spearman rank correlation over paired scenarios; p from a seeded "
                       "permutation test (20000 draws, seed 20261003) because scipy is not "
                       "assumed to be installed"),
            "paired_scenarios": len(rows),
            "missing_observed": missing,
            "unmatched_keys": unmatched,
            "spearman_rho": round(rho, 4), "p_value": round(p_value, 5),
            "supported": passed,
            "direction": "positive" if rho > 0 else "negative",
            "rows": sorted(rows, key=lambda row: row["prior_score"], reverse=True),
            "caveats": ([f"{len(rows)} paired scenarios is a small sample; the interval is wide"]
                        if len(rows) < 10 else []) +
                       (["observed values come from the file given on the command line; record "
                         "its sha256"] if True else [])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-scenarios", type=int, default=MIN_SCENARIOS)
    args = parser.parse_args()
    frozen = json.loads(args.frozen.read_text(encoding="utf-8-sig"))
    scores = load_scores(args.scores)
    summary = validate(frozen, scores, args.min_scenarios)
    summary["frozen"] = str(args.frozen)
    summary["scores_source"] = str(args.scores)
    summary["scores_scenarios"] = len(scores)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps({key: summary[key] for key in
                      ("status", "paired_scenarios", "spearman_rho", "p_value", "supported")
                      if key in summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
