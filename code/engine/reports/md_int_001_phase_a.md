# MD-INT-001 Phase A 验收报告

- 状态：PASS
- 日期：2026-08-06
- 完成任务：I001-A01、A02、A03、A04

## 产物

- `reports/md_int_001_existing_implementation_audit.md`
- `docs/decisions/ADR-MDINT001-001` 至 `008`
- `openmdbench/config/md_int_001_v1.yaml` 与严格 schema
- `reports/md_int_001_weihai_site_selection.md`
- `reports/md_int_001_weihai_site.png`

## 地图与地点

- 地图 ID/version：`weihai_v1` / `1.0`
- WGS84 hash：`1f78cfaf98e12d3b50cd595e58e103f4c31ef3ce71b433ba276c3afa1694b675`
- XY hash：`6b62aa3d3434a8de27f11bdb22627c42c1d5b930c835cfbf77ce37465a00c067`
- 入口：`benchmark_harbor_entry`，刘公岛东侧近海，`122.220521637°E, 37.498906006°N`
- 部署：2蓝UAV、1蓝USV、1蓝岸基雷达、1红UAV；雷达陆地和USV水域自动验证通过。

## 测试

阶段命令覆盖配置契约、现有坐标基线、场址几何、场景加载和全部36场景回归；联合回归18 passed、
0 failed、0 skipped。Ruff 和 strict mypy 通过。精确阶段命令在本报告归档后复跑。

## 已知边界

Phase A 只冻结规则、配置和地点。真正局部米制 GeoFrame、offset 对称转换、地图运行时 identity 和
Sim2Sea 碰撞闭环属于 B00，尚未报告为已实现。
