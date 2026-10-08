# 实验 2（选项 2）：族内 2×2 与饱和档定位

> **设计**：同一任务族（IE-05 多轴）、同一脚本执行器（`--planner rule`），
> 只改变**规划信息**。提供信息臂＝`--dose strong`（规划器输出完整目标参数，
> 经 `episode_adapter.py` 原样提交）；信息残缺臂＝`--dose hold`（目标被改写）。
> `attempt_manifest.json` 无任何 LLM 参数，`completion.json` 记录 `arm=rule`。
>
> **数据**：本轮在服务器上用合作者交付的 runner 新跑，seed 64101–64105，
> **不与既有 4151–4160 批次合并统计**。

---

## 1. 饱和档定位：32 档基线扫描

在全部 32 个已发布档位上以基线条件各跑 1 局，**据证据**而非假设选档：

| 档位 | 扫描 V |
|---|---|
| `p0count_ie_09_staggered_waves_n007` | 1.0000 |
| `p0count_ie_05_multi_axis_n013` | 0.9692 |
| `p0count_ie_05_multi_axis_n016` | 0.9625 |
| `p0count_ie_09_staggered_waves_n006` | 0.9600 |
| `p0count_ie_05_multi_axis_n014` | 0.9429 |
| … | … |
| `p0count_ie_05_multi_axis_n017` | 0.1922 |
| `p0count_ie_05_multi_axis_n026` | 0.1718 |

最高 **1.0000**（`p0count_ie_09_staggered_waves_n007`），最低 0.1718。**族内确有接近饱和的档位**——
既有 4 档（N017/018/019/027）恰好落在中段，这是选项 1 带宽不足的原因。

---

## 2. 配对 2×2（同 seed，5 档 × 5 seed）

| 档位 | 扫描 V | n | 信息完整 | 信息残缺 | **效应** | 95% CI | 显著 |
|---|---|---|---|---|---|---|---|
| `COUNT-IE-05-MULTI-AXIS-N027` | 0.7444 | 5 | 0.7841 | 0.1648 | **+0.6193** | [+0.584, +0.654] | ✅ |
| `COUNT-IE-05-MULTI-AXIS-N018` | 0.9111 | 5 | 0.8733 | 0.1722 | **+0.7011** | [+0.650, +0.743] | ✅ |
| `COUNT-IE-05-MULTI-AXIS-N016` | 0.8400 | 5 | 0.8467 | 0.1750 | **+0.6717** | [+0.607, +0.737] | ✅ |
| `COUNT-IE-05-MULTI-AXIS-N013` | 0.9692 | 5 | 0.9149 | 0.1808 | **+0.7341** | [+0.670, +0.782] | ✅ |
| `COUNT-IE-05-MULTI-AXIS-N009` | 0.7644 | 5 | 0.9200 | 0.1944 | **+0.7256** | [+0.666, +0.782] | ✅ |

**5/5 档位效应显著为正**，量级 +0.62 ～ +0.73。

---

## 3. 交互效应与一个必须承认的问题

按「提供信息臂实现水平」切分：低档 `COUNT-IE-05-MULTI-AXIS-N027`、高档 `COUNT-IE-05-MULTI-AXIS-N009`，
**交互 = +0.1063，95% CI [+0.0382, +0.1722] → 显著**。

**但这不是干净的 headroom 因果证据**，原因有三，必须随结论一起报告：

1. **参考臂不携带档位信息**：各档位残缺臂均为 0.1648–0.1944，且**对 seed 完全不敏感**——它是结构性塌陷，不是难度指纹。
2. **扫描 V 不支持分组**：被分到两端的档位扫描 V 几乎相同（0.7444 vs 0.7644），因此分组并非由预注册的难度差决定。
3. **方差来源单一**：残缺臂为常数，全部种子级方差来自提供信息臂，故该交互只能作为**描述性**结果，显著性依赖提供信息臂自身的种子离散度。

**Hedges 式提醒**：按自身结果分组再比较，会放大效应量。本报告的 CI 已按supplied arm only; the withheld arm is seed-invariant so it contributes no seed-level variance计算，但仍不能替代预注册分组。

---

## 4. 操纵机制的实测刻画（本轮最有价值的发现）

为判断「信息量」是否可做成梯度，单独做了粒度探针（N013 / seed 64101）：

| 条件 | V | 说明 |
|---|---|---|
| 原生 runner（无转换） | 0.9692 | 参照 |
| `--goal-granularity medium` | 0.9692 | `unit_id`+`target_id` |
| `--goal-granularity weak` | 0.1808 | 仅 `unit_id` |
| 适配器 `--dose strong` | 0.9692 | 完整参数（与原生一致 → **路径无混淆**）|
| 适配器 `--dose hold` | 0.1808 | 目标改写 |

**结论**：

1. **路径无混淆**：原生 runner 与适配器 strong 在同一档同一 seed 上均为 0.9692。
2. **`medium` 与完整参数数值完全相同**——删掉 `position`/`speed`/`pattern`/`constraints`
   不影响结果，因为执行器只需要 `target_id`。
3. **粒度开关实际是二值的**：一旦 `target_id` 缺失，执行器即瘫痪（约 0.18）。
   因此「规划信息」在本族中的真实杠杆是**计划可用 vs 计划残缺**，
   而非连续的信息量梯度。

---

## 5. 对实验 2 目标的结论

| v3 要求 | 本轮结果 |
|---|---|
| 同一执行器，只改规划信息 | ✅ 已满足并验证（`arm=rule`，无 LLM，路径一致）|
| 阳性对照（操纵有效性）| ✅ 5/5 档位效应显著为正（+0.62 ～ +0.73）|
| 饱和 vs 非饱和两行 | ⚠️ 残缺臂在各档位均塌陷，**无法提供可解释的 headroom 两行** |
| 交互效应及 95% CI | ⚠️ 已算出（见 §3），但分组非预注册，只能描述性报告 |

**净结论**：本族内**规划信息操纵有效且量级很大**，但其操纵对象是
「计划是否可用」，因此在 headroom 方向上**不可分辨**——
条件 (iii) 的因果证据仍须由 §6.7 的跨族对比承接，
而本轮为 §6.7 提供了一个新的事实：该族的 headroom 轴无法承载信息量操纵。

---

## 6. 逐 seed 原始值

见 `option2_result.json` 的 `cells[].per_seed_strong` / `per_seed_reference` / `per_seed_effect`（每档每臂 5 seed）。

## 7. 复算

```bash
cd role_c_toolkit && python e1_2x2_option2.py
```

---

## 附录 A. 覆盖范围与出处（逐项可核对）

### A.1 本轮实际执行的局数

| 批次 | 档位 | 臂 / 条件 | seed | 局数 |
|---|---|---|---|---|
| 饱和档定位扫描 | 全部 32 档 | 基线（`--planner rule`，无剂量干预） | 64101 | 32 |
| 配对 2×2 | 5 档（N009/N013/N016/N018/N027） | `--dose strong` 与 `--dose hold` | 64101–64105 | 50 |
| weak 臂（机制对照） | 同上 5 档 | `--goal-granularity weak` | 64101–64105 | 25 |
| 粒度探针 | N013 | 原生 / `medium` / `weak` | 64101 | 3 |
| **合计** | | | | **110** |

### A.2 原始数据位置

- 服务器根目录：`/mnt/QTJC/chenyi-codex/experiments/e4-headroom-2x2/P1/`
  - `scan/<package>/`：每档 `report.json`（完整结果 JSON）、`episode.jsonl`（过程日志）
  - `paired/<tier>/<dose>/seed-<n>/`：`report.json`、`episode.jsonl`、
    `action_batches.jsonl`、`defender_states.jsonl`、`stdout.log`、`stderr.log`
  - `granprobe/{none,medium,weak}/`：粒度探针三局
- 交付材料（合作者提供，哈希已全量核验 5077/5077 一致）：
  `…/E1_Exp2_option2_runner_materials_20261006_v1/unpacked/…`
- 分析产物（随本文件交付）：`analysis/e1_2x2_option2.json`

### A.3 判据字段

`report.json → layered_metrics.performance_v`，与既有 E1 证据同字段，故新旧可比。
每局的 `config.arm` / `config.dose` 记录在 `completion.json`，
命令原文在 `attempt_manifest.json`。

### A.4 本文件**未**声称的内容

1. **未与 4151–4160 批次合并**：本文件全部统计只用新跑的 64101–64105，
   旧批次仅作为环境一致性参照（如 N027 旧 0.7482 vs 本扫描 0.7444）。
2. **未把 weak 臂当作独立结果**：实测 weak 与 hold 逐格完全相同
   （总均值均为 0.1774，且对 seed 不敏感），故它只是**机制证据**，
   不构成第二组信息条件。
3. **未声称 headroom 因果**：见正文 §3 的三条限制。
4. **未做跨族合并**：竞争族饱和档（MD-TRK-004 = 0.9666）与本族结果
   分属不同任务与执行器，未合成任何单一统计量。

### A.5 粒度探针的完整取值（可复算）

| 条件 | V |
|---|---|
| 原生 runner（无转换） | 0.9692 |
| `--goal-granularity medium` | 0.9692 |
| `--goal-granularity weak` | 0.1808 |
| 适配器 `--dose strong` | 0.9692 |
| 适配器 `--dose hold` | 0.1808 |

适用边界：这是**单一档位（N013）单一 seed（64101）**的探针，
用于确定操纵机制的量级与是否存在中间档；不是跨档位的分布结论。
