# E1 交接导出修复与交付说明

日期：2026-10-04，北京时间。

## 修复范围

原导出程序在 `python -m pip freeze` 处失败，原因是远程引擎虚拟环境未安装 pip。此次用独立后处理程序的 Python 标准库 `importlib.metadata.distributions()` 采集已安装依赖名称和版本，未安装或升级任何包，未修改冻结的实验程序、引擎、场景、门禁和统计结果。

采集到 61 个安装分发包，包内提供 `runtime.json` 和 `requirements-environment.txt`。这是原引擎环境的名称/版本快照，包含平台相关依赖，不是跨平台求解锁文件，也不包含独立 vLLM 服务环境的完整依赖或 pip editable/direct-URL 来源信息。

## 完成与校验

远程程序已于 **2026-10-04 01:50:15** 写入 `paused-after-calibration-and-gates`。校准 960 局、门禁 200 局、确认 0 局；没有新增仿真、LLM 请求或自动启动确认。

中断时已经复制的 5,749 个文件逐一与原数据/源文件核验一致；修复前的失败状态保存在 `recovery/output-r01/previous_status.json`，原失败日志继续保留。新增依赖快照、README 和恢复记录后，交接包含 5,753 个内容文件及一份交付 manifest，总计 5,754 个 ZIP 成员。

全部 ZIP 成员 SHA256、manifest 内容及 CRC 校验通过；原冻结接收端工具 `verify_bundle` 验证通过，条件分工与 seed 契约不变。

交接 ZIP 大小：**74,894,103 字节**。

ZIP SHA256：

`76b53bd767f4d616c3633b8ba9a39ccac8f042b14b47f838e4fe4295e995b037`

## 交付位置

远程交接包：

`/root/openmd/runs/E1_partial-direction_split_p01_20261003/E1_v13_handoff_r01.zip`

远程校验信息：同目录 `handoff_verification.json`。

本地独立交付目录：

`D:/Harness workspace/migration-prep/gitlab-snapshot/experiment-deliveries/E1_handoff_20261004_v1/`

该目录提供 ZIP、远程校验信息、README、暂停状态、本地校验记录。ZIP 无需在 Windows 上展开；本地按压缩流校验全部成员，避免 Windows 长路径问题。另一台 Linux 服务器解包后，按 README 执行模型/资产核验，再人工启动 `device-b` 的数量19→27确认。

当前设备的数量17→18也仍等待人工启动，不随导出修复自动开始。

此次完成的是交接工程修复，不改变门禁结论：D1未认证、D1′未通过、D2校准通过、D3规则执行器通过而RL执行器未通过。所有结果仍在包内，不把打包成功等同于理论门禁通过。
