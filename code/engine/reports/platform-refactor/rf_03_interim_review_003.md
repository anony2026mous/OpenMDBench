# RF-03 中期独立审查 003

- TASK_ID：RF03-REVIEW-003
- 状态：DONE
- 结论：RF-03 NOT PASS（中期实现可继续）
- 独立验证：123 passed；Ruff、format、mypy strict、scoped diff check、V2 禁止特例扫描均通过
- 严重度：P0=0，P1=8，P2=4

## 已完成

- 单文件/多文件统一语义，logical/content/archive hash 分离。
- Safe YAML、重复 key/alias/非 UTF-8/非有限数和路径逃逸拒绝。
- 动态 faction 与 0/1/10/100 formation 编译期展开。
- ResolvedScenarioV2 深冻结、Python hash、规范 JSON 往返和 compiler-version 行为 hash。
- CompilerErrorV2 稳定字段齐全；V2 模块无 MD、Side、red/blue、固定 ID、`:02d`、legacy 命中。

## P1 阻断项

1. WGS84/map 尚未归一为 local metres，缺 frame/transform/range 校验。
2. Zone、Boundary、部署几何与平台域闭包未实现。
3. Resolved entity 仍保留 Catalog refs，component/sensor/communication/ammunition/energy/collision/visualization/target-domain 和 resource hash 未完全展开。
4. Event trigger/payload 未类型化，缺 tick、生命周期、引用、配对、Effect 和依赖环校验。
5. Mission、Scoring、Controller 只携带声明，缺 selector/reference/unit/weight/capability/占用和自治策略校验。
6. Visibility policy 缺失。
7. Compiler 仍是单体方法，缺显式稳定阶段与错误优先级。
8. 旧公共 Compiler 仍混合 Generic、MD 和 Side；缺 Legacy protocol/registry/adapter 与 V2 facade 的物理隔离。

## P2

- V2 package 缺 entry、单文件、总字节、ZIP 解压和压缩比配额。
- Formation offset 坏长度/类型可能逃逸稳定错误。
- 多文件字段 provenance 不精确。
- 测试需增强 Catalog 失败、重复关系、JSON extra、配额与 ZIP/symlink 安全。

## 下一 RED/GREEN 顺序

1. 判别式 local_m/wgs84/map、显式 MapBinding、统一 local metres。
2. polygon/circle、world bounds、zone containment、domain/terrain deployment compatibility。
3. exact resource expansion。
4. typed event dependency。
5. mission/scoring/controller/visibility。
6. stable compiler stages。
7. V2 package quotas/ZIP。
8. Legacy adapter/facade 物理隔离。

RF-03 未完成前不得进入 RF-04。
