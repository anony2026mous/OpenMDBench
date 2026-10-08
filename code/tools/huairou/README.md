# 本地 Codex → 怀柔服务器 → 测试反馈

## 两个窗口，只有一个代码修改源

- **本地窗口**打开 `C:/Code/source-code`：Codex 在这里编辑、保存代码并调用同步测试工具。
- **Remote-SSH 窗口**连接 `huairou`：查看服务器文件、进程、GPU 和运行结果。它不会自动同步本地文件。
- 远端专属工作区：`/mnt/<lab>/<user>-codex/source-code`。不改动 `/root` 的现有项目，也不改动他人的目录。
- 可在远程窗口“文件 → 打开文件夹”中打开 `/mnt/<lab>/<user>-codex/source-code/current`。每次发布后刷新或重新打开目录；真实测试路径以本地日志中的固定 `snapshot` 为准。

## 日常操作（在本地 PowerShell 执行）

先切换到 `C:/Code/source-code`，保存编辑器内的文件，然后执行：

```powershell
.\huairou.cmd preview       # 仅检查范围和潜在凭证，不联网
.\huairou.cmd sync          # 上传新增/修改源码，更新远端 current，不运行测试
.\huairou.cmd smoke         # 同步后检查 Python/Torch/GPU，不代表项目测试通过
.\huairou.cmd test --profile engine
```

最后一条默认**只收集测试**；服务器需要先有兼容的项目环境。实际验证时传入需要执行的具体 pytest 路径：

```powershell
.\huairou.cmd test --profile engine -- -q tests/实际测试文件.py
.\huairou.cmd test --profile openmd -- -q tests/实际测试文件.py
.\huairou.cmd run --profile workspace --command "uname -s"
```

`run --command` 是用户明确指定的远程 Shell 命令，不是安全沙箱；不要把密码或 API key 写进命令。命令在固定快照中运行。

| profile | 远端快照中的工作目录 | Python 导入路径 |
|---|---|---|
| `workspace` | 快照根目录 | 不强制修改 |
| `engine` | `source_codes` | `source_codes` |
| `openmd` | `openmd/source-code/source_codes` | 同目录 |
| `eval` | `openmd/code/eval` | `openmd/source-code/source_codes` |

`engine`、`openmd`、`eval` 会相应设置 `OPENMDBENCH_ROOT`，避免把两份引擎混用。远程测试使用 `MPLBACKEND=Agg`，不依赖显示器。

VS Code 的**本地窗口**中也可以使用“终端 → 运行任务”，选择以 `Huairou:` 开头的任务；不要在远程窗口运行 Windows 的 `.cmd` 入口。

## Codex 的自动反馈闭环

可以直接要求本地 Codex：

> 修改这个功能，然后用 huairou 的 engine profile 运行指定测试；读取 `.huairou/logs` 的错误，在本地修复后重新同步并测试。不要启动完整训练。

同步、运行和日志回传在同一条 `test`/`run` 命令中完成。日志直接显示在本地，同时写入：

```text
.huairou/logs/<运行编号>.log   # stdout/stderr，包含远程报错
.huairou/logs/<运行编号>.json  # 源码 SHA-256 清单、快照路径、退出码
```

日志随输出刷新，失败退出码会传回本地。测试生成的模型、图片、报告等仍在远端固定快照或程序指定的目录中；**不是所有产物都会自动下载**。不要把“传输成功”当成“测试成功”。

目前没有启动常驻监听或无人值守 Codex。工具上传的是已保存到磁盘的内容；运行 `sync` 或 `test` 时同步，网络/远程操作仍可能需要授权。不要同时运行两次同步。

## 同步安全性与限制

- 本地源码是唯一修改源：默认包含根 `readme.md`、`source_codes`、`openmd`、`role_c_toolkit`，包含未提交的新源码。
- 仅传 `config.json` 中列出的文件类型；排除 `.git`、私钥、`.env`、虚拟环境、缓存、报告、日志、检查点、输出目录及链接/junction。
- `include_files` 另行精确允许主实验所需的三份 `_w1_runs/rl/theta_*.npz` 和 `role_c_toolkit/assets/mappo_medium_s42_best.pt`，均为项目已有策略权重，不是新训练。其余 `_w1_runs` 内容仍排除；明确文件清单仍检查大小、凭证名称和父级链接，不全局放开 `.npz`/`.pt`。
- 凭证内容启发式检测只是额外保护，**不是完整的秘密扫描**；首次同步前务必检查目录范围。
- 超过 20MiB 的单个候选文件会中止，要求明确审核。需要的输入数据、模型权重或被排除的测试夹具需单独批准并配置，不能假定已经上传。
- 首次上传全量筛选后的源码；后续只上传内容哈希发生变化的文件。删除的本地源码不会出现在新快照，但不删除旧快照。
- 服务器把未变文件复制到新快照，**不使用共享硬链接**。启动中的任务保留旧版本，不会被同步覆盖。发布前对全部源码验证 SHA-256。
- 如果远端源码被手动编辑、旧快照丢失，增量校验会拒绝发布；保留有用远端改动后，使用 `sync --full` 或 `test --full ...` 建立新的全量快照。
- 不会自动清理旧快照或远端实验数据；频繁测试会占用磁盘，需要定期人工核对清理。
- SSH 使用已有 `huairou` 别名、密钥和严格主机校验；不会复制私钥到服务器，也不会修改 SSH 配置。
- `.huairou/` 已加入 Git 忽略。日志也可能含应用输出的敏感信息，不要随意分享。

## 服务器项目环境

- 系统 Python 3.8 保持不变；项目使用隔离环境 `/mnt/<lab>/<user>-codex/envs/openmd-py311`（Python 3.11.16）。
- `config.json` 的 `remote_python` 已指向该环境，`test`、`smoke` 使用它。`sync` 只同步文件；`run --command` 原样执行命令，运行 Python 脚本时应明确写出该解释器的绝对路径，不要默认 `python3` 已切换。
- 已安装项目 core/dev/server 依赖、训练辅助依赖和 CPU 版 `torch 2.14.0`。Taichi 使用 `1.7.3`，因为 `1.7.4` 要求比服务器 Ubuntu 20.04 更高的 GLIBC。
- 主实验 CPU 仿真还需要 SciPy；已按 `role_c_toolkit/requirements-windows-py311.snapshot.txt` 补齐 `scipy==1.17.1`。需要验证的是策略推理与仿真，不启动策略训练。测试可限制 `OMP_NUM_THREADS`、`OPENBLAS_NUM_THREADS`、`MKL_NUM_THREADS` 防止多进程过度占用 CPU。
- 当前验证环境安装的是 CPU 版 Torch，尚未验证 GPU 项目测试或大模型服务。不能仅凭驱动 535 和 `nvidia-smi` 显示 CUDA 12.2 就判定所有较新 CUDA 12.x 软件不可运行：NVIDIA 提供有条件的小版本兼容，具体还受 PTX、内核、运行时等限制。模型推理应使用独立环境并验证实际依赖与 CUDA 工作负载；不要替换系统 Python、驱动或系统 Torch。
- VS Code Remote-SSH 如果当前打开 `/root`，可直接打开快捷目录 `/root/huairou-project`；它指向 `/mnt/<lab>/<user>-codex/source-code/current`。`current` 会随每次同步切换到新快照，所以测试日志中的固定 `snapshot` 路径才是某次测试的精确代码版本。

版本不满足时，`test` 明确返回退出码 **86**，不会假装 pytest 已经运行。

## 千问部署与验收（2026-09-30）

- 项目 `openmd/code/llm_client_hifi.py` 默认服务模型名为 `Qwen3.8-27B`，请求携带 `chat_template_kwargs: {enable_thinking: false}`，默认 temperature 为 0.1、输出上限为 512 token；实际调用方可以覆盖这些值。
- 既有接口 `http://172.18.116.170:8000/v1/models` 返回模型名 `Qwen3.8-27B`、权重路径 `/model`、`max_model_len=131072`。这不能证明其精度、权重修订、GPU 并行配置或其他服务端采样默认值，不能据此宣称新部署完全复现原服务。
- 官方 `Qwen/Qwen3.8-27B` 元数据参数量为 27,781,427,952；官方权重为 BF16。用户随后确认原服务使用 BF16 主权重，故当前目标明确为 BF16（不再沿用最初 FP16 表述），仅 KV cache 为 FP8。
- 怀柔实测 4 张 RTX A6000，每张总显存 49140 MiB、空闲 48666 MiB，驱动 535.183.01。三份模型仅 FP16 权重估算约 155.24 GiB，每份约 51.75 GiB，因此不能一张 48 GiB 卡部署一份完整 GPU 驻留的 FP16 模型。关闭思考不缩小模型权重。
- 三份独立副本需要跨卡切分或 CPU offload 等方案，并为每个进程的 KV cache、执行缓冲和通信留余量。4 卡共享三份副本不等于互不抢占，尤其不可仅用权重总量判断 131072 上下文是否可用。CPU offload 会改变延迟；不要未经同意降低上下文、精度或更换模型。
- 如果目的是三个实验同时访问，可先考虑一份跨卡模型服务处理三路请求，而非三份权重；吞吐和延迟仍须压测。现有 hifi 客户端声明的并发上限为 2，不能把这个进程内限制当成跨进程的全局限流；本轮未修改客户端并发代码。
- 两份独立 BF16 推理实例已启动并通过短流程验收：GPU 0/1、2/3 各 TP=2，分别监听服务器本机 `127.0.0.1:8001/v1`、`127.0.0.1:8002/v1`。共用一份已完整下载并校验的 18 分片权重；未训练模型、未修改 GPU 驱动或系统 Python。项目原参考端点仍保留为默认值，使用新服务时显式选择地址。

### 消融一致性补充核查

原服务 `/version` 与 `/metrics` 的实际只读观察已保存至 `qwen_reference_baseline.json`：

| 项目 | 原服务或冻结实验配置 |
|---|---|
| vLLM | 0.27.1 |
| 上下文上限 | 131072 token（输入与输出合计受上限约束） |
| KV cache 精度 | fp8 |
| 动态计算 KV scales | false；具体 scales 值/来源尚未确认 |
| Prefix caching | false |
| GPU memory utilization | 0.92；相同比例不代表相同缓存容量 |
| 报告的 KV 容量 | 445946 token，engine=0；不是模型上下文上限 |
| Mamba SSM cache 精度 | float32；Mamba cache dtype 为 auto |
| Role-C 冻结消融请求 | temperature=0.1、max_tokens=1024、enable_thinking=false |

用户提供原服务信息：主权重 BF16、不做权重量化、18 分片、约 54 GB，宿主机目录 `/home/<user>/.cache/modelscope/models/Qwen--Qwen3.8-27B`；原硬件为两张 A100-PCIE-40GB，TP=2。该目录不在怀柔主机上。官方 ModelScope 清单也列出 18 个权重分片，总字节数为 55,563,006,776；下载按每文件固定修订和 SHA256 校验，但尚未与原主机文件哈希逐一比对。

权重/分词器修订、实际 KV scales、未指定采样参数的服务端默认值、实际内核等仍需进一步比对。原服务没有公开 `/server_info` 路由。A100 与 A6000 是不同硬件，不能直接把两台机器的延迟差解释成消融算法效果；所有新实验臂需保持同一服务与调度条件。

GGUF 是模型文件格式，不代表无损量化。F16/BF16 GGUF 仍为 16 位，单换容器通常不会大幅减少权重显存；Q4/Q8 等量化改变数值表示，不能承诺与原模型输出或消融条件完全一致。原模型转 GGUF 并更换推理引擎也可能改变内核、模板或数值行为。本任务不自动采用这些变更。

两个进程可读取同一份只读权重目录，避免磁盘存两份权重，不改变权重内容；两份独立实例的 GPU 权重和运行缓存仍需分别分配。磁盘去重不等于显存减半或吞吐翻倍。KV 参数应对齐原服务的 FP8 与 scales/状态缓存配置，不能擅自改成 FP16 或缩短上下文。精确容量与长上下文并发需在两套实例上分别验收，不能只把模型加载成功当成满足原配置。

严格复现还要固定所有实验臂的请求构造、采样配置、服务端默认 generation_config、版本和请求调度策略。相同设置不承诺随机采样输出逐字相同；如后端或硬件无法保持可比条件，应明确报告，并在统一新基线上重新运行相关对照，而不是混用历史结果。

核查来源：

- https://huggingface.co/Qwen/Qwen3.8-27B
- https://huggingface.co/api/models/Qwen/Qwen3.8-27B
- https://recipes.vllm.ai/Qwen/Qwen3.8-27B
- https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html

### 单份权重下载与双实例复用

- 唯一共享模型目录：`/mnt/<lab>/<user>-codex/models/Qwen3.8-27B-BF16`。两个独立进程使用同一路径，不下载两次，也无需复制目录。只有磁盘文件共享，GPU 权重与运行缓存仍分开。
- 下载脚本：`tools/huairou/download_qwen_weights.py`，远程副本位于 `/mnt/<lab>/<user>-codex/services/qwen/`。使用文件锁避免重复下载，支持 `.partial` 续传，逐文件校验 SHA256，已存在但哈希不符的文件会拒绝覆盖。
- 清单：远程服务目录的 `qwen-modelscope-source-manifest.json`；来源记录为原仓库候选快照，不冒充已比对的原主机权重。
- 进度日志：`/mnt/<lab>/<user>-codex/services/qwen/logs/model-download.log`。只有模型目录的 `download-complete.json` 显示 `all_files_sha256_verified`，才能称下载完整；服务是否可用还要另行检查。
- 初始推理环境 `qwen-vllm0271`（Python 3.11）已完成安装，双卡 BF16 矩阵运算通过，但实际 vLLM 启动被 FlashInfer 的 `array.array[int]` 类型注解兼容问题阻止。已验证 Python 3.12.14 支持该表达式，后续推理环境改为 `/mnt/<lab>/<user>-codex/envs/qwen-vllm0271-py312`，不修改第三方库源码，也不改项目 CPU 测试环境。
- 官方 vLLM 0.27.1 CUDA 12.9 轮子已在本机与服务器核对 SHA256。核心依赖版本从初始环境冻结复用；Python 3.12 的 setuptools 约束按轮子要求改为 `>=77.0.3,<81`。相应安装日志为服务目录的 `logs/install-cu129-py312.log`；依赖安装成功不等于推理服务已验收。
- `start_qwen_service.py --replica a` / `--replica b` 分别启动 GPU 0/1、2/3 上的独立进程，绑定服务器本机 `127.0.0.1:8001/8002`，共享权重目录。启动器检查完整下载标记、清单身份和文件大小，不覆盖活跃实例；实际健康、非思考输出和缓存一致性仍需验收。
- 启动器显式设置虚拟环境 `PATH`/`VIRTUAL_ENV`，使 JIT 能找到已安装的 ninja；CUDA_HOME 指向项目独立的 `tools/cuda-12.9`，不再使用缺失 nvcc 的 `/usr/local/cuda`。`install_cuda129.py` 从 NVIDIA 官方固定组件包安装 nvcc 12.9.86、cudart 12.9.79、CCCL 12.9.27，校验 SHA256 并编译 sm_86 小内核；不安装或更改驱动。
- cuRAND 开发头文件复用已安装的 `nvidia-curand-cu12==10.3.10.19`，通过 CPATH 提供给 JIT；FlashInfer 缓存限定在专属服务目录，不修改第三方库源码。`preflight_qwen_runtime.py` 已在两张卡实际通过 BF16 矩阵运算和 FlashInfer 采样，证据在服务目录 `flashinfer-preflight.json`；这仍不等于整个模型服务已经通过。
- 服务就绪后使用 `probe_qwen_service.py` 检查真实非思考短回答、模型上下文和关键 KV 指标。若缓存容量与参考服务不同，会返回失败并记录差异，不把额外显存自动分配冒充相同消融配置。

### 当前服务用法与已完成验证

- 两实例均已真实返回非思考回答；BF16 权重、FP8 KV、131072 上下文及已知缓存参数核查通过。A6000 自动分配曾为 406 块/611669 token，在确认相同 1568-token 块布局后显式限制为原服务的 296 块/445946 token。块数选择机制与原机自动分配不同，但有效缓存容量已对齐。
- CPU 主实验接线验证 9/9：三个场景 × `rule`、`rule-rl`、`rl`，每项 12 tick。新千问验证 12/12：实例 A 的三个场景 × 三类 LLM 臂共九项，实例 B 的 IE-10 三类 LLM 臂共三项，每项 6 tick。已核对实际端点、temperature=0.1、有效 max_tokens=1024、关闭思考、无解析失败或规则回退；组合 RL 臂显式 strong 档位，其他臂与正式入口一样不覆盖该参数。
- 最终证据为服务器 `validation/readiness-audit-20260930.json`，本地副本 `.huairou/logs/readiness-audit-20260930.json`。采用 `llm-main-smoke-20260930-*-strong-v2` 的修正后结果；较早的非 v2 目录已标记为被替代的诊断记录，不作为最终验收或正式实验数据。
- 这些是有限 tick 的功能测试，未运行完整 seed 集、自然终局主实验、训练或 131072-token 满长并发压测。原主机权重/分词器哈希和未公开的服务参数未全部比对，不能将此报告解释为严格历史复现或正式消融成绩。

本地 Codex 用 `huairou.cmd run` 在服务器执行测试时，设置 `ROLEC_LLM_BASE_URL=http://127.0.0.1:8001/v1` 或 `8002`，沿用既有自动同步和日志回传流程。`127.0.0.1` 此时指服务器；直接在 Windows 本地运行客户端则需要 SSH 转发，例如手动在本地终端执行：

```powershell
ssh -N -L 127.0.0.1:18001:127.0.0.1:8001 -L 127.0.0.1:18002:127.0.0.1:8002 huairou
```

转发保持开启时，本地客户端分别使用 `http://127.0.0.1:18001/v1`、`http://127.0.0.1:18002/v1`。当前服务为已启动的后台进程，不是开机自启配置；重启服务器后须按状态检查和启动流程恢复。
- P0 短流程工具现在沿用主实验已有的 `ROLEC_LLM_BASE_URL` / `ROLEC_LLM_MODEL` 环境变量约定，默认仍为原参考服务。测试新服务时显式指定目标；禁止把参考服务测试冒充新服务测试。

## 让本地 Codex 根据服务器反馈修复

在本地 Codex 会话直接指定功能和测试目标，例如：

> 修改指定功能；先 preview，再用 huairou 的 engine profile 运行 tests/unit/test_training_smoke.py；读取本地回传日志，修复后重新同步同一测试。最多三轮；遇到环境、显存或服务不可用就报告，不修改 GPU 驱动、不启动完整训练。

对应命令（本地 PowerShell）：

```powershell
.\huairou.cmd preview
.\huairou.cmd test --profile engine -- -q tests/unit/test_training_smoke.py
```

`run` 执行评估脚本时使用 `/mnt/<lab>/<user>-codex/envs/openmd-py311/bin/python` 的绝对路径；脚本路径和参数必须来自当前实际任务，不能直接触发未审核的长实验。服务端 vLLM 日志并不自动包含在测试日志里，需要另外通过 SSH 读取对应服务日志；推理服务也不会因为代码同步自动重启。

## 本地工具自检

```powershell
& .\source_codes\.venv\Scripts\python.exe -m unittest discover -s tools/huairou -p test_remote.py -v
```

入口优先使用本地 `source_codes/.venv/Scripts/python.exe`；也可以用环境变量 `HUAIROU_LOCAL_PYTHON` 指定 Python 3.10+。Windows `.cmd` 入口不更改 PowerShell 执行策略。
