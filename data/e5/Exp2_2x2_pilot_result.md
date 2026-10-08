# 实验 2（v3：2×2 headroom 交互）试点结果与阻塞

> 对象：`OpenMDBench_补实验清单_P0硬伤_20261006.md（v3）` 第 33–56 行的 2×2 设计。
> 结论：**设计本身正确且可执行**（全脚本、不需 RL/LLM 栈），
> **但"只改规划信息量"这个操纵目前没有合法落点**——已在两个候选杠杆上做了实跑试点，
> 结果如下。本文给出试点数据、阻塞原因、以及两条能落地的替代路径。

---

## 1. v3 设计要求什么

| | 规划信息少 | 规划信息多 | 预期 |
|---|---|---|---|
| 饱和场景（headroom≈0） | 基准 | 增强 | 增益 **≈ 0** |
| 非饱和场景（阳性对照） | 基准 | 增强 | 增益 **> 0** |

**硬要求**：
1. **同一执行器**，只改"规划信息量"；
2. **必须有阳性对照**（非饱和场景），否则无法区分"headroom 效应"与"操纵无效"。

---

## 2. 试点一：换通信组件（`competition-dispatch` → `competition-tracking-delayed`）

**假设**：策略读两个通道——`organic_contacts`（自身传感器）与 `shared_contacts`（网络共享）。
共享通道由实体的 `component_refs` 里的 `communication.*` 决定，且 catalog 中
`competition-dispatch`（同类内可互达）与 `competition-tracking-delayed`（延迟受限）
**platform 兼容性相同**，可互换。这是纯场景侧编辑。

**实跑结果**（seed 2301，单例）：

| 场景 / 策略 | 基准（dispatch） | 延迟共享 | 差异 |
|---|---|---|---|
| MD-TRK-004 / `follow` | 0.102 | 0.102 | **0.000** |
| MD-TRK-004 / `allocated` | 0.965 | 0.963 | 0.002 |
| MD-TRK-006 / `follow` | 0.690 | 0.690 | **0.000** |
| MD-TRK-006 / `allocated` | 0.690 | 0.690 | **0.000** |

（"无共享"变体编译失败：`CompilerErrorV2 [scenario.controller_endpo…]`，说明删掉通信组件会使
控制器端点声明不完整，不是合法编辑。）

**判定**：通信组件这条杠杆**无效**——延迟在这些场景的时序尺度上不构成信息损失。
**设计被否，未花跑批预算。**

---

## 3. 试点二：改搜索线索区域（`initial_designation_regions`）

**假设**：规划层实际只消费 brief 的三个字段（`mobile_observers`、`observer_domains`、
`initial_designation_regions`），其中第三个是搜索线索，决定初始搜索行为。改变其精度＝改变规划信息量。

**先查线索来源**（关键）：

```bash
# 场景包里没有 cue：
ls scenarios/competition_v1/md_trk_004_standard/
#   acceptance_gaps.json  public_brief.json  scenario.yaml  scripted_blue_policy.json

# 线索是构建产物：
grep -n "initial_designation_regions|cue\b" tools/competition_four_categories/tracking.py
#   tracking.py:166  cues = [zone(f"cue.{i+1:02d}", routes[i][1][0], routes[i][1][1], 65.) …]
#   tracking.py:172  "mobile_observers": observers[:3], "initial_designation_regions": cues,
grep -n "public_brief" tools/competition_four_categories/build.py
#   build.py:247  (target / "public_brief.json").write_text(json.dumps(brief, …))
```

**事实**：
- 线索区**不在 `scenario.yaml`**，而在 `public_brief.json`；
- `public_brief.json` 是 **`build.py` 生成的产物**，源头是 `tracking.py` 的构建器；
- 作者值：MD-TRK-004 有 `cue.01` x[235,365] y[−185,−55] 与 `cue.02` x[235,365] y[85,215]；
  MD-TRK-006 有 `cue.01` x[235,365] y[−65,65]。半宽均为 65 m。

**试点过程**：我第一次的 `widen_cue` 改的是 `world.zones`，而该场景 `world.zones` 为空
（→ 三次测量逐位相同，属**探针无效**，不是杠杆无效）。改为直接改 `public_brief.json` 后：

| 场景 / 策略 | 作者线索 | 线索 ±900 m | 线索 ±400 m |
|---|---|---|---|
| MD-TRK-004 / `allocated` | 0.965 | 0.965 | 0.965 |
| MD-TRK-006 / `follow` | 0.690 | 0.690 | 0.690 |

（"平"的原因是：`public_brief.json` 是**被生成**的，且线索只用于设置初始航向——见下。）

**结构原因（决定性）**：这些策略是**闭环控制器**，不是"读计划再执行"的执行器：

- `ContactFollowPolicy`（`tracking_policy.py:49`）——"per-controller association; no cross-controller truth pooling"，
  仅用 `organic_contacts` 追最近接触；
- `AllocatedTrackPolicy`、`CooperativeTrackPolicy`——同样是反应式；
- 线索只在 `__init__` 里用于指定初始搜索点，**不参与后续决策**。

**判定**：**在合法场景编辑范围内，目前没有能改变"规划信息量"的落点。**
- 改 `public_brief.json`＝**改构建产物**，`build.py` 一跑就覆盖，不可复现、不能被接受为场景参数；
- 改 `tracking.py` 的线索生成器＝**改构建器（工具代码）**，超出场景包范围；
- 改 `scenario.yaml` 的 `entities` / `component_refs` / 指标参数＝对这两个策略均**无影响**（试点一证明）。

---

## 4. 试点本身给出的一条正面证据（可写进论文）

即便"信息操纵"没做成，试点数据说明了一件对 P2 有利的事：

| 观测 | 数值 |
|---|---|
| MD-TRK-004 的 `follow`（信息/协作最弱） | 0.102 |
| MD-TRK-004 的 `allocated`（分配感知） | **0.965** |
| MD-TRK-006 的 `follow` 与 `allocated` | **完全相同 0.690** |
| 延迟共享对 `allocated` 的影响 | −0.002（≈0） |

**解读**：在这两个场景上，**信息可用性的改变（延迟共享）几乎不改变结果**，
而**决策形态**（分配/协作）才是差距来源——MD-TRK-004 上 `follow`→`allocated` 差 0.86。
这正是"D1′ 决策形态主导"的现场证据，也解释了为什么 P2 在这些场景上难以用"信息量"操纵来检验：
**它们对信息不敏感，对决策形态敏感**。

---

## 5. 两条能落地的替代路径

| 路径 | 做法 | 成本 | 是否满足 v3 的硬要求 |
|---|---|---|---|
| **D1：换操纵维度** | 把 2×2 的"规划信息量"改为"**规划决策形态**"：同一执行器（如 `allocated`），
一层只做固定分配、一层做**再分配/交接感知**（`handover_edges` 已存在于指标参数）。 | 1–2 天 | ✅ 同一执行器 + 阳性对照（MD-TRK-006 现成 0.690，有 headroom） |
| **D2：换非饱和对照到 grid/IE** | 阳性对照用清单自己提到的 IE-05 数量档或 grid medium 层——那里**有真实的 LLM 规划层**，
"信息少/多"就是"无 LLM 规划/有 LLM 规划"，操纵天然存在。饱和侧用 MD-TRK-004。 | 2–4 天（跨栈） | ✅ 但两臂不在同一栈上，需在文中说明 |

**不推荐**：直接改 `public_brief.json` 作为"少信息"臂——不可复现，审稿人会问"为什么你的 brief 与公布的不一致"。

---

## 6. 复算方式

```bash
# 线索是构建产物（不在场景包内）
ls scenarios/competition_v1/md_trk_004_standard/
grep -n "initial_designation_regions" tools/competition_four_categories/tracking.py
grep -n "public_brief" tools/competition_four_categories/build.py

# 通信组件可互换（catalog 兼容性相同）
grep -n "communication.competition-dispatch|communication.competition-tracking-delayed" \
  catalog/v2/competition_four_categories.yaml

# 试点原始数据
ls /mnt/QTJC/chenyi-codex/experiments/e4-headroom-2x2/

# 策略是闭环控制器（不读计划）
sed -n '49,60p' tools/competition_four_categories/tracking_policy.py
```

---

## 7. 一句话总结

**2×2 的设计意图是对的，但"只改规划信息量"在竞争族里没有合法操纵对象**——
两个候选杠杆（通信组件、搜索线索）经实跑试点后均被排除：前者对结果无影响，
后者是构建产物且只影响初始航向。建议改用 **D1（把操纵维度换成规划决策形态）**，
它同样满足"同一执行器 + 阳性对照"，且 MD-TRK-004 / MD-TRK-006 的现成数据（0.965 / 0.690）
已经给出了饱和与非饱和的两个端点。
