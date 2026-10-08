# Grid complex四栈补实验

授权范围：2026-10-06补实验清单的实验1，仅1号服务器；4栈×5个环境seed，共20局。没有启动实验2，不训练，不修改冻结引擎／场景／提示词／GOAI策略。

正式条件：complex，continuous，150步；Rule、Pure MAPPO、LLM+heuristic、LLM+MAPPO；seed63101–63105。冒烟seed63001，4个完整局单独保存。两个MAPPO路径使用指定medium权重，SHA256必须为223dbf740163b652f221a6ef0885d69b8c975c53378a7e63c05388e1df8cd0a8。LLM为Qwen3.8-27B，规划间隔10、temperature0.1、4096tokens、关闭思考、原生NL提示词。Rule沿用旧Grid P1包装的规划间隔10，而非未包装原agent默认5；协议显式记录这一区别。

主V沿用旧Grid P1的原生blue_score，SR为mission_success。另保存MetricEngine的10指标综合分作为明确标注的次指标，不偷偷替换主V。两个固定配对为LLM+heuristic−Rule与LLM+MAPPO−Pure MAPPO，20000次同seed配对bootstrap，95%百分位CI。

程序不择优重跑；有效输局、差计划、原部署解析fallback均保留。仅进程／原生Python异常／wall-timeout允许有限工程重试，最多2个attempt，原文件不覆盖。正式结果有不合格执行器审计时保留分数并标注。Native MAPPO控制器隐式None及其捕获异常、actor实际前向、GOAI接受情况和LLM原始HTTP响应均记录。

目录根为`/root/openmd/runs/P0_GRID_COMPLEX_LAYERED_20261006_p01`。代码和协议、冒烟、正式选择索引、逐attempt原始数据、analysis/a01、reports/r01、logs分开。每个已完成attempt有文件哈希，resume只读取身份和协议匹配且哈希一致的结果。锁防止两个调度器重复开启同一批次。

准备后执行：

```bash
PY=/root/openmd/releases/gitlab-ccabad00154e/.venv/bin/python
ROOT=/root/openmd/runs/P0_GRID_COMPLEX_LAYERED_20261006_p01
SCRIPT="$ROOT/code/grid_complex_campaign.py"
$PY -B "$SCRIPT" smoke --root "$ROOT"
$PY -B "$ROOT/code/test_grid_complex.py" --root "$ROOT" --native
$PY -B "$SCRIPT" run --root "$ROOT"
$PY -B "$SCRIPT" status --root "$ROOT"
$PY -B "$SCRIPT" analyze --root "$ROOT"
```

正式运行要求真实冒烟和原生被动等价验证均通过。run内置断点恢复，仍保留各attempt。4路LLM分两端点各2路，另2路纯基线；所有数值库单线程，不改变模型服务、不挤占他人作业。

逐局原始文件位于`attempts/confirmation/<arm>__s<seed>/attempt-01/`（若工程重试则另有attempt-02）；确认选择索引在`confirmation/<arm>__s<seed>/selected.json`。`requests.jsonl`保留真实请求参数和服务完整响应，`events.jsonl`保留逐步公开观测、原生动作及离线状态，`goals.jsonl`保留原生目标和接受回执。真值状态仅为离线日志，不加入模型输入；日志没有额外调用观测／传感器，不改变随机流。

报告脚本支持负数、CI含零、缺失局；5个环境seed不能声称5个独立训练模型，complex迁移比较也不能唯一归因于D1′。不为获得预期方向调整冻结参数或删除反例。
