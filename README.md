# OpenMDBench — Layering Law Release

Code, data and reproduction material for the paper's high-fidelity experimental suite.

> **Status: partial.** This bundle contains everything held locally. Some material is
> still with a collaborator and is listed in [`data/PENDING.md`](data/PENDING.md).
> Nothing here is a placeholder for missing numbers: where the paper reports the
> high-fidelity suite, **all 70 table cells reproduce exactly** — see
> [`reproduce/PAPER_TABLE_VERIFICATION.txt`](reproduce/PAPER_TABLE_VERIFICATION.txt).

---

## What this bundle establishes

The paper's central table (`tab_hifi_main`) is the 14-scenario high-fidelity suite under
a **unified no-intelligence regime**, five seeds per LLM stack. That table is fully
recomputable from the per-episode reports committed here:

| Check | Result |
|---|---|
| Main-table cells compared | 70 |
| Reproduced exactly | **70** |
| Materially different | 0 |

One command, run from inside this bundle:

```bash
python reproduce/verify_paper_table.py
```

Seventeen further checks run the same way, each shipping its recorded output beside it:

| Check | Command | Result |
|---|---|---|
| `tab_p1_seedgrid` (six-arm, seeds 501–510) | `verify_p1_grid.py` | **0/60 cells differ** |
| `tab:sixarm` + deployment identity | `verify_sixarm.py` | **0/6 means; identity exact** |
| Appendix I.2 dose-gain (seeds 512–521) | `verify_p2_dose.py` | **0/8 mismatch** |
| `tab:complexlayered` (seeds 63101–63105) | `verify_complex_tier.py` | **0/3 mismatch** |
| Appendix G Experiment 2 (2×2 headroom) | `verify_e2_2x2.py` | **effect +0.619…+0.734 for paper +0.62…+0.73** |
| Appendix I.3 real-stream (seeds 601–610) | `verify_p3a.py` | **0/10 cells differ** |
| `tab:interface` (NL vs JSON) | `verify_modality.py` | **0/3 tiers differ** |
| `tab:intervention` (four systems) | `verify_intervention.py` | **0/7 mismatch** |
| `tab:frequency` + `figA2` | `verify_replanning.py` | **0/3 mismatch** |
| `tab:e5pilot` (12 cases) | `verify_e5pilot.py` | **9/12 exact** (3 grid cases lack records) |
| E6 four-model scan | `verify_e6_four_models.py` | see its recorded output |
| E6b third-party MiniMax | `verify_e6b_minimax.py` | see its recorded output |
| Appendix I.4 fault costs | `verify_i4_fault.py`, `verify_g1_deltas.py` | documented, see below |
| Appendix G legacy arm | `verify_legacy_arm.py` | documented, see below |
| `tab:modelinvariance` | `verify_model_invariance.py` | documented, see below |

Three blocks do **not** reproduce and say so in their own output rather than being
smoothed over: appendix I.4's fault costs, appendix G's legacy-arm subset, and
`tab:e5pilot`'s three grid cases (no `attribution.json` exists for those).

**For the artefact-by-artefact provenance — where each table's data lives and how the
paper itself identifies it — read [`PAPER_PROVENANCE.md`](PAPER_PROVENANCE.md).** Each of
the 17 verification scripts under `reproduce/` ships with its recorded output, so any
claim here can be re-checked rather than believed.

---

## Layout

```
OpenMDBench-Release/
├── README.md                     this file
├── REPRODUCE.md                  how to rebuild every table and figure
├── PROVENANCE.json               hashes of the pinned weights and datasets
├── BUILD_REPORT.json             what was copied, what was excluded and why
│
├── paper/                        the manuscript itself
│   ├── main.tex  appendix.tex  refs.bib  main.pdf  appendix.pdf
│   ├── tables/                   the six LaTeX tables
│   ├── figures/                  all figures
│   └── figsrc/                   scripts that draw the figures
│
├── code/
│   ├── engine/                   OpenMDBench simulation platform (declarative, V2)
│   ├── analysis/                 evaluation harness + the withheld-grid analysis stack
│   ├── role_c_toolkit/           attribution / calibration toolchain
│   ├── collaborator_snapshot/    co-author's code state that produced their runs
│   └── tools/                    remote-validation helper
│
├── data/
│   ├── grid_withheld_5seeds/     the paper's main-table dataset
│   │   ├── episodes/             213 per-episode reports (JSON, ~15 KB each)
│   │   ├── DATASET_5SEEDS.csv    709 rows x 50 columns, one row per episode
│   │   ├── DATASET_5SEEDS.json   same rows as JSON
│   │   ├── DATASET_5SEEDS.md     summary tables
│   │   ├── THE_WITHHELD_RESULTS.md       results tables A–F
│   │   ├── LLMRL_WITHHELD_TABLE.md       claim tables
│   │   └── WITHHELD_BRIEFING_EVIDENCE.md fairness and boundary audit
│   ├── collaborator_runs/        co-author's 22 batch directories (grid + LLM channel)
│   ├── e5/                       E5 conclusion documents and their data tables
│   ├── campaigns/                server-side campaign records (small ones)
│   ├── EXTERNAL_DATA_MANIFEST.json   the large trees that are NOT in git
│   └── PENDING.md                coverage: what is received, awaited, or withheld
│
└── reproduce/
    ├── verify_paper_table.py     recomputes the main table and diffs it
    ├── PAPER_TABLE_VERIFICATION.txt   recorded result of that run
    ├── build_dataset.py          rebuilds DATASET_5SEEDS.*
    ├── _w1_common.py             single definition of口径, metric and baseline policy
    ├── scan_for_secrets.py       pre-publication credential scan
    ├── SECRET_SCAN.txt           its recorded output
    └── build_release.py          rebuilds this whole bundle from source
```

Baselines (`rule-rule`, `rl`) are **not** re-run and not re-derived from the private
archive: the bundle carries its own copy under `code/analysis/_w1_runs/`, verified to
give identical scenario means (rule-rule 0.723, RL 0.632).

---

## Quick start

```bash
git clone https://github.com/anony2026mous/anonymous.git
cd anonymous

# 1. verify the paper's main table against the released episodes
python reproduce/verify_paper_table.py
#    expected tail: "exact 70   rounding 0   DIFFERS 0   of 70 cells"

# 2. rebuild the consolidated dataset (authoring checkout only)
python reproduce/build_dataset.py
```

Both scripts need the analysis layer importable:

```bash
export PYTHONPATH="$PWD/code/analysis:$PWD/code/engine"     # bash
$env:PYTHONPATH = "$PWD\code\analysis;$PWD\code\engine"     # PowerShell
```

Dependencies: Python 3.11, `numpy`, `PyYAML`. The verification script needs nothing
else; running new simulations additionally needs the engine's full stack (`scipy`,
`taichi`, `torch`, `pydantic`) as pinned in `code/engine/pyproject.toml`.

---

## The experiment in one paragraph

Six decision stacks are compared on 14 interception-engagement scenarios: pure rule,
LLM planner + rule executor, rule planner + RL executor, LLM planner + RL executor,
pure RL, and pure LLM. The **main table uses a unified no-intelligence regime** — the
prompt carries no wave timing, axis, count or intent, and no force-strength numbers,
because those are not observable fields and the two single-architecture baselines never
read them. Baselines are **reused from a frozen archive** rather than re-run. Every
episode report records its own provenance (`briefing`, speed envelope, policy
checkpoint), so any number can be traced to the run that produced it.

---

## Data dictionary (the consolidated CSV)

`data/grid_withheld_5seeds/DATASET_5SEEDS.csv` — 709 rows.

| Column group | Columns | Meaning |
|---|---|---|
| identity | `scenario`, `arm`, `arm_label`, `seed` | which cell |
| provenance | `briefing`, `dataset`, `checkpoint_theta`, `checkpoint_goal_features`, `checkpoint_obs_dim`, `speed_uav_max` | how it was run |
| headline | `score`, `scored_weight` | the metric and its weight normaliser |
| outcome | `outcome`, `terminal_rule`, `terminal_tick`, `ticks_run` | how the episode ended |
| behaviour | `fires_decoy`, `fires_threat`, `fires_civilian`, `first_fire_tick`, `threat_neutralization_rate`, `intruder_total_count`, `defender_survival_rate`, `ammo_efficiency` | engine-side ROE bookkeeping |
| layers | `layer_terminal`, `layer_facilities`, `layer_depth`, `layer_leak`, `layer_exchange`, `layer_ammo`, `layer_surface` | per-layer scores |
| applicability | `applicable_depth`, `applicable_leak`, `applicable_surface`, `applicable_ammo` | which layers count |

**The metric.** `score` is `strategy_scorecard.defender_score`, which is *already* the
weighted mean over applicable layers (`Σ layers·w / Σ w`). It must **not** be divided by
`scored_weight` a second time; the `layer_*` and `applicable_*` columns exist so the
value can be recomputed independently.

---

## External data

Several evidence trees are too large for git history and are **not** in this repository.
`data/EXTERNAL_DATA_MANIFEST.json` records what they are, how big they are and where they
lived, so a reviewer can request them.

| Tree | Size | What it is |
|---|---|---|
| engine `artifacts/` | ~11.5 GB | engine-run evidence, calibration ledgers |
| `five-seed-fill` campaign episodes | ~6.0 GB | tick-by-tick traces of the server campaign |
| `e5-hifi-natural-failures` | ~12 GB | attribution evidence for the natural-failure study |
| `g1-fault-dose` | ~94 MB | goal-dose batch |

The paper's main table does **not** depend on any of them: it is reproduced from the 213
episode reports committed here.

---

## Two halves of the evidence

The project's results come from two working copies that were developed in parallel. This
release merges both:

| Half | Where | Scope |
|---|---|---|
| This repository's high-fidelity suite | `data/grid_withheld_5seeds/` | 14 scenarios × 5 stacks × 5 seeds; **the paper's main table, 70/70 reproducible** |
| Co-author's grid + LLM-channel batches | `data/collaborator_runs/` | 22 batch directories, results for the appendix tables; seed range 500–14000 |

The two seed scopes are **disjoint** (ours: 7/11/13/17/19), so the co-author's data does
not mix into the reported high-fidelity statistics. Their code state is preserved under
`code/collaborator_snapshot/` so those results stay attributable; per its README, it is a
frozen historical copy and must not be merged back — `code/analysis/` ships the newer,
fixed versions.

The co-author snapshot was verified against their live container by diffing a
`(relpath, size)` manifest of all 77,411 server files: **0 size differences**. See
`data/collaborator_runs/README.md`.

---

## Withheld on purpose

`KEY_DO_NOT_SHARE.json` — the blind-annotation **answer key** — is deliberately **not**
in this repository, from either of its two source locations. The appendix reports
human–machine agreement (Cohen's κ) on blind IDs E5-01…E5-12 with the key withheld;
publishing it would let anyone recover the labels and would invalidate the statistic it
supports. The exclusion is enforced by an explicit guard in `reproduce/build_release.py`
and recorded in `BUILD_REPORT.json`. See `data/PENDING.md` §1b.

---

## Known limitations

A reproduction claim is only as good as its caveats:

1. **Same seed is not a replay.** The LLM endpoint is non-deterministic on realistic
   (~1.3k-token) prompts — four identical requests produced four different outputs. A
   fixed seed is one independent replication. The caption's "one replication under
   nondeterminism" says exactly this.
2. **Inter-seed variance is large.** `LLM+Rule` on IE-03 scores 1.000 / 0.650 / 0.631 /
   0.856 across seeds. Single-seed scenario rankings are not evidence, which is why the
   analysis ships a three-part stability test.
3. **Training/evaluation overlap.** The `llm-rl` checkpoint was trained on four of the
   fourteen scenarios (IE-01/02/03/05) and evaluated on all fourteen, so the
   generalisation claim is reported separately for seen and unseen scenarios.
4. **The two RL arms are not the same class of policy.** `rule-rl` uses a
   goal-conditioned checkpoint (`goal_features=True`, observation width 3570); the pure
   `rl` baseline uses a goal-free one (width 2866). Their scores are not a controlled
   contrast for "adding a planning layer".
5. **A partial sixth seed exists on disk** (seed 23, 3 finished cells) and must be
   excluded when reproducing the paper's five-seed table, or `IE-04 / LLM+Rule` shifts
   from 0.710 to 0.741.

---

## License / attribution

See `paper/main.tex` for the manuscript's license statement. Third-party components keep
their own terms; `code/engine/` carries its own `README.md`, `CHANGELOG.md` and
`pyproject.toml`.
