# PENDING — material not in this bundle

This file exists so the release is honest about its own coverage. Anything listed here is
**not** a gap in the reproduction of the paper's main table; that table is fully
reproducible from what is committed (70/70 cells verified). These are separate evidence
trees.

---

## 1. Co-author data — RECEIVED

The co-author's run data has arrived and is included as
[`collaborator_runs/`](collaborator_runs/README.md) (22 batch directories, 3,519 files,
39.6 MB). It was verified against their live container (`hr-a6000-129-51`) by comparing a
`(relpath, size)` manifest of all 77,411 server files: **0 size differences**, and the
snapshot is a strict subset — nothing in it contradicts the server.

That directory's own README records what it contains, how each result record is keyed
(seed, source batch, prompt hash, model, endpoint), and the one large batch left out
(`E10_HF_restricted-continuous_p01`, 287 MB, not referenced by the paper).

Code version note: the tarball also carries the co-author's copy of the same 203
`_w1_*.py` analysis scripts. All 203 filenames match ours; 34 are byte-identical and 169
have diverged, because the two working copies evolved separately during the campaign.
The versions shipped in `code/analysis/` are the newer ones. Treat the collaborator JSON
as evidence to inspect, and re-run any published analysis with the shipped scripts.

Seed scopes are disjoint (ours: 7/11/13/17/19; theirs: 500–14000), so the collaborator
data does not mix into the reported high-fidelity statistics.

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
