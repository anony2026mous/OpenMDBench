# MD3-11 全量质量门禁记录

## 结论

**状态：DONE。** 已完成修复后的新鲜 T4 门禁。静态质量检查均为零问题，分组全量 pytest 共 **2,111 passed**；三组覆盖率采样的合并分支覆盖率为 **85%**。系统组也已在非插桩全量 pytest 中完整通过。

本报告只证明 MD-INT-003 的质量门禁；场景参数仍为 `UNVALIDATED_BENCHMARK`，平台总体 RF-15 的 `NOT_RELEASABLE` 状态不因此改变。

## 运行锚点

- 日期：2026-09-04；工作树开始时已存在用户修改，未提交、未推送、未清理。
- 主机：Ubuntu Linux 6.8.0-136-generic；Intel Core i7-10875H；16 逻辑 CPU；38 GiB 内存。
- Python 3.11.15；Taichi 1.7.4；测试使用 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`、`MPLCONFIGDIR=/tmp/openmdbench-mpl`。
- MD-INT-003 Catalog：`sha256:21913ccc615d808df3bcbbd649020acee07acf8f5c81159167c982b37f3b2409`。
- resolved hash：L1 `sha256:ee1999063ed224776bb1a15fbe0e8bdc3a2ac3ebf2a577fb30fc339695614494`；L2 `sha256:209e386d1600874c6ecdc36850e472f8271193b77cf13e8f6ccc10f3389d4d6c`；L3 `sha256:f6edbc0d95f02c1de977824d58341294d151548974c90dd0426b75ca6e8c8c6f`。

## T4 静态门禁

| 门禁 | 命令 | 结果 |
|---|---|---|
| format | `.venv/bin/ruff format --check .` | 通过：613 files already formatted |
| Ruff | `.venv/bin/ruff check .` | 通过：All checks passed |
| strict mypy | `.venv/bin/mypy --strict openmdbench tests` | 通过：385 source files, no issues |
| Bandit | `.venv/bin/bandit -r openmdbench -q` | 通过：零输出、exit 0 |
| 编译 | `find openmdbench tests env framework model config tools -name '*.py' -exec .venv/bin/python -m py_compile {} +` | 通过：exit 0 |

## pytest 与覆盖率

为遵守单命令时限，全量 suite 按目录分组执行；没有跳过任何测试。

| 分组 | 结果 | 耗时 |
|---|---:|---:|
| `tests/contract` | 1,312 passed，1 warning | 129.23 s |
| `tests/integration` | 263 passed，14 warnings | 309.65 s |
| `tests/unit tests/determinism tests/performance tests/scenarios tests/security tests/test_import_smoke.py tests/test_project_scaffold.py` | 428 passed，29 warnings | 247.49 s |
| `tests/system` | 108 passed，55 warnings | 695.74 s |
| **合计** | **2,111 passed** | **1,382.11 s** |

警告来自 Taichi/Gym 弃用提示与 headless 字体/渲染提示；未出现测试失败、超时或非确定性失败。

使用 `coverage run --branch` 对前三个分组重新采样并合并（系统组已用常规 pytest 完整通过，未在 tracer 下重复以避免突破单命令预算）：2,003 项通过；`coverage report --show-missing --skip-covered` 合计 **39,876 statements、4,633 missed、9,262 branches、1,812 partial、85%**。这是分组覆盖率门禁证据，不能误报为系统组插桩覆盖率。

## 本轮修复与回归范围

- 恢复 MD-INT-001 Accepted ADR 记录，并修复 jamming 结束后仍有效的共享航迹恢复。
- 消除殉爆 RNG 对 session ID 的依赖；将 spatial trigger 的一次性消费状态持久化并纳入 checkpoint；将 destroyed lifecycle 改为数据驱动。
- 将本地 MMG/Taichi 运行时改为每父进程一个多句柄 worker，并为 legacy adapter 保留 owner-aware core cache。
- authority log 改为有界缓冲、关闭必 flush；mission score 热路径不再反复实体化完整 receipt 历史，审计/检查点仍保留完整账本。

相关的 targeted event/checkpoint/lifecycle 回归为 `96 passed`；通信与环境回归为 `9 passed`。兼容性、确定性、日志和 checkpoint 完整性均由上述全量分组复测。

## 风险与发布边界

- native runtime 关闭后保留一个 Python multiprocessing resource tracker 子进程；100 局顺序证据显示其不增长，作为运行监测项而非仿真资源泄漏。
- 不作真实装备标定或能力声明；参数继续标记为 `UNVALIDATED_BENCHMARK`。
- MD-INT-003 通过不改变平台 RF-15 `NOT_RELEASABLE` 结论。
