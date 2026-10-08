# MD-INT-001 I001-B03 实施报告

状态：完成。

- 新增薄适配器 `openmdbench.domains.surface.mmg_adapter.Sim2SeaMMGAdapter`。
- 目标速度线性映射为合法 nps，目标公共航向通过最短角控制器映射为限幅 `rudder_rad`；绝不把 `heading_deg` 直接送入舵角。
- 实际调用仓库 `env.vessel_sim.Sim2Sea_Core.core_step(..., type="RK")`，使用原有 MMG 和 RK4、10 子步、dt=0.1 s。
- trace 记录 solver、integrator、参数集、nps 和 rudder。
- 正式配置及回放 metadata 记录 solver 与参数身份。
- `kvlcc2_l7` 仅冻结为抽象接线代理，不声称是真实 USV 参数；适用性裁决已补入 ADR-MDINT001-007。

参数集规范化 JSON SHA-256：`b1f8f14633e8c693da5cbf8a3bb4dc6a1852d9a49a8d42d25dae420badf75f36`。
