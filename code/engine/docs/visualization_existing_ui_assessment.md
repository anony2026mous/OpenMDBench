# Legacy Matplotlib 界面基线盘点

> 本文只保留为早期 T6 兼容验收证据。当前 V2 已提供
> `VisualizationFrameV2` 、`MatplotlibRendererV2` 和 `replay-v2`；新开发请阅读
> `docs/OpenMDBench_用户操作手册与场景智能体开发指南.md`。

## 结论

早期基线审计时，仓库没有可运行的 Matplotlib GUI、动画入口或回放播放器。当时全仓检索未发现
`pyplot`、`FuncAnimation`、Slider/Button 控件或自定义 Artist 管理代码；因此 T6.8
将是基于既有可复用数据/外型资产的新 renderer，而不是对一个隐藏窗口入口的改写。
这也避免为满足“复用现有界面”而虚构不存在的实现。

## 入口与数据来源

- 旧入口集中在 `env/navigation_env.py` 等 Sim2Sea/Taichi 训练环境，只提供 Gym
  观测、BEV 数组、轨迹 field 和地图障碍物，并不创建 Matplotlib Figure。
- `env/map_loader.py` 能读取旧的多边形地图数据并施加坐标偏移，可作为静态地图
  数据适配来源，但其 Python 字面量格式不应直接成为新版 renderer 的公开契约。
- 新接口的数据来源应统一为 T6.2 的 `VisualizationFrame`。实时 WorldState 和 JSONL
  回放分别经 T6.3/T6.5 适配，renderer 不直接访问 Taichi field 或裁判内部状态。

## Artist 生命周期与图层

当前没有既有 Artist 生命周期可以继承。T6.8 应建立并复用以下对象：静态地图
Collection 只创建一次；实体、contact、传感器、通信和轨迹按稳定 ID 更新；事件、
任务和得分面板更新已有文本/线条对象。不得逐帧 `axes.clear()` 或重建全部 Artist。

可直接复用 `openmdbench.visualization.profiles` 及四域/民船的 Matplotlib `Path` 工厂。
这些外型以北向为局部零航向，现有 transform 已实现世界坐标缩放、顺时针航向旋转
和平移。T6.7 在此基础上补阵营色、状态样式、最小可见尺寸和主题。

## 播放控制与线程模型

当前没有播放、暂停、单步、倍速、跳转或时间轴控件，也没有 GUI 线程模型。
新播放器应让所有 Matplotlib Artist 更新发生在主 GUI 线程；实时输入或日志预取可在
后台线程/队列中进行，但只能向主线程投递已验证的不可变 frame。无界面测试使用
Agg backend，不启动线程。

回放控制的建议接口为 `play()`、`pause()`、`step()`、`seek(timestamp)` 和
`set_speed(multiplier)`。未压缩 JSONL 的 seek 使用 T6.5 字节索引，gzip 只支持顺序
读取或从头扫描。

## 已有地图与坐标适配

旧地图加载器输出二维多边形并可能施加正坐标偏移；场景 schema 则提供明确世界
bounds 和 map_id。迁移时应把旧多边形一次性转换到场景世界坐标，记录 offset/投影
元数据，再生成静态 Collection。renderer 不应重复投影，也不得依赖旧哈希网格。

## 复用项

- 五类实体的原创 Matplotlib Path 与方向/尺度变换。
- 旧地图多边形解析和坐标偏移算法，可通过独立适配层复用。
- 旧环境的轨迹、障碍物和 BEV 数据含义，可用于转换测试和行为对照。
- Agg 后端的外型测试模式，可扩展为 renderer 无界面回归测试。

## 必要适配点

- 冻结独立的 VisualizationFrame/Pydantic/JSON Schema，取代 Taichi/Numpy 内部对象。
- 实现 referee、blue、red、public 视角适配，并在适配层完成信息过滤。
- 建立稳定 ID 到 Artist 的缓存、静态地图单次绘制和分层可见性开关。
- 增加 JSONL writer/reader/index、实时与回放 adapter、播放控制和诊断信息。
- 保证普通回放路径不导入 Taichi 或仿真内核，并对大日志采用流式读取。

## 不纳入首版

Web 前端、WebSocket/SSE 和 3D 渲染仍是可选扩展；T6–M7 的必需交付保持为
Matplotlib 实时调试与标准 JSONL 回放。
