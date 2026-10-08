# 三臂无情报（withheld）实验结果表

> **主口径**：`--llm-briefing withheld` —— 提示词不含任何敌方情报
> （无波次数量/时刻/方位/意图，亦无兵力数字）。
> **对照口径**：`declared` —— 历史口径，逐波披露 `spawn_tick/count/axis/behavior`（含未来真值），
> 仅用于复现 2026-09-27 之前的旧读数。两种口径的分数**不可混用**。

> **指标**：`strategy_scorecard.defender_score`。该值**本身即**按适用层重新归一化后的加权平均
> （`strategy_metrics.py:625-629`：`Σ layers·w / Σ w`，仅适用于 `layer_applicability` 为真者）。
> 本表每局都做**独立复算校验**：用 `layers × layer_weights × layer_applicability` 反算，
> 与报告值偏差 > 5e-4 的局直接剔除，因此离线读取不会丢失适用性掩码。

> **基线口径**：`rule-rule` 与 `rl` **不重跑**，直接复用归档数据——两臂不读情报，
> 其脚本逐位未改、场景包 14/14 逐字节未变、代码 A/B 对照 0 字段差异（见
> `WITHHELD_BRIEFING_EVIDENCE.md`）。其中 `rl` 按策略身份锁定为
> `RL` 的单一 checkpoint（唯一带训练溯源、且 `decision_interval=5` 与训练值一致者）；
> 跨 checkpoint 求平均会得到不属于任何真实策略的数字。

## 表 A　逐场景均值（withheld 主口径）

格式：`均值 (种子数/局数)`；`—` 表示该格无有效数据。

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

## 表 B　主不等式与三合稳定性判据

三合判据（用户指定）：**均值胜** ∧ **逐种子全胜**（每个种子族的均值都高于对手全部种子族的均值）
∧ **分半都胜**（按均值分半后两半都仍高于对手均值）。三项全真记 `STABLE`；
仅均值胜记 `mean-only`；均值落后记 `LOSES`；样本不足记 `insufficient`。

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

### 稳定性汇总

- **LLM+rule**：`STABLE` 6 条，覆盖 5/14 场景
  - IE-02-DUAL-THREAT > rule+rule　Δ+0.144
  - IE-02-DUAL-THREAT > RL　Δ+0.151
  - IE-07-CROSS-DOMAIN > RL　Δ+0.108
  - IE-09-STAGGERED-WAVES > RL　Δ+0.251
  - IE-11-DECOY-SCREEN > RL　Δ+0.563
  - IE-13-DEEP-STRIKE > RL　Δ+0.270
- **LLM+RL**：`STABLE` 9 条，覆盖 7/14 场景
  - IE-06-DECOY-MIXED > rule+rule　Δ+0.136
  - IE-06-DECOY-MIXED > RL　Δ+0.142
  - IE-07-CROSS-DOMAIN > RL　Δ+0.080
  - IE-09-STAGGERED-WAVES > RL　Δ+0.230
  - IE-10-DUAL-AXIS-PINCER > rule+rule　Δ+0.120
  - IE-10-DUAL-AXIS-PINCER > RL　Δ+0.192
  - IE-11-DECOY-SCREEN > RL　Δ+0.635
  - IE-13-DEEP-STRIKE > RL　Δ+0.253
  - IE-14-SATURATION-THREE-WAVE > RL　Δ+0.391
- **pure-LLM**：`STABLE` 0 条，覆盖 0/14 场景

## 表 C　覆盖度

| 场景 | **LLM+rule** | **LLM+RL** | **pure-LLM** | **rule+rule** | **RL** |
|---|---|---|---|---|---|
| IE-01-SINGLE-TARGET | 6 局 / 6 种子 | 5 局 / 5 种子 | 5 局 / 5 种子 | 42 局 / 6 种子 | 6 局 / 5 种子 |
| IE-02-DUAL-THREAT | 6 局 / 6 种子 | 5 局 / 5 种子 | 5 局 / 5 种子 | 30 局 / 5 种子 | 5 局 / 5 种子 |
| IE-03-SURFACE-RAID | 5 局 / 5 种子 | 5 局 / 5 种子 | 5 局 / 5 种子 | 31 局 / 5 种子 | 5 局 / 5 种子 |
| IE-04-COMBINED-ARMS | 6 局 / 6 种子 | 5 局 / 5 种子 | 5 局 / 5 种子 | 25 局 / 5 种子 | 5 局 / 5 种子 |
| IE-05-MULTI-AXIS | 5 局 / 5 种子 | 5 局 / 5 种子 | 5 局 / 5 种子 | 22 局 / 5 种子 | 5 局 / 5 种子 |
| IE-06-DECOY-MIXED | 5 局 / 5 种子 | 5 局 / 5 种子 | 5 局 / 5 种子 | 22 局 / 5 种子 | 5 局 / 5 种子 |
| IE-07-CROSS-DOMAIN | 5 局 / 5 种子 | 5 局 / 5 种子 | 5 局 / 5 种子 | 22 局 / 5 种子 | 5 局 / 5 种子 |
| IE-08-ISLAND-STRIKE | 5 局 / 5 种子 | 5 局 / 5 种子 | 5 局 / 5 种子 | 28 局 / 5 种子 | 5 局 / 5 种子 |
| IE-09-STAGGERED-WAVES | 5 局 / 5 种子 | 5 局 / 5 种子 | 5 局 / 5 种子 | 3 局 / 3 种子 | 4 局 / 3 种子 |
| IE-10-DUAL-AXIS-PINCER | 5 局 / 5 种子 | 5 局 / 5 种子 | 5 局 / 5 种子 | 3 局 / 3 种子 | 4 局 / 3 种子 |
| IE-11-DECOY-SCREEN | 5 局 / 5 种子 | 5 局 / 5 种子 | 5 局 / 5 种子 | 3 局 / 3 种子 | 3 局 / 3 种子 |
| IE-12-FOG-ONSET | 5 局 / 5 种子 | 5 局 / 5 种子 | 5 局 / 5 种子 | 9 局 / 3 种子 | 6 局 / 3 种子 |
| IE-13-DEEP-STRIKE | 5 局 / 5 种子 | 5 局 / 5 种子 | 5 局 / 5 种子 | 7 局 / 3 种子 | 3 局 / 3 种子 |
| IE-14-SATURATION-THREE-WAVE | 5 局 / 5 种子 | 5 局 / 5 种子 | 5 局 / 5 种子 | 3 局 / 3 种子 | 3 局 / 3 种子 |

| 臂 | 总局数 | 覆盖场景 |
|---|---|---|
| LLM+rule | 73 | 14/14 |
| LLM+RL | 70 | 14/14 |
| pure-LLM | 70 | 14/14 |
| rule+rule | 250 | 14/14 |
| RL | 64 | 14/14 |

## 表 D　反例披露

以下格子中，LLM 臂在 withheld 口径下**显著落后**于单一架构基线：

| 场景 | 臂 | 对手 | Δ |
|---|---|---|---|
| IE-01-SINGLE-TARGET | LLM+RL | RL | -0.102 |
| IE-01-SINGLE-TARGET | pure-LLM | rule+rule | -0.348 |
| IE-01-SINGLE-TARGET | pure-LLM | RL | -0.533 |
| IE-02-DUAL-THREAT | pure-LLM | rule+rule | -0.602 |
| IE-02-DUAL-THREAT | pure-LLM | RL | -0.595 |
| IE-03-SURFACE-RAID | LLM+rule | RL | -0.103 |
| IE-03-SURFACE-RAID | LLM+RL | rule+rule | -0.114 |
| IE-03-SURFACE-RAID | LLM+RL | RL | -0.326 |
| IE-03-SURFACE-RAID | pure-LLM | rule+rule | -0.049 |
| IE-03-SURFACE-RAID | pure-LLM | RL | -0.261 |
| IE-04-COMBINED-ARMS | LLM+rule | rule+rule | -0.071 |
| IE-04-COMBINED-ARMS | LLM+RL | rule+rule | -0.008 |
| IE-04-COMBINED-ARMS | pure-LLM | rule+rule | -0.566 |
| IE-04-COMBINED-ARMS | pure-LLM | RL | -0.441 |
| IE-05-MULTI-AXIS | pure-LLM | rule+rule | -0.576 |
| IE-05-MULTI-AXIS | pure-LLM | RL | -0.515 |
| IE-06-DECOY-MIXED | pure-LLM | rule+rule | -0.223 |
| IE-06-DECOY-MIXED | pure-LLM | RL | -0.218 |
| IE-07-CROSS-DOMAIN | pure-LLM | rule+rule | -0.045 |
| IE-08-ISLAND-STRIKE | LLM+rule | rule+rule | -0.028 |
| IE-08-ISLAND-STRIKE | pure-LLM | rule+rule | -0.152 |
| IE-08-ISLAND-STRIKE | pure-LLM | RL | -0.022 |
| IE-09-STAGGERED-WAVES | pure-LLM | rule+rule | -0.182 |
| IE-10-DUAL-AXIS-PINCER | LLM+rule | rule+rule | -0.089 |
| IE-10-DUAL-AXIS-PINCER | LLM+rule | RL | -0.018 |
| IE-10-DUAL-AXIS-PINCER | pure-LLM | rule+rule | -0.198 |
| IE-10-DUAL-AXIS-PINCER | pure-LLM | RL | -0.127 |
| IE-11-DECOY-SCREEN | pure-LLM | rule+rule | -0.335 |
| IE-12-FOG-ONSET | LLM+RL | rule+rule | -0.052 |
| IE-12-FOG-ONSET | pure-LLM | rule+rule | -0.270 |
| IE-12-FOG-ONSET | pure-LLM | RL | -0.199 |
| IE-13-DEEP-STRIKE | pure-LLM | rule+rule | -0.112 |
| IE-14-SATURATION-THREE-WAVE | pure-LLM | rule+rule | -0.433 |
| IE-14-SATURATION-THREE-WAVE | pure-LLM | RL | -0.152 |

## 表 E　declared 对照列

同一臂、同一场景、有情报（`declared`）口径下的读数。两列差额即情报口径的效应。

> `rl` 列在 declared 侧同样按单一策略身份过滤，因此覆盖可能少于 14 场景；
> `pure-llm` 在 declared 侧只保留包线记录与场景声明一致的局。

| 场景 | **LLM+rule** | **LLM+RL** | **pure-LLM** | **rule+rule** | **RL** |
|---|---|---|---|---|---|
| | withheld / declared | withheld / declared | withheld / declared | withheld / declared | withheld / declared |
| IE-01-SINGLE-TARGET | 0.891 / — | 0.774 / — | 0.343 / — | 0.691 / 0.691 | 0.876 / 0.876 |
| IE-02-DUAL-THREAT | 0.908 / — | 0.851 / — | 0.162 / — | 0.765 / 0.765 | 0.757 / 0.757 |
| IE-03-SURFACE-RAID | 0.856 / — | 0.634 / — | 0.699 / — | 0.748 / 0.748 | 0.960 / 0.960 |
| IE-04-COMBINED-ARMS | 0.741 / — | 0.804 / — | 0.246 / — | 0.812 / 0.812 | 0.687 / 0.687 |
| IE-05-MULTI-AXIS | 0.790 / — | 0.824 / — | 0.188 / — | 0.763 / 0.763 | 0.703 / 0.703 |
| IE-06-DECOY-MIXED | 0.767 / — | 0.793 / — | 0.434 / — | 0.657 / 0.657 | 0.652 / 0.652 |
| IE-07-CROSS-DOMAIN | 0.792 / — | 0.763 / — | 0.703 / — | 0.749 / 0.749 | 0.684 / 0.684 |
| IE-08-ISLAND-STRIKE | 0.404 / — | 0.568 / — | 0.280 / — | 0.432 / 0.432 | 0.301 / 0.301 |
| IE-09-STAGGERED-WAVES | 0.880 / — | 0.859 / — | 0.638 / — | 0.820 / 0.820 | 0.629 / 0.629 |
| IE-10-DUAL-AXIS-PINCER | 0.712 / — | 0.921 / — | 0.603 / — | 0.801 / 0.801 | 0.729 / 0.729 |
| IE-11-DECOY-SCREEN | 0.747 / — | 0.820 / — | 0.346 / — | 0.681 / 0.681 | 0.184 / 0.184 |
| IE-12-FOG-ONSET | 0.766 / — | 0.659 / — | 0.441 / — | 0.711 / 0.711 | 0.641 / 0.641 |
| IE-13-DEEP-STRIKE | 0.807 / — | 0.790 / — | 0.597 / — | 0.709 / 0.709 | 0.538 / 0.538 |
| IE-14-SATURATION-THREE-WAVE | 0.793 / — | 0.897 / — | 0.354 / — | 0.787 / 0.787 | 0.506 / 0.506 |

## 表 F　口径与剔除溯源

被剔除的局必须显式计数——静默丢弃会让覆盖率看起来比实际更好。

### withheld 侧

（无剔除）

### declared 侧

| 剔除原因 | 局数 |
|---|---|
| `unknown planner 'rule-rl'` | 152 |
| `llm-rule: no briefing provenance` | 82 |
| `llm-rl: no briefing provenance` | 63 |
| `rl obs_dim mismatch` | 46 |
| `pure-llm: no envelope record` | 42 |
| `pure-llm: no briefing provenance` | 40 |
| `llm-rl policy tag=arm5_v12` | 26 |
| `llm-rl policy tag=arm5_llm_full_ie03_v10` | 23 |
| `llm-rl policy tag=arm5_v11` | 14 |
| `unusable: ticks=0` | 11 |
| `unusable: no terminal outcome` | 8 |
| `llm-rl policy tag=arm5_v13_ie08` | 4 |
| `unusable: aborted: exception: SessionFailureV2: session.contact_invalid: opaque` | 3 |
| `llm-rl policy tag=arm5_v2` | 3 |
| `unusable: aborted: exception: CheckpointErrorV2: checkpoint.integrity_invalid: ` | 2 |
| `unusable: aborted: exception: TypeError: cannot unpack non-iterable NoneType ob` | 2 |
| `unusable: aborted: exception: KeyError: 'tick'` | 2 |
| `unusable: aborted: exception: AttributeError: 'NoneType' object has no attribut` | 1 |
| `unusable: aborted: wall_limit 120.0s reached at tick 60` | 1 |
| `llm-rl policy tag=arm5_llm_formal2` | 1 |
| `llm-rl policy tag=arm5_v4` | 1 |
| `unusable: aborted: step_timeout at tick 0: 60.7s > 60.0s` | 1 |

---

## 使用限制（必须与表同时引用）

1. **同 seed 不是重放**：LLM 端点在约 1.3k token 的真实提示词上非确定（同一请求 4 次输出互异）。固定 seed 对 LLM 臂是一次独立复现，不等于同一条轨迹的重演；引擎一侧的确定性已单独验证。
2. **不可把 n=1 的格子当作臂均值**：表中同时给出种子数与局数，凡种子数 < 3 的格子只能作为单局读数引用。
3. **局长不可作为结果指标**：终局由 `rule.intruders-destroyed`（全歼已生成来袭者）或场景声明的 tick 触发，因此不同臂即使同场景也会跑不同 tick 数；计分按战果而非时长计算。
4. **反例必须与结论同时报告**（见表 D）。
