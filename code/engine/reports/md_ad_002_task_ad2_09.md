# AD2-09 HARD 通信闭环完成报告

## 结论

`MD-AD-002-HARD` 的通信中继、延迟、TTL、可配置丢包和干扰链路已经形成任务级闭环。通信退化可在红方观察、基线策略、权威事件/步骤返回值和可视化 DTO 中一致体现。该结论只关闭 AD2-09；HARD 天气、海况、持续蛇形、设施压制和完整终局仍属于 AD2-10。

## 已实现能力

- 同阵营在线端点间按范围选路，最多两个中继，稳定排序且不依赖注册顺序；
- UAV LOS 50 km/10 Mbps/20 ms，USV LOS 30 km/5 Mbps/50 ms，路径带宽取瓶颈；
- 正时延逐跳量化到后续决策 tick，wired 零时延保持同 tick，事件同时保留物理时延；
- 消息携带产生、发送、到达、过期 tick、完整 route 和 payload 大小；
- 支持端点离线、relay 开关、阻断链路、TTL 过期和配置化确定性丢包；
- HARD `[900,1200)` 阻断指挥端与 UAV 直链，USV 中继可恢复 contact 和控制消息；
- UAV 公开通信状态为 `connected/relayed/offline`；失联继续最后导航且无新命令时不自主开火；
- 交战命令使用 2 tick TTL，其他控制命令和 contact 使用 10 tick TTL；
- 通信队列、RNG、端点/路由条件、事件和待应用命令进入 JSON checkpoint；
- routed command 已投递后，`relayed` 与 `connected` 均满足战斗通信合法性。

## 场景参数边界

冻结的 HARD v2 没有规定非零背景丢包率。本阶段没有虚构概率：通用网络层已经实现并测试 loss RNG，HARD 基线背景丢包为零，场景退化来自冻结的确定性干扰窗口。该选择记录于 AD2-ADR-018；未来更改必须新版本配置并重建哈希/golden。

## 配置身份

- EASY：`sha256:1adaa81c574ffa6a0e05c88be0da7029d45d5f24a1fa73d3ef2ad20065c81f16`
- MEDIUM：`sha256:1dd96cc3b5f0d0103a69745af12ae0de51361eb8d93a1d4a3dac48237ce8a5e4`
- HARD：`sha256:9a057519c2a6f53d0cf5d4d9073a4c7b9ad9976d1228e6b846505d9a49f8bc42`

## 自测试覆盖

- 直连、单中继、双中继、最大跳数、稳定选路与跨阵营隔离；
- 链路离线、无路径、干扰启停、恢复重连、TTL 和零/正时延边界；
- 丢包 RNG 和待投递队列的 checkpoint 精确恢复；
- contact 延迟到达、控制命令延迟应用、过期交战不执行；
- 16 个环境通信对象和 relay 状态隔离；
- 观测事件、步骤日志和可视化通信状态一致。

## 质量门禁

- Ruff：全仓零错误；
- 严格 mypy：226 个源文件零错误；
- Bandit：零问题；
- `git diff --check`：通过；
- 通信专项：25 passed；
- 全量回归：`371 passed, 90 warnings in 336.74s`；
- 告警为既有 Taichi/Gymnasium 提示及缺少中文字体时的 Matplotlib glyph 提示，无失败；
- 未增加 skip/xfail，未放宽断言或排除核心通信代码。

## 已知限制

- 不模拟波形、射频传播、协议重传、队列拥塞或真实装备抗干扰性能；
- HARD 环境随机天气、海况变化和岸基/USV 压制尚未接入，将在 AD2-10 完成；
- relay_effectiveness 的权威累计评分随 HARD 完整裁决在 AD2-10 接入。
