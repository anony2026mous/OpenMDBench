# 实验 2（选项 1）：完整 2×2 —— headroom 档位 × 规划器分配规则

> **重要更正**：本文件早先把两臂描述为「规划信息多/少」，这是**错的**。
> 由逐局 `completion.json` 核实，两臂**剂量相同（均为 `dose=strong`）**，
> 差异是 **`greedy` 分配规则**：
>
> | 臂 | `config.dose` | `config.greedy` |
> |---|---|---|
> | `rule-strong-g1` | `strong` | **`true`** |
> | `rule-strong-g0` | `strong` | **`false`** |
>
> 因此本文件衡量的是**规划器的分配决策规则**，**不是信息量**。
> 真正的信息量检验在选项 2（`--dose strong` vs `--dose hold`），见合并报告。
>
> 数据：E1 campaign `bundle/data/gate-screening/`（已冻结，**本机数据，未新跑任何实验**）
> 判据：`report.json → layered_metrics.performance_v`
> 置信区间：seed-bootstrap 10000 draws（与 `d2_headroom.bootstrap_ci` 同口径）

---

## 1. 设计核实

| 检查 | 证据 | 结论 |
|---|---|---|
| 两臂是否同一规划器与执行器 | `completion.json` 显示两臂均为 `config.arm == "rule"` | ✅ |
| **两臂差异是什么** | `config.dose` 两臂**均为 `strong`**；`config.greedy` 分别为 `true` / `false` | ⚠️ **分配规则，非信息量** |
| 是否用了 LLM | `attempt_manifest.json` 的完整命令**无任何 LLM 参数** | ✅ **无 LLM** |
| 分配规则如何生效 | adapter 的 greedy 分支按最近接触重分配 `target_id` | ✅ 规划层决策规则 |

**结论**：这是**同一执行器下两种分配决策规则**的对照；它回答"决策形态值多少"，
不回答"信息量值多少"。

---

## 2. 2×2 结果

| 档位 | n | `greedy=true` | `greedy=false` | **差值** | 95% CI | 显著 |
|---|---|---|---|---|---|---|
| COUNT-IE-05-MULTI-AXIS-**N017** | 10 | 0.8912 | 0.7850 | **+0.1062** | [0.011, 0.256] | ✅ |
| COUNT-IE-05-MULTI-AXIS-N018 | 10 | 0.8544 | 0.8422 | +0.0122 | [−0.027, 0.047] | — |
| COUNT-IE-05-MULTI-AXIS-N019 | 10 | 0.8693 | 0.7773 | +0.0920 | [−0.007, 0.244] | — |
| COUNT-IE-05-MULTI-AXIS-**N027** | 10 | 0.8469 | 0.7482 | **+0.0987** | [0.014, 0.233] | ✅ |

**`greedy=false` 侧跨度：0.7482 – 0.8422，带宽 0.0940。**

**4 个档位全部为正差值，2 个显著** → **分配决策规则**确有约 +0.1 量级的稳定影响。

---

## 3. 交互效应（差中差）

| 比较 | 交互值 | 95% CI | 显著 |
|---|---|---|---|
| 最少 headroom（N027, 基线 0.7482） vs 最有（N018, 基线 0.8422） | **−0.0865** | [−0.221, +0.009] | **不显著** |

**所有 6 个档位对的敏感性检查**：

| 档位对 | 交互值 | 95% CI | 显著 |
|---|---|---|---|
| N027 vs N019 | −0.0067 | [−0.181, +0.187] | — |
| N027 vs N017 | +0.0075 | [−0.159, +0.202] | — |
| N027 vs N018 | −0.0865 | [−0.215, +0.010] | — |
| N019 vs N017 | +0.0142 | [−0.183, +0.202] | — |
| N019 vs N018 | −0.0798 | [−0.245, +0.029] | — |
| N017 vs N018 | −0.0939 | [−0.251, +0.008] | — |

**6/6 全部不显著**，且符号随配对变化（4 负 2 正）。

---

## 4. 判读（必须原样写进论文的部分）

### 4.1 得到的

- **分配规则效应方向一致且量级可观**：4/4 档为正，均值约 **+0.077**，最大 +0.106。
- **2/4 档的 95% CI 不含 0**，其中 N027 与 N017 均通过。
- 这说明**「用哪套分配规则」值约 +0.1**——决策形态在本族中确有可测代价。

### 4.2 没得到的，以及为什么

- **交互效应不显著**（−0.0865，CI 跨零），且对档位选择敏感（6 个配对从 +0.014 到 −0.094）。
- **根本原因在数据设计，不在分析**：4 个档位的 `greedy=false` 侧只覆盖 **0.094** 的带宽
  （0.748–0.842），既没有接近饱和的下界，也没有接近满分的上界。**带宽不足 → 交互无法被表达**。
- 竞争族的饱和场景（MD-TRK-004 = 0.9666）在**另一套任务与执行器**上，不能与这 4 档组成同一 2×2。
- **信息量本身不在本文件的检验范围内**：两臂剂量相同。信息量对照见选项 2。

### 4.3 一个反直觉的观察（如实报告，不下结论）

效应最大的两档（N027 +0.099、N017 +0.106）恰是 `greedy=false` 侧水平最低的档位；
效应最小的一档（N018 +0.012）是该侧水平最高的档位。
方向与"空间越小、分配规则价值越大"一致，但 **n=4 档不足以支撑该推断**，且 CI 宽。
**写作时必须标为观察，不能作为条件 (iii) 的证据。**

---

## 5. 论文可直接引用的措辞（诚实版）

> Holding the task family and the scripted executor fixed, switching the planner's assignment
> rule (nearest-contact greedy assignment versus the default planner assignment) changed utility
> in all four screened interceptor-count tiers, by +0.106 (95% CI [0.011, 0.256]), +0.012,
> +0.092 and +0.099 (95% CI [0.014, 0.233]); both arms received the same complete plan, so this
> quantifies the decision rule rather than the information supplied. The headroom interaction
> could not be resolved at this bandwidth: the four tiers' reference levels span only 0.748-0.842
> and none of the six pairwise difference-in-differences contrasts reached significance. The
> separate manipulation of planning information (complete versus degraded plan) is reported in the
> merged Experiment 2 report.

---

## 6. 逐 seed 原始值

见 `analysis/e1_2x2_option1.json` 的 `cells[].per_seed_supplied` / `per_seed_withheld` /
`per_seed_effect`（每档 10 个 seed，共 40 个 seed × 2 臂 = 80 局）。

## 7. 复算

```bash
cd role_c_toolkit
python e1_2x2_option1.py            # 读 E1 gate-screening，bootstrap 10000 draws
python e1_2x2_export.py             # 导出台账（CSV / MD / JSON）
```
