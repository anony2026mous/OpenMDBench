# AD2-08 MEDIUM 纵向闭环完成报告

## 结论

`MD-AD-002-MEDIUM` 已达到 AD2-08 E2。MEDIUM 的难度差异来自独立 v2 配置、
通用事件解释器和 MEDIUM 蓝方策略参数，没有复制主循环；EASY、HARD 配置哈希保持不变。
该结论不代表 HARD 或整个 MD-AD-002 任务族完成。

## 配置身份

- scenario：`MD-AD-002-MEDIUM`
- config version：`2.0.0`
- config hash：
  `sha256:1dd96cc3b5f0d0103a69745af12ae0de51361eb8d93a1d4a3dac48237ce8a5e4`
- EASY hash 保持：
  `sha256:1adaa81c574ffa6a0e05c88be0da7029d45d5f24a1fa73d3ef2ad20065c81f16`
- HARD hash 保持：
  `sha256:9a057519c2a6f53d0cf5d4d9073a4c7b9ad9976d1228e6b846505d9a49f8bc42`

## 已实现能力

- Wave 2 使用独立 RNG 在 `[480,720]` tick 内抖动；出生高度稳定落在 `[50,150]` m；
- Wave 3 最后两架为45 m/s，其余为30 m/s；
- 五类 MEDIUM 传感器基础探测率按 EASY 档案乘0.88，显式表达12%难度漏检；
- tick 600 从 clear 切换为 cloudy，并进入世界状态、checkpoint 和可视化 DTO；
- 每30 tick 生成低置信度 clutter，具有确定性 ID、衰减、删除和 RNG/checkpoint 状态；
- MEDIUM 蓝方执行分路和一次规避：只使用蓝方公开观察及上一 tick 公开 engagement；
- 内置蓝方策略状态接入核心环境，使本地 runner、Gym 和 REST 使用相同场景推进语义；
- 蓝方 RNG、已规避实体和事件消费状态进入 checkpoint；
- CLI 支持 `selftest --scenario MD-AD-002-MEDIUM`，使用独立 gzip 日志；
- 在线评分与 MEDIUM 权威日志离线重算完全一致；Matplotlib `Agg` 可渲染 cloudy 帧。

## 固定 seed 基线

- 正常成功：seed=0，tick 1543，`red_success / all_threats_destroyed`，breaches=0；
- 失败路径：seed=0、禁用红方交战，tick 792，
  `blue_success / breach_threshold_reached`，breaches=3；
- 超时路径：显式5 tick上限，`red_success / timeout_denial_success`；
- golden：`tests/fixtures/md_ad_002/medium-v2-golden.json`（RF-00R3 将既有未跟踪工件逐字节迁入版本控制，值未重建）。

RF-00R3 核查发现原报告的 `tick 1523` 与2026-08-19冻结工件及当前确定性测试不一致，属于文档转录错误；本次更正为工件记录的 `1543`，未修改 golden 数值。

## 质量门禁

- Ruff：零错误；
- 严格 mypy：224 个源文件零错误；
- Bandit：零问题；
- `git diff --check`：通过；
- 修复后全量回归：`359 passed, 90 warnings in 317.40s`；
- 告警为既有 Taichi/Gymnasium 提示及无中文字体时的 Matplotlib glyph 提示，无测试失败；
- 未增加 skip/xfail，未放宽断言或排除核心代码。

## 已知限制

- MEDIUM 一次规避是任务级规则行为，不是制导/气动高保真模型；
- 蓝方无法从公开事件获知红方 opaque contact 与具体己方实体的私有映射，因此按稳定己方 ID
  选择尚未规避的平台，不读取裁判真值；
- HARD 的通信中继、干扰、丢包和消息时序尚未实现，下一阶段为 AD2-09。
