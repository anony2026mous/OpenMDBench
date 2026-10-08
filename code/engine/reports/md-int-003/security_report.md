# MD3-11 安全门禁记录

## 结论

**状态：DONE。** Bandit、静态质量门禁及包含 security suite 的新鲜全量 pytest 均通过；未发现需要记录的 Bandit High、Medium 或 Low 项。

## 证据

| 检查 | 命令/范围 | 结果 |
|---|---|---|
| 静态安全 | `.venv/bin/bandit -r openmdbench -q` | exit 0、无输出 |
| 类型与代码规则 | strict mypy、Ruff、format、py_compile | 均 exit 0 |
| 安全测试 | `tests/security`，并入 428 项 remainder 分组 | 通过 |
| 接口/边界回归 | `tests/contract`、`tests/system` 全分组 | 1,312 + 108 passed |

完整 T4 测试明细和环境锚点见 [full_test_report.md](full_test_report.md)。检查覆盖 API/REST 防护、replay 输入、ScenarioPackage 安全边界、faction/session 可见性隔离、伪造 checkpoint seed/hash 拒绝，以及只读 polling 不推进 tick。

## 安全边界与残余风险

- YAML/场景包不会执行 Python、shell、import 或 `eval`；公开接口仍受 view/controller/faction 边界过滤。
- 确定性随机流仅用于仿真与 checkpoint 可复现性，已通过静态规则和确定性回归验证；未作为密码学随机源使用。
- 关闭 native session 后有一个 multiprocessing resource tracker 常驻于父进程。它不携带世界状态，100 局顺序运行未增长，不构成越权或资源泄漏证据，但应持续监测。
- 此安全门禁不等同于平台总体发布审计；RF-15 `NOT_RELEASABLE` 仍保持。
