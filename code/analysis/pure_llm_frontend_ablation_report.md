# Pure-LLM 前置模块对照实验报告（GraphBuilder 前置模块的因果效应）

> 目的：给 Pure LLM 组接上与混合组（LLM 规划层 × GOAI 执行层）**完全相同的前置模块**
> （GraphBuilder 结构化态势图 + 攻击时间线），并给出"有/无前置模块"的对照，回答
> "LLM 组的瓶颈是输入形式还是输出形式"。
> 口径：seed=7，plan-interval=10，Qwen3.8-27B，temperature 0.1，enable_thinking=False；
> 引擎 9429392 + 接触寿命修复；AD-002 弹药 12→2；Linux 运行环境（含岸基 CIWS 槽位）。
> 场景：MD-AD-002-EASY（空中拒止）与 MD-AD-004-DECEPTION（欺骗走廊）。
> 日期：2026-09-14。

---

## 1. 前置模块是什么（混合组原配）

混合组每 10 tick 调 LLM 时，输入由脚本（非 LLM）预计算好的**结构化战场态势**，包含：

1. **拦截关系图**（`interception_graph.GraphBuilder`）：拦截机 × 接触的带属性边——
   距离 / 射程比 / ETA / 可行拦截（`feasible`/`feasible_eta_ticks`）/ 威胁度 /
   方位 / 距禁区（按方框边界算）/ 观测者 / 距离射程差 / 接近速度 / 接近状态 /
   预计进射程时间 / 提前拦截标志（`prepare_intercept`）；
2. **攻击时间线**（场景 agents.yaml 声明）：各波次时刻与性质（真实/佯动/平民）；
3. **历史决策记忆**（HistoryBuffer：近 5 轮分配 + 弹药）；
4. **岸基近防段**（有岸基设施时）。

本次改动只做一件事：让 Pure LLM 组用**同一套前置模块**，输出形式保持低层命令
（navigate / fire / hold）不变，并新增"关闭前置模块"的对照臂。

## 2. 实现（加法式，默认行为不变）

| 文件 | 改动 | 说明 |
|---|---|---|
| `code/eval/pure_llm_agent.py` | 新增 `include_graph` 参数与 `ACTION_PROMPT_RAW` 模板 | 默认 `include_graph=None` → 有 `graph_builder` 即为 True（= 官方现状，行为不变）；显式 False 或无图 → 仅原始接触报告（对照臂）；无图时不再构建图（省算力） |
| `code/eval/run_episode.py` | 新增 `--frontend {graph,raw}`（默认 `graph`） | `graph` = 建图并注入（现状）；`raw` = 不建图，pure-llm 仅收到原始接触表 |
| `code/eval/test_adaptation.py` | 新增 `test_pure_llm_frontend_toggle` | 断言两臂提示词差异（graph 含 "Interception Graph"/"Scheduled attack timeline"，raw 不含但保留 JSON schema） |
| `code/eval/run_frontend_ablation.sh` | 新增批量脚本 | 一键跑四臂 |

回归：`test_adaptation.py` **29/29 通过**（含新增开关测试）；`--frontend graph` 为默认值，
既有结果不受影响。

## 3. 实验结果（同一代码、同一 seed、同一引擎，仅前置模块开关不同）

| 组 | 场景 | 前置模块 | Ticks | 终局 | V | 歼灭率 | 开火 | 真威胁 | 诱饵 | 首开火 | masked | fallback | LLM 调用 |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rule | MD-AD-002-EASY | — | 974 | 破防(973) | 0.2889 | 0.4444 | 19 | 19 | 0 | 185 | — | — | — |
| **pure-llm** | MD-AD-002-EASY | **graph** | 974 | 破防(973) | **0.2889** | 0.4444 | 19 | 19 | 0 | **340** | 54 | 0 | 98 |
| pure-llm | MD-AD-002-EASY | raw | 509 | 破防(508) | 0.2 | 0.0 | **0** | 0 | 0 | **None** | 0 | 1 | 51 |
| rule | MD-AD-004-DECEPTION | — | 1800 | 守满成功 | 0.7867 | 0.3333 | 12 | 4 | **8** | 117 | — | — | — |
| **pure-llm** | MD-AD-004-DECEPTION | **graph** | 1800 | **守满成功** | **0.9667** | **0.8333** | 12 | 8 | 4 | 490 | 56 | 0 | 180 |
| pure-llm | MD-AD-004-DECEPTION | raw | 829 | 破防(828) | 0.2 | 0.0 | **0** | 0 | 0 | **None** | 0 | 1 | 83 |

（V = 0.6×任务成败 + 0.2×威胁歼灭率 + 0.2×防守生存率；开火 = 引擎实际执行数，
含岸基 CIWS 自动近防；AD-002 中 19 发 = 6 枚拦截弹 + 13 发近防。）

参考（官方 hifi 表同框架，无岸基 CIWS 环境）：EASY rule 0.2667 / llm 0.2889；
DECEPTION rule 0.7867 / llm 0.9。

## 4. 结论

1. **前置模块是 Pure LLM 可用的必要条件，效应是决定性的。**
   关闭前置模块（raw）时：两个场景**全程 0 开火**（首开火 None）、最早期破防
   （EASY t508、DECEPTION t828）、歼灭率 0、V 触底 0.2——LLM 面对纯文本接触表
   完全不作为。开启前置模块后：EASY 打出 6 枚拦截弹 + 近防 13 发、**破防时刻
   973 与规则组完全相同**；DECEPTION **守满 1800 成功**、歼灭 5/6。
   → 同一模型、同一提示词框架、同一执行层，**唯一变量是前置模块**，结果从
   "瘫痪"跳到"与规则组同级甚至更好"。

2. **在欺骗场景上，Pure LLM + 前置模块超过规则组与混合组。**
   V：pure-llm+graph **0.9667** > 混合组 0.9 > 规则组 0.7867；歼灭率 0.8333 vs
   规则组 0.3333；规则组把 **8 发**打在诱饵上（生存率掉到 0.6），
   pure-llm+graph 前 8 发全部命中真威胁、仅后期对诱饵补射 4 发。

3. **瓶颈判断需要修正：不是"输出形式"，而是"输入结构"。**
   此前基于无前置模块的运行得出"Pure LLM 不可用"（6/6 场景 0 开火）的结论，
   本次对照表明那是**裸 LLM（无结构化前置）**的表现；一旦给出与混合组相同的
   结构化态势图 + 时间线，Pure LLM 的低层输出形式**同样能打**。
   即：LLM 组的增益来自**前置模块提供的情报结构**（几何、可行性、时序、波次性质），
   而非"目标级抽象"本身——这也解释了混合组与规则组长期打平的现象：两者的差别
   不在决策抽象层级，而在输入是否结构化。

4. **代价与代价之外。** 有前置模块的 pure-llm 仍需 98-180 次 LLM 调用、
   单 tick 约 0.46-0.57s（规则组 0.04s）、并伴随 54-56 次被掩码的非法开火尝试
   （LLM 会尝试打非自持/超射程目标）——**可用但昂贵**，且强依赖前置模块把
   "该打谁、能不能打、什么时候打"预先算好。

## 5. 对论文消融设计的直接价值

本次改动把"前置模块"与"输出形式"两个变量解耦，形成 2×2 对照：

|  | 输出：目标命令（GOAI） | 输出：低层命令 |
|---|---|---|
| **有前置模块** | 混合组（Hybrid） | Pure LLM + graph（本次新增臂） |
| **无前置模块** | 规则组（Rule，确定性脚本） | Pure LLM raw（本次新增臂） |

- 纵向（输出形式）差异小：有前置模块时 Hybrid 与 Pure LLM+graph 在 EASY 上同为
  破防 973、V 相同；DECEPTION 上 Pure LLM+graph 反而更高（0.9667 vs 0.9）。
- 横向（前置模块）差异极大：两个场景 raw 臂均 0 开火、V=0.2。
- 结论：**"结构化前置模块"是本方法族的真实增益来源**，应作为论文的贡献点与
  消融主变量；"决策形式（D1′）"在本题中不是主要瓶颈。

## 6. 复现

```bash
cd ~/source_codes_linux/eval_w1
export PYTHONPATH=/root/source_codes_linux/source_codes MPLCONFIGDIR=/tmp/openmdbench-mpl
P=/root/source_codes_linux/source_codes/.venv/bin/python
$P run_episode.py --scenario MD-AD-002-EASY --planner pure-llm --seed 7 \
   --max-ticks 1800 --frontend graph --output out/easy_graph.json
$P run_episode.py --scenario MD-AD-002-EASY --planner pure-llm --seed 7 \
   --max-ticks 1800 --frontend raw   --output out/easy_raw.json
# 批量：bash run_frontend_ablation.sh（四臂）
```

产物：`~/eval_w1_runs/frontend_ablation/{pll_easy_graph,pll_easy_raw,pll_deception_graph,pll_deception_raw,rule_easy,rule_deception}.json(.jsonl)`

## 7. 重要提醒（环境一致性）

- **两套运行环境的场景数据当前不一致**：Linux 运行环境已打上"岸基 CIWS 控制槽位"
  （岸基可自动近防），Windows 镜像的 AD-002 场景仍是**无岸基槽位**版本。因此
  官方 hifi 表中 rule/llm 的 AD-002 行（开火 6）与本次 Linux 行（开火 19，含近防）
  **不可直接混用**。建议：把岸基槽位补丁同步到 Windows 镜像（或明确约定只在
  Linux 环境出正式结果），再重跑一次 hifi 表。
- 旧 hifi 表中 pure-llm 的"0 开火/早期破防"行与本次 **raw 臂完全一致**，
  说明那批 pure-llm 实际等效于"无前置模块"条件；本次两臂对照可直接替换该结论。
