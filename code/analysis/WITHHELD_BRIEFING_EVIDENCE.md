# WITHHELD_BRIEFING_EVIDENCE.md — 情报口径与硬边界证据台账

> 生成时间：2026-09-27
> 适用实验：三臂无情报对照（`llm-rule` / `llm-rl` / `pure-llm`）对单一架构基线（`rule-rule` / `rl`）
> 全部结论均可由本文件列出的脚本复算。

---

## 1. 口径定义

| 口径 | CLI | 提示词内容 | 用途 |
|---|---|---|---|
| `withheld`（**主表**） | `--llm-briefing withheld` | 无任何敌方情报：不给波次数量、时刻、方位、意图，也不给兵力数字。仅给"看到 can_intercept/prepare_intercept 就打"与"必须自己从观测分辨威胁" | 公平对照实验 |
| `declared`（历史） | `--llm-briefing declared` | 逐波给出 `spawn_tick / count / axis / behavior`（**含未来真值**） | 仅用于复现 2026-09-27 之前的旧读数 |

**为什么主表不给任何兵力数字**：实测确认 `"armed vs decoy"` **不是观测字段**
（`Observation` 只有位置/置信度/观测者/标签），因此"有几架武装、几架诱饵"无法从观测推导，
只能来自场景声明；而 `rule-rule` 与 `rl` 两臂**从不读取该声明**。给出即为特权信息，
与措辞无关。归档中曾有 `aggregate` 档（给聚合兵力数字），主表同样不采用。

**口径必须可由每局报告复核**：

| 臂 | 落盘位置 |
|---|---|
| `pure-llm` | `defender.briefing` |
| `llm-rule` / `llm-rl` | `defender.planner.briefing` |

读取时必须**同时检查这两处**——只读 `defender.briefing` 会把带口径的 `llm-rule` /
`llm-rl` 局误判为"无口径"（本次调试中实际踩到过）。

---

## 2. 硬边界：改了什么、没改什么

归档快照：`%USERPROFILE%\openmd_private_archive\declared_briefing_snapshot_20260927_1419\code`
（2026-09-27 14:19 采集，含 22 个 eval 文件）

### 2.1 未改动的文件（SHA256 逐位一致）

```
rule_planner.py        IDENTICAL      <- 规则规划器（rule-rule 的决策核心）
v2_executor.py         IDENTICAL      <- 规则执行器
rl_executor.py         IDENTICAL      <- RL 执行层
rl_agent.py            IDENTICAL      <- RL 智能体
strategy_metrics.py    IDENTICAL      <- 评分
attack_driver.py       IDENTICAL      <- 攻击方模型
goai_protocol.py       IDENTICAL
ie_goal_features.py    IDENTICAL
interception_graph.py  IDENTICAL
v2_agent.py            IDENTICAL
civilian_transit.py    IDENTICAL
```

### 2.2 有改动的文件与改动区域

| 文件 | 改动区域数 | 性质 |
|---|---|---|
| `run_episode.py` | **3** + 1（日志缺陷修复，见 §2.4） | 情报通道 + 无副作用的接口修复 |
| `llm_planner.py` | 2 | 提示词通道 |
| `pure_llm_agent.py` | 13 | 提示词/一致性 |
| `_w1_ie_sweep.py` | — | 实验脚手架 |
| `PAPER_READINESS_GAPS.md` | — | 文档 |

**`run_episode.py` 的 3 处改动**（`_w1_code_diff.py run_episode.py` 可复算）：

1. `_build_roe_notes(profile_data, *, briefing)` 重写——分类改为按
   `attack.weapon_policies` 的**武器装订**判定，不再做 `"decoy" in text` 子串匹配。
   旧实现对 `f"{label} {behavior}".lower()` 做子串匹配，而 IE-11 主攻那条的 behavior
   恰好写着 `"after the decoys have already drawn attention"`，导致 **4 架有武器的主攻 UAV
   被判为非威胁**（提示词出现 "declared NON-THREAT … do NOT intercept or fire at it"）。
2. `prompt_context` 新增 `speed_range`（逐平台由 `speed_by_tag` 派生）+ `briefing_declared`
   （门控位）。
3. CLI 新增 `--llm-briefing {withheld,declared}`（默认 `withheld`）。

**`llm_planner.py` 的 2 处改动**：时间线注入块改为由 `briefing_declared` 门控（未披露时输出
"NOT DISCLOSED" 文案）；`get_stats()` 增加 `briefing` 字段。

**`pure_llm_agent.py` 的 13 处改动**：`ExecutorConfigV2` 导入；`_DEFAULT_PROMPT_CONTEXT`
去掉硬编码 `"speed_range": "0-45"`；引导语第 5 条由"按声明时间线判诱饵"改为"无情报时按自身
观测判定"；三处 few-shot 示例速度 `40` → `@@SPEED@@` 占位符（`.format()` 后替换为真实包线上限）；
`__init__` 默认包线 `{45,10}` → 全 `12.0`；`speed_range` 由 `speed_max_by_tag` 派生；
`_speed_limit()` 兜底 `15.0` → `ExecutorConfigV2.default_speed_mps`(12.0)；**`graph.format_timeline_for_prompt()`
注入由无条件改为 `briefing_declared` 门控**（这是 pure-llm 最后一个情报通道）；`get_stats()`
增加 `briefing`。

> 逐条 hunk 明细：`python _w1_code_diff.py run_episode.py llm_planner.py pure_llm_agent.py`

### 2.4 第 4 处改动：日志接口缺陷修复（2026-09-27 晚）

**这处改动不触碰决策、评分、提示词或观测布局**，但它是真实缺陷且会毁掉整局算力，
故单独登记并附理由。

**缺陷**：`run_episode.py` 内部的 `log()` 包装器

```python
def log(*, kind: str, **fields) -> None:
    if run_log is not None:
        run_log.event(kind, tick=session.world_view.tick, **fields)   # ← 冲突点
```

当 `fields` 里已经带有 `tick` 时，与显式的 `tick=` 重复，抛
`TypeError: _RunLog.event() got multiple values for keyword argument 'tick'`。
该异常被外层 `except` 捕获记为 `aborted`，于是**整局作废**。
实测：`ie_purellm_ie-05-multi-axis_n3.json` 在 tick 857（约 10 分钟算力）因此中止；
更早的批次日志里同类中止至少出现过 4 次。

**修复**（3 处调用点 + 1 处接口加固）：

| 位置 | 改动 |
|---|---|
| `log(kind="checkpoint_unavailable", …, tick=ticks_run, phase="pre_engagement")` | 去掉 `tick=`，保留 `phase` |
| 同上（周期性报告处） | 去掉 `tick=`，补 `phase="periodic"` |
| 同上（收尾处） | 去掉 `tick=`，保留 `phase="final"` |
| `_RunLog.event()` | 改为显式合并：把 `fields` 里的 `tick` 取出后作为普通字段写入 |

**为什么不影响口径/决策**：
`log()` 只写 JSONL 过程日志。`tick` 的值本来就会被 `log()` 注入为 harness tick，
去掉调用点的显式 `tick=` 后写入的**数值完全相同**；`phase` 字段本就存在，
仅把原先无 phase 的那处补成 `"periodic"` 以便区分。
接口加固使"日志冲突"**永远不可能再毁掉一局**——这是本节修复的核心目的。

**验证**：改后重跑代码 A/B 门禁（`_w1_determinism_gate.py <SCEN> rule 7 --ab`），
见 §4.2 的场景表；并重跑原先中止的 `pure-llm` IE-05 格，核对 `aborted` 为 `null`。

> 注意：JSONL 日志中 `tick` 字段的**键序**可能由中间位置变为末尾
> （`_RunLog.event` 现在先弹出再写回）。JSONL 仅用于过程观测，
> **不参与任何评分或判据**，报告 JSON 与得分数值不受影响。

### 2.5 反向扫描：非 LLM 模块是否触及情报

对 `v2_executor.py / rl_executor.py / rule_planner.py / v2_agent.py` 等基线路径模块搜索
`briefing|llm_briefing|roe_notes|speed_range`：**0 命中**。
`prompt_context` 虽然对所有臂都会构造，但 `rule` / `rl` 分支**从不读取**其中任何字段，
且 `_build_roe_notes` 的返回值只进入 LLM 的提示词字符串。

### 2.3 IE-11 误分类缺陷的实测复现（`_w1_roe_fix_check.py`）

IE-11 的真实攻击剖面（`load_attack_profile_data("IE-11-DECOY-SCREEN")`）：

```
weapon_policies 武器装订标签 : ['boat', 'uav']
波次 1  'decoy screen'      count=2  spawn_tick=0    behavior='declared DECOYS: unarmed, ...'
波次 2  'real air package'  count=4  spawn_tick=150  behavior='the four armed UAVs appear only
                                                      after the decoys have already drawn attention'
波次 3  'surface element'   count=3  spawn_tick=0    behavior='three suicide boats run at ...'
```

旧实现按 `f"{label} {behavior}".lower()` 做 `"decoy" in blob` 匹配，于是
**波次 2（4 架武装主攻 UAV）因 behavior 里含 "decoys" 一词被判为非威胁**，
提示词会写出 `real air package (spawn_tick=150) is declared NON-THREAT … do NOT intercept
or fire at it`。这不是措辞瑕疵，而是让主攻包免于拦截。

新实现按**武器装订**分类（`attack.weapon_policies` → `_armed_intruder_tags`），
`decoy screen` 的 2 个目标在 `declared` 档下被正确识别为诱饵，`real air package` 与
`surface element` 被正确计为武装来袭者：

```
[aggregate briefing] Enemy order of battle: 7 armed intruder platforms (4 air, 3 surface) across all waves.
[aggregate briefing] 2 additional intruder platform(s) are UNARMED decoys/feints.
```

`withheld` 档下对同一场景逐条扫描 `spawn_tick|axis=|count=|wave-\d|\d+ armed|first wave…`：
**0 命中**，且不含任何 `non-threat` / `do not intercept` 指令。

---

## 3. 公平性验收（P0）

`python _w1_p0_fairness_accept.py` → **PASS**

```
IE-01-SINGLE-TARGET   briefing=withheld  hits= 0  OK      <- 无情报泄漏
IE-01-SINGLE-TARGET   briefing=declared  hits= 1  OK      <- 旧口径可复现
IE-11-DECOY-SCREEN    briefing=withheld  hits= 0  OK
IE-11-DECOY-SCREEN    briefing=declared  hits=12  OK
IE-08-ISLAND-STRIKE   briefing=withheld  hits= 0  OK
IE-08-ISLAND-STRIKE   briefing=declared  hits= 3  OK
```

扫描方式：对三臂**真实构造出的提示词全文**做敏感串扫描（14 个"仅场景声明可知"的字符串，
如波次时刻/数量/方位/意图措辞）。`withheld` 档 0 命中 ⇒ 无场景声明情报残留；
`declared` 档仍有命中 ⇒ 旧读数可逐字复现。

公共项一致性（CHECK 3，三臂逐字段相同）：
`weapon_range=0-8000`、`objective=(-1200,-200)`、`max_tokens=1024`、
`llm_cadence_ticks=10/10/10`、`llm_is_same_class=LLMClient`（同一客户端、同一模型、同一温度）。

---

## 4. 基线不漂移证据

### 4.0 基线口径：**只复用归档数据，不重跑实验**

单一架构两臂（`rule-rule`、`rl`）**不读情报**，其脚本与执行器逐位未改
（见 §2.1），场景包 14/14 逐字节未变（见 §4.1），代码 A/B 0 字段差异（见 §4.2）。
因此归档的基线读数是**有效且可直接复用**的对照值，本实验**不为其启动任何实验局**。

唯一需要的处理是**按策略身份过滤归档数据**：`rl` 不是单一策略，归档里混有多个
checkpoint（`_w1_baseline_partition.py` 可复算）：

| 归档中的策略身份 | 局数 | 覆盖场景 |
|---|---|---|
| `theta_rl_legacy2.npz \| speed=legacy_tags \| interval=5` | 118 | **13/14** |
| `theta_rl_main5.npz` | 74 | 7/14 |
| `theta_rl_main4.npz` | 4 | 2/14 |
| `theta_rl_main3.npz` | 2 | 1/14 |
| `theta_calib4.npz` | 2 | 1/14 |

**分析必须锁定第一支**（唯一带 `checkpoint_meta` 训练溯源、且 `decision_interval=5`
与训练值一致者）。跨 checkpoint 求平均得到的是"不属于任何真实策略"的数字。

- `IE-08-ISLAND-STRIKE` 在归档中**没有** `theta_rl_legacy2` 的读数 ⇒ 表中该项标注
  **无基线**，不臆造、不以其它 checkpoint 顶替。
- `rule-rule` 为确定性策略（无 RNG），归档各 seed 读数同值；`IE-08` 有归档读数。
- 先前版本的分析脚本曾对 `rl` 混算所有 checkpoint（早期表 `rl` 列因此偏高），
  该口径已作废。

### 4.1 场景包身份（`_w1_baseline_drift.py`）

归档 `scenarios/` 与 live `scenarios/formal/` 逐目录比对全部文件哈希：
**14/14 场景包逐字节一致** ⇒ 归档的基线读数与 live 场景可直接比较，
不存在"场景改版导致基线漂移"。

### 4.2 代码 A/B（`_w1_determinism_gate.py <SCEN> rule 7 --ab`）

把归档 `code/`（= 修改前）放入沙箱 `_w1_archive_sandbox/`，用 `PYTHONPATH` 置于 live 之前，
对同一场景同一 seed 跑一局，再与 live 代码跑的另一局做**逐字段**比对：
**22 个字段 0 差异**（`entities / engagements_by_target / fire_rejections / damage_by_kind /
strategy_scorecard / layered_metrics / terminal_result / score_state / defender / attack / ticks_run …`），
仅排除墙钟类字段。

**已覆盖的场景，全部 PASS**：

| 场景 | 结果 | 备注 |
|---|---|---|
| IE-01-SINGLE-TARGET | PASS（22 字段 0 差异） | 首轮 + 日志修复后复测 |
| IE-06-DECOY-MIXED | PASS | 诱饵场景 |
| IE-11-DECOY-SCREEN | PASS | **暴露 ROE 误分类缺陷的场景** + 修复后复测 |
| IE-02-DUAL-THREAT | PASS | 双威胁 |
| IE-09-STAGGERED-WAVES | PASS | 多波次（最长 999 tick） |
| IE-05-MULTI-AXIS | PASS | **日志缺陷修复后复测**（该场景正是被日志缺陷打死的那一局） |

IE-11 与 IE-09 是最关键的两个：前者是 `_build_roe_notes` 被重写的动因，
后者是波次机制最复杂者。二者在修改前后逐位一致，说明改动确实没有触碰基线决策路径。

**§2.4 的日志修复亦已复测**：IE-05 / IE-11 / IE-01 三个场景在修复后重跑 A/B，
全部 `PASS - decision output bit-identical`。即"修完日志接口后基线仍逐位不漂移"。

### 4.3 同代码复跑确定性（`_w1_determinism_gate.py <SCEN> rule 7`）

同一代码连跑两局：**16 个决策级字段全一致** ⇒ 引擎路径确定性成立，
任何差异都只能来自代码改动而非抽签。

---

## 5. 评分口径核对（易错点）

`strategy_metrics.py:625-629`：

```
scored_weight  = Σ w[k]  （k 取 applicable）
defender_score = Σ layers[k]·w[k] / scored_weight
```

**`defender_score` 本身就是归一化后的主统计量**，不可再除 `scored_weight`。
`layers` 中不适用的层保留占位值，只有 `layer_applicability` 为真者参与加权——
离线重算必须复现该掩码，否则会重新引入偏差。

`_w1_scoring_convention_audit.py` 对每一局用 `layers × layer_weights × layer_applicability`
复算并与之比对：

```
归档 declared LLM 臂 : 218/218 归一口径
本次 withheld 数据   :     0 局不符合主口径
```

> 归档中另有旧口径局面（`legacy_defender_score_all_layers`，全层恒定分母，
> 因此可出现 `> 1.0`，如某条 `rule` 的 1.4286）。**旧口径局面不在 LLM 臂样本内**，
> 但任何混用都会造成系统性偏移，故所有分析脚本都做了逐局口径判定。

---

## 6. 终局结构（为何"早终局"不构成不公平）

14 个 IE 场景的 `scenario.mission_rules` 结构完全同构（`_w1_terminal_structure.py`）：

| 规则 | 条件 | 结果 | 判定 |
|---|---|---|---|
| `rule.assets-lost` / `rule.facilities-lost` | `count(facility) <= 0` | `intruder_success` | 蓝方**失败** |
| `rule.defenders-destroyed` | `count(combat-unit, {scheduled,active,degraded}) <= 0` | `intruder_success` | 蓝方**失败** |
| `rule.intruders-destroyed` | `count(intruder, {scheduled,active,degraded}) <= 0` | `defender_success` | 公平 |
| `rule.defence-success` | `time >= <场景声明 tick>` | `defender_success` | 场景常量 |

两点结论：

1. **成功只能由"歼灭全部来袭者"或"跑满声明时长"取得**，两者都不是"提前结束测量"。
   两个侧面条件都只产生**失败**结果，不存在"打不过就早点结束以逃避扣分"的路径。
2. **`rule.intruders-destroyed` 把 `scheduled` 计入存活** ⇒ 尚未生成的波次会保持计数 > 0，
   该规则**不可能在后波未出现时触发**。因此"早终局"意味着真的把该场景的全部来袭者打完了。

引擎实测佐证：`_w1_engine_ground_truth.py IE-01-SINGLE-TARGET 0` 显示 tick 0 即存在全部
4 架 `wave-1` 来袭机（无待生成波次），故 66 tick 的 `defender_success` 是全歼。

长度-分数相关性（`_w1_length_audit.py`）显示 tick 与分数在部分场景呈负相关
（越早结束分越高）。这是**结果**而非**偏差**：早结束的成因就是来袭者被更快消灭，
而评分各层（facility 毁伤、loss rate、拦截纵深、弹药效率）都按战果计算，与局长短无关。

---

## 7. 复算清单

```
python _w1_p0_fairness_accept.py                     # P0 公平性验收
python _w1_code_diff.py run_episode.py llm_planner.py pure_llm_agent.py
python _w1_baseline_drift.py --arm rule              # 场景包身份 + 漂移
python _w1_baseline_partition.py                     # 归档 rl 基线的策略身份划分
python _w1_determinism_gate.py IE-01-SINGLE-TARGET rule 7 --ab   # 代码 A/B
python _w1_determinism_gate.py IE-06-DECOY-MIXED rule 7 --ab
python _w1_scoring_convention_audit.py               # 评分口径逐局判定
python _w1_terminal_structure.py                     # 终局结构
python _w1_length_audit.py                           # 长度-分数相关性
python _w1_engine_ground_truth.py IE-01-SINGLE-TARGET 0
python _w1_cell_inspect.py                           # 逐局口径字段核对
python _w1_roe_fix_check.py IE-11-DECOY-SCREEN       # IE-11 误分类缺陷复现
python _w1_behavior_signal.py                        # 口径是否真的改变了行为
python _w1_grid_eta.py                               # 工期投影
```

全部输出留档：`_w1_runs/GATE_LOG_20260927.txt`

---

## 8. 已知限制（必须与结论同时报告）

1. **同 seed 不是重放**：LLM 端点在 ~1.3k token 的真实提示词上**非确定**
   （4/4 次输出互异；19 token 短提示词 5/5 相同）。因此固定 seed 对 LLM 臂而言是
   **一次复现**，不是同一条轨迹的重演；"同 seed 配对"必须写成"同 seed 条件下的独立复现"。
   引擎侧确定性已单独验证（§4.3）。
2. **`rule.intruders-destroyed` 使局长成为臂的内生变量**：不同臂即使在同场景也会跑不同 tick 数
   （本次 IE-01：`llm` 66 tick vs 归档中位 54 tick）。计分按战果而非时长，故不影响公平性，
   但**局长本身不可作为结果指标**。
3. **每次换 seed 就是换一整条抽签流**（引擎把命中判定种子挂在 `resolved_hash + session_id`
   上，而 `session_id` 由 seed 推出）。
4. `--resume` 检查点只恢复引擎世界状态，**不恢复 `llm_planner._last_plan`**，
   故恢复局与原局不是同一轨迹。本实验**不使用 resume**，一律重跑。
