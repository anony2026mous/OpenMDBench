# RF-00R3 baseline remediation report

STATUS: COMPLETE-WITHIN-SCOPE / RF-00-REMAINS-NO-GO
TASK_ID: RF-00R3-BASELINE-REMEDIATION
RF: RF-00
TEST_LEVEL: T3

## Scope

本工作包只处理 RF-00 既有审查中的两项明确基线阻塞：MD-INT-001 固定 seed 运行产生负高度命令，以及 MEDIUM frozen golden 未进入版本控制。没有进入 RF-01，没有调整场景参数、武器概率、碰撞阈值、胜负规则或 golden 数值。

## MD-INT-001 negative-altitude remediation

根因位于 `openmdbench/policies/blue.py`：规则策略对 contact 做5秒线性预测时直接外推高度。下降目标接近海平面时，预测高度可以低于0，随后 `UAVCommand` 按正确的非负约束拒绝该命令。

测试先行证据：新增策略测试构造 `z=10 m、vz=-20 m/s`，实现前得到 `target.z=-90 m` 并失败。修复在预测拦截点将高度限制到既有 UAV 包线 `[0, 3000] m`；没有放宽 `UAVCommand` 校验或修改动力学。

## MEDIUM golden persistence

- 既有源工件：`artifacts/md-ad-002/medium-v2-golden.json`
- 源工件修改时间：2026-08-19 11:57:34 +08:00，早于 RF-00R3
- 版本化 fixture：`tests/fixtures/md_ad_002/medium-v2-golden.json`
- 两文件 SHA-256：`1b03619e58e9123efab375eb89af9fc03b7fbceb236407a654cda8ef1948680c`
- `cmp`：逐字节相同
- 配置哈希：`sha256:1dd96cc3b5f0d0103a69745af12ae0de51361eb8d93a1d4a3dac48237ce8a5e4`

系统测试改为读取版本化 fixture，并在比较结果前验证当前 MEDIUM 配置哈希。没有重新采样、搜索 seed 或以本轮输出重写期望。原 AD2-08 报告的 `tick 1523` 与冻结工件的 `1543` 不一致，已作为文档转录错误更正。

## Tests

实现前负向测试：1 failed，实际 `-90.0`、预期 `0.0`。

定向 T3：

```text
pytest -q tests/unit/policies/test_rule_agents.py \
  tests/determinism/test_md_int_001_matrix.py \
  tests/system/test_md_int_001_baselines.py::test_frozen_seed_blue_success_chain \
  tests/system/test_md_ad_002_medium.py::test_medium_seed_zero_matches_independent_golden
```

结果：10 passed，1个第三方 Taichi deprecation warning，66.75s。

额外诊断批次运行了完整 MD-INT baseline/Gym 相关集合：9 passed、3 failed。三个失败不再包含负高度或确定性失败，分别是：

1. 禁用蓝方交战时发生碰撞并得到 `blue_success`，而测试预期 red breach；
2. red hold + no engage 因碰撞得到 `threat_destroyed`，而测试预期 timeout；
3. Gym `info` 新增 `collision_events`，旧精确字典断言未包含该字段。

这些问题在 RF-00 既有审查中已登记，超出 RF-00R3 的批准范围，未通过修改测试期望掩盖。

静态与工件检查：

- Ruff format/check：通过；
- Mypy strict（受影响生产模块）：通过；
- fixture/source SHA-256 和 `cmp`：通过；
- `git diff --check`：通过。

## Review

- MD-INT 负高度：CLOSED。
- MEDIUM golden 缺失：CLOSED；fixture 已版本化并绑定配置哈希。
- 本工作包未发现新增 P0/P1。
- RF-00 仍为 NO-GO：上述两个 MD-INT 碰撞路径、Gym info 契约、全仓 mypy、Bandit/full pytest/coverage 以及其他登记 P1 尚未关闭。
