# OpenMDBench 0.1.0 独立代码审查

- 审查日期：2026-08-06
- 范围：`openmdbench/`、`tests/`、场景、回放/API 契约和发布依赖
- 结论：P0 0，P1 0，接受的 P2 2，接受的 P3 2

## 工具证据

| 工具 | 结果 |
|---|---|
| Ruff | 133 个源文件，无问题 |
| mypy strict | 133 个源文件，无问题 |
| pytest | 166 passed，0 failed，0 skipped；14 条已知第三方告警 |
| coverage.py | 总体 92%；core 90%–100%，schemas 100%，missions 93%，scoring 90% |
| Bandit | `bandit -q -r openmdbench`：0 个发现 |
| pip-audit / OSV | API、测试和构建依赖升级后，仅本地遗留的可选 Torch 2.3.1 环境有发现；发布约束已提升至 Torch >=2.10 |

覆盖率机器可读结果：`reports/coverage_0.1.0.json`。

## 九维人工审查

1. 正确性：核查动作单位、tick 推进、终止边界、检查点状态和回放帧；修复回放缺少非受控实体。
2. 确定性：随机状态由环境 RNG 保存恢复；相同 seed、动作重放和检查点测试通过；未发现业务路径全局随机调用。
3. 信息隔离：REST Observation 只返回公开结构；未知 contact 字段被拒绝；裁判回放与选手视角过滤分离。
4. API：核查 schema、幂等键、时间戳冲突、频率限制、会话隔离、标准错误体和检查点完整性。
5. 安全：核查路径、恶意 JSON、回放版本、哈希、请求体上限和依赖；请求体改为逐块限流。
6. 性能：基准覆盖三种规模、4/8 会话、日志和回放；未见随会话销毁增长的活动资源。
7. 可维护性：模块边界清楚，严格类型检查通过；CLI 分支覆盖偏低但核心路径由模块测试覆盖。
8. 测试质量：包含契约、负向输入、确定性、故障恢复、安全、性能和 1000 会话资源回收测试。
9. 文档：回放格式、API/SDK、场景、训练和各阶段报告已同步；Docker 发布材料留待 T7.6。

## 已修复发现

| 文件/行 | 原级别 | 证据 | 影响 | 修复 |
|---|---:|---|---|---|
| `openmdbench/api/app.py:52` | P1 | 无 Content-Length 的请求曾在检查前调用 `request.body()` | 攻击者可用大请求造成进程内存耗尽 | 逐块读取并在 1 MiB 配置上限立即返回 413；新增真实异步分块测试 |
| `openmdbench/api/sessions.py:200` | P1 | 权威对局帧曾只写一个蓝方实体 | 日志无法重建完整蓝红态势，T6.9 数据不完整 | 每 tick 写入场景全部实体；新增实体集合契约测试 |
| `pyproject.toml:30` | P1 | OSV 报告旧 Starlette、pytest、setuptools 和可选 Torch 漏洞 | 服务或训练环境可能继承已知漏洞 | FastAPI/Starlette、pytest、setuptools 已升级验证；发布 Torch 下限提升至 2.10 |
| `openmdbench/replay/reader.py:67` | P3 | Bandit B101：运行时代码使用 `assert` | `python -O` 可移除保护 | 改为显式 `RuntimeError`；Bandit 复跑为零发现 |

## 接受风险

| 文件/行 | 级别 | 证据 | 影响 | 负责人和后续计划 |
|---|---:|---|---|---|
| `openmdbench/api/sessions.py:256` | P2 | 恢复会话的新回放先写 tick 0，再导入较晚检查点；尚无显式 restore 帧 | 恢复后的日志存在时间跳跃，纯动作校验器不能独立重建恢复边界 | 回放负责人；在比赛发布前增加 checkpoint-reference 事件及恢复回放测试 |
| `openmdbench/api/sessions.py:249` | P2 | 帧中 `scores.total` 暂为 0，累计 reward 只放在 metrics | 当前简化 Gym 会话的日志总分不能代表完整十指标裁判评分 | 评分负责人；正式裁判环境接入时改为版本化十指标快照 |
| `openmdbench/cli/__main__.py:1` | P3 | 文件覆盖率 33%，但命令调用的模块路径均有直接测试 | CLI 参数组合的回归定位可能较慢 | 工具负责人；T7.5/T7.6 增加自测和镜像命令端到端测试 |
| `.venv`（非发布物） | P3 | 最终 OSV 扫描仅剩本地旧可选 Torch 2.3.1 的 23 条记录 | 当前工作环境若直接用于加载不可信模型仍有风险 | 环境维护者；训练环境按新约束重建，且不加载不可信模型文件 |

## 发布门禁判断

代码级 P0/P1 已清零，覆盖率门禁已满足。12 小时持续 soak 尚未执行（当前已完成 1000 会话 smoke），因此本报告不将 0.1.0 判定为最终可发布；须继续完成 T7.5、T7.6 和正式 soak。
