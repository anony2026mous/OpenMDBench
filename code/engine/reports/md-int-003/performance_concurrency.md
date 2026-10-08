# MD3-11 性能、并发与资源记录

## 结论

**状态：DONE。** 三档 1,500 tick 单会话均满足平均 tick ≤100 ms；16 和 32 个隔离 session 均完成；使用公开 `FormalRuleAgentTeamV2` 规则策略完成 100 局、每档至少 30 个 seed 的长稳证据。所有结果为 passed，没有通过降低 fidelity、丢 tick 或跳过关闭检查取得结果。

## 环境与方法

- 日期：2026-09-04；Ubuntu Linux 6.8.0-136-generic，Intel Core i7-10875H，16 逻辑 CPU，38 GiB 内存；Python 3.11.15，Taichi 1.7.4。
- headless、无 renderer；每个 session 由公开规则智能体完整推进。单会话记录每个完整 `session.step` 延迟；批量/并发还采样父进程与原生 worker 树的 RSS、线程、FD 和子进程数。
- 原生 MMG 运行时为“每父进程一个多句柄 worker”；每个 world 的船舶状态按句柄隔离，关闭后释放 world 侧资源。

## 单会话 1,500 tick

| 档位/seed | 总耗时 s | tick/s | mean ms | p50 ms | p95 ms | p99 ms | active RSS B | released RSS B |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| L1 EASY / 4000 | 120.872 | 12.409 | 74.418 | 72.502 | 77.477 | 79.992 | 468,328,448 | 235,208,704 |
| L2 MEDIUM / 3001 | 127.106 | 11.801 | 78.267 | 78.386 | 88.630 | 99.157 | 460,443,648 | 227,082,240 |
| L3 HARD / 3002 | 127.199 | 11.793 | 78.312 | 78.446 | 88.714 | 100.901 | 459,534,336 | 226,738,176 |

验收阈值为平均 tick ≤100 ms，三档均满足。L3 的短暂 p99 100.901 ms 被如实保留；它不是平均阈值失败，也未被“显示端丢帧”掩盖。

## 并发隔离与资源

| 会话数 | 结果 | 每会话 tick | active RSS B | active threads / FD / child | close 后 RSS B | close 后 threads / FD / child |
|---:|---|---:|---:|---:|---:|---:|
| 16 | passed | 2 | 385,957,888 | 53 / 22 / 2 | 152,633,344 | 17 / 12 / 1 |
| 32 | passed | 2 | 402,423,808 | 53 / 22 / 2 | 169,684,992 | 17 / 12 / 1 |

证据：`artifacts/md-int-003/md3_11_concurrency_16_v3.json` 与 `md3_11_concurrency_32_v3.json`。各 session World 实例彼此独立且均到达 tick 2；与旧的“每 session 一套 Taichi runtime”相比，资源不再随会话数线性爆炸。close 后余下的一个 child 是 Python multiprocessing resource tracker，不保存仿真 world，且下述 100 局中没有增长。

## 100 局稳定性与每档 seed 覆盖

十个批次每批十局、每局完整 1,500 tick，均为 `passed`：

| 难度 | 局数 | seed 范围 | mean step ms | 最大 active RSS B | 最大 released RSS B |
|---|---:|---|---:|---:|---:|
| L1 | 40 | 8000–8009、8020–8049 | 79.693 | 487,137,280 | 253,972,480 |
| L2 | 30 | 9000–9029 | 77.790 | 483,532,800 | 250,433,536 |
| L3 | 30 | 10000–10029 | 80.096 | 484,659,200 | 251,334,656 |
| **总计** | **100** | **三档各 ≥30** | **79.145** | **487,137,280** | **253,972,480** |

对应 artifact：`md3_11_batch_w1-l1_v8.json`、`w1-l2_v8.json`、`w2-l3_v8.json`、`w3-l2_v8.json`、`w3-l3_v8.json`、`w4-l1_v9.json`、`w4-l2_v9.json`、`w5-l3_v9.json`、`w5-l1_v9.json`、`w6-l1_v9.json`。100 局均完成到 tick 1,500；峰值 active 资源保持在约 0.49 GB、53 threads、22 FD，关闭后为 1 child/17 threads/12 FD，未观察跨局累计增长。

批次墙钟时间包含 native worker 初始化和 close；表中的 `mean step` 只量化完整仿真 step。实时 renderer 未参与这些 headless 性能结论，因而不将显示吞吐误报为仿真倍率。

## 风险与边界

- native resource tracker 的一个常驻子进程是基础设施行为，应纳入长期部署监控；当前 100 局证据不支持将其归类为泄漏。
- 参数为 `UNVALIDATED_BENCHMARK`；本报告没有真实世界性能或装备能力声明。
- 性能通过不改变平台 RF-15 `NOT_RELEASABLE` 状态。
