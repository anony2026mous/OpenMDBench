# MD-INT-001 Phase G 端到端自测试报告

- 状态：通过。
- 蓝胜黄金基线：seed 73，tick 170，`threat_destroyed`；选择理由为稳定覆盖合法开火、逐发 RNG、毁伤和摧毁链。
- 红胜基线：禁用蓝方 engage，red breach。
- Timeout：禁用 engage 且红方 hold，tick 900，`timeout_without_breach`。
- 同 tick：breach 与摧毁同时发生时 red breach 优先并锁存。
- 检查点：world、sensor、communication、combat RNG 与 mission 状态精确恢复。
- 确定性：同 seed 同进程相同；seed 73/74 的命中事件轨迹不同。
- 场景命令：`python -m openmdbench.cli selftest --scenario MD-INT-001 --seed 7` 通过。
- 产物：自测试 JSON/Markdown、蓝胜/红胜逐 tick 回放、裁判/蓝方威海底图 PNG 均已生成。

