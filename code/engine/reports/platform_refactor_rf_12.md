# RF-12 阶段报告：场景工具

- ScenarioPackageRef 新增确定性 `.omdpkg` 打包。
- unpack 在写入前校验绝对路径与 `..` 穿越，解包后复核 content hash。
- 正式场景包入口公开为 `formal_package_ref`，供 CLI/SDK/Gateway 复用。
- pack/unpack hash 一致与恶意压缩路径拒绝测试通过。
- 既有 CLI 继续提供 formal selftest/live/replay；完整 create/validate/resolve 子命令保留为后续易用性扩展。

结论：安全包格式核心通过；完整场景创作 CLI 尚未达到计划中列出的全部易用性目标。
