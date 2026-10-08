"""IE 场景集扩展：新增六个测试场景 IE-08 … IE-13（只写新包，不动老包）。

为什么单独一个脚本而不是改 `_gen_ie_set.py`
------------------------------------------------
用户约束（2026-09-24）：**优先让场景适配方法，不许为了场景去改已经调好的方法**，
否则老场景分数会漂移。`_gen_ie_set.py::main()` 会（a）重写 `catalog/v2/ie_set.yaml`、
（b）重写**全部 7 个老包**、（c）重写 registry。任何一处只要产生一个字节差异，
老场景的 `resolved_hash` 就可能变，历史分数全部作废。

因此本脚本：
* **只**复用 `_gen_ie_set.py` 里的构造函数（实体工厂、站位表、`spec/apply_pressure`
  加压口径、`build_scenario/build_agents` 的声明模板），保证新场景与老场景说同一套
  资源语言、同一套评分/终局规则；
* **只**写 `scenarios/formal/ie_08_* … ie_13_*` 六个新目录；
* **只**向 registry **追加**六条记录，并断言老记录逐字不变；
* 写前写后对老包做 SHA-256 对比，不一致就报错退出（不写 registry）；
* 完全不碰 catalog bundle（新场景复用 `catalog_bundle: ie_set`，不新增任何资源）。

难度落点（用户要求：融入已有 1–8 号场景的难度带，而不是造新难度区间）
--------------------------------------------------------------
**编号约定（用户 2026-09-24 指定）**：IE 场景集的第 8 个成员是
**IE-08 = MD-AD-006-ISLAND-STRIKE（岛礁突击）**——它本来就是该集的第八员，
因此本脚本新造的六个场景从 **IE-09 顺延到 IE-14**。
`MD-AD-006-ISLAND-STRIKE` 作为**历史别名**继续可解析（registry 里保留两条记录指向
同一个包），新代码一律用 `IE-08-ISLAND-STRIKE`。

老场景的加压表（`_gen_ie_set.py::pressure`）与 p18 实测 `rule-rule` 分数：

    #   红机 红船 我机 我船 ingress 雾tick horizon   rule-rule
    1    4    0    4    2    1.00    –      900     0.8877
    2    4    0    3    2    0.95    –      900     0.8989
    3    0    3    2    7    0.95    –     1000     1.0000
    4    4    4    3    5    0.88    –     1200     0.8707
    5    5    4    4    5    0.82    –     1200     0.6840
    6    5    4    5    5    0.76   600    1200     0.6204
    7    7    5    3    6    0.70   400    1400     0.7210
    8(MD-AD-006 → IE-08) 17  5   16    3     –      –     1800     0.4846

六个新场景的旋钮取值全部**取在相邻老场景之间**（数量、ingress、雾起始 tick、horizon
都严格落在区间内），并各自换用一条不同的**敌进攻策略轴**（分波次/钳形同时到达/
诱饵前置/雾提前/纵深双目标/三波饱和），使它们是"带内插值 + 新结构"，而不是更难或更易。

    id      红机 红船 诱饵 我机 我船 ingress 雾tick horizon  策略轴
    IE-09   4    2    0    4    3    0.93     –     1000   空中两波 + 水面一支
    IE-10   3    3    0    4    4    0.90     –     1100   双轴钳形，几乎同时到达
    IE-11   4    3    2    4    4    0.86   700     1200   诱饵先出、主攻延后 150t
    IE-12   5    4    0    5    5    0.80   150     1200   雾提前到 150t（多向）
    IE-13   6    4    0    5    6    0.74   500     1400   纵深双目标（陆+水）
    IE-14   7    5    0    6    6    0.70   300     1500   三波饱和（t0/t300/t600）

容量约束（方法不许改 ⇒ 必须落在固定张量里）：
    `ie_rl_env.MAX_UNITS = 16`（我方全部实体，含设施/岸基站），
    `ie_rl_env.MAX_CONTACTS = 20`（同屏接触）。
    上表最大 15 与 12，均在容量内（IE-08/MD-AD-006 已是 16，正好顶格）。

用法：
    python _gen_ie_set_ext.py            # 生成/刷新六个新包 + 追加 registry
    python _gen_ie_set_ext.py --check    # 只校验：编译六个新包、老包哈希未变
"""
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import sys
from typing import Any

import yaml

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import _gen_ie_set as base  # noqa: E402  （只借它的构造函数与口径）

ROOT = pathlib.Path(os.environ.get("OPENMDBENCH_ROOT") or base.ROOT)
FORMAL = ROOT / "scenarios" / "formal"
REGISTRY = FORMAL / "registry.yaml"

OLD_PACKAGES = (
    "ie_01_single_target", "ie_02_dual_threat", "ie_03_surface_raid",
    "ie_04_combined_arms", "ie_05_multi_axis", "ie_06_decoy_mixed",
    "ie_07_cross_domain",
)

# IE 场景集第 8 个成员 = 岛礁突击。历史 public_id 是 MD-AD-006-ISLAND-STRIKE；
# 用户 2026-09-24 指定它在 IE 集里的编号是 IE-08，两条记录指向同一个包。
ISLAND_STRIKE_ALIAS = "IE-08-ISLAND-STRIKE"
ISLAND_STRIKE_LEGACY = "MD-AD-006-ISLAND-STRIKE"

PA = base.PORT_ASSETS
ZONE = base.ZONE_RADIUS_M


# ---------------------------------------------------------------------------
# 航线的域约束（第 11 轮教训：自爆船不能以陆上设施为航线终点，只能搁浅）
#   水上资产：facility.berth (700,-400) / facility.pier (700,-1000)
#   陆上资产：facility.command (-1200,-200) / facility.fuel (-500,-900)
# ---------------------------------------------------------------------------
WATER_ASSETS = {"facility.berth", "facility.pier"}


def routes_for(uav_target: str, boat_target: str | None) -> list[dict]:
    uav_route = {"match_tag": "uav", "objective_m": list(PA[uav_target][1]),
                 "pattern": "direct", "speed_mps": 43.0}
    if boat_target is None:
        return [uav_route]
    if boat_target not in WATER_ASSETS:
        raise ValueError(f"自爆船航线终点必须是水上资产，收到 {boat_target}")
    boat_route = {"match_tag": "boat", "objective_m": list(PA[boat_target][1]),
                  "pattern": "direct", "speed_mps": 10.0}
    return [uav_route, boat_route]


def decoy_routes(turn_tick: int, bait_pos: tuple[float, float]) -> list[dict]:
    """诱饵：先朝诱骗方向直飞，到 `turn_tick` 转向远海脱离（沿用 IE-06 的写法）。"""
    return [
        {"match_tag": "decoy", "until_tick": turn_tick,
         "objective_m": list(bait_pos), "pattern": "direct", "speed_mps": 43.0},
        {"match_tag": "decoy", "start_tick": turn_tick,
         "objective_m": [32000.0, -9000.0], "pattern": "direct",
         "speed_mps": 43.0},
    ]


def uav(eid: str, x: float, y: float, alt: float, heading: float,
        target: str, wave: int = 1) -> dict:
    return base.red_uav(eid, x, y, alt, heading, target, wave=wave)


def boat(eid: str, x: float, y: float, heading: float, target: str,
         wave: int = 1) -> dict:
    return base.red_usv(eid, x, y, heading, target, wave=wave)


# ---------------------------------------------------------------------------
# 六个新场景
# ---------------------------------------------------------------------------
def ext_specs() -> list[dict]:
    specs: list[dict] = []

    # --- IE-08 分波次双层突防 -------------------------------------------
    # 轴：同一方向、同一目标，但**空中分两波**（t=0 两架、t=250 两架）。
    # 目的：考察"第一波打完是否留弹给第二波"；规则侧默认抢占最近威胁，
    # LLM 侧能从 timeline 里读到两波声明。难度取 IE-01/02 与 IE-04 之间。
    specs.append(base.spec(
        9, "staggered_waves", "IE-09-STAGGERED-WAVES", "分波次双层突防",
        red_uavs=[uav("intruder.uav-01", 13000.0, 2200.0, 150.0, 252.0, "facility.command", 1),
                  uav("intruder.uav-02", 15000.0, 3000.0, 220.0, 256.0, "facility.command", 1),
                  uav("intruder.uav-03", 17500.0, -2600.0, 180.0, 288.0, "facility.command", 2),
                  uav("intruder.uav-04", 19500.0, -3600.0, 260.0, 292.0, "facility.command", 2)],
        red_boats=[boat("intruder.boat-01", 6400.0, -700.0, 264.0, "facility.berth", 1),
                   boat("intruder.boat-02", 7000.0, -1400.0, 267.0, "facility.berth", 1)],
        decoys=[], blue_uavs=4, blue_usvs=3,
        protected=["facility.command", "facility.berth"], duration=1000,
        weights={"facility.command": 2.0, "facility.berth": 1.0},
        spawn_ticks={"intruder.uav-03": 250, "intruder.uav-04": 250},
        timeline=[{"label": "air wave 1", "spawn_tick": 0, "count": 2,
                   "axis": "north-east, 13-15 km out at 43 m/s",
                   "behavior": "two UAVs run straight at the command post"},
                  {"label": "air wave 2", "spawn_tick": 250, "count": 2,
                   "axis": "south-east, 17-19 km out",
                   "behavior": "two more UAVs arrive about 250 ticks later on a "
                               "different bearing; defending wave 1 with everything "
                               "leaves the second wave unopposed"},
                  {"label": "surface element", "spawn_tick": 0, "count": 2,
                   "axis": "east, 6-7 km out but slow (10 m/s)",
                   "behavior": "two suicide boats run at the harbour-mouth berth"}],
        routes=routes_for("facility.command", "facility.berth"),
        notes="分层波次：空中两波错开 250 tick、水面一支，考察弹药分配与'打完一波还剩多少'。"
              "难度取 IE-01/02 与 IE-04 之间（红 4+2、我 4+3、ingress 0.93）。",
    ))

    # --- IE-09 双轴钳形夹击 ---------------------------------------------
    # 轴：空中自东北、水面自东南，且**几乎同时**抵达（与 IE-04 的刻意错开相反）。
    # 目的：考察同一时刻必须同时应对两个域、不能先解决一个再解决另一个。
    specs.append(base.spec(
        10, "dual_axis_pincer", "IE-10-DUAL-AXIS-PINCER", "双轴钳形夹击",
        red_uavs=[uav("intruder.uav-01", 14500.0, 4200.0, 150.0, 240.0, "facility.command", 1),
                  uav("intruder.uav-02", 16500.0, 5200.0, 220.0, 243.0, "facility.command", 1),
                  uav("intruder.uav-03", 13500.0, 3200.0, 260.0, 238.0, "facility.command", 1)],
        red_boats=[boat("intruder.boat-01", 7200.0, -4200.0, 300.0, "facility.berth", 1),
                   boat("intruder.boat-02", 7800.0, -5200.0, 304.0, "facility.berth", 1),
                   boat("intruder.boat-03", 8400.0, -3300.0, 297.0, "facility.berth", 1)],
        decoys=[], blue_uavs=4, blue_usvs=4,
        protected=["facility.command", "facility.berth"], duration=1100,
        weights={"facility.command": 1.5, "facility.berth": 1.0},
        timeline=[{"label": "air arm", "spawn_tick": 0, "count": 3,
                   "axis": "north-east, bearing about 045, 13-16 km out",
                   "behavior": "three UAVs run at the command post; they reach "
                               "weapon range at roughly the same tick as the "
                               "surface arm reaches the berth"},
                  {"label": "surface arm", "spawn_tick": 0, "count": 3,
                   "axis": "south-east, bearing about 135, 8-9 km out",
                   "behavior": "three suicide boats run at the harbour-mouth berth; "
                               "armed only at 150 m, so they must be stopped before "
                               "they close, at the same time the air arm is engaged"}],
        routes=routes_for("facility.command", "facility.berth"),
        notes="钳形同时到达：两轴相隔约 90 度、且到打窗口几乎重合，考察同一时刻的跨域资源分配。"
              "难度取 IE-03 与 IE-04 之间（红 3+3、我 4+4、ingress 0.90）。",
    ))

    # --- IE-10 诱饵掩护主攻 ---------------------------------------------
    # 轴：**诱饵先出**（t=0 两架无武器诱饵），真实空中主攻延迟到 t=150，
    # 水面自 t=0 出发。IE-06 的诱饵与主攻同时出现，本场景把诱饵放在前面，
    # 直接惩罚"看见空中接触就打"的策略；LLM 侧可从 timeline 读到"decoy"声明。
    specs.append(base.spec(
        11, "decoy_screen", "IE-11-DECOY-SCREEN", "诱饵掩护主攻",
        red_uavs=[uav("intruder.uav-01", 15500.0, 1800.0, 150.0, 257.0, "facility.command", 2),
                  uav("intruder.uav-02", 17500.0, 2800.0, 230.0, 260.0, "facility.command", 2),
                  uav("intruder.uav-03", 16500.0, 800.0, 190.0, 262.0, "facility.command", 2),
                  uav("intruder.uav-04", 19000.0, 2200.0, 290.0, 264.0, "facility.command", 2)],
        red_boats=[boat("intruder.boat-01", 7400.0, -2000.0, 267.0, "facility.berth", 1),
                   boat("intruder.boat-02", 8000.0, -1200.0, 265.0, "facility.berth", 1),
                   boat("intruder.boat-03", 8600.0, -2700.0, 269.0, "facility.berth", 1)],
        decoys=[base.red_decoy_uav("intruder.decoy-01", 13500.0, -3000.0, 150.0, 296.0, wave=1),
                base.red_decoy_uav("intruder.decoy-02", 12500.0, -1800.0, 210.0, 288.0, wave=1)],
        blue_uavs=4, blue_usvs=4,
        protected=["facility.command", "facility.berth"], duration=1200,
        weights={"facility.command": 1.5, "facility.berth": 1.0},
        spawn_ticks={"intruder.uav-01": 150, "intruder.uav-02": 150,
                     "intruder.uav-03": 150, "intruder.uav-04": 150},
        timeline=[{"label": "decoy screen", "spawn_tick": 0, "count": 2,
                   "axis": "south-east, offset from the real strike axis",
                   "behavior": "declared DECOYS: unarmed, they close on a plausible "
                               "bearing first and turn away at tick 150; spending "
                               "interceptors on them leaves the real package free"},
                  {"label": "real air package", "spawn_tick": 150, "count": 4,
                   "axis": "east and north-east, 15-19 km out",
                   "behavior": "the four armed UAVs appear only after the decoys "
                               "have already drawn attention"},
                  {"label": "surface element", "spawn_tick": 0, "count": 3,
                   "axis": "east, 7-9 km out, slow",
                   "behavior": "three suicide boats run at the harbour-mouth berth "
                               "throughout, so the berth cannot be ignored while the "
                               "air picture is being sorted out"}],
        routes=routes_for("facility.command", "facility.berth")
        + decoy_routes(150, PA["facility.command"][1]),
        fog_tick=700,
        notes="诱饵**前置**：无武器诱饵先到、真主攻晚 150 tick 才出现，惩罚'见接触就打'。"
              "难度取 IE-05 与 IE-06 之间（红 4+3+2诱饵、我 4+4、ingress 0.86、雾 700）。",
    ))

    # --- IE-11 雾中多向渗透 ---------------------------------------------
    # 轴：**天气**。IE-06 雾起 600、IE-07 雾起 400，本场景提前到 150，
    # 使预警窗口在交战开始前就被压缩；进攻方向数取 3。
    specs.append(base.spec(
        12, "fog_onset", "IE-12-FOG-ONSET", "雾中多向渗透",
        red_uavs=[uav("intruder.uav-01", 15000.0, 6200.0, 150.0, 232.0, "facility.pier", 1),
                  uav("intruder.uav-02", 17000.0, 4400.0, 230.0, 238.0, "facility.pier", 1),
                  uav("intruder.uav-03", 15000.0, -6800.0, 190.0, 298.0, "facility.pier", 1),
                  uav("intruder.uav-04", 17500.0, -5000.0, 270.0, 302.0, "facility.pier", 1),
                  uav("intruder.uav-05", 19500.0, 300.0, 160.0, 270.0, "facility.pier", 1)],
        red_boats=[boat("intruder.boat-01", 7800.0, 4800.0, 226.0, "facility.pier", 1),
                   boat("intruder.boat-02", 8500.0, -5600.0, 306.0, "facility.pier", 1),
                   boat("intruder.boat-03", 8200.0, 3200.0, 232.0, "facility.pier", 1),
                   boat("intruder.boat-04", 9000.0, -2600.0, 288.0, "facility.pier", 1)],
        decoys=[], blue_uavs=5, blue_usvs=5,
        protected=["facility.pier"], duration=1200,
        timeline=[{"label": "northern group", "spawn_tick": 0, "count": 3,
                   "axis": "bearing about 045",
                   "behavior": "two UAVs and one suicide boat converge on the "
                               "submarine pier"},
                  {"label": "southern group", "spawn_tick": 0, "count": 3,
                   "axis": "bearing about 135",
                   "behavior": "two UAVs and one suicide boat converge on the pier "
                               "from the other side; fog arrives at tick 150, before "
                               "either group is in weapon range"},
                  {"label": "central probe", "spawn_tick": 0, "count": 3,
                   "axis": "due east, low altitude",
                   "behavior": "one UAV and two suicide boats run straight down the "
                               "reference bearing to split attention three ways"}],
        routes=routes_for("facility.pier", "facility.pier"),
        fog_tick=150,
        notes="雾**提前到 150 tick**（早于 IE-06 的 600 与 IE-07 的 400），三向同时进入同一水上目标。"
              "难度取 IE-05 与 IE-06 之间（红 5+4、我 5+5、ingress 0.80）。",
    ))

    # --- IE-12 纵深双目标突击 -------------------------------------------
    # 轴：**纵深**。陆上指挥所（远、需前出拦截）与潜艇码头（近港、
    # 港区远侧）同时受压，两处设施的权重不同，考察目标价值判断。
    specs.append(base.spec(
        13, "deep_strike", "IE-13-DEEP-STRIKE", "纵深双目标突击",
        red_uavs=[uav("intruder.uav-01", 19000.0, 900.0, 130.0, 267.0, "facility.command", 1),
                  uav("intruder.uav-02", 22000.0, -1600.0, 210.0, 271.0, "facility.command", 1),
                  uav("intruder.uav-03", 20500.0, 2600.0, 170.0, 264.0, "facility.command", 1),
                  uav("intruder.uav-04", 24000.0, 500.0, 250.0, 268.0, "facility.command", 1),
                  uav("intruder.uav-05", 21500.0, -3000.0, 190.0, 274.0, "facility.command", 1),
                  uav("intruder.uav-06", 25500.0, 1700.0, 300.0, 265.0, "facility.command", 1)],
        red_boats=[boat("intruder.boat-01", 7000.0, -3400.0, 278.0, "facility.pier", 1),
                   boat("intruder.boat-02", 7500.0, -4400.0, 281.0, "facility.pier", 1),
                   boat("intruder.boat-03", 8100.0, -2800.0, 276.0, "facility.pier", 1),
                   boat("intruder.boat-04", 8700.0, -4000.0, 283.0, "facility.pier", 1)],
        decoys=[], blue_uavs=5, blue_usvs=6,
        protected=["facility.command", "facility.pier"], duration=1400,
        weights={"facility.command": 1.5, "facility.pier": 1.0},
        timeline=[{"label": "deep air strike", "spawn_tick": 0, "count": 6,
                   "axis": "east, 19-25 km out at 43 m/s",
                   "behavior": "six UAVs run at the command post far inland; the "
                               "interceptors must leave the harbour to meet them"},
                  {"label": "pier raid", "spawn_tick": 0, "count": 4,
                   "axis": "east, 7-9 km out, slow",
                   "behavior": "four suicide boats run at the submarine pier on the "
                               "far side of the harbour: defending the deep axis "
                               "pulls the surface force away from the pier"}],
        routes=routes_for("facility.command", "facility.pier"),
        fog_tick=500,
        notes="纵深双目标：陆上指挥所（远）与港区远侧码头（近）同时受压，两处权重不同，"
              "考察目标价值与兵力分配。难度取 IE-06 与 IE-07 之间（红 6+4、我 5+6、ingress 0.74、雾 500）。",
    ))

    # --- IE-13 三波饱和突击 ---------------------------------------------
    # 轴：**波次密度**。t=0/t=300/t=600 三波空中 + 两波水面，
    # 全程持续施压，考察长时段弹药与兵力轮换（老场景最多两波）。
    specs.append(base.spec(
        14, "saturation_three_wave", "IE-14-SATURATION-THREE-WAVE", "三波饱和突击",
        red_uavs=[uav("intruder.uav-01", 16000.0, 1600.0, 150.0, 261.0, "facility.command", 1),
                  uav("intruder.uav-02", 18000.0, 3000.0, 220.0, 257.0, "facility.command", 1),
                  uav("intruder.uav-03", 17000.0, -2200.0, 180.0, 285.0, "facility.command", 1),
                  uav("intruder.uav-04", 20500.0, 600.0, 240.0, 268.0, "facility.command", 2),
                  uav("intruder.uav-05", 22500.0, -2800.0, 200.0, 274.0, "facility.command", 2),
                  uav("intruder.uav-06", 23500.0, 3400.0, 280.0, 262.0, "facility.command", 3),
                  uav("intruder.uav-07", 24500.0, -3600.0, 160.0, 278.0, "facility.command", 3)],
        red_boats=[boat("intruder.boat-01", 7600.0, 2600.0, 250.0, "facility.berth", 1),
                   boat("intruder.boat-02", 8200.0, -3100.0, 275.0, "facility.berth", 1),
                   boat("intruder.boat-03", 8800.0, 1200.0, 258.0, "facility.berth", 1),
                   boat("intruder.boat-04", 9200.0, -4200.0, 282.0, "facility.berth", 2),
                   boat("intruder.boat-05", 9600.0, -1600.0, 268.0, "facility.berth", 2)],
        decoys=[], blue_uavs=6, blue_usvs=6,
        protected=["facility.command", "facility.berth"], duration=1500,
        weights={"facility.command": 2.0, "facility.berth": 1.0},
        spawn_ticks={"intruder.uav-04": 300, "intruder.uav-05": 300,
                     "intruder.uav-06": 600, "intruder.uav-07": 600,
                     "intruder.boat-04": 350, "intruder.boat-05": 350},
        timeline=[{"label": "wave 1", "spawn_tick": 0, "count": 5,
                   "axis": "east and north-east, 16-18 km out",
                   "behavior": "three UAVs run at the command post and two suicide "
                               "boats at the berth"},
                  {"label": "wave 2", "spawn_tick": 300, "count": 4,
                   "axis": "east, 20-23 km out",
                   "behavior": "two more UAVs and two more boats; arriving while "
                               "wave 1 is still being engaged"},
                  {"label": "wave 3", "spawn_tick": 600, "count": 2,
                   "axis": "east, 23-25 km out",
                   "behavior": "a final pair of UAVs: ammunition held back for wave "
                               "2 must still leave something for wave 3"}],
        routes=routes_for("facility.command", "facility.berth"),
        fog_tick=300,
        notes="三波饱和：t=0/300/600 三波共 7 机 5 船，全程持续施压，考察长时段弹药与兵力轮换。"
              "难度取 IE-07 与 MD-AD-006 之间（红 7+5、我 6+6、ingress 0.70、雾 300、horizon 1500）。",
    ))

    # 加压表：与老场景同一口径（红机 1 发/架、我机 3 发/架、我船 2 发/艘、ingress 缩放）。
    pressure = {
        9: dict(red_uav=4, red_boat=2, blue_uav=4, blue_usv=3, ingress=0.93,
                blue_ammo=3, blue_usv_ammo=2),
        10: dict(red_uav=3, red_boat=3, blue_uav=4, blue_usv=4, ingress=0.90,
                 blue_ammo=3, blue_usv_ammo=2),
        11: dict(red_uav=4, red_boat=3, blue_uav=4, blue_usv=4, ingress=0.86,
                 blue_ammo=3, blue_usv_ammo=2),
        12: dict(red_uav=5, red_boat=4, blue_uav=5, blue_usv=5, ingress=0.78,
                 blue_ammo=3, blue_usv_ammo=2),
        # 第 4 轮结论：这个场景在**两个域上都是刀刃**，整数兵力下没有中间档 ——
        #   我机 4 / 我船 5 → 0.3476      （对空少一架就翻）
        #   我机 5 / 我船 4 → 0.4018      （对水少一艘就翻）
        #   我机 5 / 我船 5 → 0.8680      （零损失全歼，偏饱和）
        # ingress 0.80→0.78 这种微调无效（仍是 0.8680）。
        # 处置：保留 5/5（读数在 IE-01…IE-08 的难度带 0.485–1.000 之内），
        # 并把"该场景应看**守住率**而不是单点分数"写进 IE_EXT_SCENARIOS.md §4。
        # 若要更难的一档，直接把 blue_usv 改回 4 即得 0.4018（低于带底，不推荐）。
        13: dict(red_uav=6, red_boat=4, blue_uav=4, blue_usv=6, ingress=0.70,
                 blue_ammo=3, blue_usv_ammo=2),
        # 第 2 轮收紧：首轮 IE-13 拿到 0.8642（t=603 就全歼）。对照 IE-07（0.7210）
        # 是"红 7+5 / 我 3+6 / ingress 0.70"——红方更多却更难，因为我机只有 3。
        # 这里把我机 5→4、ingress 0.74→0.70，把预警窗口与对空火力同时压下来。
        14: dict(red_uav=7, red_boat=5, blue_uav=6, blue_usv=6, ingress=0.70,
                 blue_ammo=3, blue_usv_ammo=2),
    }
    for item in specs:
        base.apply_pressure(item, pressure[item["index"]])
    return specs


# ---------------------------------------------------------------------------
# 写入（只写新包；老包只读校验）
# ---------------------------------------------------------------------------
def _running_episodes() -> list[str]:
    """列出正在跑的 `run_episode.py` 进程（生成期互斥用）。

    用 WMIC/Win32_Process 而不引第三方依赖；非 Windows 或查询失败时返回空表
    （互斥是保护措施，不该因为它失效而挡住正常生成）。
    """
    try:
        import subprocess
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | "
             "Where-Object { $_.CommandLine -like '*run_episode*' } | "
             "ForEach-Object { $_.ProcessId }"],
            capture_output=True, text=True, timeout=30)
    except Exception:                                    # noqa: BLE001
        return []
    pids = [line.strip() for line in (out.stdout or "").splitlines() if line.strip().isdigit()]
    return [f"pid {pid}" for pid in pids]


def package_hashes() -> dict[str, str]:
    out = {}
    for name in OLD_PACKAGES:
        for fname in ("scenario.yaml", "agents.yaml"):
            path = FORMAL / name / fname
            if path.exists():
                out[f"{name}/{fname}"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def entity_capacity(spec: dict) -> tuple[int, int]:
    """(我方实体数, 威胁方实体数) —— 必须分别 ≤ MAX_UNITS(16) / MAX_CONTACTS(20)。"""
    scenario = base.build_scenario(spec)["scenario"]
    entities = list(scenario["entities"])
    for event in scenario["events"]:
        if event.get("event_type") == "spawn":
            entities.append(event["payload"]["entity"])
    defenders = sum(1 for e in entities if e["faction_id"] == "coalition.defender")
    intruders = sum(1 for e in entities if e["faction_id"] == "coalition.intruder")
    return defenders, intruders


def write_packages(specs: list[dict]) -> None:
    before = package_hashes()
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    old_entries = [item for item in registry["scenarios"]
                   if item["public_id"] not in {s["public_id"] for s in specs}]

    for spec in specs:
        defenders, intruders = entity_capacity(spec)
        if defenders > 16:
            raise SystemExit(f"{spec['public_id']}: 我方实体 {defenders} > MAX_UNITS 16 "
                             f"（方法不许改，场景必须适配）")
        if intruders > 20:
            raise SystemExit(f"{spec['public_id']}: 威胁方实体 {intruders} > MAX_CONTACTS 20")
        package = f"ie_{spec['index']:02d}_{spec['slug']}"
        pkg_dir = FORMAL / package
        pkg_dir.mkdir(parents=True, exist_ok=True)
        (pkg_dir / "scenario.yaml").write_text(
            yaml.safe_dump(base.build_scenario(spec), allow_unicode=True,
                           sort_keys=False, width=400), encoding="utf-8")
        (pkg_dir / "agents.yaml").write_text(
            yaml.safe_dump(base.build_agents(spec), allow_unicode=True,
                           sort_keys=False, width=200), encoding="utf-8")
        print(f"wrote {package}: 我方实体 {defenders} / 威胁方实体 {intruders}  "
              f"({spec['public_id']})")

    after = package_hashes()
    if before != after:
        drifted = sorted(k for k in set(before) | set(after)
                         if before.get(k) != after.get(k))
        raise SystemExit(f"★ 老包被改动，已中止（未写 registry）：{drifted}")

    wanted = {s["public_id"] for s in specs}
    merged = [item for item in registry["scenarios"]
              if item["public_id"] not in wanted]
    for spec in specs:
        merged.append({"public_id": spec["public_id"],
                       "package": f"ie_{spec['index']:02d}_{spec['slug']}",
                       "catalog_bundle": "ie_set"})

    # --- IE-08 = MD-AD-006-ISLAND-STRIKE（用户 2026-09-24 指定）--------------
    # 岛礁突击本来就是 IE 场景集的第八个成员，只是历史 public_id 沿用了 MD-AD-006。
    # 这里给它加上 IE-08 的正式编号，**同时保留旧 id 作为可解析别名**：
    # 历史存档、脚本与文档里的 `MD-AD-006-ISLAND-STRIKE` 因此继续可用，
    # 不会因为改名而让任何既有读数失效。
    #
    # 为什么改名安全：`ResolvedScenarioV2.compute_resolved_hash` 在哈希前会
    # `pop("scenario_id")` 并剔除四个包哈希字段，所以换 public_id / 改 scenario_id /
    # 换包目录**都不改变 resolved_hash**；而交战命中判定的抽签种子是
    # `f(resolved_hash, session_id, …)` ⇒ **同名不同编号的两次运行逐位同分布**。
    # 实测核对见 `_w1_resolved_hash_probe.py --compare`。
    island = next((item for item in merged
                   if item["public_id"] == "MD-AD-006-ISLAND-STRIKE"), None)
    if island is None:
        raise SystemExit("registry 里找不到 MD-AD-006-ISLAND-STRIKE，无法建立 IE-08 别名")
    alias = dict(island)
    alias["public_id"] = ISLAND_STRIKE_ALIAS
    merged = [item for item in merged if item["public_id"] != ISLAND_STRIKE_ALIAS]
    merged.append(alias)

    registry["scenarios"] = merged
    REGISTRY.write_text(yaml.safe_dump(registry, allow_unicode=True,
                                       sort_keys=False, width=200),
                        encoding="utf-8")
    assert len([i for i in registry["scenarios"]
                if i["public_id"] in {s["public_id"] for s in specs}]) == len(specs)
    print(f"registry 现在有 {len(registry['scenarios'])} 个场景"
          f"（老 {len(old_entries)} 条未动，新 {len(specs)} 条追加，"
          f"另加 IE-08 别名 → 同一包）")


def check(specs: list[dict]) -> int:
    from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2

    failures = 0
    for spec in specs:
        defenders, intruders = entity_capacity(spec)
        try:
            resolved, _catalog = compile_formal_scenario_v2(spec["public_id"])
        except Exception as error:                      # noqa: BLE001
            print(f"  [FAIL] {spec['public_id']}: {type(error).__name__}: {error}")
            failures += 1
            continue
        horizon = getattr(resolved, "world", None)
        print(f"  [ok  ] {spec['public_id']:28} 实体={len(resolved.entities):3} "
              f"控制槽={len(resolved.controller_slots):3} "
              f"我方≤16: {defenders:2} 威胁≤20: {intruders:2}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只编译校验，不写文件")
    parser.add_argument("--force", action="store_true",
                        help="即使有 episode 在跑也重新生成（默认拒绝，见下）")
    args = parser.parse_args()

    # --- 生成期互斥（第 5 轮踩到的坑）----------------------------------------
    # 实测事故：一次 sweep 是「rule → rl → rule-rl」顺序跑的（每个 10–20 分钟），
    # 我在中间重新生成了 IE-12 的包，于是同一次 sweep 里三个臂读到了**不同的包版本**：
    #   rule   写于 19:37 实体 21（5机5船版）→ 0.8680
    #   rl     写于 19:49 实体 20（5机4船版）→ 0.6623
    #   rule-rl写于 19:56 实体 21（又回到 5机5船）→ 0.3878
    # 表面症状是"改了兵力但分数逐位不变"，看起来像 checkpoint 复用或引擎 bug，
    # 实际是**测量与生成并发**。判据：报告里的实体数会暴露版本。
    # 因此这里加互斥：有 episode 进程活着就拒绝生成。
    if not args.check and not args.force:
        running = _running_episodes()
        if running:
            print("★ 检测到 episode 正在运行，拒绝重新生成场景包（会造成同批读数跨版本）：")
            for item in running:
                print(f"    {item}")
            print("  等它们跑完再生成，或确认无碍后加 --force。")
            return 2

    specs = ext_specs()
    print(f"扩展场景 {len(specs)} 个："
          f"{', '.join(s['public_id'] for s in specs)}")
    before = package_hashes()
    if args.check:
        failures = check(specs)
        after = package_hashes()
        if before != after:
            print("★ 老包哈希在本次运行中发生了变化")
            return 1
        print(f"老包哈希未变（{len(before)} 个文件）；失败 {failures} 个")
        return 1 if failures else 0

    write_packages(specs)
    failures = check(specs)
    print(f"编译校验：失败 {failures} 个")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
