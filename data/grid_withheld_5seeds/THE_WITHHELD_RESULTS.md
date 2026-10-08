# 三臂无情报（withheld）实验结果

> 生成时间：2026-09-28 21:16　|　由 `_w1_results_doc.py` 从原始报告自动生成，数字与数据不会脱节

## 0. 实验口径与数据规模

| 项目 | 内容 |
|---|---|
| 主口径 | `--llm-briefing withheld`：提示词**不含任何敌方情报**（无波次数量/时刻/方位/意图，亦无兵力数字）|
| 对照口径 | `declared`：历史口径，逐波披露 `spawn_tick/count/axis/behavior`（含未来真值），仅用于复现旧读数 |
| 指标 | `strategy_scorecard.defender_score`（**本身即**按适用层重新归一化后的加权平均）|
| 场景 | 14 个 IE 拦截交战场景 |
| 种子 | 7 / 11 / 13 / 17 |
| LLM | Qwen3.8-27B，温度 0.1，规划节奏 10 tick |
| 基线 | `rule-rule`、`rl` **复用归档数据，不重跑**；`rl` 锁定单一策略身份 `theta_rl_legacy2.npz`（obs_dim=2866）|

**当前数据量：213/168 格**（3 臂 × 14 场景 × 4 种子）。种子 17 仍在采集中，故表 A/C 中部分格子种子数 < 4。

## 表 A　逐场景均值

格式 `均值 (种子数/局数)`；`—` 表示该格无有效数据。

| 场景 | **LLM+rule** | **LLM+RL** | **pure-LLM** | **rule+rule** | **RL** |
|---|---|---|---|---|---|
| IE-01-SINGLE-TARGET | 0.891 (6s/6) | 0.774 (5s/5) | 0.343 (5s/5) | 0.691 (6s/42) | 0.876 (5s/6) |
| IE-02-DUAL-THREAT | 0.908 (6s/6) | 0.851 (5s/5) | 0.162 (5s/5) | 0.765 (5s/30) | 0.757 (5s/5) |
| IE-03-SURFACE-RAID | 0.856 (5s/5) | 0.634 (5s/5) | 0.699 (5s/5) | 0.748 (5s/31) | 0.960 (5s/5) |
| IE-04-COMBINED-ARMS | 0.741 (6s/6) | 0.804 (5s/5) | 0.246 (5s/5) | 0.812 (5s/25) | 0.687 (5s/5) |
| IE-05-MULTI-AXIS | 0.790 (5s/5) | 0.824 (5s/5) | 0.188 (5s/5) | 0.763 (5s/22) | 0.703 (5s/5) |
| IE-06-DECOY-MIXED | 0.767 (5s/5) | 0.793 (5s/5) | 0.434 (5s/5) | 0.657 (5s/22) | 0.652 (5s/5) |
| IE-07-CROSS-DOMAIN | 0.792 (5s/5) | 0.763 (5s/5) | 0.703 (5s/5) | 0.749 (5s/22) | 0.684 (5s/5) |
| IE-08-ISLAND-STRIKE | 0.404 (5s/5) | 0.568 (5s/5) | 0.280 (5s/5) | 0.432 (5s/28) | 0.301 (5s/5) |
| IE-09-STAGGERED-WAVES | 0.880 (5s/5) | 0.859 (5s/5) | 0.638 (5s/5) | 0.820 (3s/3) | 0.629 (3s/4) |
| IE-10-DUAL-AXIS-PINCER | 0.712 (5s/5) | 0.921 (5s/5) | 0.603 (5s/5) | 0.801 (3s/3) | 0.729 (3s/4) |
| IE-11-DECOY-SCREEN | 0.747 (5s/5) | 0.820 (5s/5) | 0.346 (5s/5) | 0.681 (3s/3) | 0.184 (3s/3) |
| IE-12-FOG-ONSET | 0.766 (5s/5) | 0.659 (5s/5) | 0.441 (5s/5) | 0.711 (3s/9) | 0.641 (3s/6) |
| IE-13-DEEP-STRIKE | 0.807 (5s/5) | 0.790 (5s/5) | 0.597 (5s/5) | 0.709 (3s/7) | 0.538 (3s/3) |
| IE-14-SATURATION-THREE-WAVE | 0.793 (5s/5) | 0.897 (5s/5) | 0.354 (5s/5) | 0.787 (3s/3) | 0.506 (3s/3) |

## 表 B　臂的总体表现

| 臂 | 全局均值 | 标准差 | 种子≥3 覆盖 | 均值胜 `rule-rule` | 均值胜 `RL` | STABLE 条数 |
|---|---|---|---|---|---|---|
| LLM+rule | **0.7783** | 0.1587 | 14/14 | 11/14 | 12/14 | 6 |
| LLM+RL | **0.7827** | 0.1720 | 14/14 | 11/14 | 12/14 | 9 |
| pure-LLM | **0.4310** | 0.2274 | 14/14 | 0/14 | 4/14 | 0 |
| rule+rule | **0.7036** | 0.2195 | 14/14 | 0/14 | 12/14 | — |
| RL | **0.6552** | 0.2138 | 14/14 | 2/14 | 0/14 | — |

## 表 C　三合稳定性判据逐格判定

判据：**均值胜** ∧ **逐种子全胜**（每个种子族的均值都高于对手全部种子族的均值）∧ **分半都胜**。三项全真记 `STABLE`。

| 场景 | 臂 | 对手 | 臂均值 | 对手均值 | Δ | n | 均值 | 逐种子 | 分半 | 判定 |
|---|---|---|---|---|---|---|---|---|---|---|
| IE-01-SINGLE-TARGET | LLM+rule | rule+rule | 0.891 | 0.691 | +0.201 | 6/42 | Y | n | Y | mean-only |
| IE-01-SINGLE-TARGET | LLM+rule | RL | 0.891 | 0.876 | +0.015 | 6/6 | Y | n | Y | mean-only |
| IE-01-SINGLE-TARGET | LLM+RL | rule+rule | 0.774 | 0.691 | +0.083 | 5/42 | Y | n | n | mean-only |
| IE-01-SINGLE-TARGET | LLM+RL | RL | 0.774 | 0.876 | -0.102 | 5/6 | n | n | n | LOSES |
| IE-01-SINGLE-TARGET | pure-LLM | rule+rule | 0.343 | 0.691 | -0.348 | 5/42 | n | n | n | LOSES |
| IE-01-SINGLE-TARGET | pure-LLM | RL | 0.343 | 0.876 | -0.533 | 5/6 | n | n | n | LOSES |
| IE-02-DUAL-THREAT | LLM+rule | rule+rule | 0.908 | 0.765 | +0.144 | 6/30 | Y | Y | Y | STABLE |
| IE-02-DUAL-THREAT | LLM+rule | RL | 0.908 | 0.757 | +0.151 | 6/5 | Y | Y | Y | STABLE |
| IE-02-DUAL-THREAT | LLM+RL | rule+rule | 0.851 | 0.765 | +0.086 | 5/30 | Y | n | Y | mean-only |
| IE-02-DUAL-THREAT | LLM+RL | RL | 0.851 | 0.757 | +0.094 | 5/5 | Y | n | Y | mean-only |
| IE-02-DUAL-THREAT | pure-LLM | rule+rule | 0.162 | 0.765 | -0.602 | 5/30 | n | n | n | LOSES |
| IE-02-DUAL-THREAT | pure-LLM | RL | 0.162 | 0.757 | -0.595 | 5/5 | n | n | n | LOSES |
| IE-03-SURFACE-RAID | LLM+rule | rule+rule | 0.856 | 0.748 | +0.108 | 5/31 | Y | n | Y | mean-only |
| IE-03-SURFACE-RAID | LLM+rule | RL | 0.856 | 0.960 | -0.103 | 5/5 | n | n | n | LOSES |
| IE-03-SURFACE-RAID | LLM+RL | rule+rule | 0.634 | 0.748 | -0.114 | 5/31 | n | n | n | LOSES |
| IE-03-SURFACE-RAID | LLM+RL | RL | 0.634 | 0.960 | -0.326 | 5/5 | n | n | n | LOSES |
| IE-03-SURFACE-RAID | pure-LLM | rule+rule | 0.699 | 0.748 | -0.049 | 5/31 | n | n | n | LOSES |
| IE-03-SURFACE-RAID | pure-LLM | RL | 0.699 | 0.960 | -0.261 | 5/5 | n | n | n | LOSES |
| IE-04-COMBINED-ARMS | LLM+rule | rule+rule | 0.741 | 0.812 | -0.071 | 6/25 | n | n | n | LOSES |
| IE-04-COMBINED-ARMS | LLM+rule | RL | 0.741 | 0.687 | +0.054 | 6/5 | Y | n | n | mean-only |
| IE-04-COMBINED-ARMS | LLM+RL | rule+rule | 0.804 | 0.812 | -0.008 | 5/25 | n | n | n | LOSES |
| IE-04-COMBINED-ARMS | LLM+RL | RL | 0.804 | 0.687 | +0.117 | 5/5 | Y | n | Y | mean-only |
| IE-04-COMBINED-ARMS | pure-LLM | rule+rule | 0.246 | 0.812 | -0.566 | 5/25 | n | n | n | LOSES |
| IE-04-COMBINED-ARMS | pure-LLM | RL | 0.246 | 0.687 | -0.441 | 5/5 | n | n | n | LOSES |
| IE-05-MULTI-AXIS | LLM+rule | rule+rule | 0.790 | 0.763 | +0.027 | 5/22 | Y | n | n | mean-only |
| IE-05-MULTI-AXIS | LLM+rule | RL | 0.790 | 0.703 | +0.087 | 5/5 | Y | n | Y | mean-only |
| IE-05-MULTI-AXIS | LLM+RL | rule+rule | 0.824 | 0.763 | +0.061 | 5/22 | Y | n | n | mean-only |
| IE-05-MULTI-AXIS | LLM+RL | RL | 0.824 | 0.703 | +0.121 | 5/5 | Y | n | Y | mean-only |
| IE-05-MULTI-AXIS | pure-LLM | rule+rule | 0.188 | 0.763 | -0.576 | 5/22 | n | n | n | LOSES |
| IE-05-MULTI-AXIS | pure-LLM | RL | 0.188 | 0.703 | -0.515 | 5/5 | n | n | n | LOSES |
| IE-06-DECOY-MIXED | LLM+rule | rule+rule | 0.767 | 0.657 | +0.110 | 5/22 | Y | n | Y | mean-only |
| IE-06-DECOY-MIXED | LLM+rule | RL | 0.767 | 0.652 | +0.116 | 5/5 | Y | n | Y | mean-only |
| IE-06-DECOY-MIXED | LLM+RL | rule+rule | 0.793 | 0.657 | +0.136 | 5/22 | Y | Y | Y | STABLE |
| IE-06-DECOY-MIXED | LLM+RL | RL | 0.793 | 0.652 | +0.142 | 5/5 | Y | Y | Y | STABLE |
| IE-06-DECOY-MIXED | pure-LLM | rule+rule | 0.434 | 0.657 | -0.223 | 5/22 | n | n | n | LOSES |
| IE-06-DECOY-MIXED | pure-LLM | RL | 0.434 | 0.652 | -0.218 | 5/5 | n | n | n | LOSES |
| IE-07-CROSS-DOMAIN | LLM+rule | rule+rule | 0.792 | 0.749 | +0.043 | 5/22 | Y | n | Y | mean-only |
| IE-07-CROSS-DOMAIN | LLM+rule | RL | 0.792 | 0.684 | +0.108 | 5/5 | Y | Y | Y | STABLE |
| IE-07-CROSS-DOMAIN | LLM+RL | rule+rule | 0.763 | 0.749 | +0.014 | 5/22 | Y | n | n | mean-only |
| IE-07-CROSS-DOMAIN | LLM+RL | RL | 0.763 | 0.684 | +0.080 | 5/5 | Y | Y | Y | STABLE |
| IE-07-CROSS-DOMAIN | pure-LLM | rule+rule | 0.703 | 0.749 | -0.045 | 5/22 | n | n | n | LOSES |
| IE-07-CROSS-DOMAIN | pure-LLM | RL | 0.703 | 0.684 | +0.020 | 5/5 | Y | n | n | mean-only |
| IE-08-ISLAND-STRIKE | LLM+rule | rule+rule | 0.404 | 0.432 | -0.028 | 5/28 | n | n | n | LOSES |
| IE-08-ISLAND-STRIKE | LLM+rule | RL | 0.404 | 0.301 | +0.103 | 5/5 | Y | n | Y | mean-only |
| IE-08-ISLAND-STRIKE | LLM+RL | rule+rule | 0.568 | 0.432 | +0.136 | 5/28 | Y | n | Y | mean-only |
| IE-08-ISLAND-STRIKE | LLM+RL | RL | 0.568 | 0.301 | +0.266 | 5/5 | Y | n | Y | mean-only |
| IE-08-ISLAND-STRIKE | pure-LLM | rule+rule | 0.280 | 0.432 | -0.152 | 5/28 | n | n | n | LOSES |
| IE-08-ISLAND-STRIKE | pure-LLM | RL | 0.280 | 0.301 | -0.022 | 5/5 | n | n | n | LOSES |
| IE-09-STAGGERED-WAVES | LLM+rule | rule+rule | 0.880 | 0.820 | +0.059 | 5/3 | Y | n | Y | mean-only |
| IE-09-STAGGERED-WAVES | LLM+rule | RL | 0.880 | 0.629 | +0.251 | 5/4 | Y | Y | Y | STABLE |
| IE-09-STAGGERED-WAVES | LLM+RL | rule+rule | 0.859 | 0.820 | +0.039 | 5/3 | Y | n | Y | mean-only |
| IE-09-STAGGERED-WAVES | LLM+RL | RL | 0.859 | 0.629 | +0.230 | 5/4 | Y | Y | Y | STABLE |
| IE-09-STAGGERED-WAVES | pure-LLM | rule+rule | 0.638 | 0.820 | -0.182 | 5/3 | n | n | n | LOSES |
| IE-09-STAGGERED-WAVES | pure-LLM | RL | 0.638 | 0.629 | +0.009 | 5/4 | Y | n | Y | mean-only |
| IE-10-DUAL-AXIS-PINCER | LLM+rule | rule+rule | 0.712 | 0.801 | -0.089 | 5/3 | n | n | n | LOSES |
| IE-10-DUAL-AXIS-PINCER | LLM+rule | RL | 0.712 | 0.729 | -0.018 | 5/4 | n | n | n | LOSES |
| IE-10-DUAL-AXIS-PINCER | LLM+RL | rule+rule | 0.921 | 0.801 | +0.120 | 5/3 | Y | Y | Y | STABLE |
| IE-10-DUAL-AXIS-PINCER | LLM+RL | RL | 0.921 | 0.729 | +0.192 | 5/4 | Y | Y | Y | STABLE |
| IE-10-DUAL-AXIS-PINCER | pure-LLM | rule+rule | 0.603 | 0.801 | -0.198 | 5/3 | n | n | n | LOSES |
| IE-10-DUAL-AXIS-PINCER | pure-LLM | RL | 0.603 | 0.729 | -0.127 | 5/4 | n | n | n | LOSES |
| IE-11-DECOY-SCREEN | LLM+rule | rule+rule | 0.747 | 0.681 | +0.066 | 5/3 | Y | n | Y | mean-only |
| IE-11-DECOY-SCREEN | LLM+rule | RL | 0.747 | 0.184 | +0.563 | 5/3 | Y | Y | Y | STABLE |
| IE-11-DECOY-SCREEN | LLM+RL | rule+rule | 0.820 | 0.681 | +0.138 | 5/3 | Y | n | Y | mean-only |
| IE-11-DECOY-SCREEN | LLM+RL | RL | 0.820 | 0.184 | +0.635 | 5/3 | Y | Y | Y | STABLE |
| IE-11-DECOY-SCREEN | pure-LLM | rule+rule | 0.346 | 0.681 | -0.335 | 5/3 | n | n | n | LOSES |
| IE-11-DECOY-SCREEN | pure-LLM | RL | 0.346 | 0.184 | +0.162 | 5/3 | Y | n | Y | mean-only |
| IE-12-FOG-ONSET | LLM+rule | rule+rule | 0.766 | 0.711 | +0.055 | 5/9 | Y | n | n | mean-only |
| IE-12-FOG-ONSET | LLM+rule | RL | 0.766 | 0.641 | +0.125 | 5/6 | Y | n | Y | mean-only |
| IE-12-FOG-ONSET | LLM+RL | rule+rule | 0.659 | 0.711 | -0.052 | 5/9 | n | n | n | LOSES |
| IE-12-FOG-ONSET | LLM+RL | RL | 0.659 | 0.641 | +0.018 | 5/6 | Y | n | n | mean-only |
| IE-12-FOG-ONSET | pure-LLM | rule+rule | 0.441 | 0.711 | -0.270 | 5/9 | n | n | n | LOSES |
| IE-12-FOG-ONSET | pure-LLM | RL | 0.441 | 0.641 | -0.199 | 5/6 | n | n | n | LOSES |
| IE-13-DEEP-STRIKE | LLM+rule | rule+rule | 0.807 | 0.709 | +0.098 | 5/7 | Y | n | Y | mean-only |
| IE-13-DEEP-STRIKE | LLM+rule | RL | 0.807 | 0.538 | +0.270 | 5/3 | Y | Y | Y | STABLE |
| IE-13-DEEP-STRIKE | LLM+RL | rule+rule | 0.790 | 0.709 | +0.081 | 5/7 | Y | n | Y | mean-only |
| IE-13-DEEP-STRIKE | LLM+RL | RL | 0.790 | 0.538 | +0.253 | 5/3 | Y | Y | Y | STABLE |
| IE-13-DEEP-STRIKE | pure-LLM | rule+rule | 0.597 | 0.709 | -0.112 | 5/7 | n | n | n | LOSES |
| IE-13-DEEP-STRIKE | pure-LLM | RL | 0.597 | 0.538 | +0.059 | 5/3 | Y | n | Y | mean-only |
| IE-14-SATURATION-THREE-WAVE | LLM+rule | rule+rule | 0.793 | 0.787 | +0.005 | 5/3 | Y | n | n | mean-only |
| IE-14-SATURATION-THREE-WAVE | LLM+rule | RL | 0.793 | 0.506 | +0.287 | 5/3 | Y | n | Y | mean-only |
| IE-14-SATURATION-THREE-WAVE | LLM+RL | rule+rule | 0.897 | 0.787 | +0.110 | 5/3 | Y | n | Y | mean-only |
| IE-14-SATURATION-THREE-WAVE | LLM+RL | RL | 0.897 | 0.506 | +0.391 | 5/3 | Y | Y | Y | STABLE |
| IE-14-SATURATION-THREE-WAVE | pure-LLM | rule+rule | 0.354 | 0.787 | -0.433 | 5/3 | n | n | n | LOSES |
| IE-14-SATURATION-THREE-WAVE | pure-LLM | RL | 0.354 | 0.506 | -0.152 | 5/3 | n | n | n | LOSES |

### 稳定胜出清单

**LLM+rule**：6 条，覆盖 5/14 场景

| 场景 | 对手 | Δ |
|---|---|---|
| IE-02-DUAL-THREAT | rule+rule | +0.144 |
| IE-02-DUAL-THREAT | RL | +0.151 |
| IE-07-CROSS-DOMAIN | RL | +0.108 |
| IE-09-STAGGERED-WAVES | RL | +0.251 |
| IE-11-DECOY-SCREEN | RL | +0.563 |
| IE-13-DEEP-STRIKE | RL | +0.270 |

**LLM+RL**：9 条，覆盖 7/14 场景

| 场景 | 对手 | Δ |
|---|---|---|
| IE-06-DECOY-MIXED | rule+rule | +0.136 |
| IE-06-DECOY-MIXED | RL | +0.142 |
| IE-07-CROSS-DOMAIN | RL | +0.080 |
| IE-09-STAGGERED-WAVES | RL | +0.230 |
| IE-10-DUAL-AXIS-PINCER | rule+rule | +0.120 |
| IE-10-DUAL-AXIS-PINCER | RL | +0.192 |
| IE-11-DECOY-SCREEN | RL | +0.635 |
| IE-13-DEEP-STRIKE | RL | +0.253 |
| IE-14-SATURATION-THREE-WAVE | RL | +0.391 |

**pure-LLM**：0 条，覆盖 0/14 场景

## 表 D　反例披露（LLM 臂显著落后于基线）

共 **34 条**。任何结论都必须与此表同时报告。

| 场景 | 臂 | 落后于 | Δ |
|---|---|---|---|
| IE-02-DUAL-THREAT | pure-LLM | rule+rule | -0.602 |
| IE-02-DUAL-THREAT | pure-LLM | RL | -0.595 |
| IE-05-MULTI-AXIS | pure-LLM | rule+rule | -0.576 |
| IE-04-COMBINED-ARMS | pure-LLM | rule+rule | -0.566 |
| IE-01-SINGLE-TARGET | pure-LLM | RL | -0.533 |
| IE-05-MULTI-AXIS | pure-LLM | RL | -0.515 |
| IE-04-COMBINED-ARMS | pure-LLM | RL | -0.441 |
| IE-14-SATURATION-THREE-WAVE | pure-LLM | rule+rule | -0.433 |
| IE-01-SINGLE-TARGET | pure-LLM | rule+rule | -0.348 |
| IE-11-DECOY-SCREEN | pure-LLM | rule+rule | -0.335 |
| IE-03-SURFACE-RAID | LLM+RL | RL | -0.326 |
| IE-12-FOG-ONSET | pure-LLM | rule+rule | -0.270 |
| IE-03-SURFACE-RAID | pure-LLM | RL | -0.261 |
| IE-06-DECOY-MIXED | pure-LLM | rule+rule | -0.223 |
| IE-06-DECOY-MIXED | pure-LLM | RL | -0.218 |
| IE-12-FOG-ONSET | pure-LLM | RL | -0.199 |
| IE-10-DUAL-AXIS-PINCER | pure-LLM | rule+rule | -0.198 |
| IE-09-STAGGERED-WAVES | pure-LLM | rule+rule | -0.182 |
| IE-08-ISLAND-STRIKE | pure-LLM | rule+rule | -0.152 |
| IE-14-SATURATION-THREE-WAVE | pure-LLM | RL | -0.152 |
| IE-10-DUAL-AXIS-PINCER | pure-LLM | RL | -0.127 |
| IE-03-SURFACE-RAID | LLM+RL | rule+rule | -0.114 |
| IE-13-DEEP-STRIKE | pure-LLM | rule+rule | -0.112 |
| IE-03-SURFACE-RAID | LLM+rule | RL | -0.103 |
| IE-01-SINGLE-TARGET | LLM+RL | RL | -0.102 |
| IE-10-DUAL-AXIS-PINCER | LLM+rule | rule+rule | -0.089 |
| IE-04-COMBINED-ARMS | LLM+rule | rule+rule | -0.071 |
| IE-12-FOG-ONSET | LLM+RL | rule+rule | -0.052 |
| IE-03-SURFACE-RAID | pure-LLM | rule+rule | -0.049 |
| IE-07-CROSS-DOMAIN | pure-LLM | rule+rule | -0.045 |
| IE-08-ISLAND-STRIKE | LLM+rule | rule+rule | -0.028 |
| IE-08-ISLAND-STRIKE | pure-LLM | RL | -0.022 |
| IE-10-DUAL-AXIS-PINCER | LLM+rule | RL | -0.018 |
| IE-04-COMBINED-ARMS | LLM+RL | rule+rule | -0.008 |

## 表 E　declared（有情报）对照

同臂同场景在历史 `declared` 口径下的均值，与 withheld 并排。

| 场景 | **LLM+rule** | **LLM+RL** | **pure-LLM** |
|---|---|---|---|
| IE-01-SINGLE-TARGET | 0.891 / 0.897 | 0.774 / 0.802 | 0.343 / 0.365 |
| IE-02-DUAL-THREAT | 0.908 / 0.787 | 0.851 / 0.866 | 0.162 / 0.133 |
| IE-03-SURFACE-RAID | 0.856 / 0.724 | 0.634 / 0.671 | 0.699 / 0.745 |
| IE-04-COMBINED-ARMS | 0.741 / 0.776 | 0.804 / 0.852 | 0.246 / 0.716 |
| IE-05-MULTI-AXIS | 0.790 / 0.791 | 0.824 / 0.812 | 0.188 / 0.362 |
| IE-06-DECOY-MIXED | 0.767 / 0.746 | 0.793 / 0.808 | 0.434 / 0.559 |
| IE-07-CROSS-DOMAIN | 0.792 / 0.780 | 0.763 / 0.726 | 0.703 / 0.722 |
| IE-08-ISLAND-STRIKE | 0.404 / 0.433 | 0.568 / 0.479 | 0.280 / 0.195 |
| IE-09-STAGGERED-WAVES | 0.880 / 0.802 | 0.859 / 0.792 | 0.638 / 0.728 |
| IE-10-DUAL-AXIS-PINCER | 0.712 / 0.779 | 0.921 / 0.884 | 0.603 / 0.654 |
| IE-11-DECOY-SCREEN | 0.747 / 0.680 | 0.820 / 0.757 | 0.346 / 0.618 |
| IE-12-FOG-ONSET | 0.766 / 0.790 | 0.659 / 0.739 | 0.441 / 0.401 |
| IE-13-DEEP-STRIKE | 0.807 / 0.778 | 0.790 / 0.849 | 0.597 / 0.560 |
| IE-14-SATURATION-THREE-WAVE | 0.793 / 0.774 | 0.897 / 0.863 | 0.354 / 0.466 |

| 臂 | withheld 均值 | declared 均值 | Δ | withheld 更优场景数 |
|---|---|---|---|---|
| LLM+rule | 0.7783 | 0.7442 | +0.0341 | 8/14 |
| LLM+RL | 0.7827 | 0.7741 | +0.0086 | 7/14 |
| pure-LLM | 0.4310 | 0.5082 | -0.0772 | 4/14 |

## 表 F　已知限制

1. **同 seed 不是重放**：LLM 端点在约 1.3k token 的真实提示词上非确定（同一请求 4 次输出互异）。固定 seed 对 LLM 臂是**一次独立复现**，不是同一条轨迹的重演；引擎侧确定性已单独验证。
2. **种间方差不可忽视**：`LLM+rule` 在 IE-03 上 s7=1.000 / s11=0.650 / s13=0.631，在 IE-08 上 s7=0.649 / s11=0.282 / s13=0.553。**单种子排名不可作为结论。**
3. **局长不是结果指标**：终局由 `rule.intruders-destroyed`（全歼已生成来袭者）或场景声明的 tick 触发，不同臂在同场景会跑不同 tick 数；计分按战果而非时长。
4. **基线为归档复用**：其代码逐位未改（`rule_planner.py`/`v2_executor.py`/`rl_executor.py` 等 SHA256 一致），场景包 14/14 逐字节一致，代码 A/B 对照 22 字段 0 差异（IE-01/02/05/06/09/11 六场景均 PASS）。
5. **`pure-LLM` 的部分低分与 `aborted` 无关**：日志接口缺陷已修复并复测，其 42 局三种子全部有效。
