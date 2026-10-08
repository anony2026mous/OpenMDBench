# MD-AD-002 v2 平衡参数变更

| 场景 | 配置版本 | 新配置哈希 |
|---|---|---|
| EASY | 2.0.0 | `sha256:1adaa81c574ffa6a0e05c88be0da7029d45d5f24a1fa73d3ef2ad20065c81f16` |
| MEDIUM | 2.0.0 | `sha256:1dd96cc3b5f0d0103a69745af12ae0de51361eb8d93a1d4a3dac48237ce8a5e4` |
| HARD | 2.0.0 | `sha256:9a057519c2a6f53d0cf5d4d9073a4c7b9ad9976d1228e6b846505d9a49f8bc42` |

正式参数从每机6发、damage=0.6调整为每机12发、damage=1.0。射程、命中率、
cooldown、CIWS和突破规则未改变。旧参数位于
`openmdbench/config/profiles/md_ad_002_resource_tight_v1.yaml`，仅用于压力测试。
三个正式文件分别为 `md_ad_002_easy_v2.yaml`、`md_ad_002_medium_v2.yaml` 和
`md_ad_002_hard_v2.yaml`。

本变更由需求方在 2026-08-17 明确批准，依据为旧组合无法满足至少13个目标在
8 km外终止的资源下界。参数仍是任务级比赛假设，不代表真实装备性能。
