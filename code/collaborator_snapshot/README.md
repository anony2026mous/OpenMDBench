# Co-author code snapshot

The co-author's working copy of the project code, taken from the same delivery as
[`../collaborator_runs/`](../collaborator_runs/README.md)
(`server1_owned_originals_20261008_v2.tar.gz`, path
`releases/gitlab-ccabad00154e/repo/openmd/code/`).

287 files, 2.2 MB — 262 Python, 19 PowerShell, 6 shell. No credential-like files.

## Why it is here

The run data in `../collaborator_runs/` was produced by **this** code state, so shipping
the data without it would leave the results un-attributable. Keeping both lets a reviewer
answer "which script, at which revision, produced this JSON?".

## Relationship to `code/analysis/` in this repository

Both copies descend from the same 203 `_w1_*.py` analysis scripts, and all 203 filenames
still match. The contents have diverged:

| | Count |
|---|---|
| Files byte-identical between the two copies | 34 |
| Files that differ | 169 |
| Total `_w1_*.py` files compared | 203 |

**This repository's `code/analysis/` holds the newer versions** — they carry the fixes
documented in `data/grid_withheld_5seeds/WITHHELD_BRIEFING_EVIDENCE.md` (the briefing
switch, the ROE classification fix, the log-interface fix, the scoring-convention
corrections).

## How to use it

- **To attribute a collaborator result**: read the script here, alongside the batch in
  `../collaborator_runs/`.
- **To recompute a result for publication**: use `code/analysis/`. The two copies differ,
  so mixing them will not reproduce either.
- **Do not treat this as a fork to merge.** It is a frozen historical snapshot; reverting
  the shipped analysis to it would discard the fixes above.

Beyond `_w1_*.py`, this snapshot also carries files our tree organises elsewhere or not at
all — `train.py`, `train_mappo.py`, `train_ppo.py`, `evaluate.py`, `validate.py`,
`visualize.py`, `attribute.py`/`attribution.py`, `serve_hifi.py`, `coupling_mi.py`,
`grid_info_experiment.py`, and `evaluation/` and `scripts/` subdirectories. Those are the
co-author's own tooling for the grid and LLM-channel experiments.
