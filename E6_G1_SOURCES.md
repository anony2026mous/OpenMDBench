# E6 and G1 — the real source data, checked against the paper

Both experiments are **fully sourced**. Earlier notes in this repository claimed E6's
MiniMax half was missing and that G1's data did not reproduce; both claims were wrong, and
this file records what is actually there.

---

## E6 — model-invariance scan (four models)

### Where it is

`code/role_c_toolkit/artifacts/`, from the co-author's tarball:

| Batch | Models | Files |
|---|---|---|
| `paper-E6-model-invariance/` | Qwen3.8-27B, Qwen3-8B | `analysis/e6_analysis.json`, 58 records |
| `paper-E6b-thirdparty-ablation/` | MiniMax-M3, MiniMax-M2.7-highspeed | 233 files, 3.6 MB |

`E6_family_overview.md` names both batches and states explicitly that they are **juxtaposed,
never pooled** (different output caps 1024 vs 8192, local vLLM vs third-party API, thinking
switch on vs off).

### Does it match the paper?

**Yes, exactly.** `E6_family_overview.md` §3 gives per-seed ΔV for all four models; its
means reproduce the paper's row `strong − hold` to ≤0.0015:

| Model | Overview per-seed mean | Paper | n |
|---|---|---|---|
| Qwen3.8-27B | +0.431 | **+0.431** | 13 (3 ref.) |
| Qwen3-8B | +0.464 | **+0.464** | 13 (3 ref.) |
| MM-M3 | +0.312 | **+0.313** | 10 (3 ref.) |
| MM-M2.7-highspeed | +0.449 | **+0.450** | 10 (3 ref.) |

The deployment-deficit row also matches: −0.433 / −0.200 / −0.422 / **+0.022** — including
the paper's boundary finding that MM-M2.7-highspeed reaches parity with pure RL
(CI [0.000, 0.067]).

The overview additionally records what the paper only summarises:

* **MM-M2.7-highspeed was NOT asked to disable thinking and emitted 184 thinking blocks
  across 20 cases.** That is a real confound on the one model that fails the deployment
  criterion, and the appendix does not mention it.
* MoE scale carries two variables at once (428B/A23B and 230B/A10B vs dense 8B/27B), so the
  table cannot support a parameter-scale monotonicity claim — the appendix says this too.

### One caution about the per-seed table

Its first three entries are **out of order**: the overview lists seed 301's ΔV as 0.00 and
303's as 0.80, whereas the analysis file gives 301 → +0.800 and 303 → +0.733. Seeds 4–13
match in order. The **mean is unaffected** (0.431 either way, since the values are
permuted, not changed), but do not read that column as seed-ordered.

### Status

`tab:modelinvariance` is **reproducible**. Regenerate with
`reproduce/verify_e6_four_models.py`.

---

## G1 — tiered fault-injection recovery (= what appendix I.4 describes)

### Where it is

Complete, and already inside this bundle as `data/g1-fault-dose/`:

| Artefact | Location |
|---|---|
| Full batch, **110 episodes** (10 clean + 10 seeds × 2 fault classes × 5 doses) | `data/g1-fault-dose/full/` |
| complex-tier rescue attempt | `data/g1-fault-dose/complex/` |
| pilot (2 seeds) | `data/g1-fault-dose/pilot/` |
| replay gate | `data/g1-fault-dose/replaygate/` |
| criterion result | `data/g1-fault-dose/{full,complex}/criterion_check.json` |
| dose response | `data/g1-fault-dose/{full,pilot}/dose_response.json` |

Source code, all present in `code/role_c_toolkit/`: `g1_dose_response.py`,
`g1_criterion_check.py`, `g1_pilot_report.py`, `grid_fault_replay.py` (the injector),
`grid_rolec6_counterfactual.py` (the reference).

### What G1 actually concluded

`e5_ascii/G1_final_report.md` is the final report. Its verdict, in its own words:

> **判据 2 不可达成** … 建议按清单第 44 行终止 G1，论文维持现状（无风险）
> … `5/5 graded faults` 表述已删除，无任何风险。**不补入任何「分级恢复」声明。**

The primary criterion (dose-response monotonicity: ≥4/5 adjacent tiers consistent **and**
both extreme tiers' 95% CI excluding zero) was **not met by any carrier**, on either
difficulty tier. I re-derived the profiles independently and they match the report exactly:

* medium `planner_wrong_contact` / V: 0.853 → 0.853 → 0.923 → 1.000 → 0.750
* complex `planner_wrong_contact` / V: 0.557 → 0.423 → 0.493 → 0.367 → 0.373

Both show 2/4 adjacent consistency and 0/2 extreme-CI exclusion — the same numbers the
report prints. Its mechanistic reasons: the planner fault merely *perturbs* (the executor
walks on and the mission often still succeeds), and the executor reference is substituted
on **frozen goals**, so `dE ≡ 0` by construction.

### But the paper prints loss figures

Appendix I.4 states:

> planner-side injection costs **0.567** score / 0.7 success / 0.7 extra port breach (10 seeds);
> executor-side injection costs **0.327** score / 0.4 success / 0.4 extra breach

**Those numbers are in neither the report nor the batch.** Searching the whole
`g1-fault-dose` tree for `0.567` and `0.327` returns one individual episode file and my own
README — no aggregate. Recomputing from the 110 episodes gives:

| | planner side | executor side |
|---|---|---|
| per-tier ΔV range (complex) | −0.080 … +0.110 | −0.077 … +0.230 |
| pooled ΔV (all tiers) | **+0.034** | **+0.035** |
| paper | 0.567 | 0.327 |

The pooled figures are ~1/16 of the published ones, and the sign is frequently inverted
(injection often *raises* V, because 6/10 clean seeds on medium are already at the 1.000
ceiling and the planner fault only causes wandering).

**Conclusion:** G1's data and code are complete, and G1's real result is a documented
negative. Appendix I.4's published costs do not come from this experiment as it stands.
Either they trace to an earlier P3b-phase run, or the appendix's I.4 paragraph needs
rewriting to match what G1 actually found.

---

## Corrections to earlier notes in this release

| Earlier claim | Correction |
|---|---|
| "the two MiniMax MoE runs are in no searched tree" | They are in `paper-E6b-thirdparty-ablation/`, 233 files. Earlier searches missed `role_c_toolkit/artifacts/` because the batch names begin `paper-`, not `e6-`. |
| "E6 marked done but only half the data exists" | All four models exist; `tab:modelinvariance` is reproducible. |
| "G1's data is present but the experiment was never completed" | G1 **was** completed — pilot then full, 110 episodes, with a written final report. What it produced is a **negative result**, not a missing dataset. |
