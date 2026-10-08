# BASE-00 当前 HEAD 核验与击毁崩溃基线记录

```text
TASK_ID: BASE-00
STATUS: DONE
OBJECTIVE: 在不修改产品代码、测试、Catalog、场景参数或依赖的前提下，核验当前 HEAD，
  复现或证伪 MD-AD-002 首次击毁后的崩溃，并锁定当前真实代码路径、tick 时序和根因。
REQ_IDS: BUG-V2-001; AR-003; AR-005; AR-007; ENT-005; LIFE-001; CMD-001; CMD-003; RUN-002
CURRENT_COMMIT: 4e3bf23f86ad0a46bebce1cdcfb5e0854244c21e
PRECONDITIONS:
  - 已完整读取 AGENTS.md、平台需求、平台实施/测试/审查计划和专项修复计划。
  - 用户仅授权 BASE-00；明确禁止提前执行 BUG-01、T4、T5、依赖/场景参数/测试修改。
  - 本记录是本阶段唯一允许写入的受控产物。
ALLOWED_READ:
  - 全仓库源码、测试、配置、Schema、ADR、Catalog、现有报告和 Git 只读状态。
ALLOWED_WRITE:
  - reports/repair/BASE-00_current_head.md
  - 测试或复现产生的临时目录（不得进入版本控制）。
PROHIBITED:
  - 修改任何源码、测试、Catalog、场景参数、依赖、锁文件、已有报告或 Git 历史。
  - 执行 BUG-01 或后续阶段工作。
  - 执行 T4/T5、全量测试、性能/并发/压力/soak 测试。
  - 提交、推送、合并、创建 PR 或删除文件。
TEST_LEVEL: T1
ALLOWED_COMMANDS:
  - git rev-parse/status/diff/log/show（只读）
  - rg/find/sed/python 只读源码与配置检查
  - 项目既有 MD-AD-002 定向 headless 复现入口，固定 seed，最多一次短复现和一次必要的
    受控 1800-tick 上限复现；允许保存 stdout/stderr 到 /tmp
PER_COMMAND_TIMEOUT: 120 s（必要的 1800-tick 复现可为 300 s）
TOTAL_TIME_BUDGET: 15 min
ACCEPTANCE:
  - 记录 commit、工作区既有改动和运行环境；
  - 给出 World 活动动力学集合、Session/Command 动力学命令、lifecycle 转换的真实代码路径；
  - 用固定 seed 记录首次击毁附近的 tick、实体、异常和事件序列，或有同等强度的不可复现证据；
  - 判断 MD-AD-002 其他难度是否具有同源风险；
  - 对照专项报告所述根因，给出当前 HEAD 的差异结论与下一阶段准入。
OUTPUTS:
  - reports/repair/BASE-00_current_head.md
STOP_CONDITIONS:
  - 无法在受限 T1 内复现且当前代码路径已实质变化：NEEDS_DECISION，禁止进入 BUG-01。
  - 必需输入、入口或环境不可用：BLOCKED。
  - 发现需要修改源码、测试、参数或依赖才能继续：停止并报告，禁止越界修改。
OUTPUT_FORMAT:
  - 状态、范围、修改文件、命令与退出码、测试、证据、根因、兼容性、确定性、领域影响、
    风险与下一阶段准入结论。
```

## 执行结果

### HEAD、环境与工作区

- HEAD：`4e3bf23f86ad0a46bebce1cdcfb5e0854244c21e`
  (`docs: document MD-INT-003 surface scenarios`)，分支为 `refactor`，检查时与
  `origin/refactor` 同指针。
- 环境：Linux `6.8.0-136-generic` x86_64；项目解释器
  `.venv/bin/python` 为 Python `3.11.15`。
- 工作区在开始前已非干净：`AGENTS.md`、既有用户操作手册有修改，并有用户文档、DOCX、
  运行产物等未跟踪文件。均未修改、暂存、提交或删除。本阶段新增的唯一仓库文件是本记录；
  取证脚本与输出均在 `/tmp`。
- 专项计划列出的两份外部问题报告
  `engine_bug_ad002_formal_v2_kill_crash.md`、
  `mmg_rpc_per_tick_overhead_and_virtualization_amplification.md` 不在当前工作区。
  因而不能核验其原始提交号或数字；以下结论仅以当前 HEAD、Git 历史与本次可复现运行为准。

### 实际命令与结果

| 命令/类别 | 退出码 | 结果 |
|---|---:|---|
| `git rev-parse/log/status`、解释器/系统查询 | 0（首次合并预检的错误虚拟环境路径为 127，随后以项目根目录更正） | 记录 HEAD、分支、脏工作区与环境。 |
| `rg`/`sed` 阅读 World、Session、CLI、场景、Catalog、测试和 Git 历史 | 0 | 锁定运行入口、集合生成位置、毁伤转换与变更归属。 |
| `.venv/bin/python -m openmdbench.cli run --scenario MD-AD-002-EASY --seed 73 --ticks 1800` | 1（预期复现） | 首先抛出 `ValueError: World tick requires exactly one current command per active dynamics entity`。CLI 清理阶段随后因 Session 已停止又抛出 `SessionFailureV2`，该异常不改变首个根因。 |
| `/tmp/base00_md_ad_trace.py`（相同正式 Session/规则智能体/seed，捕获异常并输出 JSON） | 0（受控捕获） | 在首次失败处记录 tick、实体 lifecycle、两侧集合及已提交事件。 |
| YAML 静态检查 EASY/MEDIUM/HARD | 0 | 三档均存在相同的静态 dynamics 实体和 `effect.ciws-hit@2.0.0` 碰撞毁伤政策。 |
| `git blame`/`git diff` | 0 | 确定两侧筛选逻辑来自不同提交；当前差异可追溯。 |

未执行 pytest、T4 或 T5；未执行性能、并发、压力、soak、依赖变更或场景参数修改。

### 可复现证据

正式入口 `openmdbench.cli._run_formal_v2` 以规则智能体运行
`MD-AD-002-EASY`，固定 `seed=73`：

1. `base-00.tick.00000357` 成功完成，World 从 tick 357 推进至 358。
2. 该 tick 的碰撞 DamageIntent 为：
   - `damage:357:defender.interceptor-001:0:collision`；
   - `damage:357:defender.interceptor-002:1:collision`。
3. 两个目标均由 `active` 变为 `disabled`，health 均由 `1.0` 变为
   `0.2997651468432486`；本次已提交 tick 无 combat request，说明触发源是碰撞毁伤，
   不是武器发射。
4. 尝试 tick 358 时，Session 已为所有 11 个仍具 `dynamics_ref` 的实体生成命令；World
   仅认可 9 个 `active/degraded` dynamics 实体。多出的两个 ID 是：
   `defender.interceptor-001`、`defender.interceptor-002`，其 lifecycle 均为 `disabled`。
5. World 在实际推进动力学前拒绝该不相等集合，`world.tick` 保持 358，
   `failed_tick_operation_id` 为 `base-00.tick.00000358`。World 的 append-only
   失败锁存随后令 Session 进入 `STOPPED`。

因此，“首次击毁后崩溃”的当前真实表现更精确地说是：**任何保留
`dynamics_ref` 但因毁伤转为 `disabled`（以及同样被排除的 `destroyed`）的实体，在下一
tick 会触发命令集合不一致崩溃。**本次 seed 首个触发状态是 `disabled`，不是
`destroyed`；故不能把根因缩窄为仅 destroyed/wreck。

### 当前真实代码路径与 tick 时序

```text
ActionPipelineV2.apply_tick (sessions/lifecycle_v2.py:1384-1425)
  └─ entities_stable() 中所有 dynamics_ref != None 的实体生成 controls
      （未按 lifecycle 过滤）
      ↓
WorldStateV2.advance_tick (world/factory_v2.py:4146-4185)
  ├─ 处理调度 lifecycle 边界
  ├─ 仅以 dynamics_ref != None 且 lifecycle ∈ {active, degraded}
  │  形成 active_dynamics_after_lifecycle
  └─ _invoke_motion_provider (2907-2915) 要求命令 ID 集合严格相等
      ↓
本 tick 后半段：apply_damage_transaction (5166, 5507-5524)
  └─ health <= 0.5 → disabled，清空 capabilities/token
      ↓
下一 tick：Session 仍含 disabled 实体；World 已排除它们；严格集合检查抛异常
```

`git blame` 显示 Session 的宽松选择器（`lifecycle_v2.py:1384-1388`）来自
`14a9c49`；World 的 lifecycle 限制（`factory_v2.py:4179`）由
`7a51816` 引入。故当前 HEAD 相对于早期基线已修改 World 的运动资格而未同步 Session
投影，是当前可证实的直接根因。外部问题报告不在仓库，无法判断其引用的提交是否完全相同；
但该差异不影响本次复现结论。

### 其他难度的同源风险

EASY/MEDIUM/HARD 三个 data-only 场景均使用相同的 `SessionLifecycleV2` 和
`WorldStateV2` 路径；静态 defender 都包含三架 `dynamics.interceptor-uav@2.0.0`
拦截机、两个 `dynamics.picket-usv@2.0.0`，并配置相同的 collision effect。
故只要任一动态实体转为 `disabled` 或保留为 `destroyed/wreck`，三档都存在同源 P1 崩溃风险。
按 BASE-00 的 T1 范围，未把 MEDIUM/HARD 各运行至终局；这是静态同源判断，不能替代
BUG-04 的三档运行回归。

### 兼容性、确定性与领域影响

- 兼容性：失败发生于 Formal V2 通用 Session/World 接口，而非场景专用分支；任何使用该
  ActionPipeline 的动态实体组合都可能受影响。
- 确定性：固定 seed 73 的单次正式运行稳定定位到 tick 358；本阶段未做重复运行或
  checkpoint 对比，因而不宣称完整确定性证明。
- 领域影响：disabled/destroyed 实体已被正确停止 capability 驱动的主动子系统，但 Session
  仍把其当作应接受运动控制的实体，违反生命周期—运动资格的一致性。被毁实体的日志、残骸和
  后续 checkpoint 语义尚未在本阶段修改或重新验证。

### 自审与风险

自审（只读）：确认无场景 ID、固定 faction 或固定实体 ID 参与根因；根因是通用选择器的
语义分叉。未发现本阶段对源码、测试、Catalog、场景参数或依赖的写入。

1. **P1 / BUG-V2-001（开放）**：非运行 lifecycle 的 dynamics 实体可导致正式对局在下一
   tick 崩溃；已在 EASY/seed 73 复现。
2. **P2（开放）**：CLI 的 `finally: session.stop().close()` 在首个异常已令 Session 停止后
   产生第二个 transition 异常，可能遮蔽外层调用者的清理语义；本阶段不修复。
3. **P2（证据边界）**：两份外部问题报告及其基准提交在当前工作区缺失，无法作逐提交对照。
4. **P2（工作区）**：已有用户修改与未跟踪产物很多；后续实施必须继续仅触碰阶段执行记录允许的
   文件，避免混入提交。

### 下一阶段准入结论

`BASE-00` 的当前 HEAD 核验、固定 seed 复现、真实代码路径、tick 时序、根因和三档同源风险
均已取得足以进入设计阶段的证据，结论为：**允许在获得下一条阶段授权后进入 BUG-01，且仅进入
BUG-01 的 T0 契约冻结。**

BUG-01 必须首先冻结“World 是 motion eligibility 唯一事实来源”、disabled/destroyed/wreck
的命令投影、persistent/discrete action 取消语义与 tick 顺序；不得在该阶段修改实现、测试、
场景参数或 MMG RPC。当前用户指令未授权 BUG-01，因此本阶段到此停止。
