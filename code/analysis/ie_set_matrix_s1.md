# IE 拦截交战场景集：完整实验矩阵（tag=s1）

> seed 7；`--plan-interval 10`；`--frontend graph`（两个 LLM 臂）。
> 三臂：`rule` = 规则规划 + GOAI 执行；`hybrid-LLM` = 千问规划 + GOAI 执行；`pure-LLM` = 每 tick 直接出低层指令。
> **配色约定**：`coalition.intruder`（红 / 威胁方）vs `coalition.defender`（蓝 / 我方）。

## 1. 敌我双方配置

| 场景 | 威胁无人机 | 威胁诱饵 | 威胁自爆船 | 威胁合计 | 来袭距离 | 波次 | 我方无人机 | 我方无人船 | 我方作战单元 | 岸基传感器 | 受保护设施 | 时长 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **IE-01-SINGLE-TARGET**<br>单目标拦截 | 1 | 0 | 0 | **1** | 12–12 km | 全程在场 | 2 | 1 | **3** | 1 | 1 | 900 |
| **IE-02-DUAL-THREAT**<br>双威胁防御 | 2 | 0 | 0 | **2** | 14–16 km | 全程在场 | 3 | 2 | **5** | 1 | 1 | 900 |
| **IE-03-SURFACE-RAID**<br>水面突袭 | 0 | 0 | 3 | **3** | 5–6 km | 全程在场 | 2 | 3 | **5** | 1 | 1 | 1000 |
| **IE-04-COMBINED-ARMS**<br>联合兵种攻击 | 3 | 0 | 3 | **6** | 6–24 km | 全程在场 | 3 | 3 | **6** | 1 | 2 | 1200 |
| **IE-05-MULTI-AXIS**<br>多方向接近 | 4 | 0 | 3 | **7** | 8–18 km | 全程在场 | 4 | 3 | **7** | 1 | 2 | 1200 |
| **IE-06-DECOY-MIXED**<br>真假威胁与诱导攻击 | 4 | 2 | 3 | **9** | 8–19 km | 全程在场 | 4 | 4 | **8** | 1 | 1 | 1200 |
| **IE-07-CROSS-DOMAIN**<br>跨域渗透 | 6 | 0 | 4 | **10** | 7–26 km | t=400:3 | 5 | 4 | **9** | 1 | 2 | 1400 |
| **MD-AD-006-ISLAND-STRIKE**<br>岛礁突击 | 12 | 0 | 5 | **17** | 7–31 km | t=0:8, t=600:9 | 9 | 3 | **12** | 0 | 4 | 1800 |

### 1.1 弹药预算与受保护设施权重

| 场景 | 我方无人机载弹 | 我方无人船载弹 | 设施权重 |
|---|---|---|---|
| IE-01-SINGLE-TARGET | 2 | 2 | {"facility.command": 1.0} |
| IE-02-DUAL-THREAT | 2 | 2 | {"facility.command": 1.0} |
| IE-03-SURFACE-RAID | 2 | 2 | {"facility.berth": 1.0} |
| IE-04-COMBINED-ARMS | 2 | 2 | {"facility.command": 2.0, "facility.fuel": 1.0} |
| IE-05-MULTI-AXIS | 2 | 2 | {"facility.command": 1.5, "facility.berth": 1.0} |
| IE-06-DECOY-MIXED | 2 | 2 | {"facility.command": 1.0} |
| IE-07-CROSS-DOMAIN | 2 | 2 | {"facility.pier": 1.0, "facility.command": 1.0} |
| MD-AD-006-ISLAND-STRIKE | 2 | 2 | {"facility.command": 2.0, "facility.comms": 1.5, "facility.fuel": 1.5, "facility.pier": 1.0} |

## 2. 总体策略评分矩阵（防守方视角，越高越好）

| 场景 | rule | hybrid-LLM | pure-LLM | 胜者 | 领先幅度 |
|---|---|---|---|---|---|
| **IE-01-SINGLE-TARGET** | **0.9250** | 0.9250 | 0.7500 | rule | 0.0000 |
| **IE-02-DUAL-THREAT** | 0.8167 | **1.0000** | 0.9833 | hybrid-llm | 0.0167 |
| **IE-03-SURFACE-RAID** | **0.8000** | 0.7750 | 0.7500 | rule | 0.0250 |
| **IE-04-COMBINED-ARMS** | 0.8500 | **1.0000** | 0.9250 | hybrid-llm | 0.0750 |
| **IE-05-MULTI-AXIS** | 0.8857 | **0.9429** | 0.9000 | hybrid-llm | 0.0429 |
| **IE-06-DECOY-MIXED** | 0.7875 | **0.8604** | 0.8333 | hybrid-llm | 0.0271 |
| **IE-07-CROSS-DOMAIN** | 0.7787 | **0.8051** | 0.7804 | hybrid-llm | 0.0247 |
| **MD-AD-006-ISLAND-STRIKE** | 0.2483 | **0.5101** | 0.2391 | hybrid-llm | 0.2618 |

**汇总**

| 臂 | 胜 | 平 | 负 | 平均差额 vs rule |
|---|---|---|---|---|
| rule | 0 | 8 | 0 | +0.0000 |
| hybrid-llm | 6 | 1 | 1 | +0.0908 |
| pure-llm | 4 | 1 | 3 | +0.0087 |

## 3. 逐层得分（每场景每臂）

| 场景 | 臂 | 总分 | terminal | facilities | depth | leak | exchange | ammo | surface |
|---|---|---|---|---|---|---|---|---|---|
| IE-01-SINGLE-TARGET | rule | 0.9250 | 1.00 | 1.00 | 1.00 | 1.00 | 0.50 | 0.50 | 1.00 |
| IE-01-SINGLE-TARGET | hybrid-llm | 0.9250 | 1.00 | 1.00 | 1.00 | 1.00 | 0.50 | 0.50 | 1.00 |
| IE-01-SINGLE-TARGET | pure-llm | 0.7500 | 1.00 | 1.00 | 0.00 | 1.00 | 0.50 | 1.00 | 1.00 |
| IE-02-DUAL-THREAT | rule | 0.8167 | 1.00 | 1.00 | 0.50 | 1.00 | 0.50 | 0.33 | 1.00 |
| IE-02-DUAL-THREAT | hybrid-llm | 1.0000 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| IE-02-DUAL-THREAT | pure-llm | 0.9833 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.67 | 1.00 |
| IE-03-SURFACE-RAID | rule | 0.8000 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| IE-03-SURFACE-RAID | hybrid-llm | 0.7750 | 1.00 | 1.00 | 0.00 | 1.00 | 0.75 | 1.00 | 1.00 |
| IE-03-SURFACE-RAID | pure-llm | 0.7500 | 1.00 | 1.00 | 0.00 | 1.00 | 0.50 | 1.00 | 1.00 |
| IE-04-COMBINED-ARMS | rule | 0.8500 | 1.00 | 1.00 | 0.33 | 1.00 | 1.00 | 0.67 | 1.00 |
| IE-04-COMBINED-ARMS | hybrid-llm | 1.0000 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| IE-04-COMBINED-ARMS | pure-llm | 0.9250 | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 0.83 | 1.00 |
| IE-05-MULTI-AXIS | rule | 0.8857 | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 0.71 | 1.00 |
| IE-05-MULTI-AXIS | hybrid-llm | 0.9429 | 1.00 | 1.00 | 0.75 | 1.00 | 1.00 | 0.86 | 1.00 |
| IE-05-MULTI-AXIS | pure-llm | 0.9000 | 1.00 | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 | 1.00 |
| IE-06-DECOY-MIXED | rule | 0.7875 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.75 | 1.00 |
| IE-06-DECOY-MIXED | hybrid-llm | 0.8604 | 1.00 | 1.00 | 0.33 | 1.00 | 1.00 | 0.88 | 1.00 |
| IE-06-DECOY-MIXED | pure-llm | 0.8333 | 1.00 | 1.00 | 0.17 | 1.00 | 1.00 | 1.00 | 1.00 |
| IE-07-CROSS-DOMAIN | rule | 0.7787 | 1.00 | 0.71 | 0.33 | 1.00 | 1.00 | 0.67 | 1.00 |
| IE-07-CROSS-DOMAIN | hybrid-llm | 0.8051 | 1.00 | 0.71 | 0.50 | 1.00 | 0.88 | 0.78 | 1.00 |
| IE-07-CROSS-DOMAIN | pure-llm | 0.7804 | 1.00 | 0.71 | 0.50 | 1.00 | 0.58 | 0.88 | 1.00 |
| MD-AD-006-ISLAND-STRIKE | rule | 0.2483 | 0.00 | 0.00 | 0.25 | 0.25 | 0.40 | 0.67 | 1.00 |
| MD-AD-006-ISLAND-STRIKE | hybrid-llm | 0.5101 | 0.00 | 0.58 | 0.50 | 0.75 | 0.39 | 1.00 | 1.00 |
| MD-AD-006-ISLAND-STRIKE | pure-llm | 0.2391 | 0.00 | 0.00 | 0.25 | 0.25 | 0.31 | 0.67 | 1.00 |

## 4. 全部记录指标（每场景每臂）


### 4.1 终局

| 场景 | 臂 | 终局判定 | 锁定 tick | 实跑 tick | 中断 |
|---|---|---|---|---|---|
| IE-01-SINGLE-TARGET | rule | defender_success | 39 | 39 | — |
| IE-01-SINGLE-TARGET | hybrid-llm | defender_success | 45 | 45 | — |
| IE-01-SINGLE-TARGET | pure-llm | defender_success | 229 | 229 | — |
| IE-02-DUAL-THREAT | rule | defender_success | 899 | 899 | — |
| IE-02-DUAL-THREAT | hybrid-llm | defender_success | 94 | 94 | — |
| IE-02-DUAL-THREAT | pure-llm | defender_success | 208 | 208 | — |
| IE-03-SURFACE-RAID | rule | defender_success | 732 | 732 | — |
| IE-03-SURFACE-RAID | hybrid-llm | defender_success | 732 | 732 | — |
| IE-03-SURFACE-RAID | pure-llm | defender_success | 732 | 732 | — |
| IE-04-COMBINED-ARMS | rule | defender_success | 1199 | 1199 | — |
| IE-04-COMBINED-ARMS | hybrid-llm | defender_success | 880 | 880 | — |
| IE-04-COMBINED-ARMS | pure-llm | defender_success | 1199 | 1199 | — |
| IE-05-MULTI-AXIS | rule | defender_success | 1199 | 1199 | — |
| IE-05-MULTI-AXIS | hybrid-llm | defender_success | 1199 | 1199 | — |
| IE-05-MULTI-AXIS | pure-llm | defender_success | 1199 | 1199 | — |
| IE-06-DECOY-MIXED | rule | defender_success | 1199 | 1199 | — |
| IE-06-DECOY-MIXED | hybrid-llm | defender_success | 1199 | 1199 | — |
| IE-06-DECOY-MIXED | pure-llm | defender_success | 1199 | 1199 | — |
| IE-07-CROSS-DOMAIN | rule | defender_success | 1399 | 1399 | — |
| IE-07-CROSS-DOMAIN | hybrid-llm | defender_success | 1399 | 1399 | — |
| IE-07-CROSS-DOMAIN | pure-llm | defender_success | 1399 | 1399 | — |
| MD-AD-006-ISLAND-STRIKE | rule | intruder_success | 1191 | 1191 | — |
| MD-AD-006-ISLAND-STRIKE | hybrid-llm | intruder_success | 1124 | 1124 | — |
| MD-AD-006-ISLAND-STRIKE | pure-llm | intruder_success | 1191 | 1191 | — |

### 4.2 交战

| 场景 | 臂 | 执行发射总数 | 我方发射 | 威胁方发射 | 拦截率 | 投弹率 | 漏防率 | 纵深拦截率 | 纵深均值 m | 纵深中位 m |
|---|---|---|---|---|---|---|---|---|---|---|
| IE-01-SINGLE-TARGET | rule | 4 | 4 | 0 | — | — | — | — | — | — |
| IE-01-SINGLE-TARGET | hybrid-llm | 4 | 4 | 0 | — | — | — | — | — | — |
| IE-01-SINGLE-TARGET | pure-llm | 2 | 2 | 0 | — | — | — | — | — | — |
| IE-02-DUAL-THREAT | rule | 6 | 6 | 0 | — | — | — | — | — | — |
| IE-02-DUAL-THREAT | hybrid-llm | 4 | 4 | 0 | — | — | — | — | — | — |
| IE-02-DUAL-THREAT | pure-llm | 6 | 6 | 0 | — | — | — | — | — | — |
| IE-03-SURFACE-RAID | rule | 6 | 6 | 0 | — | — | — | — | — | — |
| IE-03-SURFACE-RAID | hybrid-llm | 6 | 6 | 0 | — | — | — | — | — | — |
| IE-03-SURFACE-RAID | pure-llm | 4 | 4 | 0 | — | — | — | — | — | — |
| IE-04-COMBINED-ARMS | rule | 12 | 12 | 0 | — | — | — | — | — | — |
| IE-04-COMBINED-ARMS | hybrid-llm | 12 | 12 | 0 | — | — | — | — | — | — |
| IE-04-COMBINED-ARMS | pure-llm | 12 | 12 | 0 | — | — | — | — | — | — |
| IE-05-MULTI-AXIS | rule | 14 | 14 | 0 | — | — | — | — | — | — |
| IE-05-MULTI-AXIS | hybrid-llm | 14 | 14 | 0 | — | — | — | — | — | — |
| IE-05-MULTI-AXIS | pure-llm | 8 | 8 | 0 | — | — | — | — | — | — |
| IE-06-DECOY-MIXED | rule | 16 | 16 | 0 | — | — | — | — | — | — |
| IE-06-DECOY-MIXED | hybrid-llm | 16 | 16 | 0 | — | — | — | — | — | — |
| IE-06-DECOY-MIXED | pure-llm | 8 | 8 | 0 | — | — | — | — | — | — |
| IE-07-CROSS-DOMAIN | rule | 18 | 18 | 0 | — | — | — | — | — | — |
| IE-07-CROSS-DOMAIN | hybrid-llm | 18 | 18 | 0 | — | — | — | — | — | — |
| IE-07-CROSS-DOMAIN | pure-llm | 16 | 16 | 0 | — | — | — | — | — | — |
| MD-AD-006-ISLAND-STRIKE | rule | 67 | 24 | 43 | — | — | — | — | — | — |
| MD-AD-006-ISLAND-STRIKE | hybrid-llm | 47 | 15 | 32 | — | — | — | — | — | — |
| MD-AD-006-ISLAND-STRIKE | pure-llm | 68 | 24 | 44 | — | — | — | — | — | — |

### 4.3 战损

| 场景 | 臂 | 我方无人机损失 | 我方无人机总数 | 我方无人船损失 | 我方无人船总数 | 威胁无人机损失 | 威胁无人机总数 | 威胁自爆船损失 | 威胁自爆船总数 |
|---|---|---|---|---|---|---|---|---|---|
| IE-01-SINGLE-TARGET | rule | 0 | 2 | 0 | 1 | 1 | 1 | 0 | 0 |
| IE-01-SINGLE-TARGET | hybrid-llm | 0 | 2 | 0 | 1 | 1 | 1 | 0 | 0 |
| IE-01-SINGLE-TARGET | pure-llm | 0 | 2 | 0 | 1 | 1 | 1 | 0 | 0 |
| IE-02-DUAL-THREAT | rule | 0 | 3 | 0 | 2 | 1 | 2 | 0 | 0 |
| IE-02-DUAL-THREAT | hybrid-llm | 0 | 3 | 0 | 2 | 2 | 2 | 0 | 0 |
| IE-02-DUAL-THREAT | pure-llm | 0 | 3 | 0 | 2 | 2 | 2 | 0 | 0 |
| IE-03-SURFACE-RAID | rule | 0 | 2 | 0 | 3 | 0 | 0 | 3 | 3 |
| IE-03-SURFACE-RAID | hybrid-llm | 2 | 2 | 0 | 3 | 0 | 0 | 3 | 3 |
| IE-03-SURFACE-RAID | pure-llm | 0 | 2 | 3 | 3 | 0 | 0 | 3 | 3 |
| IE-04-COMBINED-ARMS | rule | 0 | 3 | 0 | 3 | 1 | 3 | 3 | 3 |
| IE-04-COMBINED-ARMS | hybrid-llm | 0 | 3 | 0 | 3 | 3 | 3 | 3 | 3 |
| IE-04-COMBINED-ARMS | pure-llm | 2 | 3 | 0 | 3 | 2 | 3 | 3 | 3 |
| IE-05-MULTI-AXIS | rule | 0 | 4 | 0 | 3 | 2 | 4 | 3 | 3 |
| IE-05-MULTI-AXIS | hybrid-llm | 0 | 4 | 0 | 3 | 3 | 4 | 3 | 3 |
| IE-05-MULTI-AXIS | pure-llm | 2 | 4 | 0 | 3 | 2 | 4 | 3 | 3 |
| IE-06-DECOY-MIXED | rule | 0 | 4 | 0 | 4 | 3 | 6 | 3 | 3 |
| IE-06-DECOY-MIXED | hybrid-llm | 0 | 4 | 2 | 4 | 4 | 6 | 3 | 3 |
| IE-06-DECOY-MIXED | pure-llm | 2 | 4 | 0 | 4 | 3 | 6 | 3 | 3 |
| IE-07-CROSS-DOMAIN | rule | 0 | 5 | 0 | 4 | 2 | 6 | 4 | 4 |
| IE-07-CROSS-DOMAIN | hybrid-llm | 0 | 5 | 3 | 4 | 3 | 6 | 4 | 4 |
| IE-07-CROSS-DOMAIN | pure-llm | 4 | 5 | 1 | 4 | 3 | 6 | 4 | 4 |
| MD-AD-006-ISLAND-STRIKE | rule | 6 | 9 | 0 | 3 | 3 | 12 | 5 | 5 |
| MD-AD-006-ISLAND-STRIKE | hybrid-llm | 9 | 9 | 3 | 3 | 6 | 12 | 5 | 5 |
| MD-AD-006-ISLAND-STRIKE | pure-llm | 6 | 9 | 3 | 3 | 3 | 12 | 5 | 5 |

### 4.4 效率与目标

| 场景 | 臂 | 我方击杀 | 我方被击杀 | 杀伤/发 | 设施加权存活 | 设施摧毁数 |
|---|---|---|---|---|---|---|
| IE-01-SINGLE-TARGET | rule | — | — | 0.0000 | — | — |
| IE-01-SINGLE-TARGET | hybrid-llm | — | — | 0.0000 | — | — |
| IE-01-SINGLE-TARGET | pure-llm | — | — | 0.0000 | — | — |
| IE-02-DUAL-THREAT | rule | — | — | 0.1667 | — | — |
| IE-02-DUAL-THREAT | hybrid-llm | — | — | 0.2500 | — | — |
| IE-02-DUAL-THREAT | pure-llm | — | — | 0.1667 | — | — |
| IE-03-SURFACE-RAID | rule | — | — | 0.1667 | — | — |
| IE-03-SURFACE-RAID | hybrid-llm | — | — | 0.3333 | — | — |
| IE-03-SURFACE-RAID | pure-llm | — | — | 0.2500 | — | — |
| IE-04-COMBINED-ARMS | rule | — | — | 0.1667 | — | — |
| IE-04-COMBINED-ARMS | hybrid-llm | — | — | 0.1667 | — | — |
| IE-04-COMBINED-ARMS | pure-llm | — | — | 0.3333 | — | — |
| IE-05-MULTI-AXIS | rule | — | — | 0.1429 | — | — |
| IE-05-MULTI-AXIS | hybrid-llm | — | — | 0.3571 | — | — |
| IE-05-MULTI-AXIS | pure-llm | — | — | 0.2500 | — | — |
| IE-06-DECOY-MIXED | rule | — | — | 0.1250 | — | — |
| IE-06-DECOY-MIXED | hybrid-llm | — | — | 0.3125 | — | — |
| IE-06-DECOY-MIXED | pure-llm | — | — | 0.2500 | — | — |
| IE-07-CROSS-DOMAIN | rule | — | — | 0.1111 | — | — |
| IE-07-CROSS-DOMAIN | hybrid-llm | — | — | 0.1667 | — | — |
| IE-07-CROSS-DOMAIN | pure-llm | — | — | 0.2500 | — | — |
| MD-AD-006-ISLAND-STRIKE | rule | — | — | 0.0597 | — | — |
| MD-AD-006-ISLAND-STRIKE | hybrid-llm | — | — | 0.0851 | — | — |
| MD-AD-006-ISLAND-STRIKE | pure-llm | — | — | 0.0735 | — | — |

### 4.5 被拒原因与耗时

| 场景 | 臂 | 开火拒绝原因 | 用时 s |
|---|---|---|---|
| IE-01-SINGLE-TARGET | rule | {} | 16.7900 |
| IE-01-SINGLE-TARGET | hybrid-llm | {} | 68.3000 |
| IE-01-SINGLE-TARGET | pure-llm | {} | 127.6600 |
| IE-02-DUAL-THREAT | rule | {} | 150.6600 |
| IE-02-DUAL-THREAT | hybrid-llm | {} | 163.0100 |
| IE-02-DUAL-THREAT | pure-llm | {} | 146.2100 |
| IE-03-SURFACE-RAID | rule | {} | 126.8000 |
| IE-03-SURFACE-RAID | hybrid-llm | {} | 959.5300 |
| IE-03-SURFACE-RAID | pure-llm | {"defender:combat.target_domain_denied": 2} | 535.4300 |
| IE-04-COMBINED-ARMS | rule | {} | 368.1900 |
| IE-04-COMBINED-ARMS | hybrid-llm | {} | 1568.3300 |
| IE-04-COMBINED-ARMS | pure-llm | {} | 1297.9700 |
| IE-05-MULTI-AXIS | rule | {} | 433.8000 |
| IE-05-MULTI-AXIS | hybrid-llm | {} | 2516.5000 |
| IE-05-MULTI-AXIS | pure-llm | {} | 1612.1800 |
| IE-06-DECOY-MIXED | rule | {} | 535.2100 |
| IE-06-DECOY-MIXED | hybrid-llm | {} | 2792.7900 |
| IE-06-DECOY-MIXED | pure-llm | {} | 1754.5700 |
| IE-07-CROSS-DOMAIN | rule | {} | 761.7800 |
| IE-07-CROSS-DOMAIN | hybrid-llm | {} | 3551.2500 |
| IE-07-CROSS-DOMAIN | pure-llm | {} | 2467.1000 |
| MD-AD-006-ISLAND-STRIKE | rule | {} | 752.3500 |
| MD-AD-006-ISLAND-STRIKE | hybrid-llm | {} | 3122.2500 |
| MD-AD-006-ISLAND-STRIKE | pure-llm | {"intruder:combat.envelope_denied": 1} | 2419.6600 |
