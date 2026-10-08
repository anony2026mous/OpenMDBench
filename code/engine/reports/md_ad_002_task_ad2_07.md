# AD2-07 EASY 纵向闭环完成报告

## 结论

`MD-AD-002-EASY` 已完成 AD2-07 E2 纵向闭环。该结论只适用于 EASY，不代表
MEDIUM、HARD 或整个 MD-AD-002 任务族完成。

## 闭环能力

- 三波 4/5/6 动态出生、动力学、感知融合、交战、突破锁存、裁决和七项评分贯通；
- 同一公开红方规则策略核心贯通本地、Gym、REST；CLI 提供一键 selftest；
- 正常成功、失败和显式超时路径均有确定性证据；
- 权威 JSONL/gzip 日志支持 referee/red/blue/public 视角，红方视角无蓝方真值泄漏；
- checkpoint 保存仿真和规则智能体状态，恢复后的后续状态一致；
- Matplotlib `Agg` 可渲染威海地图、拒止区、三类平台和轨迹；
- `usv_early_warning_gain` 使用版本化 `shore-low-altitude-envelope-v1` 基准（15 km）；
  原始累计量逐 tick 写入 referee `metric_state`，在线评分与同一日志离线重算完全一致。

## 基线轨迹

- seed=0：tick 1464，`red_success / all_threats_destroyed`，breaches=0，拦截率=1.0；
- seed=0 且禁用红方交战：`blue_success / breach_threshold_reached`，breaches=3；
- seed=17 且裁决上限5 tick：`red_success / timeout_denial_success`。

## 验证证据

- `make lint typecheck`：Ruff 零错误，严格 mypy 222 个源文件零错误；
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest -q`：
  `342 passed, 15 warnings in 245.99s`；
- 15 项告警来自既有 Taichi 弃用提示和 Gymnasium 环境建议，不是测试失败；
- 宿主 ROS 注册了不属于本项目的 pytest 插件且缺少 `lark`，因此全量命令显式关闭
  外部插件自动加载。

## 设计记录

- `docs/adr/AD2-ADR-002-uav-ammunition.md`
- `docs/adr/AD2-ADR-015-uav-mission-kill-damage.md`
- `docs/adr/AD2-ADR-016-early-warning-baseline.md`

## 已知限制

- 15 km 基准是任务级配置包络，不代表真实装备性能；未来概率标定必须新增版本；
- EASY/MEDIUM 的 relay 指标按需求为 N/A，并从加权分母中移除；
- MEDIUM 和 HARD 尚未达到各自 E2，下一阶段为 AD2-08。
