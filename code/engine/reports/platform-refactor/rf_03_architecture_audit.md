# RF-03 声明式场景编译架构审计

- TASK_ID：RF03-ARCH-001
- 状态：DONE
- 审计方式：T0，只读

## 结论

当前 `composition@1.0` 与混合式 Compiler 不能作为 RF-03 通用基线。RF-03 必须建立新的 V2 单向编译路径：

```text
Safe Package Loader
  -> ScenarioDocumentV2
  -> ScenarioCompilerV2 stable stages
  -> immutable/hashable ResolvedScenarioV2
```

Legacy adapter 只能单向生成 `ScenarioDocumentV2`；通用 V2 模块不得导入 Legacy、MD config、Side 或固定场景知识。

## 阻断项

- 旧 composition 固定 blue/red、四类平台/域且至少一个实体。
- 缺 factions、relationships、formations、boundary、mission、scoring、controller slots 和 visibility。
- 坐标只支持 Weihai WGS84，缺 local/map 通用坐标 union。
- 波次和编组在运行期展开并固定两位 ID，不符合编译后运行。
- 旧 ResolvedScenario 未完全展开资源，内部 FrozenDict 不可 Python hash。
- 目录、多文件、单文件缺统一语义模型；包 hash 包含文件名，等价改名会改变 resolved hash。
- Generic 与 MD-INT/MD-AD、Side、固定实体/武器分支物理混合。
- 事件依赖和稳定错误流水线不完整。

## V2 最小边界

`ScenarioDocumentV2` 至少包含 metadata、Catalog bindings、world/map/clock/units、factions、directed relationships、entities、formations、zones、boundaries、events、mission、scoring、controller slots、visibility 和 deterministic randomization declaration。

坐标使用带判别字段的 `wgs84`、`local_m`、`map` union，编译后统一为 local metres。Formation 必须在编译期展开，count 支持 0/1/10/100；ID pattern 显式包含 index，宽度由声明决定，展开后做全局唯一性检查。

编译阶段固定为：schema、exact resources、defaults/units、factions/relationships、formation expansion、composition compatibility、coordinate normalization、boundary/deployment、event dependency、mission/scoring/controller、visibility、stable ordering、freeze/hash。

## 包与哈希

- `archive_hash` 可绑定原始路径和字节，用于供应链审计。
- `logical_hash` 基于规范语义文档，不受目录布局、文件改名和 display name 影响。
- `resolved_hash` 基于完全展开结果、Catalog hash 与 compiler version。
- 运行期不得读取 YAML、重新查询 Catalog、转换坐标或展开编组。

## 测试矩阵

- 单文件/多文件、合并顺序、目录/文件/display-name 改名语义等价。
- 0/1/2/3/10 faction；有向 ally/hostile/neutral/unknown 关系及坏端点。
- 0/1/10/100 formation，显式实体混合、ID pattern/冲突、0 inventory 和资源不兼容。
- WGS84/local/map 等价与非法范围、非有限数、维度、地图/域/边界/部署错误。
- zone/event 引用、生命周期顺序、jamming 配对、apply_effect 类型和依赖环。
- mission/scoring/controller 引用、权重/单位、0/1/10/100 slots、重复占用。
- 深冻结、Python hash、JSON roundtrip、重复编译和输入顺序扰动 hash 稳定、断开源目录可用。
- 路径逃逸、绝对路径、重复路径、unsafe YAML tag/alias、重复 key、非 UTF-8 和解压限制。

## 禁止特例门禁

V2 通用模块中必须扫描为空：MD-AD/MD-INT/MDAD/MDInt、Side、red/blue、固定实体名、场景 ID 比较、固定 count 比较、`:02d`、legacy import。

## 阶段边界

RF-03 仅交付声明式包、Compiler 和 ResolvedScenario。WorldFactory 留 RF-04；底层系统留 RF-05～09；Legacy 正式迁移必须等待 RF-10 GEN-GATE。
