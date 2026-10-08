# MD-AD-002 frozen system baselines

`medium-v2-golden.json` 是既有 `artifacts/md-ad-002/medium-v2-golden.json` 的逐字节迁移副本，原工件修改时间为 2026-08-19 11:57:34 +08:00，早于 RF-00R3。RF-00R3 没有运行搜索 seed、重采样或用修复后输出重写期望。

- fixture SHA-256：`1b03619e58e9123efab375eb89af9fc03b7fbceb236407a654cda8ef1948680c`
- scenario：`MD-AD-002-MEDIUM`
- seed：`0`
- config version：`2.0.0`
- config hash：`sha256:1dd96cc3b5f0d0103a69745af12ae0de51361eb8d93a1d4a3dac48237ce8a5e4`

系统测试必须先校验当前配置哈希，再比较完整终局和评分字段。配置有意变化时需要新的 Accepted ADR、配置版本和独立基线工件，不得原地修改本文件掩盖回归。
