# ADR-MD3-001：对海目标域与延迟命中边界

- 状态：Accepted for benchmark implementation
- 日期：2026-09-02
- 范围：MD3-03 及后续通用 combat/Catalog

## 决策

1. 复用 V2 的实体 `domain` 和 weapon `target_domains`，将 `surface` 作为与 `air`、`shore`、`underwater` 并列的通用目标域；不得识别 MD-INT-003、defender/attacker 或具体 USV ID。
2. MD3 对海交战只通过 `WeaponProfile → Ammunition → HitModel → EffectProfile → DamageIntent → simultaneous DamageResolution` 闭环接入。现有 `CombatSystemV2` 的 relationship、contact、range、ammo、cooldown、lifecycle、RNG 和 receipt 仍是唯一权威源。
3. 新的对海资源应显式声明 `impact_delay_ticks=1`。发射 tick 只产生唯一 pending execution；下一 tick 只结算一次命中/Effect。pending state、ammo、cooldown、RNG 和 evidence 必须进入 checkpoint 和 replay。
4. 未知 target domain、资源不兼容、低置信/过期航迹、neutral/protected 目标、核心区禁火、重复同目标发射都在通用 legality 阶段稳定拒绝，且不得消耗 ammo 或武器 RNG。

## 依据与兼容

`schemas/core_v2.py:EntitySpecV2.target_domains`、`catalog/v2.py:validate_full_composition` 和 `combat/system_v2.py` 已以运行时 domain 校验通用路径。air weapon 行为不改变；新字段若造成不兼容 schema 变化，MD3-03 必须给出版本/迁移策略。

## 不采用

- 在 V4 场景代码中按目标 ID 判断命中。
- 创建第二个 USV combat loop 或直接修改 health。
- 将“发射即命中”伪装为 delay=1。

## 验证义务

MD3-03 必须覆盖 air/surface/fixed matrix、命中延迟恰好一 tick、非法请求零副作用、同 tick capacity、checkpoint pending impact、改 faction/entity/scenario 名后的等价性。

所有 Pk、射程、毁伤和弹药在 U6 冻结前为 `UNVALIDATED_BENCHMARK`。
