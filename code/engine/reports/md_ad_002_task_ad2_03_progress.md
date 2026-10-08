# MD-AD-002 AD2-03 进展报告

AD2-03 已完成第一批实现，但尚未通过完整完成门禁，因此本工作包保持 `in_progress`。

已完成：基于具名 RNG 子流预计算三波出生时间、海上位置、高度、航向和速度；T=0/600±120/1200 按稳定 ID 仅出生一次；15 个蓝方 ID 固定；出生前不进入 WorldState；checkpoint 保存并恢复剩余 scheduled descriptors 和波次事件；扩展 terminal/tombstone 生命周期；接入地图边界、USV 上岸、UAV 撞地和实体接触的同步终态锁存。

验证结果：AD2-03 定向测试及 MD-INT-001 确定性回归 `18 passed`；Ruff、mypy 和 `git diff --check` 通过。

未完成门禁：尚需补充大步长穿越的 swept collision、出生点故障注入负测试、三场景完整运行到 1800 tick、跨实际出生 tick 的连续运行/checkpoint 对照，以及本阶段独立代码审查。完成这些项目之前不得把 AD2-03 标记为完成。
