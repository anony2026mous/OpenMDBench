# 论文方法架构图 —— 绘图规范文档（交付给绘图模型 / image2.5）

> 用途：为论文补充**方法架构图**。本文档只描述"画什么、怎么画、写什么字"，
> **不涉及任何实验内容的改动**，也不需要重新跑任何实验。
> 使用方式：把 §1（全局样式）+ §2（一览）+ 需要的那一张图的 §3.x 小节整段粘给绘图模型；
> 每张图末尾都附了一段**可直接粘贴的英文提示词**（图像模型对英文提示更稳），
> 并给出**精确文本串清单**（避免模型把标签拼错）。

---

## 0. 交付清单（建议出图 10 张，可按需取舍）

| 图号 | 标题 | 类型 | 优先级 |
|---|---|---|---|
| Fig. 1 | 六种方法的架构总览与因子设计 | 总览网格图 | ★★★ 必备 |
| Fig. 2 | 两级决策链骨架与接口 | 分层数据流图 | ★★★ 必备 |
| Fig. 3 | `rule-rule`：规则规划 + 规则执行 | 架构图 | ★★ |
| Fig. 4 | `llm-rule`：LLM 规划 + 规则执行（混合 A） | 架构图 | ★★★ |
| Fig. 5 | `rule-rl`：规则规划 + RL 执行（消融诊断） | 架构图 | ★★ |
| Fig. 6 | `llm-rl`：LLM 规划 + RL 执行（混合 B / 本文方法） | 架构图 | ★★★ 必备 |
| Fig. 7 | `rl`：纯强化学习（端到端策略） | 架构图 | ★★★ |
| Fig. 8 | `pure-llm`：纯大模型（直接输出动作） | 架构图 | ★★★ |
| Fig. 9 | RL 执行层的观测张量分解（3570 维） | 技术示意/条形分解图 | ★★ |
| Fig. 10 | RL 执行层的训练—评测同构流程 | 泳道流程图 | ★★ |

---

## 1. 全局样式约定（所有图统一，保证论文内一致）

### 1.1 画布与风格

* 纯白背景，**扁平矢量风**（flat vector），细描边（1–1.5 px），**不要**拟物、渐变、阴影、3D 透视。
* 字体：无衬线（Helvetica / Arial / Roboto 类）；图中的类名/变量名用**等宽字体**（Consolas / SF Mono / Roboto Mono）。
* 图内文字**只用简洁英文标签**（见 §4 对照表），中文只出现在图题里，由排版软件另加。
* 留白充足，节点边框圆角 4 px；同一层级的节点**同高对齐**。

### 1.2 统一的层级配色（全篇同义同色）

| 逻辑层 | 建议颜色 | 说明 |
|---|---|---|
| 仿真引擎 / 环境（Environment） | 浅灰 `#ECECEC` + 深灰边 | 客观世界：传感器、通信、战斗、毁伤、判决、计分 |
| 观测（Observation） | 浅蓝 `#D6E9F8` | 阵营级、不可变快照 |
| **规划层**（Planning Layer） | 浅绿 `#D9EFD6` | 产出"目标/意图" |
| — 其中 规则规划器 | `#D9EFD6` 实线边 | |
| — 其中 LLM 规划器 | `#D9EFD6` + **双线边** | 双线边 = 由大模型驱动 |
| 目标协议 / 仲裁（Goal Protocol & Broker） | 浅黄 `#FBEFCB` | 目标命令与其生命周期 |
| **执行层**（Execution Layer） | 浅橙 `#FBE0CE` | 把目标变成"每个平台的速度/航向/开火" |
| — 其中 规则执行器 | `#FBE0CE` 实线边 | |
| — 其中 RL 执行层 | `#FBE0CE` + **粗边** | 粗边 = 可学习（神经网络） |
| 动作 / 指令（Actions） | 浅紫 `#E3DAF3` | 持久指令 + 离散动作 |

### 1.3 连线语义（重要：不同线型必须含义固定）

* **实线箭头** = 数据/控制流，箭头旁标注频率或形状。
* **虚线箭头** = 回退路径（fallback）或诊断/旁路。
* **双线箭头** = 大模型调用（上游→下游）。
* **粗箭头** = 神经网络前向。
* 每条主线箭头**必须带一个标签**，三选一并全篇统一：
  `every tick` / `every 5 ticks` / `every 10 ticks`。

### 1.4 图内必须出现的三个"尺寸常数"（技术准确性）

* `MAX_UNITS = 16`（可操控单元上限）
* `MAX_CONTACTS = 20`（同屏接触上限）
* `FIRE_CHOICES = 21`（0 = hold，1–20 = 第 j 个接触）

### 1.5 禁止项（避免画错）

* 不要把规划层画成神经网络；规划层是**符号/规则**或**大模型**。
* 不要把仲裁器（Broker）画成 LLM；它是**协议与优先级仲裁**，不含模型。
* 不要让 RL 执行层直接连到环境；它**输出动作**，动作经会话层进入引擎。
* 不要在 `pure-llm` 图里画"目标协议/Broker"框；该臂没有独立目标层。
* 不要在 `rl` 图里出现大模型图标（该臂无 LLM，无目标层）。

---

## 2. 六种方法一览（Fig. 1 的内容基础）

决策链是**两级**：**规划层**（产出目标） × **执行层**（产出每个平台的速度/航向/开火）。

| 方法（论文用名） | 规划层 | 执行层 | 角色 |
|---|---|---|---|
| **`rule-rule`** | 规则规划器 `RulePlannerV2` | 规则执行器 `GOAIExecutorV2` | 基线格 |
| **`llm-rule`** | **LLM 规划器** `LLMPlannerV2` | 规则执行器 `GOAIExecutorV2` | 混合 A |
| **`rule-rl`** | 规则规划器 `RulePlannerV2` | **RL 执行层** `RLExecutorV2` | 消融诊断 |
| **`llm-rl`** | **LLM 规划器** `LLMPlannerV2` | **RL 执行层** `RLExecutorV2` | 混合 B（本文方法） |
| **`rl`** | —（无目标层） | 端到端策略 | 单架构基线 |
| **`pure-llm`** | LLM 直接输出动作 | —（无执行器） | 单架构基线 |

**术语约定**：论文中统一写作 `<规划层>-<执行层>`；`rule-rule` 即"纯规则"，
`rl` 即"纯强化学习"，`pure-llm` 即"纯大模型"。

---

## 3. 逐图规范

### Fig. 1 —— 六种方法的架构总览与因子设计

**用途**：一张图说清"我们在消融什么"。

**版式**：左侧 2×2 网格 + 右侧两条"单侧"臂。

```
                     执行层 = 规则执行器            执行层 = RL 执行层
规划层 = 规则    ┌──────────────────────┐   ┌──────────────────────┐
                 │ rule-rule            │   │ rule-rl              │
                 │ RulePlannerV2        │   │ RulePlannerV2        │
                 │   + GOAIExecutorV2   │   │   + RLExecutorV2     │
                 └──────────────────────┘   └──────────────────────┘
规划层 = LLM     ┌──────────────────────┐   ┌──────────────────────┐
                 │ llm-rule   (Hybrid A)│   │ llm-rl     (Hybrid B)│
                 │ LLMPlannerV2         │   │ LLMPlannerV2         │
                 │   + GOAIExecutorV2   │   │   + RLExecutorV2     │
                 └──────────────────────┘   └──────────────────────┘

无规划层        ┌──────────────────────┐
（端到端）      │ rl                   │   纯 RL：观测 → 策略网络 → 动作
                └──────────────────────┘   ┌──────────────────────┐
无执行层        │ pure-llm             │   │ LLM 直接输出每个平台的动作 │
                └──────────────────────┘   └──────────────────────┘
```

**连线**：网格内四格**只画边框不画箭头**；两条单侧臂各自与网格用**虚线**相连，表示"去掉一级"。

**强调**：`llm-rl` 一格加**淡色底纹 + 星标**，标题写 `Hybrid B (ours)`；`llm-rule` 写 `Hybrid A (baseline hybrid)`。

**精确文本串**：`rule-rule` · `rule-rl` · `llm-rule` · `llm-rl` · `rl` · `pure-llm` ·
`RulePlannerV2` · `LLMPlannerV2` · `GOAIExecutorV2` · `RLExecutorV2` ·
`Planning Layer` · `Execution Layer` · `Hybrid A` · `Hybrid B (ours)`

**英文提示词（可直接粘贴）**：
> A clean flat-vector 2x2 matrix diagram plus two extra single-layer boxes, white background. Axis labels: columns "Execution Layer = Rule Executor" and "Execution Layer = RL Executor"; rows "Planning Layer = Rule Planner" and "Planning Layer = LLM Planner". Four rounded rectangles at the intersections labelled: "rule-rule / RulePlannerV2 + GOAIExecutorV2", "rule-rl / RulePlannerV2 + RLExecutorV2", "llm-rule (Hybrid A) / LLMPlannerV2 + GOAIExecutorV2", "llm-rl (Hybrid B, ours) / LLMPlannerV2 + RLExecutorV2". Below, two standalone boxes: "rl — end-to-end policy, no goal layer" and "pure-llm — LLM emits actions directly, no executor". Dashed connectors from the standalone boxes to the grid. The llm-rl cell highlighted with a light tint and a small star. Sans-serif type, monospace for class names, thin outlines, no shadows, no gradients.

---

### Fig. 2 —— 两级决策链骨架与接口（所有方法的公共骨架）

**用途**：先给读者一张"公共骨架"，后面每张架构图都是在这张骨架上替换某一级。

**版式**：自上而下 5 层，层与层之间用带标签的箭头连接。

| 层 | 框内文字 | 形状 |
|---|---|---|
| 1 | `Environment / Engine` — sensors · comms · combat · damage · mission rules · scoring | 宽横条（浅灰） |
| 2 | `Observation (immutable, faction-filtered)` | 横条（浅蓝） |
| 3 | `Planning Layer` → 两个并列子框：`RulePlannerV2` / `LLMPlannerV2` | 横条（浅绿） |
| 4 | `Goal Protocol` → `GoalCommand` `GOAIBroker` `StatusReport` | 横条（浅黄） |
| 5 | `Execution Layer` → 两个并列子框：`GOAIExecutorV2` / `RLExecutorV2` | 横条（浅橙） |
| 6 | `Actions`：`PersistentCommandV2` + `DiscreteActionV2` | 横条（浅紫） |

**箭头标签**（务必按此标注频率）：

* Environment → Observation：`per tick`
* Observation → Planning Layer：`every 10 ticks (` `plan_interval` `)`
* Planning Layer → Goal Protocol：`GoalCommand[]`
* Goal Protocol → Execution Layer：`active goals per unit`
* Execution Layer → Actions：`every tick (rule)` / `every 5 ticks (RL)`
* Actions → Environment：`session.step()`

**层 4 里要写出协议要点（小字，两行）**：
`goal_type ∈ {waypoint, patrol, track, intercept, hold, return, loiter}` +
`{barrier, ambush, reserve, disengage}`；
`status ∈ {pending, executing, completed, failed, infeasible, timeout}`

**英文提示词**：
> Vertical layered block diagram, five stacked wide bars on white, flat vector. Top bar "Environment / Engine (sensors, comms, combat, damage, mission rules, scoring)" in light grey. Second bar "Observation (immutable, faction-filtered)" in light blue. Third bar "Planning Layer" in light green containing two side-by-side sub-boxes "RulePlannerV2" and "LLMPlannerV2". Fourth bar "Goal Protocol" in light yellow containing "GoalCommand", "GOAIBroker", "StatusReport" and two small caption lines listing goal types and status states. Fifth bar "Execution Layer" in light orange containing two sub-boxes "GOAIExecutorV2" and "RLExecutorV2". Bottom bar "Actions: PersistentCommandV2 + DiscreteActionV2" in light purple. Arrows upward/downward between bars labelled "per tick", "every 10 ticks", "GoalCommand[]", "every tick (rule) / every 5 ticks (RL)", "session.step()". Sans-serif labels, monospace class names, thin outlines, no shadows.

---

### Fig. 3 —— `rule-rule`（纯规则基线）

**要点**：两级都是确定性/符号式；执行器**每 tick 重解**。

**节点与连线**

```
Observation ──▶ [ RulePlannerV2 ]
                  · nearest-threat greedy
                  · patrol anchors
                  · low-energy return
                      │ GoalCommand[]
                      ▼
                [ GOAIBroker ]  priority · negotiation · safe mode
                      │ active goals
                      ▼
              [ GOAIExecutorV2 ]  (re-solves EVERY TICK)
                  · goal → navigation / fire
                  · fire gate: self-owned contact
                    + [min,max] range + cooldown
                    + live ammo + track age ≤ threshold
                  · doctrine: assess / salvo(≤2) / pk
                  · per-target overkill cap = 2
                      │ PersistentCommandV2 + DiscreteActionV2
                      ▼
                  Environment (session.step)
```

**图内需要标注的两个"诚实性"要点（小字注）**：
① `fire gate` 是**共享教义**，`llm-rl`/`rule-rl` 用的是同一套门（消融对等）；
② 规则执行器的速度是**离散档表**（与 RL 执行层评测时所用的速度约定一致）。

**英文提示词**：
> Vertical pipeline diagram. Box 1 "Observation". Arrow to green box "RulePlannerV2" with bullet lines "nearest-threat greedy", "patrol anchors", "low-energy return". Arrow labelled "GoalCommand[]" to yellow box "GOAIBroker" with caption "priority · negotiation · safe mode". Arrow labelled "active goals" to orange box "GOAIExecutorV2" with bullet lines "regenerates every tick", "goal → navigation / fire", "fire gate: self-owned contact, range window, cooldown, live ammo, track age", "doctrine: assess / salvo (≤2) / pk", "per-target overkill cap = 2". Arrow labelled "PersistentCommandV2 + DiscreteActionV2" to grey bar "Environment". Two small footnote lines marking the fire gate as shared doctrine and the speed table as discrete. Flat vector, thin outlines, sans-serif with monospace class names.

---

### Fig. 4 —— `llm-rule`（混合 A：LLM 规划 + 规则执行）

**要点**：这是**最初那套混合方法**；与 `rule-rule` 的差别**只在规划层**，执行器完全相同。
规划层加一个**回退**：LLM 不可用/解析失败时退回规则规划器。

**节点与连线**

```
Observation ──▶ [ LLMPlannerV2 ]                    ┌── dotted: fallback ──┐
                  · three-stage graph prompt        ▼                      │
                    (incl. feasible ETA,            [ RulePlannerV2 ] ─────┘
                     shore-based segment)
                  · contact-id resolution
                    (owner-priority)
                  · command validation
                    (intercept remapped to an
                     armed observer)
                      │ GoalCommand[]                 ══ double line = LLM call ══
                      ▼
                [ GOAIBroker ]
                      │
                      ▼
              [ GOAIExecutorV2 ]   ← IDENTICAL to rule-rule
                      ▼
                  Environment
```

**图旁参数框（图例小块）**：
`LLM: Qwen3.8-27B` · `thinking: off` · `max_tokens: 1024` · `plan_interval: 10 ticks` · `≈19 s / call (idle endpoint)`

**英文提示词**：
> Vertical pipeline. Grey bar "Observation". Green box "LLMPlannerV2" with bullets "three-stage graph prompt (feasible ETA, shore-based segment)", "contact-id resolution (owner-priority)", "command validation (intercept remapped to an armed observer)". Below it a small green box "RulePlannerV2" connected by a dotted fallback arrow. Draw the Observation→LLMPlannerV2 connector as a double line to denote a large-language-model call. Arrow "GoalCommand[]" to yellow "GOAIBroker", then to orange "GOAIExecutorV2" annotated "identical to rule-rule", then to grey "Environment". A side legend card lists "LLM: Qwen3.8-27B", "thinking off", "max_tokens 1024", "plan_interval 10 ticks". Flat vector, thin outlines, monospace class names.

---

### Fig. 5 —— `rule-rl`（规则规划 + RL 执行；消融诊断臂）

**要点**：与 `rule-rule` 的唯一差别是**执行层换成学习型**；规划层保持规则，因此可以
**在同一规划器下孤立出"执行层"的贡献**（无 LLM 噪声）。

**节点与连线**

```
Observation ──▶ [ RulePlannerV2 ] ──GoalCommand[]──▶ [ GOAIBroker ]
                                                            │ active goals
                                                            ▼
                                                   [ RLExecutorV2 ]
                                        (subclass of GOAIExecutorV2;
                                         inherits doctrine, shot ledger,
                                         status reporting)
                                                            │
                        ┌───────────────────────────────────┴───────────────────────┐
                        ▼                                                           ▼
        [ Observation Encoder ]  fixed-size vector (3570)              [ shared trunk ]
        6 global │ 16×10 unit │ 20×7 contact │                                   │
        16×20×8 pair │ 16×24 goal │ 16×20 assignment mask                        ▼
                                                              ┌──────────────┬──────────────┬──────────────┐
                                                              ▼              ▼              ▼
                                                        heading (sin,cos)  speed      fire choice (21)
                                                              │              │              │
                                                              └──────────────┴──────────────┘
                                                                            │ every 5 ticks
                                                                            ▼
                                                       PersistentCommandV2 + DiscreteActionV2
                                                                            ▼
                                                                      Environment
```

**必须标注**：`RLExecutorV2 extends GOAIExecutorV2` —— 学习件**只替换"目标→指令"这一步**，
 doctrines / 状态上报 / 超杀上限全部继承（这是消融公平性的来源）。

**英文提示词**：
> Vertical pipeline with a neural-network sub-diagram. Grey "Observation" → green "RulePlannerV2" → arrow "GoalCommand[]" → yellow "GOAIBroker" → arrow "active goals" → orange box "RLExecutorV2" annotated "subclass of GOAIExecutorV2: inherits doctrine, shot ledger, status reporting". From it, a thick arrow into a neural network drawn as a light-orange panel: a bar "Observation Encoder — fixed vector of 3570" subdivided into six labelled segments "6 global", "16×10 unit", "20×7 contact", "16×20×8 pair", "16×24 goal", "16×20 assignment mask"; then a "shared trunk" block; then three parallel output heads "heading (sin, cos)", "speed", "fire choice (21: 0 = hold, 1–20 = contact)". Output arrow labelled "every 5 ticks" to purple "PersistentCommandV2 + DiscreteActionV2" then to grey "Environment". Flat vector, thin outlines, monospace names.

---

### Fig. 6 —— `llm-rl`（混合 B：LLM 规划 + RL 执行）★ 本文方法

**要点**：两级都用学习/大模型件；这是**与 Fig. 4 只差执行器**、**与 Fig. 5 只差规划器**的格子。
建议在图角上放一个小"消融指引"：两个虚线箭头分别指向 Fig. 4 与 Fig. 5 的标签，
写明"swap executor"与"swap planner"。

**节点与连线**：把 Fig. 4 的规划部分 + Fig. 5 的执行部分拼起来，即：

```
Observation ──▶ [ LLMPlannerV2 ] ──(fallback: RulePlannerV2)──┐
                      │ GoalCommand[]                         │
                      ▼                                       │
                [ GOAIBroker ] ◀────────────────────────────-─┘
                      │ active goals
                      ▼
                [ RLExecutorV2 ]  (subclass of GOAIExecutorV2)
                      │  obs 3570 → trunk → {heading, speed, fire∈21}
                      │  every 5 ticks
                      ▼
        PersistentCommandV2 + DiscreteActionV2 ──▶ Environment
```

**图角注（三行小字）**：
`vs llm-rule → only the executor differs`
`vs rule-rl  → only the planner differs`
`vs rl       → adds an explicit goal/planning layer`

**英文提示词**：
> Vertical pipeline combining an LLM planner and a learned executor. Grey "Observation" → green "LLMPlannerV2" (double-line LLM connector) with small dotted fallback to "RulePlannerV2" → arrow "GoalCommand[]" → yellow "GOAIBroker" → arrow "active goals" → orange "RLExecutorV2 (subclass of GOAIExecutorV2)" containing a compact neural block "obs 3570 → shared trunk → {heading, speed, fire (21)}"; output arrow "every 5 ticks" to purple "PersistentCommandV2 + DiscreteActionV2" → grey "Environment". Add a small corner annotation card with three lines: "vs llm-rule: only the executor differs", "vs rule-rl: only the planner differs", "vs rl: adds an explicit goal/planning layer". Highlight the two learned components with thicker outlines. Flat vector, monospace names.

---

### Fig. 7 —— `rl`（纯强化学习，端到端单架构）

**要点**：**没有目标层、没有 LLM、没有规则逻辑**；观测直接进策略网络，输出即动作。

```
Observation (3570) ──▶ [ Shared Trunk ] ──▶ { heading (sin,cos) | speed | fire (21) }
                                                      │ every 5 ticks
                                                      ▼
                              PersistentCommandV2 + DiscreteActionV2 ──▶ Environment
```

**图旁注**：`no planning layer` · `no goal protocol` · `no rule executor`

**英文提示词**：
> Minimal single-network diagram: grey "Observation (3570)" → thick arrow into a light-purple neural panel containing a "Shared Trunk" block and three output heads "heading (sin, cos)", "speed", "fire (21)". Output arrow labelled "every 5 ticks" into purple "PersistentCommandV2 + DiscreteActionV2" then grey "Environment". Add a short caption "no planning layer, no goal protocol, no rule executor". Flat vector, monospace names.

---

### Fig. 8 —— `pure-llm`（纯大模型，单架构）

**要点**：**没有独立执行层、没有目标协议**；LLM 直接读观测、**直接输出每个平台的动作**。

```
Observation ──▶ [ PureLLMAgentV2 ]  (double-line LLM connector)
                  · prompt = observation serialization
                  · response = per-platform actions
                    (heading, speed, fire) for all units
                      │
                      ▼
        PersistentCommandV2 + DiscreteActionV2 ──▶ Environment
```

**图旁注**：`no separate executor` · `no goal protocol` · `actions emitted by the LLM itself`
（另一条小字，技术准确性）：`speed envelope applied by the agent: uav 45 m/s · usv 10 m/s`

**英文提示词**：
> Minimal diagram: grey "Observation" → double-line connector → green-yellow box "PureLLMAgentV2" with bullets "prompt = observation serialization" and "response = per-platform actions (heading, speed, fire) for all units". Arrow to purple "PersistentCommandV2 + DiscreteActionV2" → grey "Environment". Caption card: "no separate executor", "no goal protocol", "actions emitted by the LLM itself". Flat vector, monospace names.

---

### Fig. 9 —— RL 执行层的观测张量分解（3570 维）

**用途**：说明"学习件看到的世界"是什么，以及为什么它与规划层是解耦的。

**版式**：横向堆叠条形图（stacked bar），总长 3570，六段，每段上标名称、下标维数。

| 段 | 名称 | 计算 | 维度 |
|---|---|---|---|
| 1 | `global` | 全局标量（时间/态势统计等） | 6 |
| 2 | `unit` | 每个己方单元的自身状态 | 16 × 10 = 160 |
| 3 | `contact` | 每个接触的航迹特征 | 20 × 7 = 140 |
| 4 | `pair` | (单元 × 接触) 配对几何，每对 8 维 | 16 × 20 × 8 = 2560 |
| 5 | `goal` | 规划层下达的目标（每单元 24 维） | 16 × 24 = 384 |
| 6 | `assign` | (单元 × 接触) 是否"我负责的目标"掩码 | 16 × 20 = 320 |
| 合计 | | | **3570** |

**强调**：段 5 + 段 6 用浅绿色（来自规划层），其余用浅橙（来自环境）。
在段 5/6 上方画一个小箭头，标 `from Planning Layer (LLM or rule)`。
条下加一行小字：`fire mask: choice 0 = hold, choices 1..20 = contacts; domain pairing and own-envelope checks applied by the mask (action masking, not a control layer)`。

**英文提示词**：
> Horizontal stacked bar chart of a 3570-dimensional observation vector, white background. Six labelled segments left to right: "global 6", "unit 16×10 = 160", "contact 20×7 = 140", "pair 16×20×8 = 2560", "goal 16×24 = 384", "assignment mask 16×20 = 320", summing to "3570". Colour the "goal" and "assignment mask" segments light green and annotate them "from Planning Layer (LLM or rule)"; colour the other four segments light orange. Add a caption line about action masking: "choice 0 = hold, 1..20 = contacts; the mask removes engine-illegal choices, it never picks one". Flat vector, sans-serif labels, monospace names.

---

### Fig. 10 —— RL 执行层的训练—评测同构流程

**用途**：说明训练与评测**用同一套构建路径**（不是"约定一致"，而是"构造上一致"）。

**版式**：两条泳道（Training / Evaluation）共用中间一组公共模块。

```
   Training (PPO)                                   Evaluation
   ─────────────                                    ──────────
   rollout episodes ──┐                        ┌── episodes with the same planners
                      ▼                        ▼
        ┌───────────────────────────────────────────────────────────┐
        │  shared construction path                                  │
        │  _build_defender(profile, ns) → AgentV2(planner, executor) │
        │  · same planner config · same prompt context               │
        │  · same fire doctrine · same broker                        │
        └───────────────────────────────────────────────────────────┘
                      │                                        │
                      ▼                                        ▼
        goal provider: rule | llm                 goal provider: rule | llm
        (matches the deployed planner)            (matches training)
                      │                                        │
                      ▼                                        ▼
        PPO update: minibatch 256 · epochs 4       read-only scoring：
        entropy coef 0.02 · 12 eps/iter            同一份 scorecard
                      │
                      ▼
        checkpoint (npz)  ──── deployed to ───▶  RLExecutorV2
```

**图旁注（术语必须出现）**：`train/eval parity` · `reward terms: r_kills · r_depth · r_terminal · r_facility · r_own_loss · r_shots · r_goal`

**英文提示词**：
> Two-lane flowchart, white background, flat vector. Left lane header "Training (PPO)", right lane header "Evaluation". Both lanes connect downward into one central wide box titled "shared construction path" listing "_build_defender(profile, ns) → AgentV2(planner, executor)", "same planner config", "same prompt context", "same fire doctrine", "same broker". From the central box, two downward arrows labelled "goal provider: rule | llm" lead to "PPO update (minibatch 256, epochs 4, entropy 0.02, 12 episodes/iter)" on the left and "read-only scoring (same scorecard)" on the right. Left lane ends in a small cylinder "checkpoint (.npz)" with an arrow "deployed to RLExecutorV2". Caption card listing reward terms "r_kills, r_depth, r_terminal, r_facility, r_own_loss, r_shots, r_goal". Sans-serif, monospace identifiers, thin outlines.

---

## 4. 术语中英对照（图内文字用右列）

| 中文 | 图内英文 |
|---|---|
| 规划层 / 执行层 | Planning Layer / Execution Layer |
| 规则规划器 | RulePlannerV2 |
| LLM 规划器 | LLMPlannerV2 |
| 规则执行器 | GOAIExecutorV2 |
| RL 执行层 | RLExecutorV2 |
| 目标协议 / 仲裁器 | Goal Protocol / GOAIBroker |
| 目标命令 | GoalCommand |
| 状态报告 | StatusReport |
| 持久指令 / 离散动作 | PersistentCommandV2 / DiscreteActionV2 |
| 观测（不可变、按阵营过滤） | Observation (immutable, faction-filtered) |
| 混合 A / 混合 B | Hybrid A / Hybrid B (ours) |
| 纯规则 / 纯强化学习 / 纯大模型 | rule-rule / rl / pure-llm |
| 回退 | fallback |
| 教义（开火门/齐射/超杀上限） | fire doctrine (gate / salvo / overkill cap) |
| 消融对等 | ablation parity |
| 训练—评测同构 | train/eval parity |

---

## 5. 画图时最容易错的 8 件事（请绘图模型逐条避开）

1. **把"规划层"画成神经网络** —— 规划层是规则或大模型；神经网络只出现在执行层（或 `rl` 臂）。
2. **把 Broker 画成模型** —— 它是协议/优先级/协商，不含任何模型。
3. **忘了频率标签** —— `every 10 ticks`（规划）与 `every 5 ticks`（RL 动作）是本文的关键量化差异，模型图里必须出现。
4. **让 RL 执行层直连环境** —— 动作必须先经过 `PersistentCommandV2 + DiscreteActionV2` 再进会话层。
5. **在 `pure-llm` 图里画目标协议框** —— 该臂没有独立目标层。
6. **在 `rl` 图里画 LLM 图标** —— 该臂没有 LLM。
7. **两处速度约定混用** —— RL 执行层与规则执行器在同一速度约定下评测（消融对等），不要画成"RL 速度不受限"。
8. **把 `llm-rl` 与 `llm-rule` 的关系画成"替代关系"** —— 它们是**同族的两条混合基线**，差别只有执行器；不要把其中一条画在另一条的下游。

---

## 6. 交付建议

* 每张图**单独出图**（不要拼成一张大图），正文里用 `\includegraphics` 拼版，便于统一字号。
* 图像模型容易写错长文本：**优先只让它画框与箭头**，类名等长标识由排版软件后加也可以；
  若必须由模型写，请只投喂 §3 里给出的**精确文本串**。
* 若模型输出的字体不一致：规定"所有标签使用同一无衬线字体；类名使用等宽字体"。
* 出图后请核对 §1.4 的三个尺寸常数与 §1.3 的线型语义是否都出现。
