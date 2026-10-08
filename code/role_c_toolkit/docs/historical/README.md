# 角色 C：测量方法实现与阶段性实验

2026-09-28 新增 **grid 角色 C 六臂／诱饵／接口／归因统一入口**：请优先阅读 [GRID_角色C_6.0同口径实验使用指南.md](GRID_角色C_6.0同口径实验使用指南.md)。新脚本为 `grid_rolec6.py`、`grid_rolec6_analyze.py`、`grid_rolec6_counterfactual.py`，依赖本目录既有的 `grid_replay.py` 与 `grid_factorial_campaign.py`；grid 游戏源码和权重只读。此代码入口**不表示 20-seed 或真实 LLM 完整实验已经结束**。下文是此前各日期的历史进展记录，不应覆盖新指南的当前操作口径。

运行环境更新（2026-09-24）：已按用户授权建立 Windows Python 3.11.0rc2 的工作区 `.venv`，核心依赖和 IE-01 两 tick 冒烟通过。此前“只能使用 WSL/缺少可用 Windows 解释器”的判断已纠正；详见 [Windows 虚拟环境说明](<D:/Harness workspace/source-code-New-architecture/role_c_measurement/Windows虚拟环境说明.md>)。有限冒烟不等于完整实验完成。

2026-09-25 最新接续状态请先看 [实验接续进展](<D:/Harness workspace/source-code-New-architecture/role_c_measurement/实验接续进展_2026-09-25.md>)。HIFI IE01/02各六个rule tier seeds已完成36/144配对；IE03 seeds101–106三档均已完成并独立审计通过，progress.json为54/144，已进入IE04 seed101。六seed支持快照纳入IE03后仍39/39 unit×tier不可估（n=4,392、k=29、稀有类别支持5–6），null不可当作0。全批仍为planner=rule，不能替代LLM+GOAI；用户确认目标vLLM地址为`localhost:33606/v1`，本轮TCP探测仍不可达。Grid A10 20-seed六臂注入holdout已独立审计通过，但严格剂量响应门未通过；离散位置通道分析显示三种task-mode在60/60同seed×interval组没有改变己方Goal/动作/状态轨迹。高保真LLM fault campaign新增`--paper-table3`精确五处理臂与三类零剂量对照（8个唯一case-dose格）及审计字段，7项定向单测通过；该campaign尚未接入真实LLM运行。正式full B_if/D3与混合架构归因验证仍未完成。以下早期段落按其发生时点作为历史证据保留。

当前状态：**完整 grid + IE-01～IE-08 的新测量/归因注入任务尚未完成**。已完成通用估计器校准、旧轨迹重分析、grid 20-seed 多臂批次、A10 归因注入 holdout，以及 4.0 HIFI seed100 和 IE01/02 部分六 seed rule 基线轨迹。Grid 有限离散位置投影提供 20-seed 描述区间，但既非 full B_if/KSG，且轨迹单例格偏高；HIFI 规则 trace 混合估计全 null。Grid A10 严格剂量门失败，rule HIFI 样本也不是论文目标混合架构。参考组件质量、full B_if 编码/D3、真实 hybrid HIFI 八场景及完整归因验收仍未通过。

2026-09-24 新增：IE-01～IE-08 已在 seed 100 的早期决策锚点完成“规则 Goal／中性 hold Goal”配对干预可行性检查，各场景原始 checkpoint 与重复对照门禁通过且动作批有变化；见 [高保真配对 Goal 干预核验](<D:/Harness workspace/source-code-New-architecture/role_c_measurement/高保真配对Goal干预可行性核验.md>)。这不是正式 (I_{do}) 或 (B_{if}) 估计。完整时段补跑中的墙钟看门狗问题与新运行配置见 [高保真记录层计时诊断](<D:/Harness workspace/source-code-New-architecture/role_c_measurement/高保真记录层计时诊断.md>)；不能把中止报告列作终局验收。

Grid 新增 20 seed × 3 task mode 的 step 6 配对 Goal/hold 探针，60/60 配对门禁和动作响应通过，独立审计无错误；详见 [Grid 配对 Goal 干预初步结果](<D:/Harness workspace/source-code-New-architecture/role_c_measurement/grid配对Goal干预初步结果.md>)。它只检验局部因果响应，不修复正式 B_if/D3 与 oracle 质量门禁。

高保真三档 Goal 字段的机制预检见 [weak／medium／strong 操纵预检](<D:/Harness workspace/source-code-New-architecture/role_c_measurement/高保真三档Goal接口操纵预检.md>)：IE-04 的早期开火窗口出现相邻档动作差异且独立审计通过；IE-01 早期窗口没有 medium→strong 动作差异，并存在 strong Goal 拒绝。两例都不构成正式 D3 统计验收。

已对现有配对探针计算有限、均匀干预集合下、**条件于完整 checkpoint** 的[局部互信息](<D:/Harness workspace/source-code-New-architecture/role_c_measurement/配对干预局部互信息解释.md>)。二元 Goal/hold 对照只要动作不同就饱和为 1 bit；该量既不等于只条件于可见观测的因果互信息，也不同于论文 KSG B_if，不能用来补填正式测量值。

历史 seed100 完整时段复现：IE-01～IE-08 的原运行与固定 Goal 回放均已自然终局并完成对应独立审计；IE-04 使用检查点间隔 50、显式 300 秒单步墙钟看门狗，详见 [记录层诊断](<D:/Harness workspace/source-code-New-architecture/role_c_measurement/高保真记录层计时诊断.md>)。这证明引擎记录/回放链路可用，不是正式 B_if 或归因注入验收。当前继续运行的是新的 weak/medium/strong rule tier 多 seed campaign，进度以 `artifacts/hifi-tier-ie01-08-s101-106-v1/progress.json` 为准。

`run_offline.py` 只做离线分析。`grid_replay.py` 和 `grid_campaign.py` 运行源项目已有游戏组件并记录完整接口，未修改源策略、引擎或评分；未连接 LLM，不覆盖历史实验结果。

## 已实现

- `information.py`：连续变量 KSG-1、离散经验互信息、完整分层质量检查、历史互信息差量、按 seed 重抽样。
- `attribution_math.py`：保留原论文符号与正向缺口符号的明确映射；区分策略替换和固定序列回放；不把代数恒等式当作因果验证。
- `test_methods.py`：20 项单元测试，包含暴力邻居计数对照、解析真值、XOR 区分反例、稀疏分层、缺失值、重复点和归因符号检查。
- `run_offline.py`：20 个 seed 的估计器校准及两份 grid 档案的投影互信息重分析；高保真结果只登记数据可用性。
- `grid_replay.py`：完整目标/状态/生命周期记录、固定决策回放、逐步环境（含 RNG）/broker/动作哈希比对；9 项新增测试。
- `grid_campaign.py`：20-seed 三档决策间隔与参考组件归因批次，严格保留正式验收未通过状态。
- `audit_grid_campaign.py`：逐文件核验新批次、检查稀疏状态退化、跨模式轨迹重复、单 seed 分类与剂量差异。
- `mixed_information.py`、`calibrate_mixed.py`：严格的离散—连续 Ross MI 与独立合成校准；新增 13 项测试，总计 42 项通过。见 [混合类型互信息校准说明](<D:/Harness workspace/source-code-New-architecture/role_c_measurement/混合类型互信息校准说明.md>)。不替代已冻结的场景测量，不把格点变量当连续变量。

最新结果见 [grid 新实验与高保真接续报告](<D:/Harness workspace/source-code-New-architecture/role_c_measurement/grid新实验与高保真接续报告.md>)。不要把“700 次运行完成”表述成“论文实验验证通过”。

高保真最新进展见 [八场景记录与回放验证报告](<D:/Harness workspace/source-code-New-architecture/role_c_measurement/高保真八场景记录与回放验证报告.md>)。新增 `hifi_trace.py`、`hifi_baseline.py`、`hifi_replay_campaign.py` 和 `audit_hifi_traces.py`；当前全部测试共 60 项，通过范围和未完成项均在报告中列明。

后续进展：IE-01 已完成 tick 41 实际终局的原运行与一致回放，新增终局证据检查后测试为 62 项通过；八场景单 seed 完整时段批次已启动。运行状态与参考组件核查见 [完整时段接续说明](<D:/Harness workspace/source-code-New-architecture/role_c_measurement/高保真完整时段接续与参考组件核查.md>)，不能把启动状态误认为已完成。

## 方法口径

### 直接 B_if 与历史代理量分开

论文 `OpenMDBench0830.md` §5.2 的文字定义对应直接目标—状态互信息 `I(G; S)`。实现必须同时声明 G 和 S 的编码、采样单位和时间关系。互信息衡量关联，并不单独识别因果方向；也不能不加说明地称为 Shannon 信道容量或 bits/s。

现有 `coupling_mi.py` 实际计算 `I(X;Y) - I(X;Y|G)`，本目录将它单独命名为 `co_information_not_direct_B_if`，保留负值，不与直接 B_if 混报。

一个完全离散的 XOR 反例已写入测试：独立二元 X、Y，令 G=X xor Y，则 `I(G;(X,Y))=1 bit`，但 `I(X;Y)-I(X;Y|G)=-1 bit`。因此两种定义不等价，也不能通过把负值截成零使它们等价。

### 连续与离散变量分开

普通 KSG-1 面向连续变量的联合密度；目标类型/ID 不能仅编码成整数后当连续距离使用。`information.py` 拒绝重复联合样本，不用隐式抖动掩盖格点或离散变量问题。拒绝不代表零互信息。

KSG 严格邻域计数中，若树查询的计数已经包含样本自身，公式应使用 `digamma(count)`；不能再用 `digamma(count+1)`。新实现用独立的暴力距离矩阵对照验证计数。

离散轨迹使用单独命名的经验互信息，披露占用联合格数和单样本格比例。高维/稀疏情形会有上偏，经验值为正不等于测得可靠信息流。混合变量 Ross 估计器已在独立合成分布完成基础校准，但正式场景编码与适用性仍待验证；当前代码没有将离散结果或 Ross 结果冒充普通连续 KSG 结果。

方法依据：[Kraskov 等，2004](https://arxiv.org/abs/cond-mat/0305641)；混合类型问题参见 [Ross，2014](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0087357)。

### 条件互信息不丢失概率质量

当某些离散条件组样本不足时，不能丢掉它们、重归一化剩余组，再当作原总体条件互信息。新实现返回 null、覆盖质量及失败组统计。旧实现的这类处理只能保留作历史方法记录，不能认定必然“保守”。

### 归因符号与设计标签

正向参考缺口约定为：

```text
ΔP_gap = V_P - V_0
ΔE_gap = V_E - V_0
ΔI = V_full - V_P - V_E + V_0
ΔP_gap + ΔE_gap + ΔI = V_full - V_0
```

论文 §5.1 中的 ΔP、ΔE 是上述 gap 的相反数。输出同时保留两种明确命名，避免把负号差异解释为实验方向变化。重匹配项 β 和更正后的交互项也单列。

现有 `attribution.py` 的 `V_E` 通过重新运行规划策略得到，并未读取和固定原始决策序列。其重复 V0 配置检查是重复运行一致性，不足以证明固定决策回放一致性。本轮未将其改名为已经通过论文回放门禁。

## 本次结果的解释边界

输出：[阶段性测量报告](<D:/Harness workspace/source-code-New-architecture/role_c_measurement/artifacts/method-calibration-v1/阶段性测量报告.md>)。

- 估计器校准：seeds 100–119，连续高斯样本每 seed 2000 对，相关系数 0、0.5、0.9；解析真值已知。
- 旧 grid 轨迹：两份输入文件各 108 条 episode 记录；每条分析两种固定表示，因此输出 432 条表示级记录，不是新增 432 局游戏。
- 现存 grid 数据记录的是单个 UAV 活动目标在一步开始时的投影及第一艘 USV/UAV 在该步结束时的位置，不能还原整个多智能体接口。无目标的显式 null 与缺失字段严格区别。
- 某些实体死亡会记录零坐标，但旧轨迹没有完整生命周期标记；不能从 `(0,0)` 反推它一定死亡或一定真实位于原点。
- 原始格点位置与 5 格分箱均展示，不根据哪种结果更好来选择。循环平移是保持时序形状的诊断，不在未验证平稳性的情况下提供显著性 p 值。
- 汇总重抽样单位为 seed，不把同局时间步当独立实验。只有一个 seed 时不给伪造的跨 seed 区间。
- 高保真八场景摘要尚不足以计算目标—状态配对互信息；`hifi_trace_readiness.json` 明确记录未完成状态，而不是填零。

## 复现

使用当前已安装的 Python、NumPy 和 SciPy，在工作区根目录执行：

```powershell
python -B -m unittest discover -s role_c_measurement -p test_methods.py -v
python -B role_c_measurement/run_offline.py --source 'D:/Harness workspace/source-code-4.0/source-code/openmd' --output 'D:/Harness workspace/source-code-New-architecture/role_c_measurement/artifacts/新的输出目录'
```

输出目录必须不存在；代码拒绝写入源项目。`manifest.json` 保存依赖版本、论文/分工/相关源码哈希及本目录代码哈希。

## 尚需完成的原目标工作

1. 为新运行记录完整且时间对齐的目标、状态和生命周期数据；固定版本及编码。
2. 验证三档干预没有破坏命令合法性，并明确实际改变的变量。
3. 完成 grid 和高保真场景的新测量，按 seed 统计，不混用旧投影代理量。
4. 实现并验证原始决策序列回放，独立核验参考组件，再完成真实场景的软件故障注入与剂量验证。
5. 汇总全部结果、失败和局限；上述数学校准不能替代这些验收项。

上述第 1、4 项的 grid 轨迹采集与固定回放部分已完成：新批次 300 个自身回放全部一致；独立参考组件质量、正式互信息编码、高保真适配和 LLM 组仍待完成。
