# BUG-04 场景、接口与恢复回归记录

```text
TASK_ID: BUG-04
STATUS: DONE
OBJECTIVE: 验证 BUG-V2-001 的 World-authoritative motion projection 在 MD-AD-002 三档、
  MD-INT-003 lifecycle/wreck、air/surface combat、Python/Gym/REST、log/frame、checkpoint 和
  deterministic replay 下保持外部语义，且不再发生 strict command-set crash。
REQ_IDS: BUG-V2-001; AR-003; AR-005; AR-006; AR-007; ENT-005; LIFE-001;
  CMD-001; CMD-002; CMD-003; RUN-001; RUN-002; CHK-001
CURRENT_COMMIT: 4e3bf23f86ad0a46bebce1cdcfb5e0854244c21e
PRECONDITIONS:
  - BASE-00 已复现 MD-AD-002-EASY/seed 73 tick 358 crash。
  - BUG-01 设计冻结，BUG-02 红灯已建立，BUG-03 T2 318 项定向测试通过。
ALLOWED_READ:
  - BUG-03 改动、CLI/scenario definitions、session/gateway/replay/frame/checkpoint、直接测试和报告。
ALLOWED_WRITE:
  - reports/repair/BUG-04_scene_interface_restore_regression.md
  - reports/repair/BUG-V2-001_requirements_traceability.md
  - 仅为直接回归所必需的 tests/contract/test_motion_eligibility_contract_v2.py；若无失败不得改源码。
PROHIBITED:
  - 修改生产源码（除发现本缺陷 P0/P1 后先记录并返回 BUG-03）、场景/Catalog/依赖/锁文件；
    T4/T5、全量 pytest、并发/压力/soak、提交/推送/PR。
TEST_LEVEL: T3
ALLOWED_COMMANDS:
  - rg/sed/git 只读；PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 的指定 pytest；
    MPLCONFIGDIR=/tmp/... .venv/bin/python -m openmdbench.cli run --scenario ... --seed ... --ticks ...。
PER_COMMAND_TIMEOUT: 10 min
TOTAL_TIME_BUDGET: 30 min
ACCEPTANCE:
  - EASY/MEDIUM/HARD 各固定 seed 到自然终局或时限；EASY/seed 73 至少 1800 tick；
  - MD-INT-003a/b/c lifecycle/self-trigger/collision/wreck 定向回归；air/surface 契约；
  - Python/Gym/REST 相同动作序列外部结果比较；击毁前/中/后 checkpoint；
    log/VisualizationFrame/outcome/score；同 seed 两次结构化结果相等；
  - P0/P1 为零，strict command-set error 不再出现。
OUTPUTS:
  - CLI/pytest 命令、种子、通过结果、失败分类、兼容性/确定性/领域结论。
STOP_CONDITIONS:
  - 重现 strict command-set error、destroyed/wreck 执行主动 dynamics、重复 action/impact/damage/
    receipt，或跨接口/restore 语义不等价：FAILED，记录后回到 BUG-03；不得开始 PERF-00。
```

## 执行结果

### 发现并关闭的直接缺陷

首次 HARD 长局已经越过此前 motion crash，但结束构造 checkpoint 时发现
`session child and status ledgers disagree`。根因、最小修复和 39 项受影响复测已如实记录在
`BUG-03_minimal_fix.md` 的“BUG-04 反馈修复”节。修复后从头重跑 HARD/seed 73/1800，成功。
因此该发现没有遗留为开放 P1/P0。

### MD-AD-002 三档真实运行

均使用 formal V2 rule team、`seed=73`、`ticks=1800`、`MPLCONFIGDIR=/tmp/openmdbench-bug04-mpl`。
每条命令均以 `CLI_EXIT=0` 完成、生成 `SessionCheckpointV2`；没有
`World tick requires exactly one current command per active dynamics entity`。

| 场景 | resolved id | 终局 tick / outcome | checkpoint hash |
|---|---|---|---|
| EASY | `md-ad-002.easy.v2` | 973 / `intruder_success` | `sha256:dce6e186217d5844899fc86d7113150e310c05470a7ef7e026370789b9b080ce` |
| MEDIUM | `md-ad-002.medium.v2` | 994 / `intruder_success` | `sha256:60a6b0a60d2193baea29ec1a177b3c55d4c5631245b9f3887d161078943dea6e` |
| HARD | `md-ad-002.hard.v2` | 547 / `intruder_success` | `sha256:b7a6acf229f208fabeb3fdd92b481bd3175b142191296ffeec13eb422e61ceb9` |

CLI 按请求继续推进至 1800 tick；terminal result 是已锁存的 mission/scoring evidence，而非
提前截断。三档最终 active entity 数均为 22。

### T3 指定测试

所有 pytest 均以 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 隔离系统 ROS 自动插件；未跳过任何项目
测试。`MPLCONFIGDIR` 仅避免 Matplotlib 默认缓存目录不可写。

| 指定集合 | 退出码 | 结果 | 覆盖 |
|---|---:|---|---|
| `test_md_ad_002_gym.py`、`test_md_ad_002_rest.py`、`test_gateway_equivalence_v2.py`、`test_md_ad_002_easy_checkpoint.py`、`test_md_int_003_damage_lifecycle.py`、`test_md_int_003_surface_combat.py`、`test_md_int_003_scenarios.py`、`test_md_int_003_interfaces.py`、`test_md_int_003_visualization.py`、`test_md_int_003_system_determinism.py` | 0 | **44 passed, 1 warning** | Python/Gym/REST 公共状态、retry exactly-once、三档 MD-INT-003、air/surface combat、self-trigger/collision/wreck、checkpoint/restore、frame/replay、same-seed/session-ID-independent timeline。 |
| `test_md_ad_002_v2_visualization.py`、`test_md_ad_002_v2_rule_agents.py`、`test_md_ad_002_v2_migration.py` | 0 | **37 passed** | MD-AD 三档 rule actions、spawn public action、MMG navigation、gateway checkpoint/restore、in-memory tick evidence、destroyed/disabled frame hiding、live/replay frame equality、renderer isolation。 |
| `test_motion_eligibility_contract_v2.py` + `test_session_action_world_v2.py`（BUG-04 反馈修复后） | 0 | **39 passed** | B01--B10、fallback/status/checkpoint 闭包与 Session World writer。 |

唯一警告是 Taichi 依赖中 Python 3.15 的未来 `locale.getdefaultlocale` deprecation warning；不影响
本轮断言、结果、确定性或运行状态，归类为依赖告警而非测试失败。

### 验收结论

- **场景与 motion**：三档真实 1800 tick 都通过，BASE-00 的 strict command-set crash 未重现。
- **lifecycle/wreck**：MD-INT-003 self-trigger、非终止 trigger、collision、weapon destruction、
  wreck/despawn policy、checkpoint restore 均通过；destroyed/wreck 不进入主动 dynamics。
- **接口**：Structured Python、Gym、Vector、REST 复用同一 gateway/action semantics；REST retry
  不重复 discrete action，observation/frame/replay 均为只读且不推进 tick。
- **恢复与确定性**：击毁/trigger 边界 restore、same seed/不同 session ID 的 authoritative frames、
  speed/renderer/polling 独立性、MD-AD gateway checkpoint/restore 全部通过。CLI 的可复现 hash 见上。
- **日志/帧/终局/评分**：live/replay 使用 authority frame；renderer 从 disabled/destroyed 帧中隐藏
  实体但不删除 artifact history；terminal result、score state 与 checkpoint 可完整读取。

### 兼容性、风险与下一阶段准入

- 兼容性：公开 Action/receipt/checkpoint/REST/Gym/Python schema 无改变；新可见结果只是在原本
  会崩溃或 checkpoint 失败时获得已有 `cancelled/rejected`/fallback status 语义。
- 确定性：所有 projection、receipt 和 fallback 均稳定排序；T3 同 seed/session independence 和
  checkpoint 恢复测试通过。没有改变 RNG、dt、子步数或积分器。
- 领域影响：air、surface、fixed/native MMG、spawn、disabled、wreck/despawn 与三档场景通过同一
  通用路径，无 MD-AD-002/MD-INT-003 核心特判。
- 未执行：T4（format/Ruff/mypy/Bandit/full pytest/coverage）与 T5（性能并发压力/soak）均未获授权，
  未执行。

准入结论：**BUG-04 DONE，P0/P1 为零；允许进入 PERF-00（T3 修复后性能基线）。**
