# ADR-MD3-002：`interdict_to` 作为公开 SDK 规划助手

- 状态：Accepted for benchmark implementation
- 日期：2026-09-02
- 范围：MD3-05、规则智能体和第三方智能体 SDK

## 决策

`interdict_to` 不进入固定 Tick 内核，也不是 MD-INT-003 专用 action type。它实现为公开 SDK/策略 helper：输入授权的融合 contact estimate、自身公开运动能力、standoff/lead/区域参数，输出普通 `navigation` persistent command 的 waypoint/速度/航向建议。

helper 不读取 `WorldState`、敌方真值、隐藏随机或未来事件；调用方仍须经 ActionBatch、controller ownership、boundary、ROE 和 normal navigation pipeline。它可被规则智能体和第三方 agent 调用，也可不调用。

## 依据与兼容

该决策直接采用 `REQ-ACT-003`，并保持 `schemas/interface_v2.py` 的动作枚举和 `SessionLifecycleV2` 的单写入者边界不变。原 V4 要求将其作为引擎动作的描述不具有更高优先级。

## 不采用

- 添加含 P0、封锁弧、USV ID 或 attacker ID 的 World action handler。
- helper 直接更改速度、航向、health 或 mission state。
- 以真值接触替代 Observation。

## 验证义务

MD3-05 需证明输出可作为普通 navigation 被执行；无 WorldState import；不同名称/任意圆心和能力参数可复用；边界和命令拒绝仍由通用层生效。
