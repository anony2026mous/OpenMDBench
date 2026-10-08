# RF-03 阶段报告：ScenarioCompiler 与 ResolvedScenario

## 本阶段需求编号

- SCN-001～SCN-005、CMP-001～CMP-004。
- RF-03：ScenarioPackage、ScenarioCompiler、ResolvedScenario、正式运行时适配。

## 修改文件

- `openmdbench/scenarios/package.py`：受根目录约束的场景包引用和包内容哈希。
- `openmdbench/scenarios/compiler.py`：场景解析、校验、地理转换、规范排序和编译诊断。
- `openmdbench/scenarios/resolved.py`：可序列化、深层不可变、可哈希的解析产物。
- `openmdbench/scenarios/runtime.py`：从解析产物创建正式运行时，运行前复核内容哈希。
- `tests/unit/scenarios/test_compiler_rf03.py`：编译、哈希、越界、泄漏、篡改和兼容回归。

## 设计选择和 ADR

- 遵循 RF-ADR-001：配置只在启动边界编译，正式运行时只消费 `ResolvedScenario`。
- 正式产物嵌入已验证组件、统一米制坐标、地图身份、资源哈希和显式单位。
- 所有嵌套映射递归冻结；直接构造、JSON 恢复和运行时入口均校验规范内容哈希。
- 保留按场景 ID 创建运行时的兼容 adapter，但 adapter 内部先编译再进入统一入口。

## 新增/修改测试

- 四个正式场景重复编译、规范哈希和 JSON round-trip。
- 解析产物顶层及嵌套不可变、错误哈希和运行前篡改拒绝。
- 场景包目录穿越拒绝、裁判信息泄漏拒绝。
- MD-INT-001 与三档 MD-AD-002 由解析产物重建的初态、调度和元数据等价。

## 实际命令和结果

- RF-03 定向与受影响回归：`63 passed`。
- `make lint typecheck security-check`：Ruff、mypy strict（250 个源文件）、Bandit 全部通过。
- `make test`：`463 passed, 93 warnings`，用时 732.01 秒。

## 覆盖率与性能

- 后续 RF-04 合并门禁测得全仓覆盖率 90.46%，高于 80% 门槛。
- 未发现编译后正式场景行为或确定性回归；未单独声明性能提升。

## 兼容影响

- MD-INT-001、MD-AD-002 EASY/MEDIUM/HARD 的旧入口继续可用。
- 原始 YAML/dict 不再直接进入正式运行时。

## 未完成、风险和下一依赖

- 场景包 pack/unpack 和更通用 include 组合属于 RF-12。
- 会话生命周期和单写入模型由 RF-04 承接。
- RF-03 完成门禁通过。
