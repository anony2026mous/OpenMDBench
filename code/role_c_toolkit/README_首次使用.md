# 角色 C 实验工具包：第一次使用

本目录应直接放在 `source-code-6.0/role_c_toolkit/`。研究对象是**游戏智能体**。脚本读取相邻的 `source-code/openmd` 中的 6.0 高保真引擎和 grid 游戏源码，不修改引擎、场景或权重；每个新批次写入新的输出目录。不要把历史结果目录复制到新机器当作本轮数据。

## 1. 先理解“能完成什么”

| 模块 | 工具包入口 | 可以报告的结论 |
|---|---|---|
| P0 版本与诱饵门禁 | `toolkit_doctor.py`、`toolkit_hifi_lock.py`、`p0_6_contacts.py`、`p0_6_summarize.py` | 来源、权重、公开提示和 IE-11 诱饵行为审计；无标签识骗须单独满足信息门禁 |
| P1 分层成绩 | `p1_6_campaign.py`、`p1_6_analyze.py`；grid 用 `grid_rolec6.py`、`grid_rolec6_analyze.py` | 同 seed 六臂比较，`P/E/I/B` 与两种混合架构盈亏；公式是成绩恒等式，不是定律本身的验证 |
| P2 Goal 接口 | 新建 weak/medium/strong 高保真批次，再运行 `toolkit_hifi_goal_compare.py`；grid 用 `grid_rolec6.py --goal-mode hold` | 整局接口操纵的成绩差；须另查 Goal/动作轨迹，不能称因果互信息 bit 值 |
| P3a 可靠性 | `p1_6_analyze.py` 和 grid 分析器 | 请求、空回复、解析失败、延迟等，须连同不合格局另报 |
| P3b 已知故障 | grid 的 `grid_factorial_campaign.py`；`experimental_hifi/` 保留历史高保真原型 | grid 可做已知故障注入和自身重放；高保真原型**尚未在 6.0 本包上通过复验**，不得直接称正式归因 |

**尚无可一键验收的正式 oracle 规划器/执行器或干预式因果互信息估计器。** 故即便跑完全部下述命令，也只能完成六臂成绩、诱饵行为、接口消融、可靠性及 grid 已知故障；论文中的“oracle 因果归因”和正式 (I_{do}(G;A\mid H)) 仍是待开发／独立验收项目，不可用四格成绩或被动 KSG 代替。详细的范围和规模见 `docs/hifi/` 的两份 6.0 规划。`docs/historical/` 是旧 grid/4.0 的规划、指南和复核报告，**不是 6.0 新结果**。

## 2. Windows 准备与只读预检

在 PowerShell 中进入 `source-code-6.0` 根目录。用可用的 Python 3.11 创建环境；不必沿用他人机器的绝对路径：

```powershell
Set-Location 'D:\Harness workspace\source-code-6.0'
py -3.11 -m venv .venv
$py = '.\.venv\Scripts\python.exe'
& $py -m pip install -r '.\source-code\openmd\code\requirements.txt'
& $py -m pip install -e '.\source-code\openmd\source-code\source_codes[core,train]'
& $py -m pip install scipy
& $py '.\role_c_toolkit\toolkit_doctor.py'
& $py '.\role_c_toolkit\toolkit_doctor.py' --probe-vllm --base-url 'http://172.18.116.170:8000/v1' --model 'Qwen3.8-27B'
```

`toolkit_doctor.py` 只检查文件/依赖；加 `--probe-vllm` 才发一条短请求。必须看到 6.0 高保真权重、grid 源码和本包自带的 `assets/mappo_medium_s42_best.pt`。这个 grid checkpoint 的 SHA-256 为 `223dbf740163b652f221a6ef0885d69b8c975c53378a7e63c05388e1df8cd0a8`；不要临时换权重补格。不同操作系统可改用本机 Python，保持输出清单中的版本记录。
工具包不依赖 `.git`；没有 Git 仓库时只记录 `GIT_UNAVAILABLE`，仍以逐文件 SHA-256 作为实验身份。

## 3. 高保真 P0/P1：先 3 seed，后决定是否 20 seed

以下 201–203 是先前最小设计的**示例 seed**；若已在本项目参与开发或看过成绩，应换成事先锁定、未使用的新 seed。`lock` 创建不可覆盖的新目录和 6.0 来源清单，**不启动局**。完整三场景的最小冒烟：

```powershell
$py = '.\.venv\Scripts\python.exe'
$kit = '.\role_c_toolkit'
$out = '.\role_c_toolkit\artifacts\hifi-strong-pilot-v1'
& $py "$kit\toolkit_hifi_lock.py" --output-dir $out `
  --scenario IE-04-COMBINED-ARMS --scenario IE-10-DUAL-AXIS-PINCER --scenario IE-11-DECOY-SCREEN `
  --seed 201 --seed 202 --seed 203 --goal-granularity strong `
  --base-url 'http://172.18.116.170:8000/v1' --model Qwen3.8-27B
& $py "$kit\p1_6_campaign.py" --output-dir $out --run-arm rule --run-arm rule-rl --run-arm rl
& $py "$kit\p1_6_analyze.py" --output-dir $out
```

廉价臂合格、端点和 D1 提示门禁过关后，**由操作者自己**执行 LLM 三臂；一格自然终局才会跳过，失败格不会被当成功：

```powershell
& $py "$kit\p1_6_campaign.py" --output-dir $out --run-arm llm --run-arm llm-rl --run-arm pure-llm
& $py "$kit\p1_6_analyze.py" --output-dir $out
```

只想先跑 IE-10，可加 `--scenario IE-10-DUAL-AXIS-PINCER`；`--run-arm` 只选本次运行，不改变锁定的六臂设计。每局保留 `*_manifest.json`、原始 `.json`、事件 `.jsonl`、`*_requests.jsonl`、控制台日志。看 `p1_missing_or_ineligible.json`、`p1_cells.csv`、`p1_summary.json`、`p1_reliability.json`。不得把中断局当完整局；代码、场景、模型或 checkpoint 改变时另建批次。脚本每个条件顺序执行，勿对同一目录启动两个 campaign 进程。

三场景完整方案应另建输出目录、预先锁定 20 个配对 seed（可把 `--seed` 参数由 PowerShell 循环组成）。**不要在已经锁定的 3-seed 目录中途增加 seed。** 6.0 默认参数：规划间隔 10 tick、RL 决策间隔 5 tick、最长 1800 tick、LLM 1024 token、Qwen/vLLM 关闭思考、纯 LLM 为 `executor` 包线。IE-11 的 `decoy_shots_authoritative` 是离线行为指标，不是识骗分类准确率；运行前仍须查实际提示和接触 ID 是否泄露标签。

## 4. 高保真 P2：接口档位

分别建全新 `weak` 和 `medium` 输出目录，选与 strong 相同的场景、seed、模型、端点和权重；每个目录的 `--goal-granularity` 与其目录名一致。先只跑廉价 `rule-rl`，确认 Goal 字段、编码和后续动作的档位差确实存在，再跑 `llm-rl`：

```powershell
$weak = '.\role_c_toolkit\artifacts\hifi-weak-pilot-v1'
& $py "$kit\toolkit_hifi_lock.py" --output-dir $weak `
  --scenario IE-10-DUAL-AXIS-PINCER --scenario IE-11-DECOY-SCREEN `
  --seed 201 --seed 202 --seed 203 --goal-granularity weak
& $py "$kit\p1_6_campaign.py" --output-dir $weak --run-arm rule-rl
& $py "$kit\p1_6_campaign.py" --output-dir $weak --run-arm llm-rl
& $py "$kit\p1_6_analyze.py" --output-dir $weak
& $py "$kit\toolkit_hifi_goal_compare.py" --strong $out --other $weak `
  --output '.\role_c_toolkit\artifacts\hifi-goal-pilot-comparison.json'
```

这只是整局消融。即使分数改变，也不能自动推出 (B_{if}) 或干预式因果互信息。`medium` 同法新建；正式 20-seed 阶段按规划决定是否做全档。

## 5. Grid：六臂、诱饵行为、接口和已知故障

Grid 源码在 `source-code/openmd/code/grid_env`，但 6.0 提交包不含 medium MAPPO `.pt`，本包已附所需 checkpoint。新 grid 的**六臂入口与反事实／重放入口均在实际 vLLM 请求中设置 `chat_template_kwargs.enable_thinking=false`**，请求日志也记录该设置；旧客户端在真实端点上曾把 4096 token 用完而返回空内容。因此它与历史 grid 批次不是同一 runner 版本，不可混接成绩。为了控制时长，下面把纯 LLM 调用间隔定为 10；历史每步调用间隔 1 是**另一种实验条件**，不能混表。

```powershell
$src = '.\source-code\openmd'
$ckpt = '.\role_c_toolkit\assets\mappo_medium_s42_best.pt'
$gridOut = '.\role_c_toolkit\artifacts\grid-medium-3seed-v1'
& $py "$kit\grid_rolec6.py" matrix --source $src --output $gridOut `
  --difficulty medium --task-mode continuous --checkpoint $ckpt `
  --base-url 'http://172.18.116.170:8000/v1' --model Qwen3.8-27B `
  --plan-interval 10 --pure-call-interval 10 `
  --seed 501 --seed 502 --seed 503 `
  --run-arm rule-rule --run-arm rule-rl --run-arm rl
& $py "$kit\grid_rolec6.py" matrix --source $src --output $gridOut `
  --difficulty medium --task-mode continuous --checkpoint $ckpt `
  --base-url 'http://172.18.116.170:8000/v1' --model Qwen3.8-27B `
  --plan-interval 10 --pure-call-interval 10 `
  --seed 501 --seed 502 --seed 503 --resume `
  --run-arm llm-rule --run-arm llm-rl --run-arm pure-llm
& $py "$kit\grid_rolec6_analyze.py" --matrix $gridOut `
  --output '.\role_c_toolkit\artifacts\grid-medium-3seed-analysis-v1'
```

P2 grid 接口消融：用**新目录**、相同 seed/来源/模型/checkpoint 及 `--goal-mode hold`，先跑 `rule-rl`，再视操纵门禁跑 `llm-rl`；然后将两个目录交给分析器。P3b 已知故障的 `clean/planner/executor/both` 四格和自身重放由 `grid_factorial_campaign.py` 及 `grid_factorial_fault.py` 实现；具体参数和审计步骤见 `docs/historical/GRID_角色C_6.0同口径实验使用指南.md`，但旧指南的绝对目录、seed 和调用间隔必须替换为本工具包的新目录/冻结参数。grid 的 P/E/I 是部署成绩核算；`grid_rolec6_counterfactual.py` 的参考替换仅为原型，参考策略没有独立 oracle 质量认证。

## 6. 高保真 P3b 试验入口（先过重放门禁）

`experimental_hifi/hifi_fault_campaign.py` 的规则路径已在 6.0 的 IE-10 上完成 **5 tick 接线及 dose-zero/0.25 自身重放冒烟**，两对重放精确；由于 5 tick 没有注入事件、也未自然终局，这**不等于故障效应验收**。如果团队要继续，先在一个新目录做单 seed、完整自然终局的规则路径，要求非零剂量实际触发事件、两条件自身重放 `exact_match=true`、审计无错误后，才扩至预注册 seed/剂量：

```powershell
$src = '.\source-code\openmd'
$fault = '.\role_c_toolkit\artifacts\hifi-rule-fault-pilot-v1'
& $py "$kit\experimental_hifi\hifi_fault_campaign.py" `
  --source $src --output $fault --scenario IE-10-DUAL-AXIS-PINCER `
  --seed 501 --case planner_wrong_contact --case executor_degradation `
  --dose 0.25 --ticks 1800 --interval 10 --require-terminal
```

这条命令会运行每个 case 的零剂量和 0.25 剂量原局及重放，不是一次单局；**先核对预计成本**。LLM 规划器版 `hifi_llm_fault_campaign.py` 尚未做真实 LLM 的 6.0 完整局验收，勿直接用作论文确认性证据。故障标签已知，不能称 oracle 反事实归因；剂量单调性必须由独立 seed 数据检验。

## 7. 运行安全与论文表述

- 不在同一冻结目录改变 seed 集、调用间隔、Goal 档位、模型或源码；失败重试保存新尝试，不覆盖原始证据。
- 输出含模型实际提示/回复；分享前审查敏感字段，但保留本地原始文件和哈希。
- `docs/hifi/` 包含两份正式 6.0 计划及 P0/P1 阶段报告；`docs/historical/` 收集此前 grid 与高保真测量规划、指南和风险复核。报告里的“已完成”是当时原机器的状态，不是复制本工具包后自动获得的新结果。
- 高保真 P3b、正式干预式因果 MI 和 oracle 归因目前缺少在 6.0 上独立验收的可移植实现；`experimental_hifi/` 只供适配研究，**首次使用者不要把它当作已冻结正式程序直接跑确认性实验**。
