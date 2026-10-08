# Server search record — hunting the four uncovered artefacts

Record of an exhaustive search (2026-10-08) across every host and directory reachable for
this project, looking for the four items `PAPER_COVERAGE.md` lists as missing or partial.
Written so the negative results are auditable: each "not found" states exactly what was
searched, because "I could not find it" is only useful with the scope attached.

## Scope searched

| Host / area | Path | What it holds |
|---|---|---|
| Local machine | `C:\Code\source-code` | working tree, 25,601 JSON parsed |
| Local machine | `~/openmd_private_archive/declared_briefing_snapshot_20260927_1419/` | 864 archived pre-fix episode reports |
| Local machine | `~/Downloads/openmd-paper/` | manuscript sources |
| **Server A** (user's, `hr-a6000-129-57`) | `/mnt/QTJC/chenyi-codex/` | 133 GB source-code + 23 GB experiments; 61 sync snapshots |
| **Server A** | every snapshot's `openmd/code/eval/_w1_runs` | 56 snapshots carry the directory |
| **Server B** (co-author's, `hr-a6000-129-51`) | `/root/openmd/{runs,exports,cache,releases,services,tools}` | 32 runs, 11 GB; 5 export packages |
| Server B | `runs/*.tar.gz` (6 delivery archives) | 338 MB of packaged deliveries |
| Server B | all `exports/*.zip` | e2, e10, e11, e14, E1/Exp2 runner materials, P0 complete |

Searches were by **content** (`"seed": <n>` inside JSON) as well as by name, because the
appendix's seed ranges turned out to be reused by unrelated experiments — a name-only
search would have produced false positives.

---

## A. Appendix G `tab:nointel` — legacy arm: **FOUND, but not the paper's exact subset**

### Where it is

`~/openmd_private_archive/declared_briefing_snapshot_20260927_1419/results/`, 864 files.
This is the archive written by `_w1_snapshot_declared.ps1`, whose own comment reads
"Snapshot the current (declared-briefing / pre-fix) state before changing anything" — i.e.
the declared/legacy regime, captured just before the withheld switch was introduced.

Confirmed by content: **0** of the 864 files mention `briefing`, which is exactly right for
pre-fix episodes (the field did not exist yet).

### What it contains

After keeping only the 14 IE scenarios, non-aborted, with a numeric score: **795 episodes**.

| Arm | Archive episodes | Mean (14-scenario convention) | Paper legacy |
|---|---|---|---|
| LLM+Rule | 79 | 0.756 ± 0.091 | 0.769 (n=82) |
| LLM+RL | 135 | 0.778 ± 0.109 | 0.782 (n=49) |
| Pure LLM | 82 | 0.542 ± 0.186 | 0.516 (n=40) |

**Agreement is close but not exact:** LLM+RL differs by 0.004, LLM+Rule by 0.013,
pure-LLM by 0.026. Crucially the **episode counts do not match** (79/135/82 vs 82/49/40),
so this is the right family of runs but not the same subset the paper aggregated.

### A trap worth recording

The archive's LLM+RL episodes carry `defender.planner.planner == "llm"` in the body —
the body reports the *planning* layer, and the RL half is the executor. A parser that
trusts the body therefore folds all 135 LLM+RL episodes into LLM+Rule and reports zero
LLM+RL. The reliable arm tag in this archive is the **filename prefix**
(`ie_llmrl_…`). This cost one wrong intermediate result during the search.

### Conclusion

The legacy column is **recomputable in kind but not in exact value** from what exists. To
publish that table, either the original subset must be recovered (the script that produced
82/49/40 is `_w1_declared_delta.py` / `_w1_declared_vs_withheld.py`, whose seed filter is
recoverable from those scripts), or the table should be regenerated from this archive and
the appendix updated to whatever numbers that yields.

---

## B. Appendix I.3 — real-stream counterfactual, seeds 601–610: **ABSENT**

Not found on either server. Specifically:

* Server B: seeds 601–610 appear **only** in `p0-strengthening-20261001/results/E3/` and
  `E3-expanded/` — deception-detection `p_real` records from a different experiment that
  reuses the range. Substituting them would mis-attribute the result.
* Server A: the only 601-hits are unrelated `competition_four_categories` artifacts
  (`ad-MD-AD-001-guard-601-…`), a separate competition track.
* No directory named for a stream/counterfactual batch exists anywhere.

The paper's `tab_p3a_seedgrid` and the +0.420 estimand therefore have **no source data**
in any reachable location.

---

## C. Appendix I.4 — anchored critical-fault, seeds 561–570: **on the local disk only**

Not on either server. Server B's `find -name 'seed-5[67]*'` returns only
`p0-next-20261002/E3-channel-v2/confirmation_sources/seed-56xx` (four-digit E3 seeds,
unrelated).

Present locally at `server-experiments/g1-fault-dose/` — 1,556 files, 94 MB, with
`complex-baseline/clean/seed-561 … seed-570` plus the injection conditions (`complex`,
`full`, `opps`, `pilot`, `probe`, `replaygate`, `smoke`). Promoting it into
`data/` would close this row.

---

## D. `figA2_replanning_sweep`: **ABSENT**

No file or directory whose name contains `replan` or `sweep` exists on either server or
the local machine (excluding `node_modules` and site-packages noise, which contain
unrelated stream/sweep libraries). The figure has no recoverable plotting data, and
`appendix.tex` does not reference it from any section.

---

## Bonus found during the search

* **`exports/e2-delivery-20261003/E2_20261003_v1.zip`** — the curated export whose
  `raw/P1__six_arm__s501-510__main__v1` and `raw/P2__goal_dose__s512-521__*/` are the
  actual sources of `tab_p1_seedgrid` and appendix I.2. Now included and verified
  (**0/60 cells differ; 0/8 means mismatch**). This closed the largest gap.
* Server A holds **61 sync snapshots**; 56 contain `_w1_runs`, but every one of those
  directories is **empty** — the sync config excludes `_w1_runs` contents, so the
  snapshots preserve the directory but not the episodes. No declared episodes there.
* Server B holds two delivery archives not in the handed-over tarball:
  `E10_20261003_v1.zip` (77 MB; `raw/{development,LLM,confirmation}`) and
  `E11_complete_delivery` / `E14_complete_delivery` (7.5 MB + 8.9 MB). They cover E10/E11
  batches, not the four artefacts hunted here, but they are available if wanted.

---

## Summary

| Artefact | Status after exhaustive search |
|---|---|
| Appendix G legacy arm | **Found** (795 episodes); paper's exact 82/49/40 subset not reproducible |
| Appendix I.4 (561–570) | Local disk only — promote to `data/` to close |
| Appendix I.3 (601–610) | **Absent** from every host |
| `figA2` replanning sweep | **Absent** from every host |
