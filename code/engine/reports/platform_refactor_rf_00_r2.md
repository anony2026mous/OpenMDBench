# RF-00R2 P0 remediation report

STATUS: COMPLETE-WITHIN-SCOPE / RF-01-NOT-YET-AUTHORIZED
TASK_ID: RF-00R2-P0-REMEDIATION
RF: RF-00
TEST_LEVEL: T3

## Scope

本工作包仅处理 RF-00 审查确认的两个 P0：碰撞吞掉同 tick 合法射击，以及 MD-AD-002 runner checkpoint 遗漏评分累计状态；同时把用户批准的13项平台基础推荐固化为 Accepted ADR。未进入 RF-01，未修改装备参数、命中概率、碰撞阈值、胜负规则或公共 Schema。

## Changes

- `openmdbench/envs/benchmark.py`
  - 双边 tick 中碰撞先生成确定性事件和待提交终态，不再立即让攻击者失去同 tick 已提交射击资格。
  - 战斗合法性、弹药和 combat RNG 处理完成后，以稳定实体 ID 顺序提交碰撞终态并重新裁决任务。
  - 非双边兼容 `step()` 仍即时提交碰撞终态。
- `openmdbench/runners/md_ad_002.py`
  - checkpoint 新增 `runner.metric_state` 和 `usv_supported_contacts`。
  - EASY/MEDIUM/HARD runner 新增可选 `resume_checkpoint`，恢复环境、双方策略及评分累计状态后继续到 `max_ticks` 指定的总 tick。
- `openmdbench/scoring/md_ad_002.py`
  - 新增带预警基线版本和距离校验的 `AD2MetricState.from_payload()`，日志与 checkpoint 共用同一恢复语义。
- `tests/integration/test_md_ad_002_ramming.py`
  - 新增“碰撞实体同 tick 合法射击仍执行”的故障复现和回归测试。
  - 同 tick breach/collision 断言与正式固定流水线一致：先锁存 breach，再统一落地毁伤。
- `tests/system/test_md_ad_002_easy.py`
  - 新增 runner checkpoint 评分状态存在性及恢复/连续运行完全等价测试。
- `docs/adr/RF-ADR-001-platform-foundation-decisions.md`
  - 固化用户批准的13项平台基础决策。

## Test-first evidence

新增测试在实现前执行并稳定失败：

- collision test：弹药仍为12，预期11；合法射击被碰撞终态吞掉。
- checkpoint test：`KeyError: 'runner'`；checkpoint 没有评分累计状态。

实现后最终定向复测：13 passed，1 warning，16.94s。恢复入口还验证了 seed/runner 选项不匹配时稳定拒绝，避免结果 metadata 与恢复状态不一致。

## T3 regression

命令覆盖碰撞、EASY checkpoint 确定性、波次、HARD 通信、三档 runner 和评分：

```text
pytest -q tests/integration/test_md_ad_002_ramming.py \
  tests/determinism/test_md_ad_002_easy_checkpoint.py \
  tests/integration/test_md_ad_002_waves.py \
  tests/integration/test_md_ad_002_hard_communications.py \
  tests/system/test_md_ad_002_easy.py \
  tests/system/test_md_ad_002_medium.py \
  tests/system/test_md_ad_002_hard.py \
  tests/unit/test_md_ad_002_scoring.py
```

结果：45 passed，1个第三方 Taichi deprecation warning，343.22s。

静态检查：

- Ruff format：通过（1个测试文件机械格式化）。
- Ruff check：通过。
- Mypy strict（3个受影响生产模块）：通过。
- `git diff --check`：通过。

## Review

- P0-01：CLOSED。本 tick 已合法射击不再因碰撞先写终态而被拒绝；碰撞双方最终仍为 `DESTROYED`。
- P0-02：CLOSED。runner评分累计量和去重 contact 集合进入 checkpoint，恢复到同一总 tick 与连续运行的完整 `AD2MatchResult` 相等。
- 未发现本工作包新增 P0/P1。

## Compatibility and remaining gates

- 三档 runner 的原调用方式保持兼容；`resume_checkpoint` 为可选参数。
- 现有碰撞距离、毁伤后果、武器概率、弹药、评分和胜负参数均未改变。
- RF-00 原审查中的 MD-INT 负高度、MEDIUM golden、全仓 mypy、Bandit/full pytest/coverage 和其他 P1 仍未在本工作包处理。
- 因此本报告不声明 RF-00 整体通过，也不授权 RF-01。
