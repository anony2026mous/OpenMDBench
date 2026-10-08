# 选项 2（补跑 E1 剂量对照）所需材料清单

> 目的：把 2×2 的缺格补上——即在**同一执行器**上，用真饱和/更宽 headroom 的档位，
> 与 E1 现有的 4 档（N017/018/019/027）一起构成可解释的交互效应。
> 本文把"本机已有 / 必须索取 / 可本地重建"分清楚，索取清单只有两项。

---

## 1. 本机已有的（不需要索取）

| 材料 | 位置 | 用途 |
|---|---|---|
| 剂量干预封装 `episode_adapter.py` | `bundle/frozen/code/` | `--dose {strong,hold}` 的 goal 注入包装器 |
| 档位目录 `original_variants.json` | `bundle/protocol/` | 32 个档位的 `package` / `public_id` / `scene_hash` / `profile_hash` / `resolved_hash` |
| 门禁协议 `gate_protocol.json` | `bundle/frozen/code/` | D1/D2/D3 判据与臂定义 |
| 战役与执行脚本 | `bundle/frozen/code/`（`count_campaign.py`、`pressure_variants.py`、`e1_trial.py`、`common.py`） | 档位扫描与 trial 编排 |
| **4 档 × 5 臂 × 10 seed 的已跑结果** | `bundle/data/gate-screening/` | 选项 1 的全部数据；也是选项 2 的对照基线 |
| 冻结引擎副本（只读） | `bundle/frozen/engine/`、`bundle/frozen/repo/` | 参考；**含 `catalog/v2/ie_set.yaml` 等场景配置** |

---

## 2. 必须索取的两项（合作者侧）

| # | 材料 | 该机器上的路径 | 为什么必须 |
|---|---|---|---|
| **①** | **release repo** | `/root/openmd/releases/gitlab-ccabad00154e/repo` | 运行入口所在：`openmd/code/eval/run_episode.py`（含 `--planner rule`、`--goal-granularity`）、`goai_protocol.py`、`llm_client_hifi.py`。本机 **无**。 |
| **②** | **experiment engine** | `/root/openmd/runs/p0-next-20261002/E1-count/experiment-engine` | `OPENMDBENCH_ROOT` 指向的引擎（`openmdbench` 包）。本机 **无**。 |

**这两项合起来大约就是"E1 的 runner"**：有了它们 + 本机已有的 `episode_adapter.py`，
就能在任意档位上跑 `--arm rule --dose {strong,hold}`。

---

## 3. 可选（有则更好，无则本地重建）

| 材料 | 说明 |
|---|---|
| **档位场景包** `p0count_ie_05_multi_axis_n0xx` | 本机只有结果目录、没有场景包。但 `original_variants.json` 给了每个档位的 `scene_hash`/`profile_hash`，配合 `bundle/frozen/code/` 的构建脚本可**本地重建**；若合作者直接给包则更省事。 |
| **`.venv`** `/root/openmd/releases/gitlab-ccabad00154e/.venv` | 本机 `openmd-py311` 环境可替代；若引擎依赖特殊版本才需要它。 |
| **seed 段约定** | 需与武昊确认新跑用哪段 seed（现有 4 档用 4151–4160），避免跨批拼接。 |

---

## 4. 索取清单（可直接转发给合作者）

> 我需要在同一台机器上补跑 E1 的剂量对照（`rule` 臂 + `--dose strong/hold`），
> 用来补 2×2 的缺格。请提供以下两项（目录打包或告知可访问路径均可）：
>
> 1. `/root/openmd/releases/gitlab-ccabad00154e/repo` —— 评测入口与协议代码
> 2. `/root/openmd/runs/p0-next-20261002/E1-count/experiment-engine` —— 引擎
>
> 如果能一并给出 `p0count_ie_05_multi_axis_n0xx` 档位场景包（或它们所在目录），
> 可以省掉本地重建步骤。
>
> 另外请确认：新跑可以用哪一段 seed（现有门禁批次用的是 4151–4160）。

---

## 5. 拿到后的执行（预计 2–4 小时）

| 步骤 | 时间 |
|---|---|
| 接入核实：路径可用、`episode_adapter.py` 能 import、单局冒烟 | 15–30 分钟 |
| 补跑：目标格 × 2 剂量 × 5 seed（脚本，无 LLM），5 路并行 | 1–3 小时 |
| 合并分析：与现有 4 档合成 2×2，算交互 + seed-bootstrap 95% CI | 45 分钟 |
| 文档与镜像 | 30 分钟 |

**若合作者只能提供"跑好的结果"**（不能给 runner）：也可以——让他按
`COUNT-IE-05-MULTI-AXIS-N0xx / rule-strong-g1 / seed-<新>` 的同一目录结构产出结果，
我直接合并分析，**无需本机运行任何东西**。此时选项 2 的耗时降到 45 分钟分析 + 等待对方跑完。

---

## 6. 若两项都拿不到

保持选项 1：用现有 4 档（N017/018/019/027）完成 2×2，如实报告
"族内 headroom 跨度仅 0.037，交互不可判定"，并把结论落为
"该族无法提供 headroom 对比，条件 (iii) 由 §6.7 跨族对比承接"。
