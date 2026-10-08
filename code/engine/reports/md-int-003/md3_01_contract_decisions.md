# MD3-01 契约、ADR 与参数可信度冻结

## 记录

- TASK_ID：`MD3-01-001`
- 结论：`PARTIAL — benchmark 契约已冻结；真实参数标定仍待需求方/评测方确认。`
- 依据：`RF-ADR-001`、MD3-00 三份报告、V4 表 B-1 的 U1–U13。
- 取样锚点：engine/schema `2.0.0/2.0`；scenario `md-ad-002.easy.v2`；seed `0`；resolved `sha256:34f8322ccbdb8ce915002dc8d886235a87b61e833dd6069c992cf8f01e6c1f66`；catalog `sha256:cf34729fad371b07f58d3f4f66ff7cb975a00f97cc716a93b3a2527650ba6350`；map `sha256:c40a43035b62340c558e1c697823a574b936b50123acb49c4754b4c1d79c398d`；registry/plugin `sha256:573277d4e4495e4b6a22c9cb33fbdbe0fb70020925d8c717009ac503e91af69a/none`。

## 已冻结的实现边界

| ADR | 决策 | 后续阶段 |
|---|---|---|
| 001 | surface 通过通用 domain/resource/CombatSystem；命中延迟为 data-driven pending execution | MD3-03 |
| 002 | `interdict_to` 是公开 SDK helper，输出普通 navigation | MD3-05 |
| 003 | 自爆/碰撞/殉爆经 Effect→DamageIntent；wreck 是配置化 static lifecycle | MD3-04 |
| 004 | radial、环扇、前向占位、冲突/迟滞/重规划均为局部米制连续几何原语 | MD3-05 |
| 005 | environment/failure 使用稳定排序的 capability modifier pipeline | MD3-06 |
| 006 | 通信秒值审计、整数 tick 权威投递，非零亚秒 delay=1 tick，TTL 边界固定 | MD3-06 |
| 007 | terminated 与 truncated 分离，按需求的权威优先级和 TOI 处理 | MD3-05/07/08 |
| 008 | N/A 为 None；应算而缺数据为 0 + `metric_data_missing` | MD3-05 |
| 009 | 两 faction 各自标准 ActionBatch；统一 queue/ownership/visibility | MD3-08 |

## 参数可信度

U1–U13 全部标记 `UNVALIDATED_BENCHMARK`。允许按 V4 表格建立确定性 Catalog/Scenario 基准；禁止声称真实装备标定、为提高某策略胜率暗改数值或在 Python 固定参数。未来冻结必须发布新的精确 `id@version`、内容 hash、来源/fidelity、基准报告和变更记录。

| 参数组 | 状态 | 非阻塞范围 | 阻塞范围 |
|---|---|---|---|
| U1–U10、U13 | UNVALIDATED_BENCHMARK | 功能、确定性、三档 benchmark 开发 | 真实保真/正式参数声明 |
| U11 | UNVALIDATED_BENCHMARK | score pipeline 与诊断实现 | 正式排名/阈值冻结 |
| U12 | 默认关闭，通用 faction 支持已验证 | 主想定 benchmark | neutral ROE 专项验收 |

## 兼容与风险

- air combat、现有 action schema、单写入者、formal compiler、MMG process isolation 和 V2 hash/checkpoint 边界保持不变。
- 当前 V2 point sensing、communications transport、environment modifier、surface Catalog、pending impact、自爆/wreck、arc geometry 和四视角仍未实现；本阶段只冻结边界，不能宣称功能完成。
- MD3-02 只能新增资源闭包、地图引用和数据校验；若发现需要新的机制，必须返回对应 MD3-03 至 MD3-06，而不是在 scenario 中绕过。

## 测试与审查

本阶段执行 T0 文档/契约审查与 Markdown/YAML 结构检查；复用 MD3-00 的 T1 基线（652 collected，3 passed/15.06 s），没有运行 T2+。所有 ADR 的定向行为测试已列为后续阶段门禁。

## 下一阶段

MD3-01 gate：`PASS for benchmark resource design`。下一阶段为 MD3-02，仅可建立 versioned Catalog/map/resource closure 和 compiler validation；不得实现 combat、damage、mission、environment、communication 或 scenario-specific Python。
