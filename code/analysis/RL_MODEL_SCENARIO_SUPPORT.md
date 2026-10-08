# RL 模型支持的场景条件（适用范围与边界）

> 适用对象：`code/eval` 下的纯 RL 拦截策略（一个网络直出无人机/无人船动作）。
> 本文说明**哪些场景可以直接用这套权重跑**、**哪些条件会跑不了或退化**、
> **边界之外要改什么**，并给出**一条命令的自检**。
>
> 文档里的数字都标注了来源：**[硬限]** 是代码里的常量或 `raise`；
> **[实测]** 是本项目跑出来的读数；**[设计]** 是架构性结论，没有实验支撑的部分会明说。

---

## 0. 一句话结论

**我方编成 ≤ 16 个可机动单元、同屏目标 ≤ 20 个、平台域属于 `air`/`surface`、
且每个单元都有可解析的武器包线与弹药 → 现有权重可直接使用，不需要重训。**
已实测到 **12 个单元 / 17 个目标**（MD-AD-006，训练时从未见过）仍能守住 4/5。

超出上述任一条件 → 需要改常量并**重训**；引入新的平台域（如水下）→ **引擎侧不支持**，
不是 RL 层能解决的。

> ⚠️ **当前 checkpoint 有一处待重训的缺陷**，见 §7。修好速度标定后，
> 空中单元的最大指令速度从 10 m/s 变成 80 m/s，动作语义变了 8 倍，
> **旧权重必须重训后才能用**。

---

## 1. 模型是什么（接口契约）

**一个神经网络**，共享主干 `obs → 256 → 256`，输出头：

| 头 | 形状 | 语义 |
|---|---|---|
| `heading` | `(16, 2)` | **绝对**航向，`(sin, cos)` 对，环境用 `atan2` 解码 |
| `speed` | `(16,)` | **绝对**速度占该单元物理上限的比例 |
| `fire` | `(16, 21)` | 掩码分类：0=不开火，`j+1`=第 j 个目标槽 |
| `value` | `(1,)` | 价值头（**在同一条主干上**，PPO 需要 critic，仍是"一个网络"） |

* 没有目标层、没有执行器、没有规则兜底、没有第二个网络、没有候选目标排序。
* 决策周期 **5 tick**（持久导航指令在两次决策之间保持）。**[硬限]** `--decision-interval 5`
* 观测尺寸：**2866**（含会遇点特征）或 **2226**（旧布局，无会遇点）。
  `rl_agent` 从 checkpoint 的 `trunk0.w` 形状**自动推断**用哪种，旧权重仍可评测。**[硬限]**

观测分四块（尺寸随编成/目标槽固定，不随实际数量变化）：

```
global(6) + units(16 × 10) + targets(20 × 7) + pairs(16 × 20 × 8)
```

槽位按 `entity_id` 排序分配；**同一份权重对槽位编号不敏感**（§4 有置换实验）。

---

## 2. 适用条件

| 条件 | 硬限 | 已验证范围 | 违反后果 | 来源 |
|---|---|---|---|---|
| 我方可机动单元数 | **≤ 16** | 5 – 12 | `reset()` 抛 `RuntimeError` 拒绝运行 | **[硬限]** `MAX_UNITS=16` |
| 同屏不同目标数 | **≤ 20** | 3 – 17 | 超出部分被丢弃（**打印告警**，不静默） | **[硬限]** `MAX_CONTACTS=20` |
| 平台域 | `air` / `surface` | 两者都见过 | 域判定来自实体的 `domain`；未知域会落到速度兜底值 | **[硬限]** `SPEED_BY_CLASS` |
| 单元武器包线 | 必须可解析（`min_range_m < max_range_m`） | 全部 8 场景 | 解析不出 → 该单元**永远不能开火**（掩码全灭） | **[硬限]** `_weapon_profile_for` |
| 单元弹药 | `> 0` | 全部 8 场景 | 无弹药 → 掩码全灭 | **[硬限]** `_ammo_total` |
| 单元可机动 | 动力学非 `native-fixed` | 全部 8 场景 | 固定设施**自动排除**在可控槽位外（给它们发导航指令会被引擎以 `capability_missing` 拒绝并中断整局） | **[硬限]** `FIXED_DYNAMICS_MODEL` |
| 攻击剖面 | 场景需有 `objective_m` | 全部 8 场景 | 缺则保护目标退化为原点，分数无意义 | **[硬限]** `load_attack_profile_data` |
| 终局规则 | 需含 `defender_success` / `intruder_success` | 全部 8 场景 | 没有 → 终局奖励项**永不触发**（只剩余项），且记分卡 `terminal` 层恒为 0 | **[硬限]** `_outcome_of` |
| 阵营 id | 默认 `coalition.defender` / `coalition.intruder` | 全部 8 场景 | 不同的阵营命名要用构造参数覆盖 | **[硬限]** 构造参数 |

**平台域与速度都是从目录里读的，不是常量表**：
`definition.domain` → 域；`dynamics.normalized_content["max_speed_mps"]` → 物理上限。
这样新场景换平台不需要改代码（见 §7 的教训）。

### 不需要满足的条件

* **不要求**我方单元型号统一：同一场景里无人机（80 m/s、500–8000 m、只打空中）和
  无人船（10 m/s、0–3000 m、只打水面）混编是原生支持的。
* **不要求**来袭者数量固定：MD-AD-006 用 spawn 事件在 t600 放第二波，环境处理了。
* **不要求**场景时长一致：IE-01 是 900 tick、MD-AD-006 是 1800 tick。

---

## 3. 一条命令自检（新场景先跑这个）

```powershell
$env:PYTHONPATH="C:\Code\source-code\openmd\source-code\source_codes"
$env:OPENMDBENCH_ROOT="C:\Code\source-code\openmd\source-code\source_codes"
$env:MPLCONFIGDIR="C:\Code\source-code\.mplcache"
& "C:\Code\source-code\source_codes\.venv\Scripts\python.exe" `
  C:\Code\source-code\openmd\code\eval\_w1_rl_scenario_check.py <SCENARIO-ID>
```

输出逐条给 **PASS/WARN/FAIL 和触发它的那个上限**，例如：

```
== IE-01-SINGLE-TARGET
   [ok  ] controllable units = 6 (MAX_UNITS=16, demonstrated 5-12); 2 fixed asset(s) correctly excluded
   [ok  ] intruders = 4 (MAX_CONTACTS=20, demonstrated 3-17)
   [ok  ] domain classes: {'air': 4, 'surface': 2}
   [ok  ] armed units 6/6
   [ok  ] engagement onset t37..48 over a 60-tick horizon
   [ok  ] observation_size=2866 (pair_width=8), action = heading_xy(16,2) speed(16,) fire(16,21)
   [ok  ] terminal rules: [('rule.assets-lost','intruder_success'), ...]
   => USABLE, inside the demonstrated envelope
```

三种结论：

* `USABLE, inside the demonstrated envelope` — 直接跑；
* `USABLE, OUTSIDE THE DEMONSTRATED ENVELOPE` — 能跑，但读数是**外推**，要谨慎解读；
* `NOT USABLE` — 环境层面跑不了，先改常量或改场景。

---

## 4. 泛化证据

### 4.1 零样本：编成和目标数**同时**超出训练范围

| | 我方可控单元 | 来袭者 | 集合 |
|---|---|---|---|
| IE-01..07（训练） | 5 – 10 | 3 – 9 | 分布内 |
| **MD-AD-006** | **12** | **17** | **两轴都超出** |

同一份权重（40 轮、7 场景训练）在 MD-AD-006 上零样本得 **0.4899，5 种子中 4 次守住**，
对照 rule 臂 0.5225 —— **同档**。**[实测]**

### 4.2 槽位置换：学的是"任意单元"，不是"第 k 号槽"

编成变化会改变槽位排序，所以泛化的前提是策略对槽位编号不敏感。
做一致性置换（观测行与动作行一起换，命令仍发给正确单元），IE-01：

| 排列 | 分数 | 结局 |
|---|---|---|
| 不打乱 | 0.8803 | defender_success |
| 置换 1 | 0.6747 | defender_success |
| 置换 2 | 0.8859 | defender_success |
| 置换 3 | 0.8974 | defender_success |

**4/4 守住**，分数落在跨种子带宽内（0.6437–0.8978）。**[实测]**

### 4.3 结构原因与保留

固定 16 槽 + 每槽自带特征 + 共享主干 ⇒ 同一权重天然适配任意 ≤16 的编成，**[设计]**。
但当前把单元块**展平**后过 MLP，**没有内建的置换不变性**（无 per-entity 编码器、
无注意力、无池化）——对称性是**学出来的**，实验证明学得不错，但没有架构保证。**[设计]**

---

## 5. 超出范围要改什么

| 需求 | 改动 | 代价 |
|---|---|---|
| 编成 > 16 | 提高 `ie_rl_env.MAX_UNITS` | obs 维线性增长 → **必须重训** |
| 目标 > 20 | 提高 `MAX_CONTACTS` | 同上 |
| 新增平台类别（同域） | 通常**不用改**：域与速度从目录读 | 无需重训 |
| 编成到 30–50 个单元 | 建议改成 **per-entity token + 注意力/池化编码器** | 恢复置换不变性、可外推更多单元，并顺带解决 GPU 利用率低（batch 可上 10⁴） |
| 新平台域（**水下 / AUV**） | **引擎侧不支持**：编成只能落地成 UAV/USV | 不是 RL 层的问题；需先在引擎与目录层支持水下域 |

---

## 6. 实测成绩（用来设定期望）

同一 checkpoint（`theta_rl_main5.npz`，40 轮），随机采样，5 种子（与 rule 同种子集）：

| 场景 | RL 均值 | sd | 守住 | rule |
|---|---|---|---|---|
| IE-01-SINGLE-TARGET | **0.8288** | 0.105 | 5/5 | 0.4126 |
| IE-02-DUAL-THREAT | 0.8780 | 0.016 | 5/5 | 0.9004 |
| IE-03-SURFACE-RAID | 0.7756 | 0.304 | 4/5 | 0.8492 |
| IE-04-COMBINED-ARMS | 0.7482 | 0.092 | 5/5 | 0.7539 |
| IE-05-MULTI-AXIS | 0.7519 | 0.079 | 5/5 | 0.7412 |
| IE-06-DECOY-MIXED | 0.6588 | 0.047 | 5/5 | 0.6815 |
| IE-07-CROSS-DOMAIN | 0.7153 | 0.017 | 5/5 | 0.7750 |
| MD-AD-006（零样本） | 0.4899 | 0.099 | 4/5 | 0.5225 |
| **场景均值** | **0.7308** | | **38/40** | 0.7045 |

* **总体 RL ≈ rule**（+0.026，在噪声带内，不能声称超越）。
* **IE-01 上 RL 明显更好且稳得多**：rule 5 种子 sd 0.325、只守住 1–2 次；RL sd 0.105、5/5。
* **短板（层均值）**：`facilities 0.573`、`depth 0.376`、`ammo 0.655`。

### 两个必须遵守的评测约定

1. **必须用 `--rl-stochastic` 评测**。逐头取边际 argmax **不是** 16 槽联合动作的众数，
   会把所有单元压成同一个选择。同一 checkpoint/种子/场景实测：
   **确定性 0.1342 vs 随机 0.6613（5 倍）**。确定性读数只用于退化诊断，不进对照。
2. **训练种子与评测种子必须不相交**。训练用 1000–1004，评测用 7/11/13/17/19。
   在评测种子上训练会让 RL 见过那次抽签，而三臂基线不训练，对照不公平。

---

## 7. ⚠️ 当前 checkpoint 有一处待重训的缺陷（重要）

**平台分类用了错误的标签启发式，把所有拦截无人机当成水面艇，速度上限被压到 1/8。**

原实现：`klass = "air" if "uav" in tags else "surface"`。
而 `defender.uav-01` 的实际标签是 `('defence','combat-unit','interceptor')` —— **没有 `uav` 标签**。
后果（IE-01 实测）：

| 单元 | 真实 `max_speed_mps` | 旧实现用的上限 | 倍差 |
|---|---|---|---|
| `defender.uav-01..04` | **80.0** | **10.0** | **8×** |
| `defender.usv-01..02` | 10.0 | 10.0 | 1× |

连带影响：观测里"是否空中"那一维**恒为 0**（策略从未见过空/海区别），
且空中单元在**每一次训练和每一次评测**中都被限制在 10 m/s。
这很可能就是 `depth` 层只有 rule 的 72% 的原因 ——
10 m/s 的拦截机追不上 43+ m/s 的来袭者，只能在门口交战。**[实测]**

**已修**：域取自 `definition.domain`（回退到平台绑定的 `domain`），
速度上限取自 `dynamics.normalized_content["max_speed_mps"]`，两者都是目录数据。
自检脚本现在报 `{'air': 4, 'surface': 2}`（修前是 `{'surface': 6}`）。

**但旧权重必须重训**：修好后空中单元的指令速度语义变了 8 倍，
继续用旧 checkpoint 属于训练/评测不同分布。

---

## 8. 相关文件与命令

| 文件 | 作用 |
|---|---|
| `_w1_rl_scenario_check.py` | **本文 §3 的自检脚本** |
| `_w1_generalisation_probe.py` | 训练分布 vs 零样本分布对照 |
| `ie_rl_env.py` | 环境：观测编码、直出动作解码、奖励、`MAX_UNITS`/`MAX_CONTACTS`、平台剖面 |
| `ie_rl_policy.py` | 一个网络的两种实现；`LOG_STD_INIT`；动作契约 |
| `ie_rl_train.py` | PPO + worker 编排（`--worker` 跑在引擎 venv） |
| `rl_agent.py` | 评测接入 `run_episode.py`；布局自动推断；`RL_SLOT_SHUFFLE` 诊断 |
| `_w1_ie_sweep.py` | 批量评测（`--planner rl --rl-stochastic`） |
| `_w1_rl_report.py` | 出 RL 结果表（按 tag 精确过滤 + 有效性校验） |

跑一个场景：

```powershell
& "C:\Code\source-code\source_codes\.venv\Scripts\python.exe" `
  C:\Code\source-code\openmd\code\eval\_w1_ie_sweep.py `
  --planner rl --rl-theta <theta.npz> --rl-stochastic `
  --scenarios <SCENARIO-ID> --tag <tag> --seed 7
```
