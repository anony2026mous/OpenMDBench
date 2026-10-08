# Windows 原生实验虚拟环境

创建日期：2026-09-24。按用户授权，使用现有 Python 创建工作区 `.venv`，没有修改全局 Python 或源引擎。

## 环境

- 基础解释器：`D:/python3.11/python.exe`，实际 `sys.version` 为 **3.11.0rc2**，Windows x64。
- 虚拟环境：`D:/Harness workspace/source-code-New-architecture/.venv`。
- `include-system-site-packages = false`，不会继承其他 Python 的已安装包。
- `.gitignore` 已排除 `.venv/`；依赖版本记录在同目录 `requirements-windows-py311.lock.txt`。
- 安装引擎 `pyproject.toml` 中的 core 依赖及测量/评测所需 SciPy、dill、requests。grid 的包入口会导入 MAPPO，因而另外需要 CPU 版 PyTorch；不运行训练。
- Python 仍是预发行版。`pyvenv.cfg` 的简写 `3.11.0` 不能替代 `sys.version` 的真实版本；后续实验 manifest 必须保留 rc2 信息。

## 已执行验证

1. 核心依赖安装后 `pip check` 返回 `No broken requirements found`。
2. NumPy、SciPy、Pydantic、PyProj、PyYAML、Gymnasium、dill、Taichi、Matplotlib 导入成功。
3. 使用当前 4.0 引擎自带 `_w1_smoke.py`，运行 `IE-01-SINGLE-TARGET --ticks 2 --seed 100`：场景编译、会话创建、两个 tick 推进、评分回执及关闭均完成，进程退出码 0。Taichi 使用 CPU x64。
4. 初次测量测试执行了 36 项，grid 集成测试类初始化因缺少 torch 失败；这是依赖问题，不是回放断言失败。随后从 PyTorch 官方 CPU 源安装 `torch==2.14.0+cpu` 及依赖，复测 **42/42 项通过**，最终 `pip check` 仍无冲突。

以上只证明当前依赖和 IE-01 的有限冒烟可运行，不代表 IE-01～IE-08 完整实验、长期运行或跨平台确定性已经验证。

## 使用方式

无需激活，也无需改变 PowerShell 执行策略。工作区根目录直接执行：

```powershell
& '.venv/Scripts/python.exe' -B -m pip check
& '.venv/Scripts/python.exe' -B -m unittest discover -s role_c_measurement -p 'test_*.py' -v
& '.venv/Scripts/python.exe' -B 'D:/Harness workspace/source-code-4.0/source-code/openmd/code/eval/_w1_smoke.py' IE-01-SINGLE-TARGET --ticks 2 --seed 100
```

可选激活：`& '.venv/Scripts/Activate.ps1'`。如果本机策略阻止脚本，继续使用上述解释器绝对/相对路径即可，不必放宽系统策略。

环境采用 Windows cp311 安装包，不复用旧 `.obm4_runtime` 中的 cp313 二进制包。以后的新实验应显式使用 `.venv/Scripts/python.exe`，并把此环境与旧 Python 3.13 批次区分记录，不混称同一运行时。

版本清单包含 CPU 专用 torch。重建时需先从 `https://download.pytorch.org/whl/cpu` 安装该 torch 版本，再安装清单中的其余依赖；普通镜像未必提供带 `+cpu` 标记的包。本次没有安装 openmdbench 为全局包，现有冒烟入口通过源路径加载引擎。
