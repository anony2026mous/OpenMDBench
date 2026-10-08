# PENDING — material not in this bundle

This file exists so the release is honest about its own coverage. Anything listed here is
**not** a gap in the reproduction of the paper's main table; that table is fully
reproducible from what is committed (70/70 cells verified). These are separate evidence
trees.

---

## 1. Co-author data — RECEIVED

The co-author's run data has arrived and is included as
[`collaborator_runs/`](collaborator_runs/README.md) (22 batch directories + a curated
`e2-delivery-20261003/`, 3,673 files, 45.6 MB). It was verified against their live
container (`hr-a6000-129-51`) by comparing a `(relpath, size)` manifest of all 77,411
server files: **0 size differences**, and the snapshot is a strict subset — nothing in it
contradicts the server.

The `e2-delivery-20261003/` export turns out to be the **only** source of the appendix's
per-seed grid tables, and both reproduce from it:

| Appendix table | Check | Result |
|---|---|---|
| `tab_p1_seedgrid` (six-arm, seeds 501–510) | `reproduce/verify_p1_grid.py` | **0/60 cells differ** |
| `tab_p2_seedgrid` + dose-gain (seeds 512–521) | `reproduce/verify_p2_dose.py` | **0/8 means mismatch** |

That directory's own README records what it contains, how each episode is keyed (seed,
arm, goal mode, checkpoint hash, per-file source hashes), and what it does **not** cover.

Code version note: the tarball also carries the co-author's copy of the same 203
`_w1_*.py` analysis scripts. All 203 filenames match ours; 34 are byte-identical and 169
have diverged, because the two working copies evolved separately during the campaign.
The versions shipped in `code/analysis/` are the newer ones. Treat the collaborator JSON
as evidence to inspect, and re-run any published analysis with the shipped scripts.

---

## 1a. Appendix I.3 — FOUND and verified

The real-stream counterfactual (seeds 601–610) was located and is now included as
`data/collaborator_runs/p0-strengthening-20261001/inputs/P3a__llm_goal_causal__s601-610__confirm__v1/`.

It reproduces `tab_p3a_seedgrid` **exactly**: per-seed LLM/hold/rule composites 10/10,
`LLM − hold` mean +0.420 positive in 10/10, `LLM − rule` mean −0.260, and the LLM call
counts 10/10. The intervention names itself in the data
(`intervention.kind = "all_unit_goals_to_legal_hold"`). Run
`python reproduce/verify_p3a.py`.

It was missed on the first pass because the seed range is **reused**: seeds 601/602/603/
605/607 also appear in `p0-strengthening-20261001/results/E3*/` as deception-detection
`p_real` records. Searching by seed finds the wrong experiment; the batch is found by its
intervention marker instead.

---

## 1b. Still missing

Full mapping in [`../PAPER_COVERAGE.md`](../PAPER_COVERAGE.md). Briefly:

| Block | Seeds | Status |
|---|---|---|
| Appendix I.4, anchored critical-fault validation | 561–570 | **no implementing experiment found.** Absent from every experiment inventory (20260930, 1003_1205, 1003_1439), and its terminology (`anchored critical`, `matched-prefix`, `critical-exposure`) has **0 hits** across e5_ascii, e5_easy, openmd/doc, role_c_toolkit/docs, server-experiments and the private archive. The nearest-named batch, `g1-fault-dose`, is experiment **G1** ("graded fault injection–recovery calibration"), whose own report concludes *terminate G1; the `5/5 graded faults` claim was deleted*, and whose costs do **not** reproduce 0.567/0.327 (every cost has |cost| < 0.25, frequently the wrong sign). |
| Appendix G, `tab:nointel` legacy arm | — | **located but not the printed subset.** The archive `~/openmd_private_archive/declared_briefing_snapshot_20260927_1419/` holds the legacy episodes (0 of 864 files mention `briefing`, as expected pre-fix), but yields 83/142/80 episodes against the table's 82/49/40. Means are close (pure-LLM 0.526 vs 0.516) yet the Δ column cannot be recomputed as printed without the seed filter from `_w1_declared_delta.py`. |
| Appendix I.4 degradation accounting, `figA4` ΔP/ΔE/ΔI table | — | the 12-case values are printed inline in the appendix but not stored as a JSON table. |
| `figA2_replanning_sweep` baseline row | — | the three sweep rows reproduce; the `pure RL` row (0.978) does not appear in any tree. |

### Still awaited from the co-author

| Item | Expected content | Paper reference | Status |
|---|---|---|---|
| _(to be listed)_ | | | **pending** |

Two scripts in `code/role_c_toolkit/` already expect external inputs and read them from
environment variables, so they will run unchanged once the data is placed:

| Script | Environment variable | Expected input |
|---|---|---|
| `e5_figA4_verify.py` | `OPENMD_FIGA4_DATA_DIR` | Figure A4 source CSV export |
| `e5_figA4_raw_audit.py` | `OPENMD_FIGA4_DATA_DIR` | same export, raw audit |
| `e4_exp2_blockers_doc.py` | `OPENMD_EXP2_BRIEF_MD` | experiment-2 planning brief (Markdown) |

---

## 1b. Deliberately withheld — do not add

| Item | Why it must stay out |
|---|---|
| `KEY_DO_NOT_SHARE.json` | The blind-annotation **answer key**. The appendix reports human–machine agreement (Cohen's κ) on blind IDs E5-01…E5-12 with the key withheld; publishing it would let anyone recover the labels and would invalidate the very statistic it supports. Two copies existed in the source trees (under `e5_ascii/` and under the E5 annotation campaign) and **both are excluded by an explicit build guard**, recorded in `BUILD_REPORT.json` as "withheld by policy". |
| `e5_easy/` | Directory excluded wholesale rather than file-filtered, because the workspace-wide policy guard is the thing that must not be bypassed. Its non-sensitive members (`E5_summary.md`, `E5_handoff.md`, `selection.json`, the blind-annotation bundle `E5_blind_annotation_12cases.zip`) can be promoted into `data/e5/` **only after** confirming the key stays out. |

---

## 2. Too large for git — request or re-derive

Present on the original machines, deliberately excluded from the repository. Sizes and
original paths are in `data/EXTERNAL_DATA_MANIFEST.json`.

| Tree | Size | What it backs |
|---|---|---|
| engine `artifacts/` | ~11.5 GB | engine-run evidence, calibration ledgers, frozen-source manifests |
| `five-seed-fill-*` episodes | ~6.0 GB | tick-by-tick traces of the server (CSS/ULHA) campaign |
| `e5-hifi-natural-failures` | ~12 GB | attribution evidence for the natural-failure study (12 cases) |
| `e4-headroom-2x2-P1` | ~218 MB | headroom 2×2 interaction batch |
| `g1-fault-dose` | ~94 MB | goal-dose batch |
| `server-artifacts/` | ~1.9 GB | validation evidence, calibration plans, run logs |

Server trees observed but not mirrored locally at the time of writing, in case they are
needed later: `E1_Exp2_option2_runner_materials_20261006_v1` (359 MB),
`V14_TRACE_ANALYSIS_20261007_p01` (643 MB) and `..._server2_v1.zip`,
`E1_device-b_v13_p01_20261004` (1.7 GB), `e4-headroom-2x2` (234 MB),
`e5-hifi-natural-failures-20261001T1920Z` (882 MB).

---

## 3. Not reproduced in this bundle

| Paper element | Why not | Where it comes from |
|---|---|---|
| `tab_p1_seedgrid` — six-arm grid, seeds 501–510 | separate campaign on a different score metric ("continuous task-authorization mode", kept apart from the payoff runs) | grid batch traces |
| `tab_p2_seedgrid` — goal-dose, seeds 512–521 | same: separate batch, four paired interface conditions | goal-dose batch |
| `tab_p3a_seedgrid` — LLM-call accounting | derived from the same grid batch | grid batch logs |
| `figA1`–`figA4` | figures ship in `paper/figures/`; their **source data** is needed only to re-draw, and `paper/figsrc/` holds the drawing scripts | campaign analysis JSONs |
| Model-invariance scan (four models) | serves two further models; the weights are 68 GB and are not project data | model serving logs |
| Kappa / human annotation agreement | raw form is committed under `data/campaigns/e5-annotation-final/` | — |

---

## 4. What a reviewer can already check without any of the above

1. `python reproduce/verify_paper_table.py` → 70/70 exact, from committed episodes.
2. `python reproduce/build_dataset.py` → rebuilds the 709-row consolidated dataset.
3. Every per-episode report carries its own provenance, so any single cell can be traced to
   the run that produced it: `briefing`, speed envelope, and policy checkpoint.
4. `data/grid_withheld_5seeds/WITHHELD_BRIEFING_EVIDENCE.md` documents the fairness,
   determinism and baseline-stability audits, with the script for each.
