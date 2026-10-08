# Grid 角色 C：6.0 同口径实验代码与操作指南

日期：2026-09-28。对象是**游戏智能体**的 grid 概念验证，不是 6.0 高保真引擎；这里的 `source-code-New-architecture/openmd` 仅作为保有 grid 游戏代码和 checkpoint 的**只读来源**，不把该目录中废弃的旧高保真引擎用于 6.0 结论。所有新代码和输出均在 `role_c_measurement/`。本指南定义运行方式，**不表示完整 grid 矩阵已经跑完**。现有修正批次结果及局限见 [v2 阶段实验报告](GRID_角色C_v2阶段实验报告_2026-09-28.md)。

## 1. 代码、对应问题与证据等级

| 文件 | 功能 | 与 6.0 方法的对应关系 |
|---|---|---|
| `grid_rolec6.py` | 一局或可续跑矩阵：六臂、原始请求、公开观测、Goal 和逐步动作；诱饵真值仅离线写入终局报告 | P0 信息门禁、P1 六臂主表、P2 strong/hold 接口操纵、P3a 可靠性 |
| `grid_rolec6_analyze.py` | 逐格来源/文件哈希/终局审计、六臂 `P/E/I/B`、同 seed 差、诱饵误打、请求统计、P2 配对与 P3b 汇总 | 使用与 6.0 相同的“仅合格自然终局入表、seed 为统计单位”原则 |
| `grid_rolec6_preflight.py` | 只读检查冻结批次的 runner、grid 源码、checkpoint 哈希，报告已合格和待运行的 seed/臂 | 不联网、不启动局；供操作者续跑前检查 |
| `grid_factorial_campaign.py`＋`grid_factorial_fault.py` | clean、规划故障、执行故障、双故障四条件，每格自身目标重放 | P3b 已知故障定位；不是独立 oracle 因果归因 |
| `grid_rolec6_counterfactual.py`＋扩展的 `grid_replay.py` | 原系统、自身重放、固定原目标＋参考执行器、参考规划器＋原执行器、双参考组件 | 可生成四条件参考替换差值；参考组件质量尚未经独立认证，不能标成 oracle 归因 |
| `test_grid_rolec6.py` | 公式、泄露门禁、纯 LLM 调用间隔、归因失败门禁单测 | 代码行为检查，不代替统计验收 |

当前六臂映射：`rule-rule`＝规则规划＋GOAI 规则执行；`llm-rule`＝LLM 规划＋GOAI 规则执行；`rule-rl`＝规则规划＋已训练 MAPPO 目标条件执行；`llm-rl`＝LLM 规划＋同一指定 MAPPO checkpoint；`rl`＝同一 checkpoint 的纯 MAPPO；`pure-llm`＝LLM 直接动作。四格 `P/E/I` 仅为这组**部署系统的成绩核算**；其结果与参考替换实验的归因量分开存放，不允许因符号相似而混算。

## 2. 前置条件与冻结清单

在 PowerShell 设置路径（按本机实际位置调整）：

```powershell
$root = 'D:\Harness workspace\source-code-New-architecture'
$py = Join-Path $root '.venv\Scripts\python.exe'
$grid = Join-Path $root 'openmd'
$runner = Join-Path $root 'role_c_measurement\grid_rolec6.py'
$analyzer = Join-Path $root 'role_c_measurement\grid_rolec6_analyze.py'
$ckpt = Join-Path $grid 'code\checkpoints\mappo_medium_s42_best.pt'
& $py -B -m unittest discover -s (Join-Path $root 'role_c_measurement') -p 'test_grid_rolec6.py' -v
# 也可运行全部 grid 相关测试；两个归档来源的加载已由新测试子进程隔离：
& $py -B -m unittest discover -s (Join-Path $root 'role_c_measurement') -p 'test_grid_*.py' -v
```

已在本机验证 `.venv`、grid 源文件和 medium checkpoint 存在。若虚拟环境缺依赖，至少需要 `numpy`、`scipy`、`requests`、`torch`；**不要自动下载或换用未登记 checkpoint**。每个矩阵的 `campaign.json` 固定来源代码哈希、checkpoint 哈希、模型地址/名称、运行参数、runner 哈希及 seed。运行中修改源代码或升级模型，将形成新实验版本，不能用 `--resume` 混接。

当前 runner 的矩阵身份未单列 HTTP `--llm-timeout`/`--llm-retries`。现有 v2 批次使用默认 **120 秒 / 2 次重试**；续跑必须保持这两个默认值（下面的命令不传这两个选项），并在最终报告中注明。若要改它们，不能把结果无标签地混入 v2；须新建实验版本并复核运行记录。为保持现有 v2 runner 哈希，本轮不修改其冻结实现。

LLM 局必须显式指定端点和模型，例如 `$url='http://172.18.116.170:8000/v1'`、`$model='Qwen3.8-27B'`。开始前先用 `Invoke-RestMethod -Uri "$url/models" -TimeoutSec 10` 检查；2026-09-28 再次检查时 `GET /v1/models` 已成功返回 `Qwen3.8-27B`，但这**只证明模型列表可达，不证明聊天请求或完整局已通过**。按使用者要求，助手已停止一次两步真实模型冒烟；其独立目录 `artifacts/grid-rolec6-live-llmrule-s901-smoke-v1/` 只有不完整的请求日志，没有 `episode.json`，不属于正式矩阵，也不得入分析。如果端点不可达，先跑规则/RL 的便宜门禁，不要把模拟回复测试当真实 LLM 结果。请求文件保存原始 prompt/response；公开数据前复核敏感信息，不保存 API key。

代码级离线测试以模拟 HTTP 响应走通 `/chat/completions` 请求体、响应解析及原始请求/回复日志；**没有代替真实 vLLM 完整局**。实际启动前建议由操作者自己先完成下节的一局真实 LLM 自然终局冒烟。

确认性 seed 必须先核查没有参加此前的场景、剂量、模型或公式开发。历史 grid 已用过 100–144；`401–420` 已用于本指南对应的 v1 廉价臂与 Goal 消融，以及修正诱饵统计口径后的 v2 复测，**不再是独立的新 seed/盲测集**。v2 只能称同 seed 重新测量，尤其不能用它独立确认已看过的 D1 结果。新的理论或诱饵结论应另锁未参与开发的 seed 区块。先锁定 seed 和 checkpoint，再看结果，不因正负方向筛选。

## 3. P0：公开信息门禁与单局冒烟

使用新输出目录，先跑便宜的自然终局：

```powershell
& $py -B $runner run --source $grid --output (Join-Path $root 'role_c_measurement\artifacts\grid-rolec6-p0-rule-s901') --seed 901 --arm rule-rule --difficulty medium --task-mode continuous
```

`episode.json` 的 `complete=true`、`aborted=null`、`d1.input_role_truth_leaks=[]` 才表示该局公开观测未直接暴露真值字段或角色词。对 LLM 臂还要看 `d1.prompt_role_truth_leaks=[]` 和 `requests.jsonl` 的**实际发送文本**；P0“没有直接泄题”只允许开始能力实验，不能证明自主识骗。`--max-steps 2` 可做短跑，但会得到 `complete=false`、命令退出码 1，**不可入 P1 主表**。离线 `d1.truth_labeled_offline_only` 用于评判是否击中诱饵，绝不传给智能体。

## 4. P1：六臂同 seed 完整局与诱饵行为

先用 2–3 个此前未使用的 seed 冒烟，确定端点、checkpoint、模型输出均可用后再发起确认矩阵。以下是一组命令模板：

```powershell
$url = 'http://172.18.116.170:8000/v1'
$model = 'Qwen3.8-27B'
# 单局真实模型冒烟：目录必须不存在；检查 episode.json 的 complete、
# aborted、d1.prompt_role_truth_leaks、requests.jsonl 的 request/response 成对情况。
& $py -B $runner run --source $grid --output (Join-Path $root 'role_c_measurement\artifacts\grid-rolec6-live-llmrule-s902-pilot') --seed 902 --arm llm-rule --difficulty medium --task-mode continuous --base-url $url --model $model --plan-interval 10

# 若要另做三 seed 六臂 pilot，使用全新目录：
$pilot = Join-Path $root 'role_c_measurement\artifacts\grid-rolec6-medium-pilot-v1'
& $py -B $runner matrix --source $grid --output $pilot --difficulty medium --task-mode continuous --checkpoint $ckpt --base-url $url --model $model --plan-interval 10 --pure-call-interval 1 --seed 901 --seed 902 --seed 903
```

未给 `--arm` 时锁定六臂。推荐第一次就锁六臂设计，但用重复的 `--run-arm rule-rule --run-arm rule-rl --run-arm rl` **只执行廉价臂**；端点恢复后，保留全部原参数与 seed，使用 `--resume --run-arm llm-rule --run-arm llm-rl --run-arm pure-llm` 补三条昂贵臂。`--run-arm` 只选择本次队列，不改变 `campaign.json`；相反，`--arm` 会改变冻结设计，不得在同一目录增减。每格独立子进程，完成后留 `episode.json`、`events.jsonl`，LLM 臂另留 `requests.jsonl`，控制台输出保存在 `*.console.txt`。重试生成 `_a2` 等新目录，不覆盖旧 `_a1`；分析按最早合格尝试入表。若代码/来源/配置变化，恢复会拒绝，必须新建批次。

完整规模必须另建一个**全新输出目录**，不可把三 seed pilot 原目录扩成二十 seed（`campaign.json` 已锁 seed 集）。下面是**已经存在的 v2 401–420 批次**的精确续跑命令；这 20 个 seed 已被使用，不是独立确认集。PowerShell 生成重复参数：

```powershell
$seedArgs = @()
foreach ($s in 401..420) { $seedArgs += @('--seed', [string]$s) }
$main = Join-Path $root 'role_c_measurement\artifacts\grid-rolec6-medium-20seed-v2'
# 只读预检：ready_to_resume=true 才继续；不会调用模型或运行仿真。
& $py -B (Join-Path $root 'role_c_measurement\grid_rolec6_preflight.py') --campaign $main
# 三条廉价臂已完成。端点可用时在同一冻结批次补三条真实 LLM 臂：
& $py -B $runner matrix --source $grid --output $main --difficulty medium --task-mode continuous --checkpoint $ckpt --base-url $url --model $model --plan-interval 10 --pure-call-interval 1 --resume --run-arm llm-rule --run-arm llm-rl --run-arm pure-llm @seedArgs
```

上一条命令将顺序执行 20 seed × 3 个 LLM 臂，不是只跑一局。若希望分段控制，可在三次独立调用中分别只保留一个 `--run-arm llm-rule`、`--run-arm llm-rl` 或 `--run-arm pure-llm`，其余冻结参数和**全部 20 个 `--seed`**保持原样并保留 `--resume`。每次调用只运行尚未认证的格；单格失败会留下 `_a1`，下次续跑生成 `_a2`，不覆盖旧证据。不要为了少跑几局而只给部分 seed：那会触发 campaign 身份不匹配；真正单 seed 测试请用独立的 `run` 输出目录。

若要新建真正未参与开发的确认批次，先核查并锁定新 seed，换一个尚不存在的输出目录；首次运行不加 `--resume`，先用三个 `--run-arm` 执行廉价臂，后续参数、seed、代码、模型和 checkpoint 完全相同时才用 `--resume` 补 LLM 臂。不能把 v2 的 401–420 改称新 holdout。

若要比较难度或结构性耦合，分别用新的 `$main` 跑 `--difficulty medium|complex`、`--task-mode independent|sequential|continuous`；每个条件单独编号和哈希，不在同一个矩阵里混合。`pure-llm` 默认**每步请求一次**，单局最多约 150 次，可能非常耗时；要改变调用间隔必须另起实验版本，不可与间隔 1 的结果无标签合并。runner 在外置包装器里修正了旧 `PureLLMAgent` 的 `step % 1 == 1` 调度错误，实际采用 `(step-1) % interval == 0`；源项目代码未修改，报告保留修正规则。

结果的 D1 量是公开条件下的**行为代理**：`feint_hits`、`real_hits`、被观察到的诱饵数及目标分母。`feint_hits` 只统计离线真值为假的 `red_transport` 命中，**不包括 `red_scout`**；旧 v1 初版汇总把侦察目标误计入诱饵命中，须使用 `grid-rolec6-medium-20seed-analysis-v1-corrected` 的重新审计结果或运行修正后的 v2，不能引用旧汇总的 D1 数字。它不是预定时点的真/假分类器准确率；不能只见少打诱饵就宣布达到原稿的 85% 自主识骗阈值。`V` 使用原引擎 `blue_score`，只有 `env.done` 自然终局才入表。

分析命令：

```powershell
$analysis = Join-Path $root 'role_c_measurement\artifacts\grid-rolec6-medium-analysis-v1'
& $py -B $analyzer --matrix $main --output $analysis
```

打开 `summary.json` 看 `expected/eligible`、逐 seed 分数、`d1`、`reliability` 和 `formula`；`cells.csv` 可用 Excel 查看。分析器对真实 LLM 局还会独立复核原始日志中的请求/回复是否逐次成对、模型/端点是否一致、提示中是否出现直接真值字段或诱饵 ID；不合格局不会入主表。只有六臂在同一 seed 集全部齐全时才计算 `P/E/I/V_m/B/ΔV_A/ΔV_B`。这些是 `ΔV_A=P−B`、`ΔV_B=P+E+I−B` 的**代数核算**，不是“验证定律”。`summary.json` 同时列逐 seed 最强纯臂差值，避免均值赢家和每个 seed 赢家混淆。

## 5. P2：Goal 接口干预

先用廉价 `rule-rl` 检查操纵是否真的通过 broker 并改变动作；随后才考虑昂贵的 `llm-rl`。`strong` 是原始 Goal，`hold` 将每次提交的 Goal 改成各单位合法的中性 hold；它是**强接口对中性目标的消融**，不是 grid 原生 weak/medium/strong 三档，也不是信息论中的 `B_if` bit 值。两个矩阵必须固定场景、seed、checkpoint、规划间隔、LLM 模型和端点：

```powershell
$strong = Join-Path $root 'role_c_measurement\artifacts\grid-rolec6-p2-strong-v1'
$hold = Join-Path $root 'role_c_measurement\artifacts\grid-rolec6-p2-hold-v1'
& $py -B $runner matrix --source $grid --output $strong --arm rule-rl --checkpoint $ckpt --seed 401 --seed 402 --seed 403 --goal-mode strong
& $py -B $runner matrix --source $grid --output $hold --arm rule-rl --checkpoint $ckpt --seed 401 --seed 402 --seed 403 --goal-mode hold
& $py -B $analyzer --matrix $strong --goal-comparator $hold --output (Join-Path $root 'role_c_measurement\artifacts\grid-rolec6-p2-analysis-v1')
```

只有分析输出 `p2.manipulation_pass=true`、`hold_rejected_goals=0`，且 `first_action_difference_step` 非空，才说明这组配对中目标改变触达了执行层。`llm-rl` 的对照另用新目录、同样两臂参数加 `--base-url $url --model $model`，并锁定 `--plan-interval`。整局分叉后 LLM 后续提示也可能变化，因此 `delta_V_strong_minus_hold` 是**接口消融的系统总效应**；不能把它叫“仅改一条 Goal 的直接效应”或因果 MI。

## 6. P3a/P3b：可靠性、已知故障与参考替换

P3a 直接复用 P1/P2 的 `requests.jsonl` 与 `agent_stats`：原始请求数、空回复、API 错误、fallback、p50/p95 延迟分别记录。引擎未提供与 6.0 高保真同名的“旧计划沿用”计数，**不能默认填 0**；纯 LLM 在非调用步保留上次动作是设计行为，不是规划故障。

P3b 先采用现有的四格**已知故障**注入；每格都做原目标/动作的自身重放，只有全部匹配才解释配对损失。下面仅展示一个 seed 的命令；正式实验需锁定新 seed、剂量及效应验收，并保留零事件和反向 seed：

```powershell
$fault = Join-Path $root 'role_c_measurement\artifacts\grid-rolec6-p3b-v1'
& $py -B (Join-Path $root 'role_c_measurement\grid_factorial_campaign.py') --source $grid --output $fault --seed 421 --seed 422 --seed 423 --difficulty medium --task-mode continuous --interval 10 --planner-dose 0.25 --executor-dose 0.25
& $py -B $analyzer --matrix $main --fault-summary (Join-Path $fault 'summary.json') --output (Join-Path $root 'role_c_measurement\artifacts\grid-rolec6-main-plus-fault-analysis-v1')
```

`p3b.replay_gate_pass` 为真只证明同配置自身重放；`planning_fault_loss`、`execution_fault_loss` 和 `nonadditivity` 是**已知注入标签的差值**。本次 421–440 的 20-seed 四格注入与 80 次自身重放全通过技术门禁，但规划/执行损失的探索性区间均跨零，不能由此声称 5/5 故障定位、稳定瓶颈或严格剂量单调。旧 grid A10 的 20-seed 严格剂量门也已失败，不得沿用原稿的成功表述。

若要实现原论文式参考组件反事实，独立运行以下命令（会额外生成五局，其中 `reference_executor` 固定原决策时间线）：

```powershell
& $py -B (Join-Path $root 'role_c_measurement\grid_rolec6_counterfactual.py') --source $grid --output (Join-Path $root 'role_c_measurement\artifacts\grid-rolec6-reference-s401') --seed 401 --difficulty medium --task-mode continuous --planner rule --executor mappo --checkpoint $ckpt --interval 10
```

可将 `--planner rule` 换成 `--planner llm --base-url $url --model $model`，但这是昂贵的真实模型运行，须先保证端点可用。`summary.json` 给出正向参考改善 `V_P−V_0`、`V_E−V_0` 及四格交互。**当前归档参考规划器/执行器尚未被独立单域试验证明为有效 oracle，输出明确设 `oracle_causal_attribution_validated=false`**；即便自身重放通过，也只能称“参考替换差值”。分叉后的外生随机流如果没有逐事件对齐，不能宣称精确逐事件反事实。

## 7. 本次代码验证与停止规则

本次已验证：新代码语法通过；11 项定向单测、全部 26 项 grid 测试通过；只读预检对 v2 报告 `ready_to_resume=true`、60/120 合格格、三个 LLM 臂各待 20 格；修正后的分析器重审既有 v2 批次仍为 60/120 合格格；规则臂自然终局分析合格；`rule-rl` strong/hold 一 seed 配对中 hold Goal 被接受且动作在第 2 步分叉；规则＋MAPPO 五条件参考替换的自身重放通过。模拟响应下 LLM＋MAPPO 路径也能自然终局，但这不是实际模型测试。修正口径的 v2 批次含 `401–420` 的廉价臂 60 局及 Goal hold 20 局，均自然终局；P2 20/20 对 Goal 改变触达动作，平均 strong-minus-hold 为 +0.6067，18 正、1 零、1 负。`421–440` 的已知故障四格 80 局及自身重放也全部合格，但故障损失方向不稳定。详见 [v2 阶段报告](GRID_角色C_v2阶段实验报告_2026-09-28.md)。这些仍**不是完整角色 C 实证**；vLLM 模型列表现已可达，但真实聊天完整局尚未验收，所以真实 LLM 臂、完整六臂 D1/P1、LLM 接口干预、多场景公式独立检验和目标 LLM+RL 的正式归因仍未验收。

任何情况出现来源哈希或 checkpoint 不一致、公开观测/真实请求泄露隐藏角色真值、LLM 端点不可用、自然终局缺失、hold 被拒绝、目标/动作无差异、自身重放失败、参考质量不合格时，停止相应因果主张；保存原始失败文件，不能填零、筛 seed、换场景或用旧版本结果补格。
