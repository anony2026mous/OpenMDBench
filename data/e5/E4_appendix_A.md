# 附录 A：场景族与入场门判定（自动生成骨架）

> 由 `role_c_toolkit/e4_scenario_family.py report` 从门禁台账生成。**verdict 为 pending 的行不得写进论文的 admitted 表。**

| 类别 | 场景 | 包 | manifest SHA-256（前 12 位） | D1′ 决策形态门 | D2 headroom（综合分） | D3 接口预算 | D1 报告量 | D1′ 先验得分 |
|---|---|---|---|---|---|---|---|---|
| 区域拒止 Area Denial | MD-AD-002-EASY | `md_ad_002_easy` | `b96b4ff00a28` | pending | fail (0.00) | blocked | not_applicable | — |
| 区域拒止 Area Denial | MD-AD-002-MEDIUM | `md_ad_002_medium` | `6f5e445e4e71` | pending | fail (0.00) | blocked | not_applicable | — |
| 区域拒止 Area Denial | MD-AD-002-HARD | `md_ad_002_hard` | `6928419fda2b` | pending | fail (0.00) | blocked | not_applicable | — |
| 拦截交战 Interception-Engagement | MD-INT-003-EASY | `md_int_003_easy` | `5d962251ac61` | pending | pending | blocked | not_applicable | — |
| 拦截交战 Interception-Engagement | MD-INT-003-MEDIUM | `md_int_003_medium` | `a4104a9025aa` | pending | pending | blocked | not_applicable | — |
| 拦截交战 Interception-Engagement | MD-INT-003-HARD | `md_int_003_hard` | `53334c40a860` | pending | pending | blocked | not_applicable | — |
| 区域拒止 Area Denial | MD-AD-004-DECEPTION | `md_ad_004_deception` | `274f8394ee78` | pending | fail (0.00) | blocked | not_applicable | — |
| 拦截交战 Interception-Engagement | MD-INT-002-AIR-SURFACE | `md_int_002_air_surface` | `0b49ebda9849` | pending | pending | blocked | not_applicable | — |
| 拦截交战 Interception-Engagement | MD-INT-005-STEALTH-MULTI-AXIS | `md_int_005_stealth_multi_axis` | `91c9dd99d4f7` | pending | pending | blocked | not_applicable | — |
| 拦截交战 Interception-Engagement | MD-INT-006-SATURATION-ROE | `md_int_006_saturation_roe` | `55ec744935a3` | pending | pending | blocked | not_applicable | — |
| 拦截交战 Interception-Engagement | IE-01-SINGLE-TARGET | `ie_01_single_target` | `852191d50c30` | pending | pending | blocked | not_applicable | 1.17 |
| 拦截交战 Interception-Engagement | IE-02-DUAL-THREAT | `ie_02_dual_threat` | `b8e9a6da2272` | pending | pending | blocked | not_applicable | 1.67 |
| 拦截交战 Interception-Engagement | IE-03-SURFACE-RAID | `ie_03_surface_raid` | `5c33b53cc6b5` | pending | pending | blocked | not_applicable | 1.17 |
| 拦截交战 Interception-Engagement | IE-04-COMBINED-ARMS | `ie_04_combined_arms` | `fcc2b8d1b54d` | pending | pending | blocked | not_applicable | 1.83 |
| 拦截交战 Interception-Engagement | IE-05-MULTI-AXIS | `ie_05_multi_axis` | `a2602a494fc4` | pending | pending | blocked | not_applicable | 1.83 |
| 拦截交战 Interception-Engagement | IE-06-DECOY-MIXED | `ie_06_decoy_mixed` | `4722cd6b7ab6` | pending | pending | blocked | 0.8425 / 0.5125 | 2.50 |
| 拦截交战 Interception-Engagement | IE-07-CROSS-DOMAIN | `ie_07_cross_domain` | `869301b252f9` | pending | pending | blocked | not_applicable | 2.17 |
| 拦截交战 Interception-Engagement | IE-08-ISLAND-STRIKE | `ie_08_island_strike` | `f9a759d201a9` | pending | pending | blocked | not_applicable | 2.17 |
| 拦截交战 Interception-Engagement | IE-09-STAGGERED-WAVES | `ie_09_staggered_waves` | `1847894ecb0c` | pending | pending | blocked | not_applicable | 2.00 |
| 拦截交战 Interception-Engagement | IE-10-DUAL-AXIS-PINCER | `ie_10_dual_axis_pincer` | `9176bdc75994` | pending | pending | blocked | not_applicable | 1.67 |
| 拦截交战 Interception-Engagement | IE-11-DECOY-SCREEN | `ie_11_decoy_screen` | `e5f18975568d` | pending | pending | blocked | 0.905 / 0.45 | 2.50 |
| 拦截交战 Interception-Engagement | IE-12-FOG-ONSET | `ie_12_fog_onset` | `81d8c535fbe0` | pending | pending | blocked | not_applicable | 2.00 |
| 拦截交战 Interception-Engagement | IE-13-DEEP-STRIKE | `ie_13_deep_strike` | `3695b7dc616f` | pending | pending | blocked | not_applicable | 1.83 |
| 拦截交战 Interception-Engagement | IE-14-SATURATION-THREE-WAVE | `ie_14_saturation_three_wave` | `c9535bd174ec` | pending | pending | blocked | not_applicable | 2.00 |
| 区域拒止 Area Denial | MD-AD-006-ISLAND-STRIKE | `ie_08_island_strike` | `f9a759d201a9` | pending | fail (0.00) | blocked | not_applicable | — |
| 区域拒止 Area Denial | MD-AD-001-STANDARD | `md_ad_001_standard` | `622ee1df059a` | pending | pass (0.45) / 二值 fail (0.00) | blocked | not_applicable | 1.83 |
| 区域拒止 Area Denial | MD-AD-002-STANDARD | `md_ad_002_standard` | `f3b24678459f` | pending | pass (0.47) / 二值 fail (0.00) | blocked | not_applicable | 1.67 |
| 区域拒止 Area Denial | MD-AD-003-STANDARD | `md_ad_003_standard` | `529e6cfc7f1c` | pending | pass (0.77) / 二值 fail (0.00) | blocked | not_applicable | 1.83 |
| 区域拒止 Area Denial | MD-AD-004-STANDARD | `md_ad_004_standard` | `b94d51ef467f` | pending | pass (0.54) / 二值 fail (0.00) | blocked | not_applicable | 2.33 |
| 区域拒止 Area Denial | MD-AD-005-STANDARD | `md_ad_005_standard` | `ba2deda546df` | pending | pass (0.63) / 二值 fail (0.00) | blocked | blocked | 2.17 |
| 区域拒止 Area Denial | MD-AD-006-STANDARD | `md_ad_006_standard` | `fca53145e4a1` | pending | pass (0.79) / 二值 fail (0.00) | blocked | not_applicable | 2.33 |
| 应急响应 Emergency Response | MD-ER-001-STANDARD | `md_er_001_standard` | `5d0ae9d6fd62` | pending | fail (0.86) / 二值 fail (1.00) | blocked | not_applicable | 1.83 |
| 应急响应 Emergency Response | MD-ER-002-STANDARD | `md_er_002_standard` | `f3acdec138c5` | pending | pass (0.84) / 二值 fail (1.00) | blocked | not_applicable | 1.50 |
| 应急响应 Emergency Response | MD-ER-003-STANDARD | `md_er_003_standard` | `5b1f588acdab` | pending | pass (0.45) / 二值 fail (0.00) | blocked | not_applicable | 1.83 |
| 应急响应 Emergency Response | MD-ER-004-STANDARD | `md_er_004_standard` | `050c1b0b9aa5` | pending | fail (0.94) / 二值 fail (1.00) | blocked | not_applicable | 2.33 |
| 应急响应 Emergency Response | MD-ER-005-STANDARD | `md_er_005_standard` | `3d30ce31721e` | pending | pass (0.69) / 二值 fail (0.00) | blocked | not_applicable | 2.00 |
| 应急响应 Emergency Response | MD-ER-006-STANDARD | `md_er_006_standard` | `73c39c0a7fb0` | pending | pass (0.83) / 二值 fail (1.00) | blocked | not_applicable | 1.83 |
| 侦察搜索 Reconnaissance | MD-REC-001-EASY | `md_rec_001_easy` | `2ba77ac8ff3e` | pending | fail (1.00) / 二值 fail (1.00) | blocked | not_applicable | 2.17 |
| 侦察搜索 Reconnaissance | MD-REC-001-HARD | `md_rec_001_hard` | `c71fd8500e4f` | pending | fail (1.00) / 二值 fail (1.00) | blocked | not_applicable | 2.17 |
| 侦察搜索 Reconnaissance | MD-REC-001-MEDIUM | `md_rec_001_medium` | `7ff88e46526d` | pending | fail (1.00) / 二值 fail (1.00) | blocked | not_applicable | 2.17 |
| 侦察搜索 Reconnaissance | MD-REC-002-STANDARD | `md_rec_002_standard` | `d650f05a3ee1` | pending | fail (0.93) / 二值 fail (1.00) | blocked | not_applicable | 2.17 |
| 侦察搜索 Reconnaissance | MD-REC-003-STANDARD | `md_rec_003_standard` | `f882e6121551` | pending | fail (0.93) / 二值 fail (1.00) | blocked | not_applicable | 2.33 |
| 侦察搜索 Reconnaissance | MD-REC-004-STANDARD | `md_rec_004_standard` | `e4d28cca1b46` | pending | fail (0.87) / 二值 fail (1.00) | blocked | not_applicable | 2.17 |
| 侦察搜索 Reconnaissance | MD-REC-005-STANDARD | `md_rec_005_standard` | `57248c139a01` | pending | pass (0.80) / 二值 fail (1.00) | blocked | not_applicable | 2.50 |
| 侦察搜索 Reconnaissance | MD-REC-006-STANDARD | `md_rec_006_standard` | `4ccddf25d01c` | pending | pass (0.63) / 二值 fail (1.00) | blocked | not_applicable | 2.17 |
| 侦察搜索 Reconnaissance | MD-REC-007-STANDARD | `md_rec_007_standard` | `a2bc7ea7f446` | pending | pass (0.81) / 二值 fail (1.00) | blocked | not_applicable | 2.33 |
| 侦察搜索 Reconnaissance | MD-REC-008-STANDARD | `md_rec_008_standard` | `35c4c6270261` | pending | pass (0.67) / 二值 pass (0.80) | blocked | not_applicable | 2.33 |
| 持续跟踪 Tracking | MD-TRK-001-STANDARD | `md_trk_001_standard` | `a304dd1ca92d` | pending | pass (0.43) / 二值 fail (0.00) | blocked | not_applicable | 1.50 |
| 持续跟踪 Tracking | MD-TRK-002-STANDARD | `md_trk_002_standard` | `406dc5e28e10` | pending | fail (0.39) / 二值 fail (0.00) | blocked | not_applicable | 1.67 |
| 持续跟踪 Tracking | MD-TRK-003-STANDARD | `md_trk_003_standard` | `365d94aab2de` | pending | fail (0.97) / 二值 fail (1.00) | blocked | not_applicable | 2.00 |
| 持续跟踪 Tracking | MD-TRK-004-STANDARD | `md_trk_004_standard` | `a26b554bf532` | pending | fail (0.98) / 二值 fail (1.00) | blocked | not_applicable | 1.83 |
| 持续跟踪 Tracking | MD-TRK-005-STANDARD | `md_trk_005_standard` | `662615483722` | pending | fail (0.88) / 二值 pass (0.80) | blocked | not_applicable | 1.67 |
| 持续跟踪 Tracking | MD-TRK-006-STANDARD | `md_trk_006_standard` | `9cc5f37e82ed` | pending | pass (0.68) / 二值 fail (0.00) | blocked | not_applicable | 2.17 |
| 持续跟踪 Tracking | MD-TRK-007-STANDARD | `md_trk_007_standard` | `bd5e3ee47b03` | pending | fail (0.93) / 二值 fail (1.00) | blocked | blocked | 2.17 |
| 持续跟踪 Tracking | MD-TRK-008-STANDARD | `md_trk_008_standard` | `448b82afef1f` | pending | fail (0.87) / 二值 fail (1.00) | blocked | not_applicable | 2.33 |

判定值含义：`pass`/`fail` = 已跑并达/未达标；`pending` = 尚未运行；`reported` = 按 v8 清单以报告量呈现（D1，无通过判定）；`not_applicable` = 该场景不具备此门的机制前提；`blocked` = 本版本无法执行（附原因）。

## 各类别门禁进度

| 类别 | 场景数 | D1′ pass | D2 pass | D2 已判定 | D3 | D1 报告量/不适用 |
|---|---|---|---|---|---|---|
| 侦察搜索 Reconnaissance | 10 | 0 | 4 | 10 | 0 | 0 |
| 区域拒止 Area Denial | 11 | 0 | 6 | 11 | 0 | 0 |
| 应急响应 Emergency Response | 6 | 0 | 4 | 6 | 0 | 0 |
| 拦截交战 Interception-Engagement | 20 | 0 | 0 | 0 | 0 | 2 |
| 持续跟踪 Tracking | 8 | 0 | 2 | 8 | 0 | 0 |

## 成功判据（清单 v8 §1）

≥3 个大类各有 ≥3 个场景完成入场门判定；场景族总数从 14 入场扩展到 20+。

- 已满足"≥3 个场景完成判定"的类别：侦察搜索 Reconnaissance、区域拒止 Area Denial、应急响应 Emergency Response、持续跟踪 Tracking（4 个大类）。
- 场景族规模：台账共 55 个场景，其中 25 个已在正式 registry，30 个为 competition_v1 候选。
- **D1′ 先验标注覆盖**：44/55 个场景有先验得分；未覆盖的 11 个是平台兼容用的 MD-* 场景（MD-AD-002 / MD-INT-003 的难度档、MD-INT-002/005/006），不属于本次场景族构建目标，如需可另行标注。

未覆盖 D1′ 的场景：MD-AD-002-EASY、MD-AD-002-MEDIUM、MD-AD-002-HARD、MD-INT-003-EASY、MD-INT-003-MEDIUM、MD-INT-003-HARD、MD-AD-004-DECEPTION、MD-INT-002-AIR-SURFACE、MD-INT-005-STEALTH-MULTI-AXIS、MD-INT-006-SATURATION-ROE、MD-AD-006-ISLAND-STRIKE
