# Paper → repository coverage

Every table, figure and numeric block in the paper, mapped to where its data lives in this
repository. Written because "the data is in the repo" is a claim that should be checkable,
not asserted: each row below states what exists, what was verified, and what does not.

Verified on 2026-10-08 against `main.tex` (408 lines) and `appendix.tex` (489 lines).

---

## Summary

| Status | Count | Meaning |
|---|---|---|
| **Reproducible from this repository** | 7 | the data is here and was matched against the paper's numbers |
| **Partially covered** | 2 | some of the data is here; the rest is listed below |
| **Absent** | 3 | the compiled figure ships, the source data does not |

The paper's **primary claim** — the high-fidelity suite table — is in the first category
and reproduces exactly.

---

## 1. Reproducible, and verified

### 1.1 `tab_hifi_main` — the main table (main text)

* **Data**: `data/grid_withheld_5seeds/episodes/` (213 per-episode reports)
* **Verdict**: **70/70 cells exact, 0 differing**
* **Run**: `python reproduce/verify_paper_table.py`
* **Record**: `reproduce/PAPER_TABLE_VERIFICATION.txt`

Also checked: the `Overall` row's five values, which use the scenario-mean convention
(mean ± sample SD over the 14 scenario means), reproduce exactly.

### 1.2 `tab_p1_seedgrid` — six-arm grid, seeds 501–510 (appendix I.1)

* **Data**: `data/collaborator_runs/e2-delivery-20261003/raw/P1__six_arm__s501-510__main__v1/`
* **Verdict**: **0/60 cells differ** (34 exact, 26 within the table's 2-dp rounding)
* **Run**: `python reproduce/verify_p1_grid.py`
* **Record**: `reproduce/P1_GRID_VERIFICATION.txt`

The batch holds exactly 60 episodes: 10 seeds × 6 arms
(`rule-rule`, `llm-rule`, `rule-rl`, `llm-rl`, `rl`, `pure-llm`), matching the table's
"All 60 cells eligible" caption. The composite is the episode's `V` field, which equals
`metrics.blue_score`.

### 1.3 `tab_p2_seedgrid` + `tab:dosegain` + `figA3_dose_gain` — goal-dose, seeds 512–521 (appendix I.2)

* **Data**: `data/collaborator_runs/e2-delivery-20261003/raw/P2__goal_dose__s512-521__{hold,mask1,mask2,strong}__v1/`
* **Verdict**: **0/8 stack-by-dose means mismatch** — all agree to 3 decimals
* **Run**: `python reproduce/verify_p2_dose.py`
* **Record**: `reproduce/P2_DOSE_VERIFICATION.txt`

Each condition holds 20 episodes (10 seeds × 2 stacks), i.e. 80 episode reports across the
four conditions. The eight means in appendix I.2 reproduce exactly, including the
non-monotone detail it discusses (rule-rl falls 0.833 → 0.670 from mask1 to strong while
llm-rl rises 0.710 → 0.750).

### 1.4 Appendix I.5a — natural-failure pilot, HF cases (seeds 5101–5112)

* **Data**: `data/campaigns/e5-hifi-attribution-r3/`, `e5-hifi-attribution-r3b/`
* **Coverage**: all 12 seeds present in `plan.json`, `plan-input.json`
* **Note**: `e5-hifi-attribution-r3b` also carries the 12-case counterfactual evidence.

### 1.5 Appendix I.5b — natural-failure pilot, grid cases (seeds 5201–5212)

* **Data**: `data/campaigns/e5-grid-natural-failures/e5_grid_summary.json`
* **Coverage**: all 12 seeds present

### 1.6 Appendix I.5 — human annotation agreement (Cohen's κ, blind IDs E5-01…E5-12)

* **Data**: `data/campaigns/e5-annotation-final/` (`kappa_summary.json`, `selection.json`)
* **Note**: the **answer key is deliberately withheld** — see `PENDING.md` §1b. The
  κ = 0.25 result is only meaningful while the key stays unpublished.

### 1.7 Appendix K — E1 headroom calibration and confirmation

* **Data**: `data/collaborator_runs/E1_partial-direction_split_p01_20261003/` (calibration
  4101–4110, gate 4151–4160), `E1_combined_confirmation_p01_20261004/` and
  `E1_confirm_device-a_p01_20261004/` (confirmation 4201–4210)
* **Coverage**: all three seed blocks complete (10/10 each)
* **Note**: appendix K describes 960 calibration episodes, 120 confirmation episodes,
  device-a on 17/18 and device-b on 19/27 — all four quantities are present.

### 1.8 `figA1_model_invariance` — four-model scan

* **Data**: `data/campaigns/e6-model-invariance/` — `analysis/e6_analysis.json`,
  `analysis/per_case.csv`, `plan.json`, `plan-10seeds.json`, plus per-run episodes
* **Coverage**: present, including the per-case table behind the figure.

---

## 2. Partially covered

### 2.1 Appendix I.4 — anchored critical-fault validation (seeds 561–570)

* **Present on this machine**: `server-experiments/g1-fault-dose/` (1,556 files, 94 MB)
  holds `complex-baseline/clean/seed-561 … seed-570` plus the injection conditions
  (`complex`, `full`, `opps`, `pilot`, `probe`, `replaygate`, `smoke`).
* **Not in the repository**: the tree is listed in `EXTERNAL_DATA_MANIFEST.json` rather
  than committed, to keep the clone small.
* **What is missing**: nothing evident; the batch appears complete locally. Promoting it
  into `data/` would close this row.

### 2.2 Appendix G — "intelligence-regime ablation" (`tab:nointel`)

**Updated after an exhaustive search of both servers — see
[`SERVER_SEARCH_RECORD.md`](SERVER_SEARCH_RECORD.md) §A.**

* **Present**: the no-intelligence arm. `tab_hifi_main`'s 70 episodes per stack are the
  withheld-regime runs, and the no-intel column of the ablation (0.774 / 0.783 / 0.431)
  matches the baseline column of the main table.
* **Also present, newly located**: the **legacy (declared-intelligence) episodes** — 795
  of them, in `~/openmd_private_archive/declared_briefing_snapshot_20260927_1419/`, the
  archive written by `_w1_snapshot_declared.ps1` just before the withheld switch.
* **But not the paper's subset**: the archive yields 79 / 135 / 82 episodes for
  LLM+Rule / LLM+RL / pure-LLM, whereas the table reports n = 82 / 49 / 40. The means come
  close (0.756 vs 0.769; 0.778 vs 0.782; 0.542 vs 0.516) but the counts do not agree, so
  the exact Δ column and "better on k/14" counts are **not reproducible as published**.
* **To close it**: recover the seed filter from `_w1_declared_delta.py` /
  `_w1_declared_vs_withheld.py`, or regenerate the table from this archive and update the
  appendix to the values that yields.

Two further observations a reviewer should know:

1. The appendix carries this table **inline** (labelled `tab:nointel`, appendix.tex
   ~line 220) while a separate `paper/tables/tab_hifi_nointel.tex` also exists. The two
   **do not agree**: the file version reports LLM+Rule legacy 0.753 / no-intel 0.774, the
   inline version reports legacy 0.769 / no-intel 0.790. The inline copy is the one the
   manuscript compiles; the file copy appears to be a stale earlier extraction.
2. The two regimes have **unequal n** (70 vs 82/49/40) and different seeds, so the
   contrast is not paired. The appendix does not claim it is.
3. **Parsing trap**: the archive's LLM+RL episodes report
   `defender.planner.planner == "llm"` in the body — the body names the *planning* layer.
   Trusting it folds all 135 LLM+RL episodes into LLM+Rule. Use the filename prefix
   (`ie_llmrl_…`) as the arm tag for this archive.


---

## 3. Absent — figure ships, source data does not

### 3.1 `figA2_replanning_sweep.pdf`

No plotting data anywhere in this repository or on **either** server — no file or directory
whose name contains `replan` or `sweep` exists on the local machine, on the user's server
(`hr-a6000-129-57`) or on the co-author's (`hr-a6000-129-51`). The figure is not referenced
by an appendix section in `appendix.tex`.

### 3.2 Appendix I.3 — real-stream counterfactual (seeds 601–610) and `tab_p3a_seedgrid`

* **Absent from every host.** Confirmed by content search on both servers.
* **Warning for a reader**: seeds 601, 602, 603, 605, 607 *do* appear — in the co-author's
  **E3 deception-detection** predictions (`p0-strengthening-20261001/results/E3*/`), which
  are `p_real` classification records, **not** the stream-versus-hold utility contrast this
  section reports (+0.420, 95% CI [0.200, 0.637]). The seed range is reused by an unrelated
  experiment, so matching on seed alone would mis-attribute them.

### 3.3 Appendix I.4's degradation accounting and the figA4 source data

* The `figA4_natural_failure_pilot` figure's underlying 12-case table is printed inline in
  the appendix (`tab:e5pilot`) and the per-case machine labels are in
  `e5-hifi-attribution-r3b/`, but there is no JSON holding the ΔP/ΔE/ΔI values for the 12
  cases as a single table.

---

## 4. Coverage of the four independent batches

Appendix I states the four batches are independent and must not be pooled. Their status:

| Batch | Seeds | Status |
|---|---|---|
| I.1 six-arm accounting | 501–510 | **present, verified** (0/60 cells differ) |
| I.2 goal-dose | 512–521 | **present, verified** (0/8 means mismatch) |
| I.3 real-stream counterfactual | 601–610 | **absent** |
| I.4 anchored critical-fault | 561–570 | on disk (`server-experiments/g1-fault-dose`), not committed |

---

## 5. Reproducing these checks

```bash
export PYTHONPATH="$PWD/code/analysis:$PWD/code/engine"
python reproduce/verify_paper_table.py    # tab_hifi_main      70/70 exact
python reproduce/verify_p1_grid.py        # tab_p1_seedgrid    0/60 differ
python reproduce/verify_p2_dose.py        # appendix I.2       0/8 mismatch
```
