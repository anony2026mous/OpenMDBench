"""Generate the "why experiment 2 cannot run as specified" document.

The reasons are assembled from checks already run against the live tree, each one naming the
file and the concrete result, so the document is evidence rather than assertion.
"""
from __future__ import annotations

import os
from pathlib import Path

OUT = (Path("role_c_toolkit/artifacts/e4-scenario-family")
       / "实验2_不可执行原因.md")
BRIEF = Path(os.environ.get("OPENMD_EXP2_BRIEF_MD", ""))

TEXT = """# 实验 2（gates 外场景 layered 表现）为什么按现有定义无法执行

> 对象：`OpenMDBench_补实验清单_P0硬伤_20261006.md` 第 40–78 行的「实验 2」。
> 结论：**不是预算问题，是缺少实现**。清单列出的 4 个栈里，竞争族（`competition_v1`）
> 只存在 1 个；`Pure RL`、`LLM+Rule`、`LLM+RL` 三个都需要先新建。
> 本文每条结论都附可复算的证据（文件 + 命令 + 实测结果）。

---

## 0. 一句话结论

清单要求「每场景 4 栈 × 3 seed = 12 局，3 场景共 36 局」，其中
**Rule 栈现成（脚本策略），另外三个栈在竞争族里没有任何实现**；
且这三个栈**不是"接线"就能补上的**——竞争族与学习型栈（RL/LLM）的动作空间、
观测维度、运行时 API、场景集合四层都不对齐，需要域适配 + 重训。

---

## 1. 原因一：竞争族只有脚本策略，没有加载学习型权重的代码

**证据**：

```bash
grep -rn "np.load|torch.load|load_state_dict|nn.Module" \\
  tools/competition_four_categories/*.py
# → 空（0 命中）
```

- 竞争族策略模块共 18 个（`allocated_tracking_policy.py`、`coverage_tracking_policy.py`、
  `identity_tracking_policy.py`、`track_reporting_policy.py`、`denial_policy.py`、
  `recon_policy.py`、`response_policy.py` …），**全部是脚本策略**，没有一个是学习型策略。
- 唯一的 "checkpoint" 相关文件是 `checkpoint_availability_probe.py`，它自己的 docstring 写着：

  > *"Diagnostic native checkpoint contract probe, not a scoring workaround. An in-memory
  > test-only model and package exercise the existing public compiler, registry, session and
  > checkpoint APIs. … Expected rejection documents a limitation, not a passed checkpoint gate."*

  即**接口契约探针，不是 RL 运行器**。

**后果**：`Pure RL（原 RL 权重）` 这一栈在竞争族里没有承载物。

---

## 2. 原因二：竞争族没有 LLM 规划层，"llm" 只出现在自我声明字符串里

**证据**：

```bash
for f in tools/competition_four_categories/*.py; do grep -in "llm" "$f"; done
# 命中仅两处，且都是"我们没做 LLM/RL"的声明：
#   calibration_matrix.py:113   "scope": "Frozen cross-scenario reference-policy calibration,
#                               not LLM/RL experiments, a uniform-policy leaderboard or ..."
#   validate_observation_search.py:132  "scope": "matched-speed development baseline;
#                               not LLM/RL comparison or formal acceptance"
```

**架构上确实有一个理想的层叠接缝**：执行器 `tracking_policy.py: ScheduledNavigationPolicy`
接受 `scheduled-navigation@1.0` 计划（严格校验
`segments[].payload = {speed_mps, heading_deg[, altitude_m]}`）。

**但没有生成器**：该格式目前只被 `tracking.py`、`tracking_policy.py`、`denial_policy.py`
**脚本生成**，不存在"从 briefing 调 LLM 产出计划"的代码路径。

**后果**：`LLM+Rule` 与 `LLM+RL` 两栈的规划层需要从零写。

---

## 3. 原因三：竞争族的"栈"只有 2 个脚本位，且都是 rule 侧

**证据**（校准矩阵注册 + 批次实测两处一致）：

```bash
sed -n '35,80p' tools/competition_four_categories/calibration_matrix.py
```

| 场景 | A 位 | B 位 |
|---|---|---|
| MD-TRK-004 | `follow` | `allocated` |
| MD-TRK-007 | `report-honest` | `identity-honest` |
| MD-ER-004 | `direct` | `preissued` |

实测（从最终批次 state/evidence 反推）与上表完全一致：

```
MD-TRK-004: ['allocated', 'follow']
MD-TRK-007: ['identity-honest', 'report-honest']
MD-ER-004:  ['direct', 'preissued']
```

**注意一处容易被误读的地方**：清单把 `Pure RL` 写成"纯 RL + 原 RL 权重"，
但 `allocated` / `preissued` **是脚本策略的名字，不是 RL**。竞争族里没有任何一格是 RL。

**后果**：清单的 4 栈在竞争族上最多只能凑出 1 个（Rule），且它是 2 个脚本位的统称。

---

## 4. 原因四：清单的"4 栈"架构来自 grid 实验 1，与竞争族不是同一套

**证据**：

| | grid（实验 1 的语境） | competition_v1（实验 2 的目标） |
|---|---|---|
| 任务 | grid 网格任务 | MD-TRK / MD-ER 等 4 大类 |
| 执行器 | GOAI heuristic + **MAPPO medium 检查点** | 18 个脚本策略 |
| 规划器 | LLM 可规划（`grid_env/agents/hybrid_agent.py` 449 行） | 无 |
| 检查点 | 清单给的 SHA `223dbf74…`（medium） | **无对应物** |

清单里 "Pure MAPPO / 指定 medium 检查点" 属于**实验 1**；实验 2 的表（第 59–66 行）
却沿用了同一套"规划层 + 执行层"术语。**竞争族没有 medium 检查点这个概念。**

**后果**：实验 2 的栈定义是从实验 1 迁移过来的，缺少竞争族侧的对应实现。

---

## 5. 原因五：学习型栈与竞争族在四层上都不对齐

`SCEN = list(sweep.IE_SET)`（`_w1_grid_driver.py:42`）——学习型驱动**硬编码 14 个 IE 场景**。

```bash
grep -rc "competition_v1|md_trk|md_er_" openmd/code/eval/_w1_grid_driver.py   # → 0
grep -rc "npz|theta_" tools/competition_four_categories/runtime.py             # → 0
```

| 层 | 学习型栈（RL/LLM 所在） | 竞争族 | 是否对齐 |
|---|---|---|---|
| 场景集合 | 14 个 IE（硬编码） | 30 个竞争包 | ✗ |
| 驱动 | `_w1_grid_driver.py` → `_w1_ie_sweep` | `calibration_matrix.py` → `validate_*.py` | ✗ |
| 运行时 | `_w1_ie_sweep` 的会话 | `openmdbench.sessions.lifecycle_v2.SessionLifecycleV2` | ✗ |
| 动作 | `heading(2) + speed`（连续导航，见 `ie_rl_policy.py:103-104`） | 另有 `send_message` / `hold`，且身份绑定、报告诚实度、三角检伤是**离散语义决策** | ✗ |

**后果**：要跑 36 局，先要写观测/动作/运行时适配层。

---

## 6. 原因六（最关键）：即便写完适配器，**权重也需要重训**，否则实验会得出反向结论

现有 3 个权重文件：

```
openmd/code/eval/_w1_runs/rl/theta_rl_legacy2.npz
openmd/code/eval/_w1_runs/rl/theta_arm5_v12.npz
openmd/code/eval/_w1_runs/rl/theta_arm5_llm_reward_v9.npz
```

它们是 `ie_rl_policy.py`（312 行，MLP trunk → heading/speed）的权重，**训练任务是 IE 拦截交战**。
把它们零样本搬到：

- **MD-TRK 持续跟踪**（要求：维持接触 + 身份一致性 + 报告轮换）
- **MD-ER 应急响应**（要求：调度到达 + 三角检伤纪律）

模型对这些任务语义**一无所知**，大概率退化成"朝接触点飞"（≈ `follow`）。

而竞争族的脚本基线本来就强：

| 场景 | 最优脚本基线 composite |
|---|---|
| MD-TRK-004 | `allocated` = **0.967** |
| MD-TRK-007 | `identity-honest` = **0.937** |
| MD-ER-004 | `preissued` = **0.942** |

**风险**：若移植后的策略只得 0.5 左右，测出来的"layered 不 pay"来自
**执行器不会做这个任务**，而不是 P2 的 "headroom→0 ⇒ layer 不 pay"。
**结论会被审稿人反向使用**（"不是没有 headroom，是你的 RL 太弱"）。

要避免这一点，必须**先在竞争族任务上重训**（重新定义观测/动作/奖励接口 + 训练 + 校验），
这不是 6–12 小时的跑批，而是数天开发 + 训练。

---

## 7. 什么**不是**原因（避免误判）

| 看起来像障碍，其实没问题 | 实测 |
|---|---|
| 服务器地址/端口 | `172.18.129.57:32422` ✅ 本次会话的 `huairou` 别名即此机（`hr-a6000-129-57`） |
| `/root/huairou-project` | ✅ 存在（**符号链接** → `snapshots/20261003T180603Z-32b1d3de`，即本项目树） |
| 三个目标场景包是否可运行 | ✅ 三个 `scenario.yaml` 都在 |
| LLM 服务是否在线 | ✅ `127.0.0.1:8001` 与 `127.0.0.1:8002` 均可连接 |
| 场景选得是否合理 | ✅ 3 个场景选得对（避开满分与触底、跨类别、0.93–0.97 有"不足但非零"空间） |

**所以问题是实现缺失，不是环境或选型错误。**

---

## 8. 一个必须澄清的方法学疑问

竞争族每个场景**只跑过两个脚本策略**，且它们**不是"同一执行器 + 两个规划器"**，
而是**两个完整策略**（如 `follow` vs `allocated`）。

因此**不能用它们之间的差值冒充"层叠增益"**——我在上一轮曾建议过这种"2-lite"简化方案，
**现予撤回**：方法上不成立。

---

## 9. 可行路径

| 选项 | 内容 | 成本 | 是否检验 P2 |
|---|---|---|---|
| **A** | 把本文作为证据补进 §6.7："gates 外场景未跑 layered"的准确表述是**当时无该通路**，并附实现缺失的证据 | 30 分钟 | — |
| **B** | 把 3 个场景加进 grid 学习型栈 | 数天，且 grid 不认识竞争族（需重新定义任务） | 可能偏题 |
| **C** | 在竞争族新建 LLM 规划层 + RL 执行层（适配 + 重训 + 校验） | 数天开发 + 周级训练 | 是（但见原因六的风险） |
| **D** | 换设计：**不需要 LLM 栈**也能检验 P2——在同一执行器上只改变规划信息量（例如 MD-TRK-007 已有诚实度对照；或给跟踪场景加"有/无共享接触信息"的规划层开关） | 1–2 天 | **是，且干净** |

**建议：先做 A（今天可交），同时决定 C 还是 D。**
若目标是 P2（headroom 不足 ⇒ 层叠不 pay），**D 比 C 更省、更不易被反驳**；
若目标确实是"LLM 规划层的必要性"，那才是 C，需要先立项。

---

## 10. 复算方式

```bash
# 竞争族是否有学习型策略（应为空）
grep -rn "np.load\\|torch.load\\|load_state_dict\\|nn.Module" \\
  openmd/source-code/source_codes/tools/competition_four_categories/*.py

# 竞争族是否出现 LLM（应只有两条自我声明）
grep -rin "llm" openmd/source-code/source_codes/tools/competition_four_categories/*.py

# 学习型驱动是否引用竞争族（应为 0）
grep -rc "competition_v1\\|md_trk\\|md_er_" openmd/code/eval/_w1_grid_driver.py

# 学习型栈的场景集合（硬编码 14 IE）
grep -n "SCEN = \\|SCEN=" openmd/code/eval/_w1_grid_driver.py

# 三个目标场景实际跑过的策略（从批次 state 反推）
python role_c_toolkit/e4_scenario28_pack.py    # 输出含最优基线策略列
```
"""


def main() -> None:
    OUT.write_text(TEXT, encoding="utf-8")
    lines = TEXT.splitlines()
    print(f"written {OUT} ({len(lines)} lines)")
    print("sections:")
    for line in lines:
        if line.startswith("## "):
            print("  " + line)
    if BRIEF.is_file():
        print(f"\n关联清单: {BRIEF.name}")


if __name__ == "__main__":
    main()
