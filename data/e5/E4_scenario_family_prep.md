# E4-场景族构建与入场：前置状态与门禁台账

> 生成：2026-10-03 ｜ 对应清单：v9 §1（E4-场景族构建 + **D1′ 任务属性标注**）
> **2026-10-03 更新**：① 新增 **D1′ 6 维先验标注**（44/55 场景，见 `D1prime_标注说明.md`）；
> ② D1 按 v8/v9 口径以**报告量**落账（E10 实测）；③ D3 记 **blocked**（本版本引擎无三档实现）；
> ④ D2 已预注册并跑 seed 2001 小样（见 `D2_preregistration.md`）；
> ⑤ 服务器调度：8B 副本退役、GPU 2/3 换为第二个 27B 副本。
> **未改动任何场景包、registry 与引擎。**

## 0a. D2 headroom：5-seed 主结论（已可验收）

**数据**：seeds 2001–2005 共 **300 例**，0 失败、0 不可用；单例中位 36 s、最慢 351 s；
4 个 seed 并行墙钟 69 分钟。

| 度量 | 1 seed | **5 seeds（主结论）** |
|---|---|---|
| 二值成功（事前预注册） | 0/28 | **2/28**（MD-REC-008、MD-TRK-008 的最优基线 4/5 成功） |
| **声明综合分（度量修订 v2）** | 7/30 | **7/30**（稳定） |

**二值成功率分布（5 seeds）**：1.00 → 25 场景、0.80 → 2 场景、0.00 → 1 场景。
⇒ 25 个场景的脚本基线 **5/5 全成功**，补 seed 不改变饱和结论（这也证明"近饱和"不是样本量问题）。

**headroom 分档（30 个竞争运行包）**：窗口内 7、近饱和 23（其中 6 个 = 1.000）、触底 0。
按类别落在窗口内的场景数：REC 4 / ER 2 / AD 1 / TRK 0。

**验收判定（两个读法）**：
- 字面"≥3 个大类各有 ≥3 个场景完成入场门判定" → ✅ 4 个大类全部已判定；
- 隐含"判定应通过" → ⚠️ 仅 REC 一类达标（≥3 个在窗口内）。

详见 **`D2_验收页.md`**（含 7 个窗口内场景的 5-seed 均值与区间、按类别表、复算命令、已知陷阱）。

**未通过的原因是场景侧**：把最优基线限制为任务相关策略后，AD-001/002/003/004/005、
TRK-001/002、REC-001 三档的综合分仍是 1.000 → 天花板效应。两条真实设计缺陷已记入台账：
① 地板控制在 AD-001/002/004、ER-003 上达到任务相关基线水平（区分度不足）；
② MD-REC-008 合同写 `coordinated`、实际运行 `sweep`（口径需澄清）。

---

## 0. 本次新增的 D1′ 先验标注（P0）

清单 v9 响应审稿人 P0-1：D1′ 必须是**先验任务属性**而非事后结果指标。已完成：

| 项 | 结果 |
|---|---|
| 维度 | 6 维（决策形态 / 目标开放性 / 状态空间 / 时间尺度 / 对手多样性 / 规则复杂度），每维 1–3 分 |
| 覆盖 | **44/55 场景**：14 个 HF IE + 3 个 grid 档位 + 30 个 competition 运行包（11 个 MD-* 平台兼容场景未标，已在附录披露） |
| 依据 | **仅设计文档**：scenario.yaml 设计字段、生成器 `spec(...)` 的轴/目的/timeline/notes、SCENARIO_CONTRACTS、grid 难度参数表 |
| 强制约束 | 工具拒绝读取 `artifacts/`、`results/`、`experiments/` 路径与含 score/outcome 等 token 的字段（有单测） |
| 得分范围 | 1.17（IE-01/IE-03 纯几何）– 2.50（IE-06/IE-11 诱饵识别）；47 行中 27 行偏 LLM-strong 侧 |
| 冻结 | `d1prime_FROZEN.json`（含内容哈希与设计输入 SHA-256），供主理人独立标注后算 κ |
| 待办 | 主理人交叉标注 → κ ≥ 0.6；先验得分 vs 实际分层优势 Spearman ρ > 0.5（统计由主理人负责） |

产物：`d1prime_table.md` / `.csv`（附录用）、`D1prime_标注说明.md`（含判分锚点与边界）、
`d1prime_worksheet.json`（设计信号底稿）、`d1prime_annotations.json`（人工标注原件）。

## 0b. 服务器调度变更（本次）

| 变更 | 详情 |
|---|---|
| 8B 副本退役 | `stop_qwen_service.py --replica c`，收据 `shutdown-replica-c-e6.json`；GPU 2/3 显存已释放 |
| 第二个 27B 副本 | `start_qwen_service.py --replica b` → `127.0.0.1:8002`，与 8001 完全同配置（BF16/TP=2/FP8 KV/kv_blocks 296/ctx 131072） |
| 权重收据修复 | 09-30 的 `download-complete.json` 缺 `repository` 字段、当前启动器要求它存在；已按 manifest 补写并留备份 `download-complete.json.pre-repository-field-backup` |
| 影响面 | D2 标定是**纯 CPU** 任务，不依赖 GPU；`five-seed-fill`（8001）未受影响 |
| E13 前提 | 跑 Qwen3-8B 需让出 GPU 2/3（即停副本 b）；见 `E13_preregistration.md` §4 |

---

## 1. 最重要的发现：4 大类场景**已经存在**，缺的是"入场门判定"

清单 v5 的措辞是"构建 3–4 个大类的代表场景"。实际清点结果：**这 4 大类的场景包已经在候选树里了**，
一共 28 个基础场景（+ REC001 的三档难度 = 30 个运行包），并且已经有 11 份专项验证报告。

| 类别 | 候选场景数 | 位置 |
|---|---|---|
| 侦察搜索 Reconnaissance (REC) | 8（REC001 有 easy/medium/hard 三档 → 10 个运行包） | `scenarios/competition_v1/` |
| 持续跟踪 Tracking (TRK) | 8 | 同上 |
| 区域拒止 Area Denial (AD) | 6 | 同上 |
| 应急响应 Emergency Response (ER) | 6 | 同上 |

**因此 E4 的工作量重心不是"造场景"，而是"跑入场门 + 出判定数据 + 定稿附录 A"**——
这与你清单里写的"仅构建与入场验证，不对具体场景算法做实现"是一致的，
但比"从零构建"要轻，因为场景本体和专项验证已经在了。

**同时要注意**：这些候选场景**尚未进入正式 registry**。当前正式 registry 只有 25 条
（14 个 IE 拦截交战 + 11 个 MD-* 平台/难度场景），候选的 30 个只在 `competition_v1/` 里，
不在 `formal/registry.yaml`。所以"入场"是一个有实义的动作：**过门 → 写进正式 registry → 进附录 A**。

---

## 2. 已存档（改场景前的回退点）

存档位置：`role_c_toolkit/artifacts/e4-scenario-family/backup-20261003T0400Z/`

| 内容 | 文件数 | 说明 |
|---|---|---|
| `hifi-scenarios/` | 175 | `openmd/source-code/source_codes` 的 `scenarios/` 全树（formal 25 条注册 + competition_v1 30 个候选包 + synthetic）+ `catalog/` |
| `formal-repo/`、`catalog-v2/`、`synthetic/` | 26 | 本仓库 `source_codes/` 的 formal 场景与 catalog |
| `MANIFEST.json` | — | **201 个文件的逐文件 SHA-256 + 字节数**，可随时校验是否被改动 |

校验方式（任一文件被改都会被发现）：

```bash
python - <<'PY'
import hashlib, json, pathlib
root = pathlib.Path('role_c_toolkit/artifacts/e4-scenario-family/backup-20261003T0400Z')
rows = json.loads((root / 'MANIFEST.json').read_text(encoding='utf-8'))
bad = [r['path'] for r in rows
       if hashlib.sha256((root / r['path']).read_bytes()).hexdigest() != r['sha256']]
print('条目:', len(rows), '| 改动文件:', bad or '无')
PY
```

实测输出：`条目: 201 | 改动文件: 无`。

### 2b. 存档时工作树里**已经存在**的未提交改动（不是我改的，请知悉）

存档保存的是**当前工作树状态**，而工作树在我动手之前就已经带着未提交改动。
用 `git status` / `git diff` 可复核，涉及场景树的有 9 个文件：

| 文件 | 改动 |
|---|---|
| `source_codes/scenarios/formal/registry.yaml` | **新增 3 条**：MD-INT-002-AIR-SURFACE、MD-INT-005-STEALTH-MULTI-AXIS、MD-INT-006-SATURATION-ROE |
| `source_codes/scenarios/formal/md_ad_002_{easy,medium,hard}/scenario.yaml` | 各 6 行改动（3 增 3 删） |
| `source_codes/scenarios/formal/md_int_003_easy/agents.yaml` | 3 行改动 |
| `source_codes/openmdbench/benchmark.py`、`md_int_001_selftest.py`、`release_validation.py`、`sessions/lifecycle_v2.py` | 少量改动（1–11 行） |

关键事实：`registry.yaml` 的磁盘修改时间是 **2026-09-26 14:53**，早于本次工作（2026-10-03），
所以这些是**本次会话之前就存在的改动**。我没有回退、没有覆盖、也没有提交它们。
如果这些改动需要保留，请注意我的存档正是"含这些改动的状态"；
如果你要先回到 git HEAD 版本，请在改动场景前自行决定（我不做破坏性 git 操作）。

---

## 3. 清点结果（自动生成）

- `scenario_inventory.json`：**55 个场景**（25 正式 + 30 候选），每个含包内逐文件哈希与
  `package_sha256`（把"文件名:哈希"排序后再哈希，作为包的稳定指纹）。
- 类别分布：

| 类别 | 已入场 | 候选 | 合计 |
|---|---|---|---|
| 拦截交战 Interception-Engagement | 20 | 0 | 20 |
| 区域拒止 Area Denial | 5 | 6 | 11 |
| 侦察搜索 Reconnaissance | 0 | 10 | 10 |
| 持续跟踪 Tracking | 0 | 8 | 8 |
| 应急响应 Emergency Response | 0 | 6 | 6 |

> 说明：拦截交战 20 = 14 个 IE 场景 + 6 个 MD-INT-* 平台场景（同一家族）；
> 区域拒止 5 = MD-AD-002 三档 + MD-AD-004 + 平台场景。
> 类别是按场景编号里的家族段判定的，不依赖任何场景内字段——
> **场景包里目前没有"类别"字段**（`scenario.yaml` 只有 `scenario_id` / `display_name`），
> 所以附录 A 的类别列只能由编号或外部台账提供。

---

## 4. 入场门台账（空表，待真实运行填入）

文件：`admission_ledger.json`（55 行，每行 4 个门，全部 `pending`）。

门禁定义直接引用冻结基线 `openmd/doc/hifi_requirements.md` §1（一票否决约束），未自行发明：

| 门 | 判定标准（原文口径） |
|---|---|
| **D1′** 决策形态匹配 | 手写贪心规则拿不到 rule+heuristic 基线的 90% 分 |
| **D2** 基线 headroom | 最优纯基线 SR ∈ [40%, 85%] |
| **D3** 接口成本预算 | 粒度三档 B_if 单调、档间距 > 估计方差、最细档 B_if ≥ 0.3 |
| **D1** 信息不对称 | 真假目标：规则辨别 ≤60%、LLM ≥85%（**形态待武昊 E10-高保真定稿后补**） |

台账每条记录：`verdict`（pass/fail/pending/deferred_pending_E10）+ `evidence`（指向运行产物）+
`note`。**工具在任何情况下都只统计 `pass`**，`pending` 不会出现在"已通过"计数里；
`appendix_A_scenario_family.md` 骨架里也写明"verdict 为 pending 的行不得写进论文的 admitted 表"。

### 现在还没有的（必须真实跑，我不能替跑）

1. **D2 headroom**：需要每个候选场景"最优纯基线成功率"——要按同一评分口径、
   自然终局、多 seed 跑 rule / heuristic 等纯基线。现有验证报告是**计分可用性与定位/可见性**
   专项，不是基线能力标定，不能当 D2 数据用。
2. **D3 接口预算**：需要粒度三档（单目标/分组/全权委托）的 B_if 估计与方差——尚未见到该批数据。
3. **D1′ 形态评审**：需要"贪心规则 vs rule+heuristic 基线"的同场景同 seed 对比。
4. **D1 控制场景**：待 E10 定稿。

---

## 5. 与主理人确认后要冻结的事（我不能自己定）

| 项 | 现状 | 需要谁定 |
|---|---|---|
| 每个类别收录几个场景 | 候选 8/8/6/6，清单说"每类 3–6 个，与主理人确认后冻结" | 张老师/主理人 |
| 是否允许直接复用 competition_v1 的包（而不是另建新包） | 我方判断可复用：它们是同引擎声明式包，且已有专项验证；但"入场"意味着写进正式 registry | 主理人 |
| D1 的最终形态（硬门 vs 报告量） | 待 E10 | 武昊 |
| 是否把 30 个候选一次性全部送门，还是每类先送 3 个 | 建议每类先送 3 个跑通门流程再扩，降低无效算力 | 主理人 |

---

## 6. 复算命令

```bash
# 1) 重新清点并生成台账模板（只读，不写任何场景包）
python role_c_toolkit/e4_scenario_family.py inventory \
  --source openmd/source-code/source_codes \
  --output role_c_toolkit/artifacts/e4-scenario-family/scenario_inventory.json \
  --ledger-output role_c_toolkit/artifacts/e4-scenario-family/admission_ledger.json \
  --control-report openmd/doc/competition_four_categories/COMPETITION_ACCEPTANCE_REVIEW_20261001.md

# 2) 由台账渲染附录 A 表（pending 不会被算作通过）
python role_c_toolkit/e4_scenario_family.py report \
  --ledger role_c_toolkit/artifacts/e4-scenario-family/admission_ledger.json \
  --output role_c_toolkit/artifacts/e4-scenario-family/appendix_A_scenario_family.md
```

单测：`python -m unittest discover -s role_c_toolkit -p "test_e4_scenario_family.py"`
（4 项：类别判定取自编号段而非前缀、每个包都被哈希、台账初始全 pending 且不谎报通过、只统计 pass。）

---

## 7. 我这次**没有**做的事（避免越界）

- 没有新增、修改、删除任何场景包；没有改 `formal/registry.yaml`；没有改 `openmdbench/` 引擎。
- 没有把任何候选场景写进正式 registry（那是过门后的动作，且需主理人确认名单）。
- 没有跑仿真、没有产生任何门禁 verdict——台账里 55×4 = 220 个门全部是 `pending`。
- 没有动你的其他文件；存档目录是新增的，工作区其余部分只有新增的 1 个脚本 + 1 个测试 + 若干产物。
