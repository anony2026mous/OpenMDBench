# Paper → repository coverage

Every table, figure and numeric block in the paper, mapped to where its data lives in this
repository. Written because "the data is in the repo" is a claim that should be checkable,
not asserted: each row below states what exists, what was verified, and what does not.

Verified on 2026-10-08 against `main.tex` (408 lines) and `appendix.tex` (489 lines).

---

## Summary

| Status | Count | Meaning |
|---|---|---|
| **Reproducible from this repository** | 12 | the data is here and was matched against the paper's numbers |
| **Diverges** | 3 | data is here, the printed numbers do not follow from it |
| **Partial** | 2 | some data is here; the rest is listed below |
| **Absent** | 1 | no source data in any available tree |

The paper's **primary claim** — the high-fidelity suite table — is in the first category
and reproduces exactly. Nine checks now run from this bundle:

| Script | Target | Result |
|---|---|---|
| `reproduce/verify_paper_table.py` | `tab_hifi_main` | **70/70 exact, 0 differ** |
| `reproduce/verify_p1_grid.py` | `tab_p1_seedgrid` | **0/60 cells differ** |
| `reproduce/verify_p2_dose.py` | appendix I.2 dose-gain | **0/8 mismatch** |
| `reproduce/verify_sixarm.py` | `tab:sixarm` + P/E/I identity | **0/6 means; identity exact** |
| `reproduce/verify_complex_tier.py` | `tab:complexlayered` | **0/3 mismatch** |
| `reproduce/verify_replanning.py` | appendix H sweep / `figA2` | **0/3 mismatch** |
| `reproduce/verify_legacy_arm.py` | appendix G legacy arm | runs; values **differ** (§2.2) |
| `reproduce/verify_i4_fault.py` | appendix I.4 fault costs | **not reproduced** (§2.1) |
| `reproduce/verify_model_invariance.py` | `tab:modelinvariance` | 2 of 4 models; **differ** (§2.3) |

### Where each item sits in the paper

| Item | Location | Status |
|---|---|---|
| `tab_hifi_main` | main text §6 (`tab:hifi`, `fig:hifigap`) | reproducible |
| `tab:sixarm` | main text §6, "Three paired batches" (main.tex 294–325) | reproducible |
| `tab_p1_seedgrid` | appendix I.1 (appendix.tex 318–321) | reproducible |
| `tab_p2_seedgrid` + `tab:dosegain` + `figA3` | appendix I.2 (appendix.tex 323–356) | reproducible |
| `tab:complexlayered` | appendix (appendix.tex 140–150), seeds 63101–63105 | reproducible |
| `tab:frequency` + `figA2_replanning_sweep` | **appendix H** (appendix.tex 260–288) | reproducible; baseline row present |
| `tab:e5pilot` + `figA4` | appendix I.5 (appendix.tex 366–402) | machine labels present; Δ table partial |
| `tab_scenario_params` | appendix A (`\input`) | shipped; content not re-derived |
| E1 headroom calibration | appendix K (appendix.tex 404–475) | reproducible |
| `tab:modelinvariance` + `figA1` | appendix (appendix.tex 178–205) | **2 of 4 models; contrast differs** |
| `tab:nointel` | **appendix G** (appendix.tex 217–234, inline) | **partial**; legacy arm differs |
| Anchored critical-fault validation | appendix I.4 (appendix.tex 363–364) | batch present, **numbers do not reproduce** |
| `tab_p3aseed` + real-stream counterfactual | appendix I.3 (appendix.tex 358–361) | **absent** |
| `tab:interface`, `tab:intervention`, `tab:comparison` | appendix (appendix.tex 246, 296) | **no source data located** |


---

## 1. Reproducible, and verified

### 1.1 `tab_hifi_main` — the main table

* **Data**: `data/grid_withheld_5seeds/episodes/` (213 per-episode reports)
* **Verdict**: **70/70 cells exact, 0 differing**
* **Run**: `python reproduce/verify_paper_table.py`
* **Record**: `reproduce/PAPER_TABLE_VERIFICATION.txt`

Also checked: the `Overall` row's five values, which use the scenario-mean convention
(mean ± sample SD over the 14 scenario means), reproduce exactly.

### 1.2 `tab:sixarm` — main-text six-arm aggregates (seeds 501–510)

* **Location**: main.tex 304–325, referenced 3×
* **Data**: `data/collaborator_runs/e2-delivery-20261003/raw/P1__six_arm__s501-510__main__v1/`
* **Verdict**: **0/6 mean mismatches**, success counts 9/9/8/6/6/1 all match, and the
  deployment accounting identity reproduces (P = −0.213, E = −0.103, I = +0.077)

This is the same batch as appendix I.1 seen from the aggregate angle, so it is the
strongest verification here: one dataset reproduces both the per-seed table and the
main-text accounting identity.

### 1.3 `tab_p1_seedgrid` — six-arm grid per seed (appendix I.1)

* **Data**: same P1 batch
* **Verdict**: **0/60 cells differ** (34 exact, 26 within the table's 2-dp rounding)
* **Run**: `python reproduce/verify_p1_grid.py`
* **Record**: `reproduce/P1_GRID_VERIFICATION.txt`

The batch holds exactly 60 episodes (10 seeds × 6 arms), matching the table's "All 60 cells
eligible" caption. The composite is the episode's `V` field, equal to `metrics.blue_score`.

### 1.4 `tab_p2_seedgrid` + `tab:dosegain` + `figA3_dose_gain` (appendix I.2)

* **Data**: `.../raw/P2__goal_dose__s512-521__{hold,mask1,mask2,strong}__v1/`
* **Verdict**: **0/8 stack-by-dose means mismatch** — all agree to 3 decimals
* **Run**: `python reproduce/verify_p2_dose.py`
* **Record**: `reproduce/P2_DOSE_VERIFICATION.txt`

Each condition holds 20 episodes (10 seeds × 2 stacks) = 80 reports. The eight means
reproduce exactly, including the non-monotone detail appendix I.2 discusses (rule-rl falls
0.833 → 0.670 from mask1 to strong while llm-rl rises 0.710 → 0.750).

### 1.5 `tab:frequency` + `figA2_replanning_sweep` (appendix H)

* **Location**: appendix H, appendix.tex 260–288; line 283 is the **only** occurrence of
  `figA2` in the paper, so the figure belongs to this section
* **Data**: `data/campaigns/paper-e5-e7-priority/E7-frequency-stage1/`
* **Verdict**: **0/3 mismatches** on the reported arm — k=10 0.467, k=5 0.733, k=2 0.733,
  three episodes each, matching appendix H to 3 decimals
* **Run**: `python reproduce/verify_replanning.py`

**One trap worth stating.** That directory mixes arms: 9 `llm-rl` episodes (the reported
series) and 2 `rl` episodes. Averaging the k=10 group without filtering the arm gives
**0.680 instead of 0.467** — a wrong answer that looks like a real number. The script
filters on `config.arm` for this reason.

**Partial.** The table's `pure RL` row (V = 0.978) is not in this tree: `E7-baseline` is
0.933 and the two `rl` episodes inside the frequency batch are both 1.000. Every `rl`-arm
episode in the release (20 of them) takes one of {0.233, 0.867, 0.933, 1.000}; none is
0.978. The three sweep rows reproduce; the baseline row does not.

### 1.6 Appendix I.5a — natural-failure pilot, HF cases (seeds 5101–5112)

* **Data**: `data/campaigns/e5-hifi-attribution-r3/`, `e5-hifi-attribution-r3b/`
* **Coverage**: all 12 seeds present in `plan.json`, `plan-input.json`

### 1.7 Appendix I.5b — natural-failure pilot, grid cases (seeds 5201–5212)

* **Data**: `data/campaigns/e5-grid-natural-failures/e5_grid_summary.json`
* **Coverage**: all 12 seeds present

### 1.8 Appendix I.5 — human annotation agreement (κ, blind IDs E5-01…E5-12)

* **Location**: appendix I.5, appendix.tex 367
* **Data**: `data/campaigns/e5-annotation-final/` (`kappa_summary.json`, `selection.json`)
* **Note**: the **answer key is deliberately withheld** — see `PENDING.md` §1b. The
  κ = 0.25 result is only meaningful while the key stays unpublished.

### 1.9 Appendix K — E1 headroom calibration and confirmation

* **Location**: appendix K, appendix.tex 404–475
* **Data**: `data/collaborator_runs/E1_partial-direction_split_p01_20261003/` (calibration
  4101–4110, gate 4151–4160), `E1_combined_confirmation_p01_20261004/` and
  `E1_confirm_device-a_p01_20261004/` (confirmation 4201–4210)
* **Coverage**: all three seed blocks complete (10/10 each)

### 1.10 `figA1_model_invariance` — four-model scan

* **Data**: `data/campaigns/e6-model-invariance/` — `analysis/e6_analysis.json`,
  `analysis/per_case.csv`, `plan.json`, `plan-10seeds.json`, plus per-run episodes
* **Coverage**: present, including the per-case table behind the figure

---

## 2. Partially covered

### 2.1 Appendix I.4 — anchored critical-fault validation (seeds 561–570)

* **Location**: appendix I.4, appendix.tex 363–364
* **On this machine**: `server-experiments/g1-fault-dose/` — 1,556 files, 94 MB, 316
  episode reports across 8 sub-batches (`complex`, `complex-baseline`, `full`, `opps`,
  `pilot`, `probe`, `replaygate`, `smoke`). Seeds 561–570 are present.
* **Not committed**: listed in `EXTERNAL_DATA_MANIFEST.json` to keep the clone small.

**But the numbers do not reproduce, and this should be flagged before submission.**
Appendix I.4 reports single per-side costs: planner 0.567 score / 0.7 success / 0.7 breach,
executor 0.327 / 0.4 / 0.4. Running the batch (`reproduce/verify_i4_fault.py`, recorded in
`reproduce/I4_FAULT_VERIFICATION.txt`):

| Tier | clean mean V | planner-side cost range | executor-side cost range |
|---|---|---|---|
| `complex` | 0.477 | +0.053 … +0.110 | −0.077 … +0.230 |
| `full` | 0.847 | −0.153 … +0.097 | −0.147 … −0.060 |

* **No dose level reproduces 0.567 or 0.327.** Every cost in the batch has |cost| < 0.25.
* **The signs are frequently inverted**: the injected fault often *raises* V (e.g. `full`
  / `planner_wrong_contact` / dose 0.4 gives V = 1.000 against a clean 0.847).
* The paper says "20/20 paired seeds"; the batch has 10 seeds per tier.

So `g1-fault-dose` is **not** the experiment behind I.4, or it encodes conditions that
differ from what the appendix describes. Either way the I.4 numbers cannot be reproduced
from it, and shipping the batch without this note would invite a false expectation.
Resolve before submission: locate the actual I.4 batch, or reconcile the appendix text.

### 2.2 Appendix G — "intelligence-regime ablation" (`tab:nointel`)

* **Location**: appendix G, appendix.tex 217–234. The table is **inline**, so the separate
  `paper/tables/tab_hifi_nointel.tex` is not the copy that compiles.
* **Present**: the no-intelligence arm. `tab_hifi_main`'s 70 episodes per stack are the
  withheld-regime runs, and the no-intel column (0.774 / 0.783 / 0.431) matches the main
  table's baseline column.
* **Also present, located by the server search**: the **legacy (declared-intelligence)
  episodes** — 795 of them — in
  `~/openmd_private_archive/declared_briefing_snapshot_20260927_1419/`, the archive written
  by `_w1_snapshot_declared.ps1` immediately before the withheld switch. Confirmed by
  content: 0 of its 864 files mention `briefing`, as expected for pre-fix runs.
* **But not the paper's subset**: the archive yields 79 / 135 / 82 episodes for
  LLM+Rule / LLM+RL / pure-LLM, where the table reports n = 82 / 49 / 40. The means come
  close (0.756 vs 0.769; 0.778 vs 0.782; 0.542 vs 0.516) but the counts do not agree, so
  the published Δ column and its "better on k/14" counts remain **not reproducible as
  printed**. To close it, recover the seed filter from `_w1_declared_delta.py` /
  `_w1_declared_vs_withheld.py`, or regenerate the table from this archive and update the
  appendix accordingly.

Three further points a reviewer should know:

1. The inline table and the file copy **disagree**: the file reports LLM+Rule legacy
   0.753 / no-intel 0.774; the inline version reports 0.769 / 0.790. The inline copy is
   what the manuscript compiles; the file copy looks like a stale extraction.
2. The regimes have **unequal n** (70 vs 82/49/40) and different seeds, so the contrast is
   not paired. The appendix does not claim it is.
3. **Parsing trap** in that archive: its LLM+RL episodes report
   `defender.planner.planner == "llm"` in the body, because the body names the *planning*
   layer. Trusting it folds all 135 LLM+RL episodes into LLM+Rule and reports zero LLM+RL.
   Use the filename prefix (`ie_llmrl_…`) as the arm tag for this archive.

---

## 3. Absent

### 3.1 Appendix I.3 — real-stream counterfactual (seeds 601–610) and `tab_p3aseed`

* **Location**: appendix I.3, appendix.tex 358–361; also cited from main.tex 294 and 296
  ("the real-stream counterfactual agrees (10/10 seeds, +0.420)")
* **Absent**: the counterfactual episodes for seeds 601–610
* **Warning**: seeds 601, 602, 603, 605, 607 **do** appear in the co-author's
  `p0-strengthening-20261001/results/E3*/` files — but those are deception-detection
  `p_real` classification records from a *different experiment that reuses the range*.
  Matching on seed alone would mis-attribute them and yield a confident wrong answer.

### 3.2 `figA4` ΔP/ΔE/ΔI table and appendix I.4's degradation accounting

* **Location**: `tab:e5pilot`, appendix.tex 369–393
* The 12-case values are printed inline in the appendix and the per-case machine labels are
  in `e5-hifi-attribution-r3b/`, but **no JSON holds the ΔP/ΔE/ΔI values as a table**, so
  the printed numbers cannot be re-derived from released files alone.

---

## 4. Coverage of the four independent batches

Appendix I states the four batches are independent and must not be pooled:

| Batch | Seeds | Location in paper | Status |
|---|---|---|---|
| six-arm accounting | 501–510 | main §6 + appendix I.1 | **present, verified twice** |
| goal-dose | 512–521 | appendix I.2 | **present, verified** |
| anchored critical-fault | 561–570 | appendix I.4 | batch on disk, **numbers do not reproduce** |
| real-stream counterfactual | 601–610 | appendix I.3 | **absent** |

---

## 5. Reproducing these checks

```bash
export PYTHONPATH="$PWD/code/analysis:$PWD/code/engine"
python reproduce/verify_paper_table.py   # tab_hifi_main       70/70 exact
python reproduce/verify_p1_grid.py       # tab_p1_seedgrid     0/60 differ
python reproduce/verify_p2_dose.py       # appendix I.2        0/8 mismatch
python reproduce/verify_replanning.py    # appendix H / figA2  0/3 mismatch
python reproduce/verify_sixarm.py        # main tab:sixarm     0/6 mismatch
python reproduce/verify_i4_fault.py      # appendix I.4        (needs server-experiments/g1-fault-dose)
```
