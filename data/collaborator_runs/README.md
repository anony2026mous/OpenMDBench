# Collaborator run data

Experiment result data produced by a co-author on their container
(`hr-a6000-129-51`). It is the second half of the project's evidence: the grid and
LLM-channel experiments that back the appendix tables, as distinct from the
high-fidelity suite reproduced under `../grid_withheld_5seeds/`.

## Source and provenance

| | |
|---|---|
| Delivered as | `server1_owned_originals_20261008_v2.tar.gz` |
| Contents | `runs/` (20 batches) and `releases/<rev>/repo/openmd/code/` |
| Verified against | the co-author's live container, by `(relpath, size)` manifest |
| Verification result | **0 size differences**; every file here matches the server byte-for-byte |
| Relationship to server | strict **subset** — the server holds more (see below), but nothing here contradicts it |

The verification is a fact about this snapshot, not an assumption: a manifest of all
77,411 server files under `runs/` was diffed against these. Files present on both sides
are identical in size in every case; the snapshot contains **no file that is absent or
different on the server**.

## What is here

22 batch directories, 3,673 files, 45.6 MB, plus one curated delivery:

### `e2-delivery-20261003/` — the appendix I.1/I.2 dataset (verified)

The co-author's curated export of the two grid batches, and the **only** source of the
appendix's per-seed grid tables. 516 files, 9.9 MB:

| Batch | Episodes | What it is | Verification |
|---|---|---|---|
| `raw/P1__six_arm__s501-510__main__v1/` | 60 | six-arm accounting, continuous task-authorization mode | reproduces `tab_p1_seedgrid`: **0/60 cells differ** |
| `raw/P2__goal_dose__s512-521__hold__v1/` | 20 | goal-dose, hold condition | — |
| `raw/P2__goal_dose__s512-521__mask1__v1/` | 20 | goal-dose, mask1 | — |
| `raw/P2__goal_dose__s512-521__mask2__v1/` | 20 | goal-dose, mask2 | — |
| `raw/P2__goal_dose__s512-521__strong__v1/` | 20 | goal-dose, strong | 4 conditions together reproduce appendix I.2's eight means: **0/8 mismatch** |

Each episode carries its own provenance in `config` (seed, arm, `goal_mode`,
`task_mode: continuous`, model, endpoint, checkpoint hash) and in `source_hashes` (a
per-file SHA-256 map of the code that produced it). The composite utility is the
top-level `V` field, equal to `metrics.blue_score`.

Verify with:
```bash
python reproduce/verify_p1_grid.py     # tab_p1_seedgrid
python reproduce/verify_p2_dose.py     # appendix I.2 dose-gain means
```

### The 22 batch directories

| Batch | Files | MB | What it holds |
|---|---|---|---|
| `p0-next-20261002` | 2023 | 21.8 | largest batch: LLM channel predictions, development-window audits, reports |
| `E1_partial-direction_split_p01_20261003` | 611 | 5.4 | direction-split confirmation; also E1 calibration + gate seeds |
| `p0-strengthening-20261001` | 81 | 3.3 | P0 strengthening payload, incl. the E3 deception predictions |
| `E1_combined_confirmation_p01_20261004` | 198 | 2.1 | combined confirmation (E1 seeds 4201–4210) |
| `E1_confirm_device-a_p01_20261004` | 187 | 1.5 | device-A confirmation |
| `E10_HF_restricted-continuous_p02_20261003` | 102 | 1.2 | restricted-continuous HF |
| `E14_Grid_complex-baseline_p01_20261003` | 68 | 1.1 | grid complex baseline (**E14 is cited by name in the appendix**) |
| `E2_Grid_dose-shape_reanalysis_p01_20261002` | 10 | 0.6 | goal-dose shape reanalysis |
| `V14_TRACE_ANALYSIS_20261007_p01` | 47 | 0.6 | trace analysis |
| `E11_HF_perception-value_p01_20261003` | 17 | 0.6 | perception-value HF |
| `E10_grid_feature-alignment_p01_20261002` | 21 | 0.3 | feature alignment |
| `P0_GRID_COMPLEX_LAYERED_20261006_p01` | 90 | 0.3 | layered grid complex |
| `e11-cross-scene-20261003` | 7 | 0.2 | cross-scene |
| `linux-smoke-local-47a5631c` | 23 | 0.08 | environment smoke record (fetched from the server) |
| `e1-split-v13-20261003` | 7 | 0.07 | v13 split |
| `v5-core-20261002` | 6 | 0.05 | v5 core |
| `e14-grid-diagnostic-20261003` | 6 | 0.05 | grid diagnostic |
| `e10-hf-p02-20261003` | 4 | 0.04 | HF p02 launcher |
| `grid-rl-linux-s9901` | 2 | 0.03 | environment smoke record (fetched from the server) |
| `e1-recovery-20261003` | 2 | 0.02 | recovery |
| `e1-scheduler-v2-20261003` | 2 | 0.02 | scheduler v2 |
| `e1-device-a-v13-20261004` | 3 | 0.01 | device-A v13 |

Plus `V14_TRACE_ANALYSIS_20261007_server1_v1.zip` — the zipped companion to the `.p01`
trace-analysis directory, fetched from the server so both forms are present.

Composition: results in JSON, batch launcher / analysis scripts living inside the runs
(e.g. `e1_analyze.py`, `inspect_run.py`), Markdown reports, CSV, PNG and SVG.

## What this data does NOT cover

Two appendix blocks are **not** here, and matching on seed range alone would
mis-attribute them:

| Appendix block | Seeds | Status |
|---|---|---|
| I.3 real-stream counterfactual | 601–610 | **absent.** Seeds 601/602/603/605/607 do appear in `p0-strengthening`'s E3 files, but those are `p_real` **deception-detection** records, a different experiment that reuses the range. |
| I.4 anchored critical-fault | 561–570 | not here; the data is on the user's machine under `server-experiments/g1-fault-dose/` (94 MB) |

See `PAPER_COVERAGE.md` at the repository root for the full paper-to-data mapping.


## How the numbers are keyed

Result records carry their own provenance inline, which is what makes the batches
auditable. A representative record from
`p0-next-20261002/E3-channel-complex/channel_predictions.json`:

```json
{"id": "009317da80b06bd6380040e3", "seed": 14263, "gold_real": false,
 "source_batch": "D1-complex-20261002", "rule_p_real": 0.5,
 "snapshot_p_real": 0.5, "llm_p_real": 0.05, "model": "Qwen3.8-27B",
 "endpoint": "http://127.0.0.1:8102/v1", "prompt_sha256": "0d13f4fc..."}
```

So each prediction is traceable to its seed, source batch, prompting rule, model and
endpoint, with a prompt hash.

## Not included, and why

The co-author's server holds **~130,000 files**; this snapshot is a curated subset. It was
compared against the server and then **extended with four small items fetched directly**,
so the only substantive omission left is one large batch:

| Item | Size | Note |
|---|---|---|
| `runs/E10_HF_restricted-continuous_p01_20261002` | 287 MB | separate HF batch (p01); the **p02 variant is included** above. Not referenced by the paper or appendix. Omitted to keep the repository clonable; fetch it if that batch is ever needed. |
| `runs/*.tar.gz` (6 delivery archives) | — | earlier packaged deliveries of the same material, superseded by this snapshot |
| `releases/gitlab-ccabad00154e/.venv/` | ~50,000 files | a virtual environment, not project material |

**Fetched from the server to complete the snapshot** (not in the original tarball):
`grid-rl-linux-s9901`, `linux-smoke-local-47a5631c`,
`V14_TRACE_ANALYSIS_20261007_server1_v1.zip`.

None of the remaining omissions are required to recompute the results present here. They
are recorded so the coverage of this snapshot is explicit rather than implied.

## A note on code

`releases/<rev>/repo/openmd/code/` in the tarball holds the co-author's copy of the same
203 `_w1_*.py` analysis scripts that this repository ships under `code/analysis/`.
Verification: all 203 filenames match; **34 files are byte-identical and 169 differ**,
because the two working copies diverged during the campaign. The versions in this
repository are the newer ones (they carry the fixes documented in
`../WITHHELD_BRIEFING_EVIDENCE.md`).

Practical consequence: the JSON in `collaborator_runs/` was produced under the
co-author's intermediate code state. Treat these files as **evidence to inspect**, and
re-run any analysis you intend to publish with the scripts in `code/analysis/`.
The two seed scopes are also disjoint — our main table uses seeds 7/11/13/17/19, while
these batches key on seeds in the 500–14000 range — so this data does **not** mix into
the reported high-fidelity statistics.
