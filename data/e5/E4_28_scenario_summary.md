# 竞争族 28 个场景：门禁与实测数据汇总

> 范围：`competition_v1` 的 30 个包。MD-REC-001 的 EASY/MEDIUM/HARD 三档是**同一场景的三个难度水平**，合并计 1 → **28 个场景**。
> 数据来源：`admission_ledger.json` + `analysis/d2_graded_final2.json`（5-seed 实测）；已逐行核对两者一致（28 行，0 处不符）。
> 这批场景由本角色（<author-C>）在 E4 场景族重标定中建立与标定；`formal` 树的 14 个 IE 场景属**更早的**实验，不在本表。

## 0. 两个口径的总览（先说清，避免与附录 A 的 16/19/20 混淆）

| 口径 | 通过 | 未通过 | 判据 |
|---|---|---|---|
| **二值成功（事前预注册）** | 3 | 25 | 场景声明的 terminal outcome 成功率 ∈ [0.40, 0.85] |
| **声明综合分（utility-v1）** | **16** | **12** | 场景声明的 Σ wᵢ·valueᵢ ∈ [0.40, 0.85] |

- 纯基线 composite 落在窗口**之外**：**12** 个（饱和 11、触底 1）
- 二值口径在这批场景上信息量很低：确定性脚本策略的成功率只有 0/1，多数场景跨 seed 恒为 1.000，无法落入窗口。

## 1. 逐场景（按类别）

### 侦察搜索 Reconnaissance

| 场景 | 综合分口径 | 二值口径 | 最优纯基线 | composite | 95% CI | 分档 | 窗口外 | 标定前 | D1′先验 |
|---|---|---|---|---|---|---|---|---|---|
| MD-REC-001-MEDIUM | fail | fail | `sweep` | 1.000 | [1.000, 1.000] | near_ceiling | ✅ | 1.000 | 2.17 |
| MD-REC-002-STANDARD | fail | fail | `coordinated` | 0.928 | [0.928, 0.929] | near_ceiling | ✅ | 0.929 | 2.17 |
| MD-REC-003-STANDARD | fail | fail | `coordinated` | 0.931 | [0.931, 0.931] | near_ceiling | ✅ | 0.931 | 2.33 |
| MD-REC-004-STANDARD | fail | fail | `sweep` | 0.865 | [0.865, 0.865] | near_ceiling | ✅ | 0.865 | 2.17 |
| MD-REC-005-STANDARD | pass | fail | `coordinated` | 0.800 | [0.794, 0.808] | window |  | 0.804 | 2.50 |
| MD-REC-006-STANDARD | pass | fail | `observation-patrol` | 0.635 | [0.633, 0.637] | window |  | 0.635 | 2.17 |
| MD-REC-007-STANDARD | pass | fail | `sweep` | 0.808 | [0.808, 0.808] | window |  | 0.808 | 2.33 |
| MD-REC-008-STANDARD | pass | pass | `coordinated` | 0.671 | [0.666, 0.678] | window |  | 0.671 | 2.33 |

### 区域拒止 Area Denial

| 场景 | 综合分口径 | 二值口径 | 最优纯基线 | composite | 95% CI | 分档 | 窗口外 | 标定前 | D1′先验 |
|---|---|---|---|---|---|---|---|---|---|
| MD-AD-001-STANDARD | pass | fail | `indiscriminate` | 0.443 | [0.430, 0.454] | below_window |  | 1.000 | 1.83 |
| MD-AD-002-STANDARD | pass | fail | `indiscriminate` | 0.473 | [0.469, 0.477] | window |  | 1.000 | 1.67 |
| MD-AD-003-STANDARD | pass | fail | `indiscriminate` | 0.833 | [0.833, 0.833] | window |  | 1.000 | 1.83 |
| MD-AD-004-STANDARD | pass | fail | `guard` | 0.576 | [0.561, 0.586] | window |  | 1.000 | 2.33 |
| MD-AD-005-STANDARD | pass | fail | `guard` | 0.621 | [0.618, 0.624] | window |  | 1.000 | 2.17 |
| MD-AD-006-STANDARD | pass | fail | `guard` | 0.788 | [0.788, 0.788] | window |  | 0.788 | 2.33 |

### 应急响应 Emergency Response

| 场景 | 综合分口径 | 二值口径 | 最优纯基线 | composite | 95% CI | 分档 | 窗口外 | 标定前 | D1′先验 |
|---|---|---|---|---|---|---|---|---|---|
| MD-ER-001-STANDARD | fail | fail | `safe` | 0.863 | [0.863, 0.863] | near_ceiling | ✅ | 0.863 | 1.83 |
| MD-ER-002-STANDARD | pass | fail | `team` | 0.835 | [0.835, 0.835] | window |  | 0.835 | 1.50 |
| MD-ER-003-STANDARD | pass | fail | `naive` | 0.453 | [0.453, 0.453] | window |  | 0.938 | 1.83 |
| MD-ER-004-STANDARD | fail | fail | `preissued` | 0.942 | [0.942, 0.942] | near_ceiling | ✅ | 0.942 | 2.33 |
| MD-ER-005-STANDARD | pass | fail | `coordinated` | 0.453 | [0.453, 0.453] | window |  | 0.935 | 2.00 |
| MD-ER-006-STANDARD | pass | fail | `progress-watch` | 0.833 | [0.832, 0.833] | window |  | 0.833 | 1.83 |

### 持续跟踪 Tracking

| 场景 | 综合分口径 | 二值口径 | 最优纯基线 | composite | 95% CI | 分档 | 窗口外 | 标定前 | D1′先验 |
|---|---|---|---|---|---|---|---|---|---|
| MD-TRK-001-STANDARD | pass | fail | `follow` | 0.431 | [0.429, 0.432] | window |  | 1.000 | 1.50 |
| MD-TRK-002-STANDARD | fail | fail | `follow` | 0.393 | [0.385, 0.401] | below_window | ✅ | 0.978 | 1.67 |
| MD-TRK-003-STANDARD | fail | fail | `allocated` | 0.966 | [0.965, 0.967] | near_ceiling | ✅ | 0.969 | 2.00 |
| MD-TRK-004-STANDARD | fail | fail | `allocated` | 0.967 | [0.963, 0.971] | near_ceiling | ✅ | 0.981 | 1.83 |
| MD-TRK-005-STANDARD | fail | pass | `allocated` | 0.871 | [0.860, 0.882] | near_ceiling | ✅ | 0.879 | 1.67 |
| MD-TRK-006-STANDARD | pass | fail | `follow` | 0.686 | [0.682, 0.689] | window |  | 0.972 | 2.17 |
| MD-TRK-007-STANDARD | fail | fail | `identity-honest` | 0.937 | [0.934, 0.939] | near_ceiling | ✅ | 0.934 | 2.17 |
| MD-TRK-008-STANDARD | fail | pass | `coverage-honest` | 0.861 | [0.858, 0.864] | near_ceiling | ✅ | 0.864 | 2.33 |

## 2. 窗口外场景清单（供跑 layered stack 用）

判据：纯基线 composite 不在 [0.40, 0.85]。

| 场景 | composite | 95% CI | 方向 | 最优基线策略 | 综合分口径 | 二值口径 | 是否被本标定移动 |
|---|---|---|---|---|---|---|---|
| MD-REC-001-MEDIUM | 1.000 | [1.000, 1.000] | 饱和（无 headroom） | `sweep` | fail | fail | 否（天然） |
| MD-TRK-004-STANDARD | 0.967 | [0.963, 0.971] | 饱和（无 headroom） | `allocated` | fail | fail | 否（天然） |
| MD-TRK-003-STANDARD | 0.966 | [0.965, 0.967] | 饱和（无 headroom） | `allocated` | fail | fail | 否（天然） |
| MD-ER-004-STANDARD | 0.942 | [0.942, 0.942] | 饱和（无 headroom） | `preissued` | fail | fail | 否（天然） |
| MD-TRK-007-STANDARD | 0.937 | [0.934, 0.939] | 饱和（无 headroom） | `identity-honest` | fail | fail | 否（天然） |
| MD-REC-003-STANDARD | 0.931 | [0.931, 0.931] | 饱和（无 headroom） | `coordinated` | fail | fail | 否（天然） |
| MD-REC-002-STANDARD | 0.928 | [0.928, 0.929] | 饱和（无 headroom） | `coordinated` | fail | fail | 否（天然） |
| MD-TRK-005-STANDARD | 0.871 | [0.860, 0.882] | 饱和（无 headroom） | `allocated` | fail | pass | 否（天然） |
| MD-REC-004-STANDARD | 0.865 | [0.865, 0.865] | 饱和（无 headroom） | `sweep` | fail | fail | 否（天然） |
| MD-ER-001-STANDARD | 0.863 | [0.863, 0.863] | 饱和（无 headroom） | `safe` | fail | fail | 否（天然） |
| MD-TRK-008-STANDARD | 0.861 | [0.858, 0.864] | 饱和（无 headroom） | `coverage-honest` | fail | pass | 否（天然） |
| MD-TRK-002-STANDARD | 0.393 | [0.385, 0.401] | 触底 | `follow` | fail | fail | 是 |

> 其中 5 个只比 0.85 高出一点（0.861–0.871）；MD-TRK-002 是触底（0.393）。「天然」的场景没有被本次标定调整过，最合适直接当作 gates 外实验对象。

## 3. 标定前 vs 标定后（同一批 28 个场景）

被本次标定移动超过 0.02 的场景：**10** 个；其余 **18** 个标定前后一致（未被人为调整）。

| 场景 | 标定前 | 标定后 | 变化 |
|---|---|---|---|
| MD-TRK-002-STANDARD | 0.978 | 0.393 | -0.585 |
| MD-TRK-001-STANDARD | 1.000 | 0.431 | -0.569 |
| MD-AD-001-STANDARD | 1.000 | 0.443 | -0.557 |
| MD-AD-002-STANDARD | 1.000 | 0.473 | -0.527 |
| MD-ER-003-STANDARD | 0.938 | 0.453 | -0.485 |
| MD-ER-005-STANDARD | 0.935 | 0.453 | -0.482 |
| MD-AD-004-STANDARD | 1.000 | 0.576 | -0.424 |
| MD-AD-005-STANDARD | 1.000 | 0.621 | -0.379 |
| MD-TRK-006-STANDARD | 0.972 | 0.686 | -0.286 |
| MD-AD-003-STANDARD | 1.000 | 0.833 | -0.167 |

## 4. 口径说明（避免与 44/42 混淆）

| 口径 | 数 | 说明 |
|---|---|---|
| 本表场景数 | **28** | competition_v1 去 REC-001 变体 |
| competition_v1 包数 | 30 | 含 REC-001 三档 |
| 台账条目 | 55 | 54 包 + 1 条别名（MD-AD-006-ISLAND-STRIKE） |
| 剔演示包 | 44 | 54 − 10 个演示包；与 D1′ 标注覆盖数一致 |
| 剔演示 + REC-001 合并 | 42 | 若一个难度算一个实验 |
| formal 树正式 IE 场景 | 14 | 早期实验，非本次，不在本表 |

## 5. REC-001 三档的实测（合并前）

| 档位 | 综合分口径 | 二值口径 | composite |
|---|---|---|---|
| MD-REC-001-EASY | fail | fail | 1.0 |
| MD-REC-001-HARD | fail | fail | 1.0 |
| MD-REC-001-MEDIUM | fail | fail | 1.0 |

三档 composite 均为 1.000（纯基线满分），时限分别为 181 / 161 / 141 tick。
本表默认报告 **MEDIUM** 档；如需改报 HARD 或 EASY，替换该行即可。
