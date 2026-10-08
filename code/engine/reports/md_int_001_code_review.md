# MD-INT-001 独立代码审查

## 结论

- P0：0。
- P1：0 个未解决；2 个发现均已修复。
- P2：3 个已知限制。
- P3：2 个第三方告警。

## 已修复发现

### P1：正式回放缺少 WGS84 实体坐标

- 证据：原 `frame_from_world` 只复制本地米制 `position`，场景自测试没有传入 GeoFrame。
- 影响：离线日志无法独立核验威海经纬度终态。
- 修复：`openmdbench/visualization/live.py` 支持可选 GeoFrame，并在 DTO 中写入 `position_wgs84`；场景 recorder 强制传入已校验 GeoFrame。
- 验证：`tests/system/test_md_int_001_replay.py` 断言五实体终态经纬度均存在。

### P1：回放任务终态和十项评分未进入帧

- 证据：原 recorder 使用默认 `MissionPanel(status=unknown)` 和零分 ScoreSets。
- 影响：在线裁决与离线回放无法逐项对账。
- 修复：每 tick 写入 adjudication、剩余时间、terminal event，以及 MUS/RAE/AS/CDCS/OIIS/TSR/TE/EE/CSS/TA；AS 明确为 N/A。
- 验证：系统回放测试断言 `blue_success/threat_destroyed`、TSR 和十个指标键。

## 已知限制

### P2：USV 参数集是接线验证替代参数

- 文件：`openmdbench/domains/surface/mmg_adapter.py`、`openmdbench/config/md_int_001_v1.yaml`。
- 证据：元数据明确标记 `kvlcc2_l7_wiring_only` 和 `abstract_7m_kvlcc2_surrogate_not_validated_real_usv`。
- 影响：求解器/积分器是真实 Sim2Sea MMG 调用，但参数不能解释为真实参赛 USV 海试标定结果。
- 后续负责人：动力学模型负责人；取得船体辨识数据后新增版本化参数集及 golden trajectory。

### P2：依赖漏洞在线审计受 PyPI 超时阻塞

- 证据：`pip-audit` 在沙箱内被网络禁止；批准联网后 PyPI 读取仍超时。
- 影响：Ruff、mypy、Bandit 和安全测试通过，但当前环境未取得最新依赖漏洞结论。
- 后续负责人：发布负责人；在具有稳定 PyPI/OSV 网络的 CI 中重跑 `python -m pip_audit`。

### P2：长稳测试尚未达到发布时长

- 证据：性能 smoke 与短 soak 通过，未在本次交互中等待 2 小时场景 soak/12 小时发布 soak。
- 影响：当前功能和短时资源稳定性有证据，不能宣称已满足发布级长稳时长。
- 后续负责人：发布负责人；CI/夜间任务运行 2 小时与 12 小时 soak 并归档 RSS 曲线。

## P3 告警

- Taichi 1.7.4 内部调用 Python 将弃用的 `locale.getdefaultlocale`。
- Gymnasium 检查器对 list observation 做 NumPy cast 并建议归一化 Box；公开 space 实值断言通过。

## 审查覆盖

- 正确性：五实体主循环、GeoFrame 单一坐标权威、UAV/MMG/固定雷达、能量、传感、通信、combat、breach-first 裁决。
- 确定性：SessionRNG 子流、稳定实体顺序、spawn 并发、checkpoint 中 world/contact/sensor/communication/combat RNG/mission。
- 信息隔离与安全：规则策略仅使用公开 Observation，蓝方 REST 观察不含红方 truth，回放视角过滤，时间戳/幂等/限流/跨会话负向测试。
- 性能与生命周期：MMG core 复用且每 adapter 恢复状态，Matplotlib retained artists，ReplayWriter 批量 flush，会话删除关闭 replay/env。
- 测试质量：关键链路断言具体终态、tick、事件、哈希和 DTO 字段；36 场景均加载，无 skip/xfail。

