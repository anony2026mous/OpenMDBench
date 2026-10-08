# RF-14 阶段报告：全量验证

执行时间：2026-08-27。

- `make full-test`：509 passed，93 warnings，2432.41 秒。
- 总覆盖率：90.51%（门槛 80%）。
- Ruff：通过；mypy strict：274 个源文件通过；Bandit：通过。
- performance、security、determinism、system、visualization/replay 均包含在全量套件。
- AD-002 正式 2 小时 soak：EASY 7206.86 秒、MEDIUM 7204.70 秒、HARD 7205.17 秒；三者 FD 均 5→5。
- 未修改 golden、未新增 skip/xfail、未降低门槛。

结论：代码回归门禁通过；MD-INT-001 独立 2 小时 soak 证据当前不存在，不能宣称完整满足“四个核心场景各 2 小时”。
