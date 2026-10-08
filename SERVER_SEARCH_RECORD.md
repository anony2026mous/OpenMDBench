# Server search record — hunting the four uncovered artefacts

Record of an exhaustive search (2026-10-08) across every host and directory reachable for
this project. Written so the negative results are auditable: each "not found" states what
was searched, because a negative is only useful with its scope attached.

## Scope searched

| Host / area | Path | What it holds |
|---|---|---|
| Local machine | `C:\Code\source-code` | working tree |
| Local machine | `~/openmd_private_archive/declared_briefing_snapshot_20260927_1419/` | 864 archived pre-fix episode reports |
| Local machine | `~/Downloads/openmd-paper/` | manuscript sources |
| **Server A** (user's, `<server-host>`) | `/mnt/QTJC/chenyi-codex/` | 133 GB source-code + 23 GB experiments; 61 sync snapshots |
| **Server A** | every snapshot's `openmd/code/eval/_w1_runs` | 56 snapshots carry the directory |
| **Server B** (co-author's, `<server-host>`) | `/root/openmd/{runs,exports,cache,releases,services,tools}` | 32 runs, 11 GB; 5 export packages |
| Server B | `runs/*.tar.gz` (6 delivery archives) | 338 MB of packaged deliveries |
| Server B | all `exports/*.zip` | e2, e10, e11, e14, E1/Exp2 runner materials, P0 complete |

Searches were by **content** (`"seed": <n>` inside JSON) as well as by name, because the
appendix's seed ranges are reused by unrelated experiments — a name-only search produces
false positives.

**Stated limitation:** on Server A the first sweep's output was truncated at 80 lines, so
its items 2–6 did not complete in that pass. Server A was then re-searched item by item
with dedicated scripts, but it did not receive the single consolidated sweep that Server B
did. The Server A conclusions below are correspondingly slightly weaker than the Server B
ones.

---

## A. Appendix G `tab:nointel` — legacy arm: FOUND, but not the paper's subset

### Where

`~/openmd_private_archive/declared_briefing_snapshot_20260927_1419/results/`, 864 files —
the archive written by `_w1_snapshot_declared.ps1`, whose own comment reads "Snapshot the
current (declared-briefing / pre-fix) state before changing anything".

Confirmed by content: **0** of the 864 files mention `briefing`, exactly right for pre-fix
episodes (the field did not exist yet).

### What it yields

Keeping only the 14 IE scenarios, non-aborted, with a numeric score: **795 episodes**.

| Arm | Archive episodes | Mean (14-scenario convention) | Paper legacy |
|---|---|---|---|
| LLM+Rule | 79 | 0.756 +/- 0.091 | 0.769 (n=82) |
| LLM+RL | 135 | 0.778 +/- 0.109 | 0.782 (n=49) |
| Pure LLM | 82 | 0.542 +/- 0.186 | 0.516 (n=40) |

Means are close (delta 0.013 / 0.004 / 0.026) but the **counts do not match**, so this is
the right family of runs and not the same subset the paper aggregated.

### A trap worth recording

The archive's LLM+RL episodes carry `defender.planner.planner == "llm"` in the body — the
body names the *planning* layer, and the RL half is the executor. A parser that trusts the
body folds all 135 LLM+RL episodes into LLM+Rule and reports zero LLM+RL. The reliable arm
tag here is the **filename prefix** (`ie_llmrl_...`). This cost one wrong intermediate
result during the search.

### Conclusion

The legacy column is recomputable **in kind but not in exact value**. To publish that
table, recover the seed filter from `_w1_declared_delta.py` /
`_w1_declared_vs_withheld.py`, or regenerate the table from this archive and update the
appendix to whatever it yields.

---

## B. Appendix I.3 — real-stream counterfactual, seeds 601–610: ABSENT

* Server B: seeds 601–610 appear **only** in `p0-strengthening-20261001/results/E3/` and
  `E3-expanded/` — deception-detection `p_real` records from a different experiment that
  reuses the range.
* Server A: the only 601-hits are unrelated `competition_four_categories` artifacts
  (`ad-MD-AD-001-guard-601-...`).
* No directory named for a stream or counterfactual batch exists on either host.

`tab_p3aseed` and the +0.420 estimand therefore have **no source data** in any reachable
location.

---

## C. Appendix I.4 — anchored critical-fault, seeds 561–570: on the local disk only

* Server B: `find -name 'seed-5[67]*'` returns only
  `p0-next-20261002/E3-channel-v2/confirmation_sources/seed-56xx` (four-digit E3 seeds,
  unrelated).
* Server A: not present.

Present locally at `server-experiments/g1-fault-dose/` — 1,556 files, 94 MB. **Now
included in this release** as `data/g1-fault-dose/`.

Its `MANIFEST.json` confirms the base the appendix describes
(`"design": {"planner": "rule", "executor": "heuristic", ...}`), and the seed range is
exactly 561–570. But the published fault costs (0.567 planner / 0.327 executor) do **not**
reproduce from it: no dose level reaches those values, signs are often inverted, and the
batch has 10 seeds where the appendix says 20/20. See `data/g1-fault-dose/README.md`.

---

## D. `figA2_replanning_sweep`: data present — an earlier "absent" verdict was wrong

A correction to an earlier conclusion in this project. The sweep's data lives in this
repository, not on a server:

```
data/campaigns/paper-e5-e7-priority/E7-frequency-stage1/    (k = 10, 5, 2)
data/campaigns/paper-e5-e7-priority/E7-baseline/            (RL baseline)
```

`reproduce/verify_replanning.py` matches the appendix H values for the reported arm:
k=10 -> 0.467, k=5 -> 0.733, k=2 -> 0.733, **0/3 mismatches**. The check also documents a
real trap: the k=10 directory holds RL-arm episodes alongside the LLM+RL ones, and failing
to filter by arm gives 0.680 instead of 0.467.

The earlier "no file named replan or sweep exists" search was a **filename** search, and
the directory is named `E7-frequency-stage1` — "frequency", not "replan". A name-based
negative is only as good as the name you guessed.

---

## Bonus findings

* **`exports/e2-delivery-20261003/E2_20261003_v1.zip`** — the curated export whose
  `raw/P1__six_arm__s501-510__main__v1` and `raw/P2__goal_dose__s512-521__*/` are the
  actual sources of `tab_p1_seedgrid`, the main-text `tab:sixarm` and appendix I.2. Now
  included and verified (0/60 cells differ; 0/6 means; 0/8 dose means).
* Server A holds **61 sync snapshots**; 56 contain `_w1_runs`, but every one of those
  directories is **empty** — the sync config excludes `_w1_runs` contents, so the snapshots
  preserve the directory and not the episodes. No declared episodes there.
* Server B holds two delivery archives not in the handed-over tarball:
  `E10_20261003_v1.zip` (77 MB; `raw/{development,LLM,confirmation}`) and
  `E11_complete_delivery` / `E14_complete_delivery` (7.5 MB + 8.9 MB).

---

## Summary

| Artefact | Status after exhaustive search |
|---|---|
| Appendix G legacy arm | **Found** (795 episodes); paper's exact 82/49/40 subset not reproducible |
| Appendix I.4 (561–570) | local disk only — **now in the release**; numbers still do not reproduce |
| Appendix I.3 (601–610) | **absent** from every host |
| `figA2` replanning sweep | **present in this repository** — earlier absence verdict was wrong |
