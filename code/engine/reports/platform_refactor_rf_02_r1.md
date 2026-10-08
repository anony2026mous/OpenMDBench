# RF-02 R1：统一 Catalog、可信模型注册与 AD2 武器迁移

STATUS: IMPLEMENTED / TARGETED-GATE-PASS

## 结果

- 新增只读 CatalogRepository、精确版本解析、engine compatibility、稳定 hash、冲突与循环检测；
- 新增冻结式 ModelRegistry 及 reviewed weapon/effect factories；
- 统一覆盖 CAT-001 十四类资源，建立平台/动力学/载荷/传感器/武器兼容校验；
- AD2 v2 显式 adapter 可解析三个正式难度的平台、传感器、武器、effect、通信和评分资源；
- AD2Combat 已改从 resolved weapon/effect 读取合法性、射程、概率、弹数、功耗和 damage；
- Catalog hash 已进入 session、replay 和 checkpoint，恢复 mismatch fail closed。

## 当前边界

RF-02 不实现 ScenarioCompiler/ResolvedScenario（RF-03），不改变三指标评分 golden，亦不提前
实现 RF-11 七指标评分或统一命令通信语义。非 AD2 generic 资源尚未接入主循环，文档中明确标注。

## 定向证据

契约、正式 adapter、作战、checkpoint、REST 和 replay metadata 定向测试通过；Ruff 与受影响
模块 mypy strict 通过。下一步执行全仓静态门禁、完整契约/集成回归和最终 T4。
