# 出图提示词包（配合 `PAPER_METHOD_FIGURES.md`）

> 文档本体：`C:\Code\source-code\openmd\code\eval\PAPER_METHOD_FIGURES.md`
> Windows 绝对路径：`C:\Code\source-code\openmd\code\eval\PAPER_METHOD_FIGURES.md`
> 文件 URI：`file:///C:/Code/source-code/openmd/code/eval/PAPER_METHOD_FIGURES.md`
> 工程内相对路径：`openmd/code/eval/PAPER_METHOD_FIGURES.md`
> 本文档：`C:\Code\source-code\openmd\code\eval\PAPER_METHOD_FIGURES_PROMPTS.md`

---

## 0. 先判断你的出图工具属于哪一种

| 情况 | 用哪一段提示词 |
|---|---|
| **A. 工具能读本地文件**（有文件读取能力的 Agent / 支持附件的模型） | 用 §1 的**元提示词**，只给路径 + 图号，让它自己去读规范 |
| **B. 只能吃文本**（纯文生图，最常见） | 用 §3 的**逐图提示词**，每条都已自带样式与内容 |
| **C. 出图后文字容易糊** | 用 §3 提示词 + §4 的"只画框图"变体，长类名后期用排版软件加 |

**建议**：10 张图**分 10 次单独出**，每次都带上 §2 的 STYLE 前缀（或直接用 §3 里已含前缀的完整版），这样风格才一致。

---

## 1. 元提示词（工具能读文件时用）

> 逐字复制，只把 `<图号>` 换掉（例如 `6`）。

```
请阅读本机文件：
C:\Code\source-code\openmd\code\eval\PAPER_METHOD_FIGURES.md

这是一份"论文方法架构图"的绘图规范。请只画其中的 Fig. <图号>：
以该文件 §3 中标题为「### Fig. <图号> —— ...」的那一小节为准，
严格遵守 §1「全局样式约定」（配色、线型语义、字体、禁止项），
图内文字只使用 §3 该小节给出的「精确文本串」与 §4「术语中英对照」的右列，
不要添加任何未在文档中出现的标签、图例、图标或装饰。

输出：单张图，扁平矢量风格，白底，4:3 横向。
```

**一次出多张的顺序建议**（重要度递减）：
`Fig. 6` → `Fig. 1` → `Fig. 2` → `Fig. 4` → `Fig. 7` → `Fig. 8` → `Fig. 5` → `Fig. 3` → `Fig. 9` → `Fig. 10`

---

## 2. STYLE 前缀（纯文生图时，每条提示词前都加这一段）

```
STYLE: flat vector technical diagram for an academic paper, pure white background,
thin 1–1.5px dark outlines, rounded corners, generous whitespace, no gradients,
no drop shadows, no 3D, no photographs, no clip-art icons, no logos, no watermarks.
One clean sans-serif font for all labels; a monospace font for code identifiers
(e.g. RulePlannerV2, GOAIExecutorV2). Landscape 4:3.
PALETTE (meaning is fixed): environment/engine = light grey #ECECEC;
observation = light blue #D6E9F8; planning layer = light green #D9EFD6;
goal protocol / broker = light yellow #FBEFCB; execution layer = light orange #FBE0CE;
actions = light purple #E3DAF3.
LINE SEMANTICS (fixed): solid arrow = data/control flow; dotted arrow = fallback path;
double line = large-language-model call; thick arrow = neural-network forward pass.
CONSTRAINT: render ONLY the exact text strings listed below; do not invent additional
labels, legends, captions, arrows or decorative elements.
```

---

## 3. 逐图提示词（纯文生图：STYLE 前缀 + 下面每一条）

### Fig. 1 —— 六方法总览与因子设计

```
[STYLE 前缀] +
A 2x2 matrix of four rounded rectangles plus two standalone boxes below.
Column headers: "Execution Layer = Rule Executor" (left), "Execution Layer = RL Executor" (right).
Row headers: "Planning Layer = Rule Planner" (top), "Planning Layer = LLM Planner" (bottom).
Cell contents (title line + second line):
  top-left:  "rule-rule"  /  "RulePlannerV2 + GOAIExecutorV2"
  top-right: "rule-rl"    /  "RulePlannerV2 + RLExecutorV2"
  bottom-left:  "llm-rule (Hybrid A)" / "LLMPlannerV2 + GOAIExecutorV2"
  bottom-right: "llm-rl (Hybrid B, ours)" / "LLMPlannerV2 + RLExecutorV2"
Highlight the bottom-right cell with a light tint and a small star.
Below the matrix, two standalone boxes connected to the matrix by dotted lines:
  "rl — end-to-end policy, no goal layer"
  "pure-llm — the LLM emits per-platform actions directly, no executor"
Text only from this list; no other words.
```

### Fig. 2 —— 两级决策链公共骨架

```
[STYLE 前缀] +
Five stacked wide bars, top to bottom:
1) "Environment / Engine"  caption "sensors · comms · combat · damage · mission rules · scoring"
2) "Observation (immutable, faction-filtered)"
3) "Planning Layer" containing two side-by-side sub-boxes "RulePlannerV2" and "LLMPlannerV2"
4) "Goal Protocol" containing "GoalCommand", "GOAIBroker", "StatusReport" plus two small caption lines:
   "goal_type: waypoint · patrol · track · intercept · hold · return · loiter · barrier · ambush · reserve · disengage"
   "status: pending · executing · completed · failed · infeasible · timeout"
5) "Execution Layer" containing "GOAIExecutorV2" and "RLExecutorV2"
6) bottom bar "Actions: PersistentCommandV2 + DiscreteActionV2"
Arrow labels between bars: "per tick", "every 10 ticks", "GoalCommand[]",
"active goals per unit", "every tick (rule) / every 5 ticks (RL)", "session.step()".
```

### Fig. 3 —— `rule-rule`

```
[STYLE 前缀] +
Vertical pipeline: "Observation" -> "RulePlannerV2" -> "GOAIBroker" -> "GOAIExecutorV2" -> "Environment".
"RulePlannerV2" bullet lines: "nearest-threat greedy", "patrol anchors", "low-energy return".
Arrow from planner labelled "GoalCommand[]".
"GOAIBroker" caption: "priority · negotiation · safe mode".
"GOAIExecutorV2" bullet lines: "regenerates every tick", "goal to navigation / fire",
"fire gate: self-owned contact, range window, cooldown, live ammo, track age",
"fire doctrine: assess / salvo (max 2) / pk", "per-target overkill cap = 2".
Final arrow labelled "PersistentCommandV2 + DiscreteActionV2".
Two small footnote lines: "fire gate is shared doctrine (ablation parity)" and
"discrete speed table".
```

### Fig. 4 —— `llm-rule`（混合 A）

```
[STYLE 前缀] +
Vertical pipeline: "Observation" -> "LLMPlannerV2" -> "GOAIBroker" -> "GOAIExecutorV2" -> "Environment".
Draw the Observation-to-LLMPlannerV2 connector as a DOUBLE LINE (LLM call).
"LLMPlannerV2" bullet lines: "three-stage graph prompt (feasible ETA, shore-based segment)",
"contact-id resolution (owner-priority)",
"command validation (intercept remapped to an armed observer)".
Below the planner, a smaller box "RulePlannerV2" connected by a DOTTED fallback arrow.
"GOAIExecutorV2" annotated "identical to rule-rule".
Side legend card: "LLM: Qwen3.8-27B", "thinking: off", "max_tokens: 1024", "plan_interval: 10 ticks".
```

### Fig. 5 —— `rule-rl`

```
[STYLE 前缀] +
Vertical pipeline: "Observation" -> "RulePlannerV2" -> arrow "GoalCommand[]" -> "GOAIBroker"
-> arrow "active goals" -> "RLExecutorV2" annotated
"subclass of GOAIExecutorV2: inherits fire doctrine, shot ledger, status reporting".
From RLExecutorV2 a THICK arrow into a light-orange neural-network panel containing:
a labelled bar "Observation Encoder — 3570" split into six segments
"6 global", "16×10 unit", "20×7 contact", "16×20×8 pair", "16×24 goal", "16×20 assignment mask";
then a block "shared trunk";
then three parallel heads "heading (sin, cos)", "speed", "fire choice (21: 0 = hold, 1..20 = contact)".
Output arrow labelled "every 5 ticks" to "PersistentCommandV2 + DiscreteActionV2" then "Environment".
```

### Fig. 6 —— `llm-rl`（混合 B，本文方法）★

```
[STYLE 前缀] +
Vertical pipeline: "Observation" -> "LLMPlannerV2" (DOUBLE-LINE LLM connector)
-> arrow "GoalCommand[]" -> "GOAIBroker" -> arrow "active goals" -> "RLExecutorV2".
Dotted fallback arrow from "LLMPlannerV2" to a small box "RulePlannerV2".
"RLExecutorV2" annotated "subclass of GOAIExecutorV2" and contains a compact neural block
"obs 3570 -> shared trunk -> {heading, speed, fire (21)}".
Output arrow "every 5 ticks" to "PersistentCommandV2 + DiscreteActionV2" then "Environment".
Give the two learned components (LLMPlannerV2 and RLExecutorV2) visibly thicker outlines.
Corner annotation card with exactly three lines:
"vs llm-rule: only the executor differs"
"vs rule-rl: only the planner differs"
"vs rl: adds an explicit goal and planning layer"
```

### Fig. 7 —— `rl`（纯 RL）

```
[STYLE 前缀] +
Minimal diagram: "Observation (3570)" -> THICK arrow -> light-purple neural panel containing
"Shared Trunk" and three heads "heading (sin, cos)", "speed", "fire (21)".
Output arrow "every 5 ticks" -> "PersistentCommandV2 + DiscreteActionV2" -> "Environment".
Caption line: "no planning layer, no goal protocol, no rule executor".
```

### Fig. 8 —— `pure-llm`

```
[STYLE 前缀] +
Minimal diagram: "Observation" -> DOUBLE-LINE connector -> box "PureLLMAgentV2" with bullets
"prompt = observation serialization" and
"response = per-platform actions (heading, speed, fire) for all units".
Arrow -> "PersistentCommandV2 + DiscreteActionV2" -> "Environment".
Caption card: "no separate executor", "no goal protocol", "actions emitted by the LLM itself".
```

### Fig. 9 —— 观测量分解

```
[STYLE 前缀] +
A single horizontal stacked bar representing a 3570-dimensional vector, six segments left to right:
"global 6", "unit 16×10 = 160", "contact 20×7 = 140", "pair 16×20×8 = 2560",
"goal 16×24 = 384", "assignment mask 16×20 = 320", with a total marker "3570".
Colour "goal" and "assignment mask" segments light green and annotate them
"from Planning Layer (LLM or rule)"; colour the other four segments light orange.
Caption line: "fire mask: choice 0 = hold, 1..20 = contacts; the mask removes engine-illegal
choices, it never picks one".
```

### Fig. 10 —— 训练—评测同构

```
[STYLE 前缀] +
Two-lane flowchart. Left lane header "Training (PPO)"; right lane header "Evaluation".
Both lanes connect downward into one central wide box titled "shared construction path" with lines
"_build_defender(profile, ns) -> AgentV2(planner, executor)", "same planner config",
"same prompt context", "same fire doctrine", "same broker".
From the central box two downward arrows labelled "goal provider: rule | llm" lead to
"PPO update (minibatch 256, epochs 4, entropy 0.02, 12 episodes per iteration)" on the left
and "read-only scoring (same scorecard)" on the right.
Left lane ends with a small cylinder "checkpoint (.npz)" and an arrow "deployed to RLExecutorV2".
Caption card: "reward terms: r_kills, r_depth, r_terminal, r_facility, r_own_loss, r_shots, r_goal".
```

---

## 4. 变体：只画框图、不写长文字（文字易糊时用）

在上面任一提示词末尾追加：

```
Do NOT render any class names or long words inside the boxes. Render only the short
structural labels (layer names and axis headers). Leave all boxes otherwise empty so the
labels can be added later in a typesetting tool. Keep every box and arrow in the same
positions as described.
```

---

## 5. 图内文字白名单（防止模型自创标签）

**允许出现的全部文本**（其余一律不许）：

```
rule-rule   rule-rl   llm-rule   llm-rl   rl   pure-llm
Hybrid A   Hybrid B (ours)
Planning Layer   Execution Layer   Goal Protocol   Environment / Engine   Actions
Observation   Observation (immutable, faction-filtered)
RulePlannerV2   LLMPlannerV2   GOAIExecutorV2   RLExecutorV2   GOAIBroker
GoalCommand   StatusReport   PersistentCommandV2   DiscreteActionV2
PureLLMAgentV2   shared trunk   Shared Trunk   Observation Encoder
heading (sin, cos)   speed   fire (21)   fire choice (21: 0 = hold, 1..20 = contact)
global 6   unit 16×10 = 160   contact 20×7 = 140   pair 16×20×8 = 2560
goal 16×24 = 384   assignment mask 16×20 = 320   3570
MAX_UNITS = 16   MAX_CONTACTS = 20
every tick   every 5 ticks   every 10 ticks   per tick   session.step()
fallback   ablation parity   train/eval parity
LLM: Qwen3.8-27B   thinking: off   max_tokens: 1024   plan_interval: 10 ticks
waypoint · patrol · track · intercept · hold · return · loiter · barrier · ambush · reserve · disengage
pending · executing · completed · failed · infeasible · timeout
r_kills · r_depth · r_terminal · r_facility · r_own_loss · r_shots · r_goal
no planning layer, no goal protocol, no rule executor
no separate executor   actions emitted by the LLM itself
```

---

## 6. 出图后自检清单（逐张核对）

1. 配色是否符合语义（规划层绿 / 执行层橙 / 协议黄 / 动作紫 / 环境灰）？
2. 线型是否正确：LLM 调用是**双线**、神经网络是**粗箭头**、回退是**虚线**？
3. 是否出现了 `every 10 ticks`（规划）与 `every 5 ticks`（RL 动作）两处频率标签？
4. 是否出现了 `MAX_UNITS = 16` / `MAX_CONTACTS = 20`？
5. `rl` 图里有没有误加 LLM 图标或目标协议框？（**不该有**）
6. `pure-llm` 图里有没有误加"执行器"框？（**不该有**）
7. `llm-rule` 与 `llm-rl` 是否被画成"替换关系"而非"同族两条基线"？（**不许画成上下游**）
8. `RLExecutorV2` 是否标注了"继承 `GOAIExecutorV2`"？
9. 图内是否有模型自创的文字/图例/logo？有则要求重出。
10. 字体是否统一（标签一种无衬线、类名等宽）？
