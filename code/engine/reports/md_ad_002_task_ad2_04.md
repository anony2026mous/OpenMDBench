# MD-AD-002 AD2-04 阶段报告

## 结论

AD2-04“多传感器探测、融合与虚警”完成。

## 实现

- 三份 YAML 配置五类档案：`radar_ew`、`radar_gap`、`radar_usv`、`radar_uav`、`eo_uav`。
- 严格校验传感器 ID、平台分配、标称/低空射程、概率、FOV、周期、噪声和虚警参数。
- 探测概率组合 RCS 四次方根距离、低空、天气、海况、USV 运动和 degraded 修正。
- 检测、距离噪声、方位噪声和虚警使用独立具名 RNG 子流。
- 每传感器独立扫描节拍；三次连续应更新帧确认，五次应更新帧未检测删除，删除后重捕获重新确认。
- 2 tick 融合周期，稳定关联与 tie-break，多源报告不引起 contact ID 抖动。
- 真实 track 和虚警均具有置信度、不确定度及出生/老化/删除生命周期。
- MEDIUM/HARD 启用确定性虚警，EASY 关闭。
- 公开 Observation 增加 `last_update_time` 和 `age`；contact ID 不包含真实实体 ID。
- tracker、关联、pending reports、命中/漏检计数、虚警及所有 RNG 进入 checkpoint。
- 脱敏后的 sensor_report、track_fused、false_alarm 事件进入 replay 事件流。

## 验证

- 射程内/边界、RCS、低空、天气、海况、USV 运动和设备降级修正。
- 三帧确认、五帧删除、重新捕获、多源融合和稳定 ID。
- 关闭传感器后的结果变化、红蓝 contact 隔离及 Observation 真值泄露检查。
- 同 seed 虚警一致；checkpoint 后下一帧 RNG、tracks 和输出完全一致。
- 三个场景运行 650 tick 后红方均可看到不透明稳定 contact，Observation 不含 `blue-striker-uav-*` 真值 ID。
- AD2-04 与 MD-INT-001 定向回归 `32 passed`；最终配置/核心专项 `19 passed`。
- Ruff、mypy、`git diff --check` 通过。

独立审查见 `artifacts/review/md-ad-002-code-review-ad2-04.md`，P0/P1/P2/P3 均为 0。

## 边界

本阶段不实现通信路由对 contact 投递的影响、武器、ROE 或突破裁决。HARD 的真实天气随机事件、干扰和压制由 AD2-09/10 接入；当前感知模块已经提供对应修正接口。
