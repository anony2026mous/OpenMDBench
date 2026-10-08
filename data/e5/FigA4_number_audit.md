# Fig. A4（E5 自然失败 pilot）数值核对说明

> 回应："这 4 行数值是我从 Fig.A4 图上读出的，建议让肖棹对一下原始 pilot 日志，确认没有 OCR / 抄录误差。"
> 结论：**已对原始归因日志逐项核对，12 行全部一致，被点名的小量行无任何抄录或 OCR 误差。**

## 1. 这是哪个任务的数据

| 项 | 内容 |
|---|---|
| 实验 | **E5 自然失败盲标 pilot**（paper-E5-natural-failures） |
| 图 | `figA4_natural_failure_pilot.pdf`（附录图 A4） |
| 数据表 | `data/figA4_natural_failure_pilot_12.csv`（12 行） |
| 用例来源 | HiFi 8 例（IE-03 surface-raid 与 IE-08 island-strike 各 4 个 seed）+ Grid 3 例（seeds 5201/5202/5204），共 11 个原始 episode；另有 1 例（E5-03）来自更晚的重跑 |
| 汇总文件 | `kappa_summary.json`（`n_cases=12`、`kappa=0.25`、一致 4/12、两侧标签分布） |
| 原始日志 | 服务器 `experiments/e5-hifi-natural-failures-*`、`e5-hifi-attribution-r3b-*`、`e5-grid-natural-failures-*` 下的 `attribution.json` / `summary.json` |

## 2. 被点名的 4 行：ΔE 与原始日志逐项一致

老师在图上读到的是 **ΔE 列**的小量（图中显示两位小数）。这 4 行是：

| 用例 | 原始 episode | ΔP（图/原始） | **ΔE（图/原始）** | ΔI（图/原始） | machine 标签 | 原始来源文件 |
|---|---|---|---|---|---|---|
| E5-02 | IE-08 s5102 | +0.0091 / +0.0091 | **+0.0320 / +0.0320** | +0.3484 / +0.3484 | interface | `attribution.json`(r2) |
| E5-05 | IE-08 s5103 | −0.0064 / −0.0064 | **+0.0754 / +0.0754** | +0.2223 / +0.2223 | interface | `attribution.json`(r2) |
| E5-07 | IE-03 s5105 | +0.0000 / +0.0000 | **+0.0095 / +0.0095** | +0.4026 / +0.4026 | interface | `attribution.json`(r2) |
| E5-11 | IE-08 s5104 | +0.0182 / +0.0182 | **−0.0221 / −0.0221** | +0.1726 / +0.1726 | interface | `attribution.json`(r2) |

**四行的 ΔE 与原始日志完全相同**（差异 < 5×10⁻⁵，即图上的两位小数就是原始值的四舍五入）。
图中数值不是手抄的：`make_figs_A2_A4.py` 直接从 CSV 读取并用 `f"{dv:+.2f}"` 格式化，
**图上不存在第二个数值来源**，因此不存在"从图上读数再录回表"的环节。

## 3. 老师的第二个判断也成立

这 4 行的 ΔE（0.0095–0.0754）**远小于同行的 |ΔI|**（0.1726–0.4026），
而 machine 标签规则是 `argmax(ΔP, ΔE, |ΔI|)`（图脚本第 148–151 行）。

因此即使 ΔE 有 0.01 级偏差，**任何一个标签都不会改变**——这与老师说的"machine 标签都不会变"一致。

## 4. 核对做了三层，不是一层

| 层 | 检查内容 | 结果 |
|---|---|---|
| ① 图 ↔ 汇总 | 图 CSV 的 12 行 × 3 列 + 标签 vs `kappa_summary.json` | **12/12 一致** |
| ② 汇总 ↔ 原始分 | `ΔP = reference_planner − self_replay`、`ΔE = reference_executor − self_replay` 由四个参考分复算 | **ΔP 12/12、ΔE 12/12 命中** |
| ③ 图 ↔ 原始日志 | 12 行 vs 服务器 `attribution.json` 自带的 `delta_planning/delta_execution/delta_interface`（grid 用 `summary.json` 的 `reference_improvement_*` / `reference_nonadditivity`） | **12/12 一致** |

复现命令：`python role_c_toolkit/e5_figA4_verify.py`、`python role_c_toolkit/e5_figA4_raw_audit.py`
（后者输出 `figA4_raw_audit.json`，含每行的原始来源文件）。

## 5. 核对中发现并已澄清的一处 provenance（供老师参考）

**E5-03（IE-08 s5101）有两次归因运行**：

- `e5-hifi-natural-failures-r2`（10-02 08:14）标记为 `counterfactual_incomplete` ——
  该次的 `reference_executor` 运行 `ineligible`，因此那次没有产出 delta；
- `e5-hifi-attribution-r3b`（10-02 09:33）**重跑后 `status=complete`**，四个参考分齐全
  （0.265 / 0.266 / 0.2313 / 0.5286），delta 与图完全一致。

图与 `kappa_summary.json` 用的是**较晚的 r3b 那次**，这是正确选择。留此记录是因为它正是
"数据可复现性"要交代的地方：同一个 case 存在一次不完整运行和一次完整重跑，采用后者。

## 6. 数据可复现性说明（本轮新增核实）

### 6.1 pilot 所用场景文件至今未被改动 —— 已逐文件哈希核实

pilot 的 episode manifest 记录了当时的引擎快照 `20261001T191215Z-7c3bded0`。与该快照逐文件比对：

| 比对对象 | 结果 |
|---|---|
| `scenarios/formal/`（含 IE-03-surface-raid、IE-08-island-strike） | **51/51 文件哈希完全一致** |
| `openmd/code/grid_env/`（grid 任务定义与各 agent） | **差异 0 条** |
| `openmd/code/eval/`（评测驱动） | **差异 0 条** |
| `openmd/code/grid_info_experiment.py` | **一致** |

⇒ 本图涉及的 IE 场景与 grid 任务定义，从 pilot 到今天**没有任何改动**。

**一处需要说明的对照**：同一比对里 `scenarios/` 下有 **13 个文件不同**，全部位于
`scenarios/competition_v1/`（竞争族场景），是**后续 E4 场景重标定工作**改的，
与本图无关（本图不用竞争族场景）。这一条写在这里是为了避免"场景文件被动过"引起误解。

### 6.2 每个 case 都有确定性回放门，且逐行一致

12 例的 `replay_gate` 全部为 `exact_match: true`，细到行数：

| 用例 | `trajectory.jsonl` | `decisions.jsonl` |
|---|---|---|
| E5-01 / 07 / 10 | identical，匹配 499 行 | identical，匹配 498 行 |
| E5-02 / 05 | identical，匹配 1187 行 | identical，匹配 1186 行 |
| E5-06 | identical，匹配 565 行 | identical，匹配 564 行 |
| E5-11 / 12 | identical，匹配 1800 行 | identical，匹配 1799 行 |

即：**给定记录的轨迹，引擎重放是逐行确定性的**——这正是"分数可复算"的依据。

### 6.3 复现所需的依赖全部已落盘

每个 episode 的 manifest 记录了：`compiled_hashes`（resolved / catalog）、
`weights_sha256`（RL 权重文件哈希）、`runtime_packages`（numpy 2.4.6 / scipy 1.17.1 /
taichi 1.7.3 / torch 2.14.0+cpu / pydantic 2.13.5 / PyYAML 6.0.3）、`engine_module_origin`、
以及请求级 `requests.jsonl` 与决策级 `decisions.jsonl`。

### 6.4 一条诚实的边界：LLM 推理本身不做 bit-identical 重放承诺

episode 由 LLM 规划（如 E5-02 有 13 次 `llm_calls`）。即使冻结采样参数，更换推理后端
（HF ↔ vLLM）或改变 KV 精度都可能产生不同输出，因此**"重跑得到同一分数"不能承诺**。
能承诺的是：**给定已记录的 trajectory / decisions，归因分解可确定性复算**——即 6.2 所证明的。

## 7. 可直接回复老师

> 已对原始归因日志逐项核对：Fig. A4 的 12 行数值与标签全部一致，您读的那 4 行 ΔE
> （0.0320 / 0.0754 / 0.0095 / −0.0221）与 `attribution.json` 里归因步骤自己记录的
> `delta_execution` **完全相同**，无数值抄录或 OCR 误差。图中数值由脚本从 CSV 直接格式化，
> 不存在二次录入环节。另外这 4 行 ΔE 都远小于同行的 ΔI，所以即使有 0.01 级偏差也不会改变
> 任何 machine 标签——与您的判断一致。
>
> 数据可复现性方面补充三点：① **pilot 所用场景文件至今未被改动**——与当时的引擎快照
> `20261001T191215Z` 逐文件比对，`scenarios/formal`（含 IE-03/IE-08）51 个文件哈希全部一致，
> grid 任务定义与评测驱动差异 0 条；② 12 例的**回放门全部 `exact_match`**，轨迹与决策文件逐行
> 一致（499～1800 行），即给定记录后引擎重放是确定性的；③ 每个 episode 的 manifest 里记录了
> 权重哈希、catalog/resolved 哈希与运行期依赖版本，可追溯。唯一不做承诺的是 LLM 推理本身
> 的 bit-identical 重放（换后端或改 KV 精度可能改变输出），这一点与"归因分解可复算"是两件事。

