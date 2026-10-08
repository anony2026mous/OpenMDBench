# Who owns each data gap

Read off the team's own planning documents in `~/Downloads`, not inferred:

| Document | Owner | Latest |
|---|---|---|
| `OpenMDBench_实验强化清单_武昊_20261003_2128.md（v13…）` | 武昊 | v13, 10-03 |
| `OpenMDBench_实验强化清单_肖棹_20261003_2128.md（v10…）` | 肖棹 | v10, 10-03 |
| `OpenMDBench_实验强化清单_肖棹_20261004_1501.md（v11，E4完成）` | 肖棹 | v11, 10-04 |
| `OpenMDBench_实验清单_肖棹_20261007_1738.md` | 肖棹 | v1, 10-07 |
| `OpenMDBench_实验强化清单_20261002_1801（v4）` | 全体 | v4, 10-02 |

## The division of labour, as stated

**武昊 — 定律证据核心**
`E10 ✅ · E1 ⏳顺序执行中 · E2 ✅ · E11 ✅ · E14 ✅` / optional: `E12 ⏸`

**肖棹 — 平台泛化与诊断 + E1 承接**
`E4 ✅ · E5 ✅ · E6 ✅ · E13 ⏸ · G1 🆕待启动` / plus `E1 承接（数量 19/27）⏳`

## Gaps, with owners

| Gap in the release | Code | Owner | Status the documents state |
|---|---|---|---|
| **I.4** anchored critical-fault — numbers do not reproduce | **G1 分级注入故障-恢复校准** | **肖棹** | `🆕 待启动（先 pilot）` — never completed |
| **tab:modelinvariance** — ~~MM-M3 / MM-M2.7-hs absent~~ **RESOLVED** | **E6b 第三方模型消融** | **肖棹** | **found and in the bundle.** All four columns reproduce exactly: Qwen3.8-27B +0.431, Qwen3-8B +0.464, MM-M3 +0.313, MM-M2.7-hs +0.450, against the paper's +0.431 / +0.464 / +0.313 / +0.450. See finding 2 below. |
| **E13** positive-region model reproduction — never run | **E13 正区模型复现** | **肖棹** | `⏸ 可选，视时间线` |
| **E12** key-contrast seed extension (5→10) | **E12** | **武昊** | `⏸ 可选，视时间线` |
| **E1** confirmation tiers 19/27 | **E1 承接** | **肖棹** (transferred from 武昊) | `🆕 新增，待启动` |
| **tab:e5pilot** — 3 grid cases lack attribution records | **E5 自然故障盲归因 pilot** | **肖棹** | `✅ 完成` |
| **I.3** real-stream counterfactual (601–610) — ~~no data anywhere~~ **RESOLVED** | real-stream batch | 肖棹 | **found and now in the bundle.** Located on the co-author's server as `runs/p0-strengthening-20261001/inputs/P3a__llm_goal_causal__s601-610__confirm__v1` and verified 0/10 cell mismatches by `reproduce/verify_p3a.py`. It was missed because the seed range is reused by the E3 deception files; the batch is found by its intervention marker (`all_unit_goals_to_legal_hold`). |
| **tab:interface** — NL vs JSON modality | — | **unassigned** | see below |

## Three findings that matter

### 1. I.4's metric was never V — which is why the numbers did not reproduce

肖棹's 10-07 G1 design specifies the measurement:

> 输出：每档 **ΔP（规划）/ ΔE（执行）** 均值 + seed-bootstrap 95% CI；层定位在 goal/action 记录边界

I measured **mean V per dose tier** and could not reach 0.567 / 0.327. The experiment is
about **ΔP/ΔE per dose**, a different quantity. So the earlier "does not reproduce"
verdict is a statement about the wrong metric as much as about the data — and the honest
position is: *the batch is present, the experiment G1 was never completed, and the
published I.4 figures should be traced to whichever run produced them before being
trusted.*

The same document also confirms the dose tiers `{0.05, 0.10, 0.20, 0.40, 0.60}` and the
base (`grid medium / continuous, rule planner + heuristic executor`) — exactly the
structure found in `data/g1-fault-dose/`. The design and the data agree; the *result* was
never produced.

### 2. "E6 complete" is accurate — the MoE half ships as a separate batch

肖棹's lists mark E6 `✅ 完成` with `四模型 4/4`, and that is right, but the four models
are split across **two** batches that must not be pooled:

| Batch | Models | Where |
|---|---|---|
| `paper-E6-model-invariance` | Qwen3.8-27B, Qwen3-8B | `data/e6-sources/paper-E6-model-invariance/` |
| `paper-E6b-thirdparty-ablation` | MiniMax-M3, MiniMax-M2.7-highspeed | `data/e6-sources/paper-E6b-thirdparty-ablation/` |

An earlier version of this document reported the MoE half as unfindable. It was not
missing; it was filed under **E6b** rather than E6, which is why searching inside
`e6-model-invariance` found nothing, and the failure was compounded by a measurement
error of my own. Two things are worth recording:

1. **The four columns reproduce exactly** — `reproduce/verify_e6_four_models.py`:
   Qwen3.8-27B +0.431, Qwen3-8B +0.464, MM-M3 +0.313, MM-M2.7-hs +0.450 against the
   printed +0.431 / +0.464 / +0.313 / +0.450.

2. **Two genuinely different questions, do not merge them.** The batches differ by
   `max_tokens` (1024 for the dense pair, 8192 for the MoE pair, because M2.x cannot
   disable thinking and truncates at 1024), so the appendix's "juxtaposed and never
   merged" wording is a real constraint rather than a stylistic one. `E6_family_overview.md`
   states the same thing.

The boundary finding is also intact: MM-M2.7-highspeed reaches parity with pure RL
(+0.022, CI [0.000, 0.067]), so the headroom premise vanishes on that model.

### 3. ~~Two items are unassigned in every checklist~~ Both resolved

* **I.3 real-stream counterfactual (seeds 601–610).** Earlier text here concluded the
  batch had no data anywhere. That was wrong: it ships in this repository at
  `data/collaborator_runs/p0-strengthening-20261001/inputs/P3a__llm_goal_causal__s601-610__confirm__v1/`
  and reproduces 0/10 cell mismatches. The reason it was missed is worth keeping: **the
  seed range is reused** by `results/E3*/` deception-detection `p_real` records, so a
  search by seed finds the wrong experiment. The batch identifies itself by its
  intervention marker (`intervention.kind = "all_unit_goals_to_legal_hold"`), not by its
  seeds. `toolkit_finalize_seed601.py`'s `cancelled_seeds: [602, 603]` refers to a
  different, unrelated campaign.
* **`tab:interface` (NL vs JSON modality).** The experiment script exists —
  `code/collaborator_snapshot/ablation_nl_json.py`, headed "A3 natural-language interface
  ablation (Appendix D, grid-exclusive)" — and its outputs reproduce all three tiers
  (0/3 differing) via `reproduce/verify_modality.py`. It was simply never listed in a
  checklist; the 8/23 `experiment_guide.md` TODO that mentioned it was stale.

## What to ask whom

| Ask | Who |
|---|---|
| I.4 / G1 — is any run behind 0.567 and 0.327, and where? | 肖棹 |
| E13 batch, if the appendix's "positive-region model" claim is to stand | 肖棹 |
| The real-stream batch (601–610) and its owner | the PI / whoever kept the master checklist |
| Whether `tab:interface` was ever run, and under what code | the PI |
