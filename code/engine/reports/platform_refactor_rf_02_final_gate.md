# RF-02 final gate and independent diff review

STATUS: PASS / RF-03-READY-PENDING-USER-APPROVAL
TASK_ID: RF-02-FINAL-GATE-20260826
TEST_LEVEL: T4
REVIEW_SCOPE: immutable Catalog, trusted ModelRegistry, AD2 resource adapter and combat migration

## Outcome

统一 Catalog 1.0 与可信模型注册已完成。武器、effect、传感器和平台均可从三个 AD2 正式
场景精确解析；AD2Combat 不再扫描 legacy `config.weapons`，合法性、目标域、射程、概率、
单次发数、功耗与 damage 均来自 resolved weapon/effect。

## Implemented

- 只读 `CatalogRepository`，覆盖 CAT-001 十四类资源；
- 精确 `id@major.minor.patch`、engine compatibility、未知/重复/歧义/循环引用 fail closed；
- 稳定 canonical snapshot、Catalog hash 和单资源 content hash，加载顺序不影响 hash/结果；
- 冻结 `ModelRegistry`，只允许已登记 built-in weapon/effect factory，未知模型不能实例化；
- 平台—动力学—载荷—传感器—武器矩阵，包含平台类型、目标域、载荷质量和载荷内武器校验；
- Catalog 定义与会话实体状态分离，实际弹药、健康、能源、冷却、模式和 RNG 不进入 Catalog；
- AD2 v2 adapter 规范化三个难度的正式资源，不向新核心泄漏 legacy dict；
- Catalog schema/hash 写入 session metadata、replay metadata 和 checkpoint，恢复 mismatch 拒绝。

## T4 evidence

Command: `make full-test`

- Ruff: PASS；
- Mypy strict: PASS, 246 source files；
- Bandit: PASS；
- Pytest: PASS, 438 tests；
- Coverage: 91.30%, threshold 80%；
- Warnings: 93，仅为既有 Taichi 弃用、Gymnasium 建议/类型转换、CJK 字体和 Agg 非交互提示；
- Duration: 2272.38s (37m52s)，与 RF-01 37m55s 基线等价，无可观察性能回退；
- 正式报告：`reports/md_int_001_full_test.json`, `passed: true`。

T3 扩大回归另有 156 tests PASS；最终隔离补充测试 2 tests PASS。`git diff --check` PASS。

## Independent review

Correctness：精确版本、semver、engine compatibility、未知/重复/循环、hash 稳定、加载顺序、
兼容矩阵、两会话隔离、旧武器行为对比均有覆盖。三个难度、逐发 RNG、同时毁伤、拒绝无副作用、
checkpoint/replay/REST/可视化系统链全量通过；未修改概率、golden、seed 或评分阈值。

Architecture：普通资源只声明 model 名称，不动态 import 代码；factory registry 冻结后不可写。
Repository resolve/instantiate 返回隔离对象，全局定义没有会话弹药或 cooldown。Catalog 与 combat
模块不读取 YAML；原 YAML 只在既有启动 adapter 边界解析为严格类型。

Compatibility：现有 v2 config hash/golden 保持不变。通信和现有三指标评分已成为版本化资源，
但不宣称 RF-11 的统一命令通信或七指标评分已经实现；这些 downstream gap 仍明确保留。

Scope：ScenarioPackage、Compiler、ResolvedScenario、运行中完全禁止 YAML 属于 RF-03，本工作包
未提前建立第二套场景编译器。其他 generic 资源完成统一命名空间/hash，不误报为所有主循环均已迁移。

Worktree hygiene：未恢复或纳入既有 `docs/agents.md` 删除、`../map_modified.py`、`.cao/` 等无关
内容；覆盖率和正式报告仅由成功 T4 更新。

## Verdict

P0: 0 open.
P1: 0 undispositioned in RF-02.
RF-02: PASS.
RF-03: READY，尚未开始，等待用户明确批准。
