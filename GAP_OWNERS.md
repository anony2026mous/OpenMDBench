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
| **tab:modelinvariance** — MM-M3 / MM-M2.7-hs absent | **E6 模型无关性扫描** (four models) | **肖棹** | `✅ 完成`, claimed `四模型 4/4` |
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

### 2. "E6 complete" covers only the dense half

肖棹's lists mark E6 `✅ 完成` with `四模型 4/4`. The bundle holds
`campaigns/e6-model-invariance` covering **Qwen3.8-27B and Qwen3-8B only**. The two
MiniMax MoE runs (MM-M3, MM-M2.7-hs) are in no tree that was searched, on either server.

Either they live somewhere not yet looked at, or the "4/4" refers to a result table whose
raw runs were never exported. Worth asking 肖棹 directly, because the appendix table prints
all four columns.

### 3. Two items are unassigned in every checklist

* **I.3 real-stream counterfactual (seeds 601–610).** The master checklist (v4, line 183)
  names the "four batches (six-arm / dose / **real-stream** / fault)" as forbidden to pool
  — so the batch is a known deliverable — but **no owner is recorded**. 肖棹's 10-07 list
  refers to `10/10 live LLM streams` as already done, so it predates these lists.
  Separately, `toolkit_finalize_seed601.py` shows seed 601 belonged to a `pure-llm`
  episode in a campaign **cancelled after seed 601** (`cancelled_seeds: [602, 603]`),
  which may be why seeds 602–610 have no episodes anywhere.
* **`tab:interface` (NL vs JSON modality).** No checklist mentions an interface-modality
  experiment at all. `main.tex` 332 lists three "rescue channels" — information injection,
  replanning frequency, interface modality — and only the frequency one (**E7**) has a
  checklist entry.

## What to ask whom

| Ask | Who |
|---|---|
| I.4 / G1 — is any run behind 0.567 and 0.327, and where? | 肖棹 |
| The two MiniMax MoE runs for `tab:modelinvariance` | 肖棹 |
| E13 batch, if the appendix's "positive-region model" claim is to stand | 肖棹 |
| The real-stream batch (601–610) and its owner | the PI / whoever kept the master checklist |
| Whether `tab:interface` was ever run, and under what code | the PI |
