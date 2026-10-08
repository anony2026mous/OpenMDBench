# 五种子实验数据集汇总

> 生成时间：2026-09-28 21:16　|　由 `_w1_consolidate.py` 自动生成
> **主数据：210 局**（withheld 口径，3 臂 × 14 场景 × 5 种子 = 210 格）
> **对照数据：499 局**（declared 口径历史读数）
> **基线：250 局 rule-rule + 64 局 rl**（归档复用，不重跑）

## 文件

| 文件 | 说明 |
|---|---|
| `DATASET_5SEEDS.csv` | 逐局明细，50 列，可直接用 Excel/pandas 打开 |
| `DATASET_5SEEDS.json` | 同上，JSON 数组 |
| `DATASET_5SEEDS.md` | 本文（汇总表） |

**CSV 列说明（关键列）**：`score` 为主指标（本身即按适用层归一化后的加权平均）；
`scored_weight` 为适用层权重和；`layer_*` 为各层得分；`applicable_*` 为该层是否适用；
`briefing` 为情报口径；`checkpoint_*` 为策略溯源；`fires_decoy` 为引擎记录的误击诱饵弹数。

## 表 1　逐场景均值（withheld，5 种子）

| 场景 | **LLM+rule** | **LLM+RL** | **pure-LLM** | **rule+rule** | **RL** |
|---|---|---|---|---|---|
| IE-01-SINGLE-TARGET | 0.898 | 0.795 | 0.351 | 0.691 | 0.876 |
| IE-02-DUAL-THREAT | 0.830 | 0.860 | 0.151 | 0.765 | 0.757 |
| IE-03-SURFACE-RAID | 0.768 | 0.654 | 0.716 | 0.748 | 0.960 |
| IE-04-COMBINED-ARMS | 0.743 | 0.822 | 0.422 | 0.812 | 0.687 |
| IE-05-MULTI-AXIS | 0.791 | 0.820 | 0.253 | 0.763 | 0.703 |
| IE-06-DECOY-MIXED | 0.756 | 0.799 | 0.481 | 0.657 | 0.652 |
| IE-07-CROSS-DOMAIN | 0.786 | 0.749 | 0.710 | 0.749 | 0.684 |
| IE-08-ISLAND-STRIKE | 0.423 | 0.523 | 0.248 | 0.432 | 0.301 |
| IE-09-STAGGERED-WAVES | 0.851 | 0.834 | 0.664 | 0.820 | 0.629 |
| IE-10-DUAL-AXIS-PINCER | 0.737 | 0.907 | 0.622 | 0.801 | 0.729 |
| IE-11-DECOY-SCREEN | 0.722 | 0.796 | 0.424 | 0.681 | 0.184 |
| IE-12-FOG-ONSET | 0.775 | 0.689 | 0.426 | 0.711 | 0.641 |
| IE-13-DEEP-STRIKE | 0.796 | 0.812 | 0.583 | 0.709 | 0.538 |
| IE-14-SATURATION-THREE-WAVE | 0.786 | 0.885 | 0.396 | 0.787 | 0.506 |

## 表 2　臂的总体表现

| 臂 | 均值 | 标准差 | n | 最小值 | 最大值 | 胜 `rule-rule` | 胜 `RL` |
|---|---|---|---|---|---|---|---|
| LLM+rule | **0.7578** | 0.1837 | 152 | 0.1071 | 1.0000 | 10/14 | 13/14 |
| LLM+RL | **0.7786** | 0.1922 | 133 | 0.0000 | 1.0000 | 12/14 | 12/14 |
| pure-LLM | **0.4591** | 0.2311 | 110 | 0.0278 | 0.9048 | 0/14 | 4/14 |
| rule+rule | **0.7036** | 0.2195 | 250 | 0.0556 | 1.0000 | —/14 | —/14 |
| RL | **0.6552** | 0.2138 | 64 | 0.1733 | 0.9615 | —/14 | —/14 |

## 表 3　逐种子均值（检验种间稳定性）

| 臂 | s7 | s11 | s13 | s17 | s19 | 种间极差 |
|---|---|---|---|---|---|---|
| LLM+rule | 0.7339 | 0.7317 | 0.8016 | 0.7717 | 0.7981 | 0.0699 |
| LLM+RL | 0.7804 | 0.8198 | 0.7751 | 0.8361 | 0.6577 | 0.1784 |
| pure-LLM | 0.4773 | 0.5010 | 0.4468 | 0.3484 | 0.4743 | 0.1526 |
| rule+rule | 0.7088 | 0.7468 | 0.6424 | 0.5958 | 0.7264 | 0.1510 |
| RL | 0.6334 | 0.6570 | 0.6319 | 0.6287 | 0.7743 | 0.1455 |

## 表 4　逐格种间极差最大的 14 个格子（方差预警）

- `IE-03-SURFACE-RAID` / LLM+RL：极差 **0.914**（0.086 ~ 1.000，5 种子）
- `IE-02-DUAL-THREAT` / pure-LLM：极差 **0.539**（0.028 ~ 0.566，5 种子）
- `IE-12-FOG-ONSET` / LLM+RL：极差 **0.511**（0.388 ~ 0.899，5 种子）
- `IE-04-COMBINED-ARMS` / pure-LLM：极差 **0.482**（0.198 ~ 0.680，5 种子）
- `IE-14-SATURATION-THREE-WAVE` / pure-LLM：极差 **0.462**（0.176 ~ 0.639，5 种子）
- `IE-06-DECOY-MIXED` / pure-LLM：极差 **0.454**（0.171 ~ 0.625，5 种子）
- `IE-01-SINGLE-TARGET` / pure-LLM：极差 **0.428**（0.214 ~ 0.642，5 种子）
- `IE-11-DECOY-SCREEN` / pure-LLM：极差 **0.381**（0.225 ~ 0.606，5 种子）
- `IE-01-SINGLE-TARGET` / LLM+RL：极差 **0.324**（0.581 ~ 0.905，5 种子）
- `IE-14-SATURATION-THREE-WAVE` / LLM+rule：极差 **0.300**（0.599 ~ 0.899，5 种子）
- `IE-03-SURFACE-RAID` / LLM+rule：极差 **0.299**（0.588 ~ 0.887，5 种子）
- `IE-08-ISLAND-STRIKE` / LLM+rule：极差 **0.294**（0.231 ~ 0.525，5 种子）
- `IE-08-ISLAND-STRIKE` / LLM+RL：极差 **0.279**（0.402 ~ 0.682，5 种子）
- `IE-04-COMBINED-ARMS` / LLM+rule：极差 **0.279**（0.594 ~ 0.873，5 种子）

> 极差越大，该格越不能用单种子读数下结论。上表即「三合稳定性判据」存在的理由。

## 表 5　口径剔除溯源

| 剔除原因 | 局数 |
|---|---|
| `declared: unknown planner 'rule-rl'` | 152 |
| `declared: rl obs_dim mismatch` | 46 |
| `declared: pure-llm: no envelope record` | 42 |
| `declared: llm-rl policy tag=arm5_v12` | 26 |
| `declared: llm-rl policy tag=arm5_llm_full_ie03_v10` | 23 |
| `declared: llm-rl policy tag=arm5_v11` | 14 |
| `declared: ticks=0` | 11 |
| `declared: no terminal outcome` | 8 |
| `declared: llm-rl policy tag=arm5_v13_ie08` | 4 |
| `declared: aborted: exception: SessionFailureV2: session.contact_invalid: opaque` | 3 |
| `declared: llm-rl policy tag=arm5_v2` | 3 |
| `declared: aborted: exception: CheckpointErrorV2: checkpoint.integrity_invalid: ` | 2 |
| `declared: aborted: exception: TypeError: cannot unpack non-iterable NoneType ob` | 2 |
| `declared: aborted: exception: KeyError: 'tick'` | 2 |
| `declared: aborted: exception: AttributeError: 'NoneType' object has no attribut` | 1 |
| `declared: aborted: wall_limit 120.0s reached at tick 60` | 1 |
| `declared: llm-rl policy tag=arm5_llm_formal2` | 1 |
| `declared: llm-rl policy tag=arm5_v4` | 1 |
| `declared: aborted: step_timeout at tick 0: 60.7s > 60.0s` | 1 |

## 已知限制

1. **同 seed 不是重放**：LLM 端点非确定（同一请求 4 次输出互异），固定 seed 是独立复现。
2. **③④ 训练场景与评测场景重叠**：`llm-rl` 权重训练于 IE-01/02/03/05，`rule-rl` 训练于 IE-01…07。
3. **`rl` 基线与 `rule-rl` 的 RL 执行层不是同类策略**：前者 `goal_features=False`（观测 2866 维），
   后者 `goal_features=True`（观测 3570 维），二者分数不可直接相比。
4. **口径读取路径有两个**：`pure-llm` 在 `defender.briefing`，另两臂在 `defender.planner.briefing`。
