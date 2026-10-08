# E13 正区模型复现：可执行性核查与预注册

> 对应清单：v9 §4（P2，自武昊移交，响应审稿人 P2-2）
> 状态：**预注册草案；本会话未启动实跑**（用户批准的计划中 E13 只做核查与预注册）

## 1. 目标与判据

E6 的模型无关性只在 grid（边界区）验证了接口因果必要 4/4；HF（正区）主结果只有一个 27B 模型。
审稿人 P2-2 质疑：分层优势会不会只是这个特定模型的特性。

**判据（照录清单 v9）**：

1. 两模型在**多数（≥4/6）关键场景**复现正分层优势（方向与 Qwen3.8-27B 主结果一致）；
2. 整体 mean composite 与主结果同方向（LLM+Rule > Rule baseline）；
3. 任一模型在任一场景方向相反 → 如实报告并讨论模型尺度/架构差异。

## 2. 设计

| 项 | 取值 | 依据 |
|---|---|---|
| 模型 | MiniMax-M3（MoE，428B/A23B）、Qwen3-8B（稠密） | 与 E6 一致，保证可比 |
| 栈 | **LLM+Rule**（rule executor，无需 RL checkpoint） | 清单 §4 |
| 场景（阶段 1） | IE-01、IE-02、IE-05、IE-06、IE-09、IE-14 | 清单 §4：覆盖高/中/低分层优势与诱饵类 |
| seeds | 5 seeds / 模型 / 场景 | 与主结果一致 |
| prompt regime | **`--llm-briefing withheld`（无情报）** | 已是 `run_episode.py` 的默认值；与主结果一致 |
| 量级 | 2 模型 × 6 场景 × 5 seeds = **60 episodes** | 清单 §4 |
| 统计 | seed-bootstrap 95% CI；与 27B 主结果的 LLM+Rule 列**做方向对比，不合并统计** | 正文 §6.4 口径 |

## 3. 工具链核查结果（已核对，未运行）

| 环节 | 现状 | 证据 |
|---|---|---|
| 分场景运行 HF 对局 | 可用：`role_c_toolkit/hifi_record_campaign.py` 支持任意 `--scenario`，E5 已用它跑过 IE-03/04/08 各 12 个种子 | `episode_arguments()` / `run_episode_case()` |
| LLM+Rule 栈 | 可用：`case['planner'] = 'llm-rule'`（LLM 规划 + 规则执行） | 同上 |
| 无情报口径 | 默认：`--llm-briefing` 默认 `withheld`，prompt 不含敌方波次/方位/兵力 | `openmd/code/eval/run_episode.py`（默认值与说明） |
| 第三方模型接入 | 可用：`role_c_toolkit/minimax_client.py`（Anthropic Messages 路径）+ `e6b_remote_ablation.py` 的重定向补丁模式 | E6b 已跑通 46 局 |
| 本机 8B 服务 | **需要资源**：GPU 2/3 目前被第二个 27B 副本（replica b）占用；8B 需 `--replica c` 重启 | `tools/huairou/start_qwen_service.py` |

**成本参考（来自既有批次，非新测量）**：E5 hifi 单局 LLM+RL 为 400–1200 tick、60+ 次规划调用；
按 E6b 的 hifi 类比（108 s/局）估算，单局 LLM+Rule 约数分钟量级，60 局**串行约 5–10 小时墙钟**，
并发 2 时约 3–5 小时。**精确成本需先跑 1 个场景 × 1 seed 的冒烟。**

## 4. 执行前必须确定的事项

1. **8B 的 GPU 归属**：跑 Qwen3-8B 需要让出 GPU 2/3（即停掉第二个 27B 副本）。
   这一步会改变我此前为 D2/调度做的部署，**需用户确认时机**（D2 是纯 CPU，不受影响）。
2. **第三方 API 配额**：MiniMax-M3 走付费 key，60 局约 300–600 次调用；需与武昊同步避免同批竞争。
   配额紧张时**优先保 Qwen3-8B**（稠密，先证明不是 27B 独有）。
3. **MoE/稠密不合并**：输出上限与服务形态不同，只能并列报告（与 E6/E6b 口径一致）。
4. **思考策略**：M2.x 关不掉思考（E6b 实测），但 E13 用 **M3**（可关，实测 0 思考块），
   因此本批不引入"是否思考"这一额外变量——这是相对 E6b 的改进。

## 5. 预注册的最小冒烟（建议第一步）

| 项 | 内容 |
|---|---|
| 范围 | 1 场景（IE-01）× 1 seed × 2 模型 = 2 局 |
| 目的 | 实测单局墙钟、LLM 调用数、token 消耗、failure 率；确认 `withheld` 在提示词里生效、无诱饵标签泄漏 |
| 判据 | 两局都自然终局、无 empty response、调用数在预期量级；据实测重估 60 局总时长 |
| 不做 | 不做统计、不与主结果对比、不写论文数字 |

## 6. 产物（执行后）

| 内容 | 路径 |
|---|---|
| 预注册计划（场景 × seed × 模型 × 栈） | `role_c_toolkit/artifacts/e13-hf-model-replication/plan.json` |
| 逐局原生报告与请求记录 | 同上 `run-<model>/episodes/` |
| 汇总表（6 场景 × 3 模型 composite，并列不合并） | `E13_summary.md` |

## 7. 边界

- 本轮**不动** grid 的 E6 数据（已完成，直接引用）。
- 不宣称在线自主诱饵识别率；判别成绩限定为受控刺激集（附录 G 限定）。
- 失败如实报告：若某模型方向相反，写进论文并讨论，不改判据。
