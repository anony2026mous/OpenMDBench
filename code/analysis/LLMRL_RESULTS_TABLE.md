# 四臂结果数据表（llm-rl / llm-rule / rl / pure-llm）

> 口径：`strategy_scorecard.defender_score`（归一化加权平均）。
> 过滤：`llm-rl` 限 tag `arm5_llm_reward_v9`；`rl` 限 `obs_dim=2866`（rlb2 基线）；
> `pure-llm` 仅收带包线记录且**逐场景等于 `agents.yaml` 声明值**的局
> （IE-08 声明 40 m/s，其余 43 m/s）；`rule-rule` 为纯规则基线。

## 表 A　逐场景均值（括号内为种子数 / 局数）

| 场景 | **LLM+rule** | **LLM+RL** | **RL** | **pure-LLM** | **rule+rule** |
|---|---|---|---|---|---|
| IE-01-SINGLE-TARGET | 0.903 (5s/11) | 0.903 (3s/5) | 0.876 (5s/6) | 0.365 (3s/3) | 0.619 (6s/26) |
| IE-02-DUAL-THREAT | 0.769 (5s/8) | 0.821 (3s/3) | 0.757 (5s/5) | 0.133 (3s/3) | 0.751 (5s/17) |
| IE-03-SURFACE-RAID | 0.719 (5s/9) | 0.671 (5s/6) | 0.960 (5s/5) | 0.745 (3s/3) | 0.709 (5s/16) |
| IE-04-COMBINED-ARMS | 0.731 (3s/4) | 0.852 (3s/3) | 0.687 (5s/5) | 0.716 (3s/3) | 0.775 (5s/14) |
| IE-05-MULTI-AXIS | 0.774 (3s/6) | 0.812 (3s/3) | 0.703 (5s/5) | 0.362 (3s/3) | 0.696 (5s/12) |
| IE-06-DECOY-MIXED | 0.729 (3s/5) | 0.808 (3s/3) | 0.652 (5s/5) | 0.559 (3s/3) | 0.542 (5s/12) |
| IE-07-CROSS-DOMAIN | 0.784 (3s/4) | 0.726 (3s/3) | 0.684 (5s/5) | 0.722 (3s/3) | 0.752 (5s/12) |
| IE-08-ISLAND-STRIKE | 0.488 (3s/6) | 0.479 (3s/5) | 0.301 (5s/5) | 0.195 (3s/3) | 0.493 (5s/13) |
| IE-09-STAGGERED-WAVES | 0.802 (3s/3) | 0.792 (3s/3) | 0.629 (3s/4) | 0.728 (2s/2) | 0.820 (3s/3) |
| IE-10-DUAL-AXIS-PINCER | 0.779 (3s/3) | 0.884 (3s/3) | 0.729 (3s/4) | 0.654 (3s/3) | 0.801 (3s/3) |
| IE-11-DECOY-SCREEN | 0.680 (3s/3) | 0.757 (3s/3) | 0.184 (3s/3) | 0.618 (2s/2) | 0.681 (3s/3) |
| IE-12-FOG-ONSET | 0.790 (3s/3) | 0.739 (3s/3) | 0.641 (3s/6) | 0.401 (3s/3) | 0.711 (3s/9) |
| IE-13-DEEP-STRIKE | 0.778 (3s/3) | 0.849 (3s/3) | 0.538 (3s/3) | 0.560 (3s/3) | 0.709 (3s/7) |
| IE-14-SATURATION-THREE-WAVE | 0.774 (3s/3) | 0.863 (3s/3) | 0.506 (3s/3) | 0.466 (3s/3) | 0.787 (3s/3) |

## 表 B　12 条主不等式（判定用合并 SD 规则）

判定规则：两侧 n≥2 且 |Δ| ≥ 2×合并SD → **通过/未过**；|Δ| < 0.05 且一侧 n<2 → 证据不足；
否则 |Δ| < 2×合并SD → 不可判读。

| 场景 | 混合臂 | 对手 | 混合均值 | 对手均值 | Δ | 2×合并SD | 判定 |
|---|---|---|---|---|---|---|---|
| IE-01-SINGLE-TARGET | LLM+rule | rule+rule | 0.903 | 0.619 | +0.283 | 0.606 | 不可判读 |
| IE-01-SINGLE-TARGET | LLM+rule | RL | 0.903 | 0.876 | +0.027 | 0.037 | 不可判读 |
| IE-01-SINGLE-TARGET | LLM+rule | pure-LLM | 0.903 | 0.365 | +0.538 | 0.499 | 通过 |
| IE-01-SINGLE-TARGET | LLM+RL | rule+rule | 0.903 | 0.619 | +0.283 | 0.635 | 不可判读 |
| IE-01-SINGLE-TARGET | LLM+RL | RL | 0.903 | 0.876 | +0.027 | 0.043 | 不可判读 |
| IE-01-SINGLE-TARGET | LLM+RL | pure-LLM | 0.903 | 0.365 | +0.538 | 0.619 | 不可判读 |
| IE-02-DUAL-THREAT | LLM+rule | rule+rule | 0.769 | 0.751 | +0.018 | 0.552 | 不可判读 |
| IE-02-DUAL-THREAT | LLM+rule | RL | 0.769 | 0.757 | +0.012 | 0.470 | 不可判读 |
| IE-02-DUAL-THREAT | LLM+rule | pure-LLM | 0.769 | 0.133 | +0.636 | 0.713 | 不可判读 |
| IE-02-DUAL-THREAT | LLM+RL | rule+rule | 0.821 | 0.751 | +0.070 | 0.563 | 不可判读 |
| IE-02-DUAL-THREAT | LLM+RL | RL | 0.821 | 0.757 | +0.063 | 0.441 | 不可判读 |
| IE-02-DUAL-THREAT | LLM+RL | pure-LLM | 0.821 | 0.133 | +0.688 | 0.783 | 不可判读 |
| IE-03-SURFACE-RAID | LLM+rule | rule+rule | 0.719 | 0.709 | +0.010 | 0.552 | 不可判读 |
| IE-03-SURFACE-RAID | LLM+rule | RL | 0.719 | 0.960 | -0.241 | 0.593 | 不可判读 |
| IE-03-SURFACE-RAID | LLM+rule | pure-LLM | 0.719 | 0.745 | -0.026 | 0.597 | 不可判读 |
| IE-03-SURFACE-RAID | LLM+RL | rule+rule | 0.671 | 0.709 | -0.038 | 0.591 | 不可判读 |
| IE-03-SURFACE-RAID | LLM+RL | RL | 0.671 | 0.960 | -0.288 | 0.687 | 不可判读 |
| IE-03-SURFACE-RAID | LLM+RL | pure-LLM | 0.671 | 0.745 | -0.074 | 0.703 | 不可判读 |
| IE-04-COMBINED-ARMS | LLM+rule | rule+rule | 0.731 | 0.775 | -0.044 | 0.374 | 不可判读 |
| IE-04-COMBINED-ARMS | LLM+rule | RL | 0.731 | 0.687 | +0.044 | 0.187 | 不可判读 |
| IE-04-COMBINED-ARMS | LLM+rule | pure-LLM | 0.731 | 0.716 | +0.015 | 0.240 | 不可判读 |
| IE-04-COMBINED-ARMS | LLM+RL | rule+rule | 0.852 | 0.775 | +0.077 | 0.376 | 不可判读 |
| IE-04-COMBINED-ARMS | LLM+RL | RL | 0.852 | 0.687 | +0.165 | 0.213 | 不可判读 |
| IE-04-COMBINED-ARMS | LLM+RL | pure-LLM | 0.852 | 0.716 | +0.136 | 0.246 | 不可判读 |
| IE-05-MULTI-AXIS | LLM+rule | rule+rule | 0.774 | 0.696 | +0.078 | 0.324 | 不可判读 |
| IE-05-MULTI-AXIS | LLM+rule | RL | 0.774 | 0.703 | +0.071 | 0.185 | 不可判读 |
| IE-05-MULTI-AXIS | LLM+rule | pure-LLM | 0.774 | 0.362 | +0.411 | 0.512 | 不可判读 |
| IE-05-MULTI-AXIS | LLM+RL | rule+rule | 0.812 | 0.696 | +0.116 | 0.352 | 不可判读 |
| IE-05-MULTI-AXIS | LLM+RL | RL | 0.812 | 0.703 | +0.109 | 0.202 | 不可判读 |
| IE-05-MULTI-AXIS | LLM+RL | pure-LLM | 0.812 | 0.362 | +0.450 | 0.611 | 不可判读 |
| IE-06-DECOY-MIXED | LLM+rule | rule+rule | 0.729 | 0.542 | +0.186 | 0.423 | 不可判读 |
| IE-06-DECOY-MIXED | LLM+rule | RL | 0.729 | 0.652 | +0.077 | 0.153 | 不可判读 |
| IE-06-DECOY-MIXED | LLM+rule | pure-LLM | 0.729 | 0.559 | +0.170 | 0.227 | 不可判读 |
| IE-06-DECOY-MIXED | LLM+RL | rule+rule | 0.808 | 0.542 | +0.266 | 0.458 | 不可判读 |
| IE-06-DECOY-MIXED | LLM+RL | RL | 0.808 | 0.652 | +0.156 | 0.180 | 不可判读 |
| IE-06-DECOY-MIXED | LLM+RL | pure-LLM | 0.808 | 0.559 | +0.249 | 0.286 | 不可判读 |
| IE-07-CROSS-DOMAIN | LLM+rule | rule+rule | 0.784 | 0.752 | +0.033 | 0.135 | 不可判读 |
| IE-07-CROSS-DOMAIN | LLM+rule | RL | 0.784 | 0.684 | +0.101 | 0.143 | 不可判读 |
| IE-07-CROSS-DOMAIN | LLM+rule | pure-LLM | 0.784 | 0.722 | +0.063 | 0.123 | 不可判读 |
| IE-07-CROSS-DOMAIN | LLM+RL | rule+rule | 0.726 | 0.752 | -0.026 | 0.124 | 不可判读 |
| IE-07-CROSS-DOMAIN | LLM+RL | RL | 0.726 | 0.684 | +0.042 | 0.069 | 不可判读 |
| IE-07-CROSS-DOMAIN | LLM+RL | pure-LLM | 0.726 | 0.722 | +0.004 | 0.044 | 不可判读 |
| IE-08-ISLAND-STRIKE | LLM+rule | rule+rule | 0.488 | 0.493 | -0.005 | 0.207 | 不可判读 |
| IE-08-ISLAND-STRIKE | LLM+rule | RL | 0.488 | 0.301 | +0.187 | 0.315 | 不可判读 |
| IE-08-ISLAND-STRIKE | LLM+rule | pure-LLM | 0.488 | 0.195 | +0.293 | 0.354 | 不可判读 |
| IE-08-ISLAND-STRIKE | LLM+RL | rule+rule | 0.479 | 0.493 | -0.014 | 0.232 | 不可判读 |
| IE-08-ISLAND-STRIKE | LLM+RL | RL | 0.479 | 0.301 | +0.177 | 0.345 | 不可判读 |
| IE-08-ISLAND-STRIKE | LLM+RL | pure-LLM | 0.479 | 0.195 | +0.284 | 0.390 | 不可判读 |
| IE-09-STAGGERED-WAVES | LLM+rule | rule+rule | 0.802 | 0.820 | -0.018 | 0.292 | 不可判读 |
| IE-09-STAGGERED-WAVES | LLM+rule | RL | 0.802 | 0.629 | +0.173 | 0.228 | 不可判读 |
| IE-09-STAGGERED-WAVES | LLM+rule | pure-LLM | 0.802 | 0.728 | +0.074 | 0.175 | 不可判读 |
| IE-09-STAGGERED-WAVES | LLM+RL | rule+rule | 0.792 | 0.820 | -0.029 | 0.375 | 不可判读 |
| IE-09-STAGGERED-WAVES | LLM+RL | RL | 0.792 | 0.629 | +0.162 | 0.306 | 不可判读 |
| IE-09-STAGGERED-WAVES | LLM+RL | pure-LLM | 0.792 | 0.728 | +0.063 | 0.313 | 不可判读 |
| IE-10-DUAL-AXIS-PINCER | LLM+rule | rule+rule | 0.779 | 0.801 | -0.022 | 0.210 | 不可判读 |
| IE-10-DUAL-AXIS-PINCER | LLM+rule | RL | 0.779 | 0.729 | +0.050 | 0.168 | 不可判读 |
| IE-10-DUAL-AXIS-PINCER | LLM+rule | pure-LLM | 0.779 | 0.654 | +0.125 | 0.201 | 不可判读 |
| IE-10-DUAL-AXIS-PINCER | LLM+RL | rule+rule | 0.884 | 0.801 | +0.083 | 0.223 | 不可判读 |
| IE-10-DUAL-AXIS-PINCER | LLM+RL | RL | 0.884 | 0.729 | +0.155 | 0.226 | 不可判读 |
| IE-10-DUAL-AXIS-PINCER | LLM+RL | pure-LLM | 0.884 | 0.654 | +0.230 | 0.288 | 不可判读 |
| IE-11-DECOY-SCREEN | LLM+rule | rule+rule | 0.680 | 0.681 | -0.001 | 0.273 | 不可判读 |
| IE-11-DECOY-SCREEN | LLM+rule | RL | 0.680 | 0.184 | +0.496 | 0.591 | 不可判读 |
| IE-11-DECOY-SCREEN | LLM+rule | pure-LLM | 0.680 | 0.618 | +0.062 | 0.269 | 不可判读 |
| IE-11-DECOY-SCREEN | LLM+RL | rule+rule | 0.757 | 0.681 | +0.075 | 0.225 | 不可判读 |
| IE-11-DECOY-SCREEN | LLM+RL | RL | 0.757 | 0.184 | +0.572 | 0.645 | 不可判读 |
| IE-11-DECOY-SCREEN | LLM+RL | pure-LLM | 0.757 | 0.618 | +0.138 | 0.229 | 不可判读 |
| IE-12-FOG-ONSET | LLM+rule | rule+rule | 0.790 | 0.711 | +0.079 | 0.353 | 不可判读 |
| IE-12-FOG-ONSET | LLM+rule | RL | 0.790 | 0.641 | +0.150 | 0.265 | 不可判读 |
| IE-12-FOG-ONSET | LLM+rule | pure-LLM | 0.790 | 0.401 | +0.389 | 0.533 | 不可判读 |
| IE-12-FOG-ONSET | LLM+RL | rule+rule | 0.739 | 0.711 | +0.028 | 0.413 | 不可判读 |
| IE-12-FOG-ONSET | LLM+RL | RL | 0.739 | 0.641 | +0.098 | 0.357 | 不可判读 |
| IE-12-FOG-ONSET | LLM+RL | pure-LLM | 0.739 | 0.401 | +0.337 | 0.593 | 不可判读 |
| IE-13-DEEP-STRIKE | LLM+rule | rule+rule | 0.778 | 0.709 | +0.068 | 0.254 | 不可判读 |
| IE-13-DEEP-STRIKE | LLM+rule | RL | 0.778 | 0.538 | +0.240 | 0.348 | 不可判读 |
| IE-13-DEEP-STRIKE | LLM+rule | pure-LLM | 0.778 | 0.560 | +0.218 | 0.278 | 不可判读 |
| IE-13-DEEP-STRIKE | LLM+RL | rule+rule | 0.849 | 0.709 | +0.140 | 0.275 | 不可判读 |
| IE-13-DEEP-STRIKE | LLM+RL | RL | 0.849 | 0.538 | +0.311 | 0.404 | 不可判读 |
| IE-13-DEEP-STRIKE | LLM+RL | pure-LLM | 0.849 | 0.560 | +0.289 | 0.340 | 不可判读 |
| IE-14-SATURATION-THREE-WAVE | LLM+rule | rule+rule | 0.774 | 0.787 | -0.014 | 0.261 | 不可判读 |
| IE-14-SATURATION-THREE-WAVE | LLM+rule | RL | 0.774 | 0.506 | +0.268 | 0.409 | 不可判读 |
| IE-14-SATURATION-THREE-WAVE | LLM+rule | pure-LLM | 0.774 | 0.466 | +0.307 | 0.446 | 不可判读 |
| IE-14-SATURATION-THREE-WAVE | LLM+RL | rule+rule | 0.863 | 0.787 | +0.076 | 0.235 | 不可判读 |
| IE-14-SATURATION-THREE-WAVE | LLM+RL | RL | 0.863 | 0.506 | +0.357 | 0.464 | 不可判读 |
| IE-14-SATURATION-THREE-WAVE | LLM+RL | pure-LLM | 0.863 | 0.466 | +0.397 | 0.505 | 不可判读 |

## 表 C　稳定性（三合判据：均值 ↑ / 逐种子全胜 / 分半都胜）

| 场景 | 混合臂 | 对手 | Δ | 均值 | 逐种子 | 分半 | 结论 |
|---|---|---|---|---|---|---|---|
| IE-01-SINGLE-TARGET | LLM+rule | rule+rule | +0.283 | Y | Y | Y | 稳定 |
| IE-01-SINGLE-TARGET | LLM+rule | RL | +0.027 | Y | Y | Y | 稳定 |
| IE-01-SINGLE-TARGET | LLM+rule | pure-LLM | +0.538 | Y | Y | Y | 稳定 |
| IE-01-SINGLE-TARGET | LLM+RL | rule+rule | +0.283 | Y | Y | Y | 稳定 |
| IE-01-SINGLE-TARGET | LLM+RL | RL | +0.027 | Y | Y | Y | 稳定 |
| IE-01-SINGLE-TARGET | LLM+RL | pure-LLM | +0.538 | Y | Y | Y | 稳定 |
| IE-02-DUAL-THREAT | LLM+rule | rule+rule | +0.018 | Y | n | n | 仅均值 |
| IE-02-DUAL-THREAT | LLM+rule | RL | +0.012 | Y | n | n | 仅均值 |
| IE-02-DUAL-THREAT | LLM+rule | pure-LLM | +0.636 | Y | Y | Y | 稳定 |
| IE-02-DUAL-THREAT | LLM+RL | rule+rule | +0.070 | Y | n | Y | 仅均值 |
| IE-02-DUAL-THREAT | LLM+RL | RL | +0.063 | Y | n | Y | 仅均值 |
| IE-02-DUAL-THREAT | LLM+RL | pure-LLM | +0.688 | Y | Y | Y | 稳定 |
| IE-03-SURFACE-RAID | LLM+rule | rule+rule | +0.010 | Y | n | n | 仅均值 |
| IE-03-SURFACE-RAID | LLM+rule | RL | -0.241 | n | n | n | 否 |
| IE-03-SURFACE-RAID | LLM+rule | pure-LLM | -0.026 | n | n | n | 否 |
| IE-03-SURFACE-RAID | LLM+RL | rule+rule | -0.038 | n | n | Y | 否 |
| IE-03-SURFACE-RAID | LLM+RL | RL | -0.288 | n | n | n | 否 |
| IE-03-SURFACE-RAID | LLM+RL | pure-LLM | -0.074 | n | n | n | 否 |
| IE-04-COMBINED-ARMS | LLM+rule | rule+rule | -0.044 | n | n | n | 否 |
| IE-04-COMBINED-ARMS | LLM+rule | RL | +0.044 | Y | n | Y | 仅均值 |
| IE-04-COMBINED-ARMS | LLM+rule | pure-LLM | +0.015 | Y | n | Y | 仅均值 |
| IE-04-COMBINED-ARMS | LLM+RL | rule+rule | +0.077 | Y | n | Y | 仅均值 |
| IE-04-COMBINED-ARMS | LLM+RL | RL | +0.165 | Y | Y | Y | 稳定 |
| IE-04-COMBINED-ARMS | LLM+RL | pure-LLM | +0.136 | Y | Y | Y | 稳定 |
| IE-05-MULTI-AXIS | LLM+rule | rule+rule | +0.078 | Y | n | Y | 仅均值 |
| IE-05-MULTI-AXIS | LLM+rule | RL | +0.071 | Y | n | Y | 仅均值 |
| IE-05-MULTI-AXIS | LLM+rule | pure-LLM | +0.411 | Y | Y | Y | 稳定 |
| IE-05-MULTI-AXIS | LLM+RL | rule+rule | +0.116 | Y | n | Y | 仅均值 |
| IE-05-MULTI-AXIS | LLM+RL | RL | +0.109 | Y | n | Y | 仅均值 |
| IE-05-MULTI-AXIS | LLM+RL | pure-LLM | +0.450 | Y | Y | Y | 稳定 |
| IE-06-DECOY-MIXED | LLM+rule | rule+rule | +0.186 | Y | n | Y | 仅均值 |
| IE-06-DECOY-MIXED | LLM+rule | RL | +0.077 | Y | n | Y | 仅均值 |
| IE-06-DECOY-MIXED | LLM+rule | pure-LLM | +0.170 | Y | Y | Y | 稳定 |
| IE-06-DECOY-MIXED | LLM+RL | rule+rule | +0.266 | Y | Y | Y | 稳定 |
| IE-06-DECOY-MIXED | LLM+RL | RL | +0.156 | Y | Y | Y | 稳定 |
| IE-06-DECOY-MIXED | LLM+RL | pure-LLM | +0.249 | Y | Y | Y | 稳定 |
| IE-07-CROSS-DOMAIN | LLM+rule | rule+rule | +0.033 | Y | n | Y | 仅均值 |
| IE-07-CROSS-DOMAIN | LLM+rule | RL | +0.101 | Y | Y | Y | 稳定 |
| IE-07-CROSS-DOMAIN | LLM+rule | pure-LLM | +0.063 | Y | n | Y | 仅均值 |
| IE-07-CROSS-DOMAIN | LLM+RL | rule+rule | -0.026 | n | n | n | 否 |
| IE-07-CROSS-DOMAIN | LLM+RL | RL | +0.042 | Y | Y | Y | 稳定 |
| IE-07-CROSS-DOMAIN | LLM+RL | pure-LLM | +0.004 | Y | n | Y | 仅均值 |
| IE-08-ISLAND-STRIKE | LLM+rule | rule+rule | -0.005 | n | n | n | 否 |
| IE-08-ISLAND-STRIKE | LLM+rule | RL | +0.187 | Y | n | Y | 仅均值 |
| IE-08-ISLAND-STRIKE | LLM+rule | pure-LLM | +0.293 | Y | Y | Y | 稳定 |
| IE-08-ISLAND-STRIKE | LLM+RL | rule+rule | -0.014 | n | n | n | 否 |
| IE-08-ISLAND-STRIKE | LLM+RL | RL | +0.177 | Y | n | Y | 仅均值 |
| IE-08-ISLAND-STRIKE | LLM+RL | pure-LLM | +0.284 | Y | Y | Y | 稳定 |
| IE-09-STAGGERED-WAVES | LLM+rule | rule+rule | -0.018 | n | n | n | 否 |
| IE-09-STAGGERED-WAVES | LLM+rule | RL | +0.173 | Y | Y | Y | 稳定 |
| IE-09-STAGGERED-WAVES | LLM+rule | pure-LLM | +0.074 | Y | n | Y | 仅均值 |
| IE-09-STAGGERED-WAVES | LLM+RL | rule+rule | -0.029 | n | n | n | 否 |
| IE-09-STAGGERED-WAVES | LLM+RL | RL | +0.162 | Y | n | Y | 仅均值 |
| IE-09-STAGGERED-WAVES | LLM+RL | pure-LLM | +0.063 | Y | n | Y | 仅均值 |
| IE-10-DUAL-AXIS-PINCER | LLM+rule | rule+rule | -0.022 | n | n | n | 否 |
| IE-10-DUAL-AXIS-PINCER | LLM+rule | RL | +0.050 | Y | n | Y | 仅均值 |
| IE-10-DUAL-AXIS-PINCER | LLM+rule | pure-LLM | +0.125 | Y | n | Y | 仅均值 |
| IE-10-DUAL-AXIS-PINCER | LLM+RL | rule+rule | +0.083 | Y | n | Y | 仅均值 |
| IE-10-DUAL-AXIS-PINCER | LLM+RL | RL | +0.155 | Y | n | Y | 仅均值 |
| IE-10-DUAL-AXIS-PINCER | LLM+RL | pure-LLM | +0.230 | Y | Y | Y | 稳定 |
| IE-11-DECOY-SCREEN | LLM+rule | rule+rule | -0.001 | n | n | n | 否 |
| IE-11-DECOY-SCREEN | LLM+rule | RL | +0.496 | Y | Y | Y | 稳定 |
| IE-11-DECOY-SCREEN | LLM+rule | pure-LLM | +0.062 | Y | n | Y | 仅均值 |
| IE-11-DECOY-SCREEN | LLM+RL | rule+rule | +0.075 | Y | n | Y | 仅均值 |
| IE-11-DECOY-SCREEN | LLM+RL | RL | +0.572 | Y | Y | Y | 稳定 |
| IE-11-DECOY-SCREEN | LLM+RL | pure-LLM | +0.138 | Y | n | Y | 仅均值 |
| IE-12-FOG-ONSET | LLM+rule | rule+rule | +0.079 | Y | n | Y | 仅均值 |
| IE-12-FOG-ONSET | LLM+rule | RL | +0.150 | Y | n | Y | 仅均值 |
| IE-12-FOG-ONSET | LLM+rule | pure-LLM | +0.389 | Y | Y | Y | 稳定 |
| IE-12-FOG-ONSET | LLM+RL | rule+rule | +0.028 | Y | n | Y | 仅均值 |
| IE-12-FOG-ONSET | LLM+RL | RL | +0.098 | Y | n | Y | 仅均值 |
| IE-12-FOG-ONSET | LLM+RL | pure-LLM | +0.337 | Y | n | Y | 仅均值 |
| IE-13-DEEP-STRIKE | LLM+rule | rule+rule | +0.068 | Y | n | Y | 仅均值 |
| IE-13-DEEP-STRIKE | LLM+rule | RL | +0.240 | Y | Y | Y | 稳定 |
| IE-13-DEEP-STRIKE | LLM+rule | pure-LLM | +0.218 | Y | Y | Y | 稳定 |
| IE-13-DEEP-STRIKE | LLM+RL | rule+rule | +0.140 | Y | n | Y | 仅均值 |
| IE-13-DEEP-STRIKE | LLM+RL | RL | +0.311 | Y | Y | Y | 稳定 |
| IE-13-DEEP-STRIKE | LLM+RL | pure-LLM | +0.289 | Y | Y | Y | 稳定 |
| IE-14-SATURATION-THREE-WAVE | LLM+rule | rule+rule | -0.014 | n | n | n | 否 |
| IE-14-SATURATION-THREE-WAVE | LLM+rule | RL | +0.268 | Y | Y | Y | 稳定 |
| IE-14-SATURATION-THREE-WAVE | LLM+rule | pure-LLM | +0.307 | Y | Y | Y | 稳定 |
| IE-14-SATURATION-THREE-WAVE | LLM+RL | rule+rule | +0.076 | Y | n | Y | 仅均值 |
| IE-14-SATURATION-THREE-WAVE | LLM+RL | RL | +0.357 | Y | Y | Y | 稳定 |
| IE-14-SATURATION-THREE-WAVE | LLM+RL | pure-LLM | +0.397 | Y | Y | Y | 稳定 |

## 表 D　汇总

| 臂 | 稳定不等式 | 覆盖场景 | vs rule+rule | vs RL | vs pure-LLM |
|---|---|---|---|---|---|
| **LLM+rule** | **15** | 11/14 | 1 | 6 | 8 |
| **LLM+RL** | **18** | 11/14 | 2 | 7 | 9 |

## 表 E　逐场景最优臂

| 场景 | 最优臂 | 均值 | 次优 | 均值 |
|---|---|---|---|---|
| IE-01-SINGLE-TARGET | **LLM+rule** | 0.903 | LLM+RL | 0.903 |
| IE-02-DUAL-THREAT | **LLM+RL** | 0.821 | LLM+rule | 0.769 |
| IE-03-SURFACE-RAID | **RL** | 0.960 | pure-LLM | 0.745 |
| IE-04-COMBINED-ARMS | **LLM+RL** | 0.852 | rule+rule | 0.775 |
| IE-05-MULTI-AXIS | **LLM+RL** | 0.812 | LLM+rule | 0.774 |
| IE-06-DECOY-MIXED | **LLM+RL** | 0.808 | LLM+rule | 0.729 |
| IE-07-CROSS-DOMAIN | **LLM+rule** | 0.784 | rule+rule | 0.752 |
| IE-08-ISLAND-STRIKE | **rule+rule** | 0.493 | LLM+rule | 0.488 |
| IE-09-STAGGERED-WAVES | **rule+rule** | 0.820 | LLM+rule | 0.802 |
| IE-10-DUAL-AXIS-PINCER | **LLM+RL** | 0.884 | rule+rule | 0.801 |
| IE-11-DECOY-SCREEN | **LLM+RL** | 0.757 | rule+rule | 0.681 |
| IE-12-FOG-ONSET | **LLM+rule** | 0.790 | LLM+RL | 0.739 |
| IE-13-DEEP-STRIKE | **LLM+RL** | 0.849 | LLM+rule | 0.778 |
| IE-14-SATURATION-THREE-WAVE | **LLM+RL** | 0.863 | rule+rule | 0.787 |
