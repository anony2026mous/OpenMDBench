# ADR-MD3-003：自爆、接触引爆、殉爆与残骸生命周期

- 状态：Accepted for benchmark implementation
- 日期：2026-09-02
- 范围：MD3-04 通用 effect/damage/lifecycle

## 决策

1. 核心区进入和实体碰撞使用连续 TOI/zone crossing 生成通用 source event，再引用 Catalog `EffectProfile` 产生 `DamageIntent`。场景不能直接写 health、speed 或 lifecycle。
2. `suicide_detonation` 只可由一次性 trigger 触发；其港口 Effect、attacker 终态和 mission terminal evidence 均由权威事件记录。重复 zone evaluate 或 restore 不得再次引爆。
3. 火力摧毁的 attacker 可按 lifecycle policy 变为静态 wreck；wreck 保留碰撞体但不再运动、感知、通信或开火。引爆的 attacker 默认 despawn；两者均由数据选择。
4. secondary explosion 是独立命名 RNG 子流驱动的 Effect，使用 target filter 排除港口；它仍进入同一 DamageIntent 聚合与 simultaneous resolution。

## 依据与兼容

V2 已有 `DamageIntentV2`、`DamageResultV2`、`LifecycleStateV2`、连续 boundary/collision 和 `WorldStateV2.apply_damage_transaction`。本 ADR 不新增场景专用 damage system。

## 验证义务

MD3-04 覆盖高速 crossing、切线、同 tick 拦截/自爆、对称碰撞、wreck 再碰撞、secondary filter/RNG、restore 后不重复 trigger，以及完整 authority log。

U7 的数值在冻结前为 `UNVALIDATED_BENCHMARK`。
