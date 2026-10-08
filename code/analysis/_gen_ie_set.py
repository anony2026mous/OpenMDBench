"""Generate the IE (Interception Engagement) scenario set: 7 new packages.

The set is eight interception-engagement sub-scenarios sharing one vocabulary of
catalogs, so the three method architectures (rule / hybrid LLM / pure LLM) need no
per-scenario branching:

    IE-01-SINGLE-TARGET     单目标拦截      1 red UAV
    IE-02-DUAL-THREAT       双威胁防御      2 red UAV, two bounded axes
    IE-03-SURFACE-RAID      水面突袭        3 red USV against the harbour mouth
    IE-04-COMBINED-ARMS     联合兵种攻击    2 red UAV + 2 red USV, split arrival
    IE-05-MULTI-AXIS        多方向接近      4 red (2 UAV + 2 USV), two directions
    IE-06-DECOY-MIXED       真假威胁与诱导  5 red, 3 real + 2 declared decoys
    IE-07-CROSS-DOMAIN      跨域渗透        2 red UAV in two staged waves
    (+ MD-AD-006-ISLAND-STRIKE 岛礁突击, the existing eighth member)

Colour convention (IMPORTANT).  The requirement table writes "blue appears from
outside, red is distributed around the port", i.e. it calls the *threat* blue and
*our side* red.  This repository's existing convention is the opposite:
``coalition.intruder`` (red) is the threat and ``coalition.defender`` (blue) is
ours, and the whole harness (``attack_driver``, the three planners, the scorecard)
is built on it.  This generator maps the table by ROLE, not by colour: the
table's 敌方 becomes ``coalition.intruder`` and its 我方 becomes
``coalition.defender``.

Engine capabilities deliberately NOT used (per the requirement): AUV / subsurface
platforms, and any behaviour needing engine support beyond declarative routes
(the "decoy turns into a real attacker" escalation is not implemented — only the
easy variant, where decoys are clearly declared non-threats).

Sources every resource from the validated ``md_ad_006.yaml`` bundle and adds only
one platform (a dedicated shore sensor site), so all eight scenarios speak exactly
the same resource language.

Usage:
    python _gen_ie_set.py
"""
from __future__ import annotations

import copy
import math
import os
from pathlib import Path

import yaml

ROOT = Path(os.environ.get("OPENMDBENCH_ROOT")
            or Path(__file__).resolve().parents[2] / "source-code" / "source_codes")
SRC_BUNDLE = ROOT / "catalog/v2/md_ad_006.yaml"
OUT_BUNDLE = ROOT / "catalog/v2/ie_set.yaml"
FORMAL = ROOT / "scenarios/formal"
REGISTRY = FORMAL / "registry.yaml"

ENGINE_COMPAT = ">=2.0.0,<3.0.0"
MODEL = "models.formal-data@2.0.0"
SET_NAME = "IE 拦截交战场景集"
DIRECTIONS = ["east", "north-east", "south-east"]


# ---------------------------------------------------------------------------
# shared geometry: a small port on the island, harbour mouth facing east (+x)
#
# 陆上设施的点位取自 MD-AD-006（该场景已通过编译与世界构造），因此必然是地图
# 权威地形内的合法陆地位置；岸基站取同一陆地区域内的偏移点。
#
# **第 11 轮更正**：泊位（berth）原先直接沿用了 MD-AD-006 的 `facility.comms`
# 点位 (-800, 250)，那是**陆上**通信站。而 IE-03 / IE-05 的自爆船（surface 域）
# 以泊位为目标 —— 船不可能抵达陆上目标，只能搁浅并被 `environment` 边界毁伤
# 摧毁。实测 IE-03：我方只开火 2 发，4 艘船全部落损，
# `damage_by_kind = {"environment": 129}`（**没有一次 weapon 毁伤来自红方**），
# 于是"水面突袭"不成立、我方几乎白拿一场胜利。
# 现在泊位改到港口入口的**水面**点位，并按水面设施建模（见 `facility_block`）。
# 水/陆判定用 `_w1_water_probe.py`（读地图权威陆地多边形）实测：
#   facility.berth (700,-400) WATER  facility.pier (700,-1000) WATER
#   facility.command (-1200,-200) LAND  facility.fuel (-500,-900) LAND
#   site.shore-radar (-1400,-300) LAND
# ---------------------------------------------------------------------------
PORT_ASSETS = {
    # 港口入口泊位：位于港口入口水面，作为"水面突袭"的打击目标
    "facility.berth":   ("港口入口泊位", (700.0, -400.0)),
    "facility.command": ("指挥中心",     (-1200.0, -200.0)),
    "facility.fuel":    ("油料设施",     (-500.0, -900.0)),
    "facility.pier":    ("潜艇码头",     (700.0, -1000.0)),
}
SHORE_SITE = ("site.shore-radar", "岸基预警雷达站（岸基传感器）", (-1400.0, -300.0), 250.0)
ZONE_RADIUS_M = 300.0  # 与 MD-AD-006 一致：保护区只是目标标定圈，不是部署区

# 保护目标在各子场景里的权重（未列出的目标不参与该子场景）
WEIGHTS_DEFAULT = 1.0


def entity_block(eid, faction, platform, dynamics, loadout, components, ammo,
                 position, heading, tags, target_domains, controller_slot,
                 energy=1.0, speed=0.0) -> dict:
    item = {
        "schema_version": "2.0",
        "id": eid,
        "faction_id": faction,
        "platform_ref": platform,
        "dynamics_ref": dynamics,
        "component_refs": components,
        "initial_state": {
            "schema_version": "2.0",
            "position_m": list(position),
            "velocity_mps": [speed, 0.0, 0.0],
            "heading_deg": heading,
            "health": 1.0,
            "energy": energy,
        },
        "tags": tags,
        "controller_slot": controller_slot,
    }
    if loadout:
        item["loadout_ref"] = loadout
    if ammo:
        item["ammunition"] = ammo
    if target_domains:
        item["target_domains"] = target_domains
    return item


def polygon_circle(zone_id: str, cx: float, cy: float, radius_m: float,
                   tags: list, segments: int = 32) -> dict:
    """圆的 32 边形近似（引擎的 zone 需要 geometry_type + coordinates_m）。"""
    points = [
        [round(cx + radius_m * math.cos(2 * math.pi * i / segments), 3),
         round(cy + radius_m * math.sin(2 * math.pi * i / segments), 3)]
        for i in range(segments)
    ]
    return {
        "schema_version": "2.0",
        "id": zone_id,
        "geometry_type": "polygon",
        "coordinates_m": points,
        "tags": list(tags),
    }


# ---------------------------------------------------------------------------
# force builders
# ---------------------------------------------------------------------------
def red_uav(eid, x, y, alt, heading, target=None, wave=1, extra_tags=()) -> dict:
    tags = ["intruder", "uav", f"wave-{wave}"] + list(extra_tags)
    if target:
        tags.append(f"target.{target}")
    return entity_block(
        eid, "coalition.intruder", "platform.interceptor-uav@2.0.0",
        "dynamics.interceptor-uav@2.0.0", "loadout.loitering-uav@2.0.0",
        ["sensor.interceptor-radar@2.0.0", "sensor.interceptor-eo@2.0.0",
         "communication.command-network@2.0.0"],
        {"ammunition.loitering-munition@2.0.0": 4},
        (x, y, alt), heading, tags, ["air", "land"], None, speed=-43.0)


def red_decoy_uav(eid, x, y, alt, heading, wave=1) -> dict:
    """A declared decoy: no weapon, no `target.` tag — it can never fire."""
    return entity_block(
        eid, "coalition.intruder", "platform.interceptor-uav@2.0.0",
        "dynamics.interceptor-uav@2.0.0", None,
        ["sensor.interceptor-radar@2.0.0",
         "communication.command-network@2.0.0"],
        None, (x, y, alt), heading,
        ["intruder", "uav", "decoy", f"wave-{wave}"], ["air"], None, speed=-43.0)


def red_usv(eid, x, y, heading, target=None, wave=1, extra_tags=()) -> dict:
    tags = ["intruder", "boat", f"wave-{wave}"] + list(extra_tags)
    if target:
        tags.append(f"target.{target}")
    return entity_block(
        eid, "coalition.intruder", "platform.suicide-usv@2.0.0",
        "dynamics.suicide-usv@2.0.0", "loadout.suicide-usv@2.0.0",
        ["sensor.usv-radar@2.0.0", "communication.command-network@2.0.0"],
        {"ammunition.suicide-warhead@2.0.0": 1},
        (x, y, 0.0), heading, tags, ["surface", "land"], None, speed=-10.0)


def blue_uav(eid, x, y, alt, heading, ammo: int = 2) -> dict:
    return entity_block(
        eid, "coalition.defender", "platform.interceptor-uav@2.0.0",
        "dynamics.interceptor-uav@2.0.0", "loadout.air-interceptor-uav@2.0.0",
        ["sensor.interceptor-radar@2.0.0", "sensor.interceptor-eo@2.0.0",
         "communication.command-network@2.0.0"],
        {"ammunition.air-interceptor-munition@2.0.0": int(ammo)},
        (x, y, alt), heading,
        # combat-unit：提前终局规则要区分"作战力量"与设施/传感器站
        ["defence", "combat-unit", "interceptor"], ["air"], None)


def blue_usv(eid, x, y, ammo: int = 2) -> dict:
    return entity_block(
        eid, "coalition.defender", "platform.armed-usv@2.0.0",
        "dynamics.armed-usv@2.0.0", "loadout.armed-usv@2.0.0",
        ["sensor.usv-radar@2.0.0", "communication.command-network@2.0.0"],
        {"ammunition.surface-missile@2.0.0": int(ammo)},
        (x, y, 0.0), 90.0, ["defence", "combat-unit", "usv", "surface"],
        ["surface"], None)


def shore_site() -> dict:
    eid, _zh, (x, y), _r = SHORE_SITE
    return entity_block(
        eid, "coalition.defender", "platform.shore-sensor-site@2.0.0",
        "dynamics.fixed-site@2.0.0", None,
        ["sensor.shore-early-warning@2.0.0", "sensor.shore-gap-filler@2.0.0",
         "communication.command-network@2.0.0"],
        None, (x, y, 0.0), 90.0, ["defence", "sensor-site", "fixed"], None, None)


def facility_block(fid) -> dict:
    """受保护资产。**水面**资产必须用 surface 域的码头平台：

    `platform.harbor-pier` 的 domain 是 surface（mobile: false），因此不受
    "land 域实体必须落在陆地多边形内"的部署检查约束；若按陆基平台建模，
    位于水上的码头会被判 scenario.deployment_outside_allowed
    —— 这正是 IE-07（以码头为保护目标）编译失败的根因。

    第 11 轮把泊位也纳入这一支：泊位是自爆船的打击目标，必须真的在水面上，
    否则船只能搁浅（见 `PORT_ASSETS` 上方注释与 `_w1_water_probe.py`）。
    """
    zh, (x, y) = PORT_ASSETS[fid]
    if fid in ("facility.pier", "facility.berth"):
        return entity_block(
            fid, "coalition.defender", "platform.harbor-pier@2.0.0",
            "dynamics.static-structure@2.0.0", None,
            ["sensor.usv-radar@2.0.0", "communication.command-network@2.0.0"],
            None, (x, y, 0.0), 90.0, ["defence", "facility", "pier", "fixed"],
            None, None)
    return entity_block(
        fid, "coalition.defender", "platform.shore-defence-site@2.0.0",
        "dynamics.fixed-site@2.0.0", None,
        ["sensor.shore-gap-filler@2.0.0", "communication.command-network@2.0.0"],
        None, (x, y, 0.0), 90.0, ["defence", "facility", "fixed"], None, None)


def blue_uav_row(prefix, start_index, positions, ammo: int = 2) -> list[dict]:
    return [blue_uav(f"defender.uav-{index:02d}", x, y, alt, 100.0, ammo=ammo)
            for index, (x, y, alt) in enumerate(positions, start_index)]


# ---------------------------------------------------------------------------
# the seven new scenarios
# ---------------------------------------------------------------------------
BLUE_UAV_STATIONS = [
    # 港区以东的前出站位；按各场景需要取前 N 个
    (3200.0, 1200.0, 800.0), (3600.0, 0.0, 800.0), (3200.0, -1200.0, 800.0),
    (4600.0, 1800.0, 900.0), (5000.0, 600.0, 900.0), (5000.0, -600.0, 900.0),
    (4600.0, -1800.0, 900.0), (6200.0, 900.0, 1000.0), (6200.0, -900.0, 1000.0),
]
BLUE_USV_STATIONS = [
    (1800.0, -200.0), (2400.0, 800.0), (2200.0, -1400.0),
    (1500.0, 1200.0), (2800.0, -400.0), (3000.0, 1400.0),
    # 第 14 轮扩展：桌面拦截线。原表只有 6 个站位，而
    # `blue_force` 用 `BLUE_USV_STATIONS[:usv_count]` 取人 —— 超过 6 会被**静默
    # 截断**（请求 8 艘实际只生成 6 艘），水面兵力因此无法上调。这里补齐并在
    # `blue_force` 里加了显式断言。全部点位经 `_w1_water_probe.py` 实测为水面。
    (3400.0, -800.0), (3600.0, 400.0), (3200.0, -2000.0),
    (4000.0, 1000.0), (4000.0, -1200.0), (3800.0, 2000.0),
    (3000.0, 2200.0), (2600.0, -2200.0),
]


def blue_force(uav_count: int, usv_count: int, *, uav_ammo: int = 2,
               usv_ammo: int = 2) -> list[dict]:
    """我方兵力：N 架无人机（对空）+ M 艘武装无人船（对海）+ 岸基传感器（另加）。

    载弹是可调的难度旋钮，但**不是**"弹药数 ≥ 威胁数就必然全歼"：第 11 轮核对
    了实际毁伤链，原先这里的说法是错的。对空弹 `weapon.air-interceptor-munition`
    挂的是 `effect.loitering-hit`（0.6 × `damage.kinetic-partial` 的 health_scale
    0.5 = **0.3 生命/发**），不是一击即毁：命中 2 发才到 `disabled_threshold 0.5`，
    4 发才 `destroyed`。命中率 0.75，故"中性化一架"期望约 2.7 发。真正一击即毁的
    是 `effect.surface-missile-hit` / `effect.suicide-detonation`（kinetic-terminal
    1.0），也就是我方对海弹与红方自爆战斗部。

    相应地，把载弹从 2 降到 1 并不产生突防（第 12 轮实测反而把 7 个场景里 6 个的
    分数抬高了：载弹少 → 射击更省 → `ammo` 层 = kills/shots 更高），因此该改动
    已回退，本参数默认保持 2。
    """
    force = blue_uav_row("defender.uav", 1, BLUE_UAV_STATIONS[:uav_count],
                         ammo=uav_ammo)
    if usv_count > len(BLUE_USV_STATIONS):
        raise ValueError(
            f"requested {usv_count} surface units but only "
            f"{len(BLUE_USV_STATIONS)} stations exist: the slice would silently "
            f"generate fewer units than the pressure table asks for")
    if uav_count > len(BLUE_UAV_STATIONS):
        raise ValueError(
            f"requested {uav_count} air units but only "
            f"{len(BLUE_UAV_STATIONS)} stations exist")
    force += [blue_usv(f"defender.usv-{index:02d}", x, y, ammo=usv_ammo)
              for index, (x, y) in enumerate(BLUE_USV_STATIONS[:usv_count], 1)]
    return force


def red_uav_force(ingress: list[tuple], target: str, wave: int = 1) -> list[dict]:
    """威胁方无人机编队。ingress = [(x, y, alt, heading), ...]"""
    return [red_uav(f"intruder.uav-{index:02d}", x, y, alt, heading, target,
                    wave=wave)
            for index, (x, y, alt, heading) in enumerate(ingress, 1)]


def red_boat_force(ingress: list[tuple], target: str, wave: int = 1) -> list[dict]:
    """威胁方自爆船编队（威胁方没有武装无人船，只有自爆船）。"""
    return [red_usv(f"intruder.boat-{index:02d}", x, y, heading, target, wave=wave)
            for index, (x, y, heading) in enumerate(ingress, 1)]


def spec(index, slug, public_id, zh, *, red_uavs, red_boats, decoys, blue_uavs,
         blue_usvs, protected, duration, timeline, routes, notes,
         spawn_ticks=None, weights=None, fog_tick=None) -> dict:
    return {
        "index": index, "slug": slug, "public_id": public_id, "zh": zh,
        "protected": protected,
        "weights": weights or {fid: 1.0 for fid in protected},
        "duration": duration,
        "fog_tick": fog_tick,
        "defender": blue_force(blue_uavs, blue_usvs),
        "blue_uavs": blue_uavs, "blue_usvs": blue_usvs,
        "target_red_uav": sum(1 for e in red_uavs if "decoy" not in e["id"]),
        "target_red_boat": len(red_boats),
        "intruder": red_uavs + red_boats + decoys,
        "timeline": timeline, "routes": routes, "notes": notes,
        "spawn_ticks": spawn_ticks or {},
    }


def scenario_specs() -> list[dict]:
    """8 个拦截交战子场景中新增的 7 个。

    编成梯度（威胁方：无人机 + 自爆船；我方：无人机 + 武装无人船 + 岸基传感器）：

        #   威胁无人机  威胁自爆船  诱饵   我方无人机  我方无人船  保护设施
        1       1          0       0        2          1         1
        2       2          0       0        3          2         1
        3       0          3       0        2          3         1
        4       3          3       0        3          3         2
        5       4          3       0        4          3         2
        6       4          3       2        4          4         1
        7       6          4       0        5          4         2
        8      12          5       0        9          3         4

    威胁方总量 1→2→3→6→7→9→10→17、我方作战单元 3→5→5→6→7→8→9→12，
    使第 7 到第 8 个场景的落差不再突兀。所有场景的目标都是**岛上设施**。
    """
    specs: list[dict] = []
    direct_uav = {"match_tag": "uav", "objective_m": None,
                  "pattern": "direct", "speed_mps": 43.0}
    direct_boat = {"match_tag": "boat", "objective_m": None,
                   "pattern": "direct", "speed_mps": 10.0}

    def uav_routes(target_pos):
        route = dict(direct_uav)
        route["objective_m"] = list(target_pos)
        return [route]

    def all_routes(target_pos):
        uav = dict(direct_uav); uav["objective_m"] = list(target_pos)
        boat = dict(direct_boat); boat["objective_m"] = list(target_pos)
        return [uav, boat]

    def split_routes(uav_target_pos, boat_target_pos):
        """按域分别指定航线：空中打 `uav_target_pos`、水面打 `boat_target_pos`。

        必须分域给航线。第 11 轮发现 IE-04 / IE-05 用 `all_routes(command)` 把
        **自爆船也导航到陆上的指挥中心**，而船的打击目标（`target.*` 标签）却是
        泊位 —— 航线与目标不一致，船只会朝陆地开、搁浅、被边界毁伤摧毁。
        航线（去哪）与目标指派（打谁）必须指向同一个可达资产。
        """
        uav = dict(direct_uav); uav["objective_m"] = list(uav_target_pos)
        boat = dict(direct_boat); boat["objective_m"] = list(boat_target_pos)
        return [uav, boat]

    # --- IE-01 单目标拦截 ------------------------------------------------
    specs.append(spec(
        1, "single_target", "IE-01-SINGLE-TARGET", "单目标拦截",
        red_uavs=red_uav_force([(12000.0, -300.0, 150.0, 270.0)], "facility.command"),
        red_boats=[], decoys=[], blue_uavs=2, blue_usvs=1,
        protected=["facility.command"], duration=900,
        timeline=[{"label": "single intruder UAV", "spawn_tick": 0, "count": 1,
                   "axis": "east",
                   "behavior": "straight run at the command post; no evasive "
                               "manoeuvre and no second wave"}],
        routes=uav_routes(PORT_ASSETS["facility.command"][1]),
        notes="最小规模：单架突防无人机攻击指挥所，考察发现—跟踪—拦截链是否闭环。",
    ))

    # --- IE-02 双威胁防御 ------------------------------------------------
    specs.append(spec(
        2, "dual_threat", "IE-02-DUAL-THREAT", "双威胁防御",
        red_uavs=red_uav_force([(14000.0, 2600.0, 150.0, 250.0),
                                (16000.0, -3400.0, 250.0, 290.0)],
                               "facility.command"),
        red_boats=[], decoys=[], blue_uavs=3, blue_usvs=2,
        protected=["facility.command"], duration=900,
        timeline=[{"label": "threat north-east", "spawn_tick": 0, "count": 1,
                   "axis": "north-east, about 16 deg off the reference bearing",
                   "behavior": "straight run at the command post"},
                  {"label": "threat south-east", "spawn_tick": 0, "count": 1,
                   "axis": "south-east, about 21 deg off the reference bearing",
                   "behavior": "straight run at the command post; both threats "
                               "arrive within 60 ticks of each other"}],
        routes=uav_routes(PORT_ASSETS["facility.command"][1]),
        notes="两架突防无人机从夹角受限的两个方向同时进入，考察多目标任务分配与重复投入。",
    ))

    # --- IE-03 水面突袭 --------------------------------------------------
    specs.append(spec(
        3, "surface_raid", "IE-03-SURFACE-RAID", "水面突袭",
        red_uavs=[], decoys=[],
        red_boats=red_boat_force([(5200.0, 300.0, 265.0), (5600.0, -600.0, 268.0),
                                  (6000.0, 1100.0, 262.0)], "facility.berth"),
        blue_uavs=2, blue_usvs=3,
        protected=["facility.berth"], duration=1000,
        timeline=[{"label": "surface raid group", "spawn_tick": 0, "count": 3,
                   "axis": "east, a narrow bearing band on the harbour approach",
                   "behavior": "three suicide boats run in parallel at the "
                               "harbour-mouth berth, saturating the approach"}],
        routes=all_routes(PORT_ASSETS["facility.berth"][1]),
        notes="三艘自爆船在窄带内平行突入，考察水面封堵、空间协同与防线维持；"
              "威胁方没有武装无人船，我方对海火力只有武装无人船。",
    ))

    # --- IE-04 联合兵种攻击 ----------------------------------------------
    specs.append(spec(
        4, "combined_arms", "IE-04-COMBINED-ARMS", "联合兵种攻击",
        red_uavs=red_uav_force([(20000.0, 3000.0, 150.0, 250.0),
                                (22000.0, 4200.0, 250.0, 255.0),
                                (24000.0, 1800.0, 300.0, 258.0)],
                               "facility.command"),
        red_boats=red_boat_force([(6200.0, -900.0, 265.0), (6800.0, -1700.0, 262.0),
                                  (7400.0, -300.0, 268.0)], "facility.berth"),
        decoys=[], blue_uavs=3, blue_usvs=3,
        protected=["facility.command", "facility.berth"], duration=1200,
        weights={"facility.command": 2.0, "facility.berth": 1.0},
        timeline=[{"label": "air element", "spawn_tick": 0, "count": 3,
                   "axis": "north-east, 20-24 km out but fast (43 m/s)",
                   "behavior": "runs at the command post; reaches weapon range "
                               "well before the surface element"},
                  {"label": "surface element", "spawn_tick": 0, "count": 3,
                   "axis": "south-east, only 6-7 km out but slow (10 m/s)",
                   "behavior": "suicide boats run at the harbour-mouth berth; they "
                               "arrive well after the air element"}],
        routes=split_routes(PORT_ASSETS["facility.command"][1],
                            PORT_ASSETS["facility.berth"][1]),
        notes="空中远而快、水面近而慢，两类到达时间明显错开，考察异构平台协同与跨域资源调度。"
              "水面打击目标原为陆上油料设施，自爆船无法抵达（只能搁浅），第 11 轮改指港口入口泊位。",
    ))

    # --- IE-05 多方向接近 ------------------------------------------------
    specs.append(spec(
        5, "multi_axis", "IE-05-MULTI-AXIS", "多方向接近",
        red_uavs=red_uav_force([(16000.0, 7000.0, 150.0, 230.0),
                                (18000.0, 5600.0, 250.0, 235.0),
                                (16000.0, -7500.0, 200.0, 300.0),
                                (18500.0, -5800.0, 300.0, 305.0)],
                               "facility.command"),
        red_boats=red_boat_force([(8000.0, 5200.0, 230.0), (9000.0, -6200.0, 305.0),
                                  (8600.0, 3600.0, 235.0)], "facility.berth"),
        decoys=[], blue_uavs=4, blue_usvs=3,
        protected=["facility.command", "facility.berth"], duration=1200,
        weights={"facility.command": 1.5, "facility.berth": 1.0},
        timeline=[{"label": "group north-east", "spawn_tick": 0, "count": 3,
                   "axis": "bearing about 045",
                   "behavior": "two UAVs and one suicide boat approach the "
                               "command post"},
                  {"label": "group south-east", "spawn_tick": 0, "count": 4,
                   "axis": "bearing about 135",
                   "behavior": "two UAVs and two suicide boats approach the "
                               "berth; the two groups are about 90 deg apart, so "
                               "covering one leaves the other open"}],
        routes=split_routes(PORT_ASSETS["facility.command"][1],
                            PORT_ASSETS["facility.berth"][1]),
        notes="两个攻击群从相隔约 90 度的方向进入，考察多方向态势理解与动态调度。"
              "水面航线原指向陆上指挥中心（与船只的泊位目标不一致），第 11 轮改为分域给航线。",
    ))

    # --- IE-06 真假威胁与诱导攻击 ----------------------------------------
    specs.append(spec(
        6, "decoy_mixed", "IE-06-DECOY-MIXED", "真假威胁与诱导攻击",
        red_uavs=red_uav_force([(15000.0, 2200.0, 150.0, 255.0),
                                (17500.0, 3300.0, 250.0, 258.0),
                                (16500.0, 1200.0, 200.0, 260.0),
                                (19000.0, 2600.0, 300.0, 262.0)],
                               "facility.command"),
        red_boats=red_boat_force([(7500.0, -2400.0, 268.0), (8200.0, -1500.0, 266.0),
                                  (8800.0, -3000.0, 270.0)], "facility.berth"),
        decoys=[red_decoy_uav("intruder.decoy-01", 14500.0, -4200.0, 150.0, 300.0),
                red_decoy_uav("intruder.decoy-02", 16500.0, -5200.0, 250.0, 305.0)],
        blue_uavs=4, blue_usvs=4,
        protected=["facility.command", "facility.berth"], duration=1200,
        weights={"facility.command": 1.5, "facility.berth": 1.0},
        timeline=[{"label": "real strike package", "spawn_tick": 0, "count": 7,
                   "axis": "east and north-east",
                   "behavior": "four UAVs run at the command post and three suicide "
                               "boats run at the harbour-mouth berth; these carry "
                               "the strike munitions"},
                  {"label": "decoy flight", "spawn_tick": 0, "count": 2,
                   "axis": "south-east, offset from the real axis",
                   "behavior": "declared DECOYS: unarmed, they approach on a "
                               "plausible bearing and turn away at tick 150 without "
                               "ever entering weapon range; do not spend missiles "
                               "on them"}],
        routes=split_routes(PORT_ASSETS["facility.command"][1],
                            PORT_ASSETS["facility.berth"][1]) + [
            {"match_tag": "decoy", "until_tick": 150,
             "objective_m": list(PORT_ASSETS["facility.command"][1]),
             "pattern": "direct", "speed_mps": 43.0},
            {"match_tag": "decoy", "start_tick": 150,
             "objective_m": [32000.0, -9000.0], "pattern": "direct",
             "speed_mps": 43.0}],
        fog_tick=600,
        notes="3 真 2 假：诱饵无武器、且由场景在 attack.timeline 里明确声明为非威胁；"
              "规则侧没有这个概念、只看得见空中接触，LLM 侧拿得到声明式上下文 —— "
              "这是本场景集里最能体现判读差异的一轴。诱饵'转为真实攻击'的升级版未实现。"
              "水面打击目标原为陆上指挥中心（自爆船无法抵达），第 11 轮改指港口入口泊位。",
    ))

    # --- IE-07 跨域渗透 --------------------------------------------------
    specs.append(spec(
        7, "cross_domain", "IE-07-CROSS-DOMAIN", "跨域渗透",
        red_uavs=red_uav_force([(18000.0, 600.0, 120.0, 268.0),
                                (22000.0, -1800.0, 200.0, 272.0),
                                (20000.0, 2400.0, 160.0, 265.0),
                                (24000.0, 400.0, 240.0, 268.0),
                                (21000.0, -3200.0, 180.0, 275.0),
                                (26000.0, 1600.0, 300.0, 264.0)],
                               "facility.pier"),
        red_boats=red_boat_force([(6800.0, -3600.0, 280.0), (7200.0, -4600.0, 282.0),
                                  (7800.0, -3000.0, 278.0), (8400.0, -4200.0, 284.0)],
                                 "facility.pier"),
        decoys=[], blue_uavs=5, blue_usvs=4,
        protected=["facility.pier", "facility.command"], duration=1400,
        weights={"facility.pier": 1.0, "facility.command": 1.0},
        spawn_ticks={"intruder.uav-04": 400, "intruder.uav-05": 400,
                     "intruder.uav-06": 400},
        timeline=[{"label": "probe wave", "spawn_tick": 0, "count": 7,
                   "axis": "east, low altitude (120-200 m) so mainly the shore "
                           "sensor sees it early",
                   "behavior": "three UAVs and four suicide boats converge on the "
                               "submarine pier"},
                  {"label": "main wave", "spawn_tick": 400, "count": 3,
                   "axis": "east, 21-26 km out",
                   "behavior": "three more UAVs arrive about 400 ticks later; the "
                               "pier is on the far side of the harbour, so the "
                               "approach is only partly observable from the port"}],
        routes=all_routes(PORT_ASSETS["facility.pier"][1]),
        fog_tick=400,
        notes="原需求含 2 艘 AUV（水下），引擎不支持水下平台，故只实现空中分波次渗透；"
              "低空进入 + 分波次 + 目标在港区远侧，制造跨域/跨时段的观察不完全性。"
              "编成已上调，使第 7 到第 8 个场景的数量落差不再突兀。",
    ))

    # ------------------------------------------------------------------
    # 编成加压表（第 11 轮重标定）：让前 7 个场景都落在
    # "我方理论最优策略刚好能够成功拦截"的临界点。
    #
    # **第 10 轮的表已作废**，因为它是在"红方没有开火入口"的畸形模型上标定的
    # （见 s1 实验的运行记录 §8）：那时红方全程不开火，任何"加压"都测不出
    # 真实难度。本轮改用闭式火力账（`_w1_ladder_calc.py`）重新推导：
    #
    #   失能所需命中 = ceil((1.0 - 0.5) / (magnitude × health_scale))
    #   每次失能所需发数 = 命中数 / 命中率
    #
    # 实际弹药参数（catalog/v2/ie_set.yaml，均为实测核对）：
    #   weapon.air-interceptor-munition  effect.loitering-hit → 0.6 × 0.5 = 0.30/发，
    #                                    命中率 0.75 ⇒ **2 发才失能、每 2.67 发换 1 架**
    #   weapon.loitering-munition        同为 0.30/发、0.75 ⇒ 同上
    #   weapon.surface-missile           effect.surface-missile-hit 1.0/发、0.5
    #                                    ⇒ 每 2 发换 1 艘
    #   weapon.suicide-warhead           1.0/发，但射程只有 0–30 m
    #
    # 关键推论（第 10 轮的表因此是错的）：
    #   * 对空弹**不是**一击即毁。`blue_ammo=1` 时每架我机只有 1 发，1 发 × 0.3
    #     = 0.3 < 失能阈值 0.5，**连一架都打不掉**，等于把防守方解除武装 ——
    #     实测 IE-02 因此崩到 0.0556（红方 194 tick 摧毁指挥所）。
    #   * 摧毁一个设施需 4 发命中（1.0 / 0.30），而红机载弹上限 3 发：
    #     单机最多让设施失能，**必须多机叠加火力**才能触发 rule.assets-lost。
    #
    # 本表口径（第 13 轮按 p13 实测逐场景归位）：红机 **1 发/架**（见
    # `apply_pressure`），结局因此按"突防架数"分档：
    #   0 架突防 → 设施完好（≈0.88–0.91）
    #   1 架突防 → 设施失能（≈0.67–0.68）  ← "刚好守住"
    #   ≥2 架突防 → 设施被毁（≈0.14）
    # p13 实测的落档：IE-01 1 架、IE-02 ≥2 架、IE-03 ≥2 架、IE-04 0 架(带伤)、
    # IE-05 0 架、IE-06 1 架、IE-07 0 架、IE-08 —— 与场景序号并不单调。
    # 本表据此**逐场景**调我方兵力，把落档搬到与序号一致的单调阶梯：
    #   IE-01 3→4 架（消掉那 1 架突防）、IE-02 4→4 架且 4 发/架（从 ≥2 架压到 0 架）、
    #   IE-03 我船 4→5 艘（水面同理）、IE-05/IE-06/IE-07 我机 5→4 架。
    #
    # p14 实测后又做了三处微调（本轮最终口径）：
    #   * IE-02 我机 5→4 架（4 发/架不变）：p14 得 0.9097 略高于 IE-01 的 0.8903，
    #     按序号应当更低；减少 1 架即从"0 架突防"档的偏高位置回落。
    #   * IE-03 我船 6→5 艘：p14 得 1.0000（弹药层也饱和），减 1 艘让弹药效率回落。
    #   * IE-06 我机 4→5 架（**回退**）：p14 减到 4 架后从 0.6789 掉到 0.2902
    #     （1 架突防 → ≥2 架突防），方向反了，故回退。
    # 我方无人机/无人船数量本身就是需求里点名的加压旋钮，这里把它用作**分档**手段。
    # 难度阶梯同时由**来袭距离**（ingress 0.70→1.00）、方向数、波次、天气承担。
    # ------------------------------------------------------------------
    # 第 14 轮末：水面兵力重标定（引信修正后）
    # ------------------------------------------------------------------
    # 引信由 8 m 放宽到 25 m 后，水面交战第一次真正成立（见 build_bundle）：
    # IE-04 实测 **15 发 8 击杀（1.9 发/杀）**、`non_combat = 0`、
    # `damage_by_kind = {'weapon': 10}` —— 全部落损都是武器战果。
    # 于是水面可以按与对空相同的口径配兵：**约 2 发换 1 艘**。
    # 但自爆船现在是"1 换 1"的威胁：每艘船带 1 枚战斗部、在 150 m 定角起爆，
    # 命中即摧毁我方一艘无人船（IE-03 曾出现 4 艘我船被换掉、只剩 1 艘）。
    # 因此我船数按"红船数 + 冗余"配，冗余用来吸收这种 1 换 1 交换：
    #   红船 4 → 我船 7（IE-03）/ 5（IE-04~06）；红船 5 → 我船 6（IE-07）。
    # 我机数沿用 p15 的落档结果（红机 1 发/架 ⇒ 0/1/≥2 架突防三档）。
    #
    # p17 实测后又做了三处收尾（本轮最终口径），目标是让分数随 IE-01→IE-08 单调不增：
    #   * IE-02 我机 4→3 架（4 发/架）：p17 得 0.9069 高于 IE-01 的 0.8877，按序号应更低；
    #   * IE-03 红船 4→3 艘（我船保持 7）：p17 得 0.6756，明显低于序号 3 该在的位置 ——
    #     纯水面场景里自爆船是"1 换 1"威胁，4 艘对蓝色而言偏重，减 1 艘使其回到
    #     "最简水面突袭"的定位；
    #   * IE-07 我机 4→3 架：p17 得 0.7908 高于 IE-06 的 0.6204，按序号应更难。
    # ------------------------------------------------------------------
    pressure = {
        1: dict(red_uav=4, red_boat=0, blue_uav=4, blue_usv=2, ingress=1.00,
                blue_ammo=3, blue_usv_ammo=2),
        2: dict(red_uav=4, red_boat=0, blue_uav=3, blue_usv=2, ingress=0.95,
                blue_ammo=4, blue_usv_ammo=2),
        3: dict(red_uav=0, red_boat=3, blue_uav=2, blue_usv=7, ingress=0.95,
                blue_ammo=3, blue_usv_ammo=2),
        4: dict(red_uav=4, red_boat=4, blue_uav=3, blue_usv=5, ingress=0.88,
                blue_ammo=3, blue_usv_ammo=2),
        5: dict(red_uav=5, red_boat=4, blue_uav=4, blue_usv=5, ingress=0.82,
                blue_ammo=3, blue_usv_ammo=2),
        6: dict(red_uav=5, red_boat=4, blue_uav=5, blue_usv=5, ingress=0.76,
                blue_ammo=3, blue_usv_ammo=2),
        7: dict(red_uav=7, red_boat=5, blue_uav=3, blue_usv=6, ingress=0.70,
                blue_ammo=3, blue_usv_ammo=2),
    }
    for item in specs:
        apply_pressure(item, pressure.get(item["index"]))
    return specs

def apply_pressure(item: dict, target: dict | None) -> None:
    """按目标编成增删双方兵力（第 10 轮加压）。"""

    if not target:
        return

    # --- 威胁方无人机：按需增删（诱饵不计入 red_uav）---
    uavs = [e for e in item["intruder"]
            if "uav" in e["id"] and "decoy" not in e["id"]]
    boats = [e for e in item["intruder"] if "boat" in e["id"]]
    others = [e for e in item["intruder"] if e not in uavs and e not in boats]

    def grow(pool: list[dict], want: int, prefix: str, dy: float) -> list[dict]:
        pool = list(pool)
        index = 0
        while len(pool) < want:
            template = pool[index % len(pool)] if pool else None
            if template is None:
                break
            clone = copy.deepcopy(template)
            serial = 90 + len(pool)
            clone["id"] = f"intruder.{prefix}-{serial:02d}"
            clone["initial_state"]["position_m"][1] += dy * (len(pool) - index + 1)
            # 只做横向展开、**不改变来袭距离**：加压必须干净地归因于"数量增加"。
            # 早先这里写成 x += 300/个，等于把增援放到更远处、给了我方更长预警，
            # 结果 IE-04 加了威胁反而从 0.833 升到 0.873 —— 与加压方向相反。
            pool.append(clone)
            index += 1
        return pool[:want]

    if uavs or target["red_uav"]:
        uavs = grow(uavs, int(target["red_uav"]), "uav", 700.0)
        # 威胁无人机载弹 4 -> 1（第 12 轮）：这是**消除结局二值跳变**的关键。
        #
        # 实测毁伤链（见 _w1_ladder_calc.py 注释、damage_v2.py:440）：每发命中
        # 扣 `magnitude` = 0.6 生命，阈值硬编码为失能 ≤0.5 / 摧毁 ≤0.0。
        # 于是一个设施只要被命中 **2 发**就被摧毁，而 3 发/架的红机只要有一架
        # 突防，2 发命中的概率就是 1-(1-0.75)³-3×0.75×0.25² ≈ 0.84 —— 结局因此
        # 在"全歼(0.89)"与"设施被毁(0.20)"之间跳变，p11/p12 两轮都出现这种二值分布。
        #
        # 降到 1 发/架后，单架突防最多只能给设施 1 发命中 ⇒ 只能"失能"(health 0.4)
        # 而不能摧毁；要摧毁必须有 **2 架**同时突防命中。于是结局分级为
        #   0 架突防 → 设施完好（易）
        #   1 架突防 → 设施失能（刚好守住）
        #   2 架突防 → 设施被毁（失守）
        # 中间档正是"我方理论最好策略刚好能够成功拦截"的位置，评分卡也因此获得
        # 真实的区分度，而不是在两个极值间跳。
        for unit in uavs:
            ammo = unit.get("ammunition")
            if ammo:
                for key in list(ammo):
                    ammo[key] = min(int(ammo[key]), 1)
    boats = grow(boats, int(target["red_boat"]), "boat", -600.0)

    item["intruder"] = uavs + boats + others

    # --- 我方兵力：按目标编成重建（沿用站位表，几何不越界）---
    item["defender"] = blue_force(int(target["blue_uav"]),
                                  int(target["blue_usv"]),
                                  uav_ammo=int(target.get("blue_ammo", 2)),
                                  usv_ammo=int(target.get("blue_usv_ammo",
                                                          target.get("blue_ammo", 2))))
    item["blue_uavs"] = int(target["blue_uav"])
    item["blue_usvs"] = int(target["blue_usv"])
    item["pressure"] = dict(target)

    # 来袭距离缩放：<1 表示从更近处出现，直接压缩我方预警窗口与拦截纵深。
    # 这是控制难度最直接的杠杆 —— 仅靠加数量实测不足以形成单调阶梯
    # （IE-04 加到 4 威胁后反而更易守，因为威胁被分散在两个域、各自都不难拦）。
    scale = float(target.get("ingress", 1.0))
    if scale != 1.0:
        for unit in item["intruder"]:
            position = unit["initial_state"]["position_m"]
            position[0] = round(position[0] * scale, 1)
            position[1] = round(position[1] * scale, 1)



# ---------------------------------------------------------------------------
# resource bundle
# ---------------------------------------------------------------------------
def build_bundle() -> list[dict]:
    payload = yaml.safe_load(SRC_BUNDLE.read_text(encoding="utf-8"))
    out = [copy.deepcopy(item) for item in payload["resources"]]
    ids = {item["id"] for item in out}
    # 注（第 12 轮否证）：曾把 sensor.interceptor-radar 的探测距离由 15 km 收到
    # 10 km、把 weapon.air-interceptor-munition 的 max_range 由 8 km 收到 4.5 km，
    # 想靠"压缩交战窗口"制造突防。实测 7 个场景里 6 个分数反而上升或持平
    # （IE-01 0.774→0.875、IE-02 0.774→0.867、IE-07 0.724→0.751），与加压意图相反，
    # 因此**不保留该改动**。包线不是可用的难度杠杆 —— 下一轮改用别的手段，
    # 并先做单场景探针确认机制再动全局参数。
    #
    # ------------------------------------------------------------------
    # 第 14 轮：水面交战的两处口径（经确认后的口径）
    # ------------------------------------------------------------------
    # (1) `weapon.surface-missile` **保持原设计**：15 m/s 的"慢速鱼雷"
    #     （`_gen_md_ad_006.py` 原文即"水面鱼雷巡航速度 15 m/s"，交付模型是
    #     guided_missile）。这与 10 m/s 的自爆船相比**只有 5 m/s 追击速度优势**，
    #     正面对冲时约 25 m/s（3 km 需 ~120 s，在 max_flight_ticks 400 之内），
    #     尾追则需 ~600 s 超出航时 —— 因此是否命中高度依赖几何。
    #     第 14 轮曾把它改成 60/120 m/s，实测把 IE-03 从 0.583 抬到 0.704，
    #     但那实质是**设计变更而非缺陷修复**，已按确认**回退**。
    #     水面拦截的可行性改由**兵力数量/弹药**保证（见 pressure 表的 usv 列），
    #     而不是靠改武器性格。
    # (2) `weapon.suicide-warhead` 的起爆距离由 30 m 放宽到 **150 m**。
    #     原设计是 `delivery_model: contact_detonation`（靠撞击引爆），
    #     后果是"自爆船实际是撞上去的"：毁伤由 world.spatial_damage_policy 的
    #     collision-impact 给出，实测 IE-03 出现 228 次 collision 毁伤意图而只有
    #     2 次 weapon，泊位 `shots_taken = 0` 却被撞到 disabled ——
    #     交战因此不体现为"武器事件"，我方拦阻也无法在武器口径上体现。
    #     150 m 定角起爆让"自爆战斗部"成为真正的交战手段，同时给我方留出
    #     在引爆前拦下的窗口。这是**经确认保留**的口径变更。
    for item in out:
        if item["id"] == "weapon.suicide-warhead":
            item["content"]["min_range_m"] = 0.0
            item["content"]["max_range_m"] = 150.0
        elif item["id"] == "weapon.surface-missile":
            # (1b) 15 m/s 的航速**保持不动**（原设计），只把近炸引信半径由 8 m
            #      放宽到 25 m —— 与另外两种弹（loitering 15 / interceptor 25）对齐。
            #      依据：8 m 是三者中最紧的，而这一发弹的速度也是三者中最低的
            #      （15 m/s 对 10 m/s 目标，`max_turn_rate_deg_s` 30、加速度 5 m/s²），
            #      实测 IE-03（纯水面、只有这一种武器）**11 发 0 击杀**；
            #      把弹速改成 120 m/s 后 6 发 2 击杀。也就是说"打不中"的主因是
            #      近炸判定过苛，而不是弹速本身 —— 因此按最小改动修引信，而不是
            #      改武器性格。核验见 q 系列探针与 s1 实验的运行记录 §9。
            missile = item["content"].setdefault("missile", {})
            missile["fuse_radius_m"] = 25.0
    if "platform.shore-sensor-site" not in ids:
        out.append({
            "schema_version": "2.0",
            "resource_type": "platforms",
            "id": "platform.shore-sensor-site",
            "version": "2.0.0",
            "engine_compatibility": ENGINE_COMPAT,
            "model_id": MODEL,
            "dependencies": [],
            "content": {
                # 岸基传感器站：只有传感器与通信，没有武器。
                # 带 `sensor-site` 标签 → strategy_metrics.classify_role 归为 other，
                # 既不计入受保护设施，也不计入任何一方的兵力总数。
                "platform_type": "fixed-sensor-site",
                "domain": "land",
                "mobile": False,
                "allowed_dynamics": ["dynamics.fixed-site@2.0.0"],
                # 两部雷达（远程预警 + 低空补盲）→ sensor 槽容量必须是 2，
                # 否则编译期报 "combined component slot capacity exceeded"。
                "component_slots": ["sensor", "sensor", "communication"],
                "loadout_slots": [],
                "payload_capacity_kg": 0.0,
                "mass_kg": 3000.0,
                "energy_ref": "energy.normalized@2.0.0",
                "collision_shape_ref": "shape.fixed-site@2.0.0",
                "visualization_ref": "visual.fixed-site@2.0.0",
            },
        })
    return out


# ---------------------------------------------------------------------------
# scenario package
# ---------------------------------------------------------------------------
def controller_slots(all_entities: list[dict]) -> list[dict]:
    """One slot per entity, endpoint = the entity itself (zero-hop)."""
    slots = []
    for entity in all_entities:
        entity_id = str(entity["id"])
        suffix = entity_id.split(".", 1)[-1].replace(".", "-")
        required = ["weapon"] if entity.get("loadout_ref") else (
            ["sensor"] if any(str(ref).startswith("sensor.")
                              for ref in entity.get("component_refs", ()))
            else [])
        slots.append({
            "schema_version": "2.0",
            "id": f"controller.{entity['faction_id'].split('.')[-1]}.{suffix}",
            "controller_id": f"agent.{entity_id}",
            "faction_id": entity["faction_id"],
            "selector": {"schema_version": "2.0", "entity_ids": [entity_id]},
            "controller_endpoint_ref": entity_id,
            "required_capabilities": required,
            "action_schema_ref": "action-batch@2.0",
            "observation_schema_ref": "observation@2.0",
            "exclusive": True,
        })
    return slots


def build_scenario(spec: dict) -> dict:
    duration = int(spec["duration"])
    entities: list[dict] = []
    events: list[dict] = []

    for fid in spec["protected"]:
        entities.append(facility_block(fid))
    entities.append(shore_site())
    entities.extend(spec["defender"])

    spawn_ticks = dict(spec.get("spawn_ticks") or {})
    for unit in spec["intruder"]:
        tick = int(spawn_ticks.get(str(unit["id"]), 0))
        if tick == 0:
            entities.append(unit)
            continue
        blueprint = copy.deepcopy(unit)
        blueprint.pop("controller_slot", None)
        events.append({
            "schema_version": "2.0",
            "id": f"spawn.{unit['id']}",
            "event_type": "spawn",
            "trigger": {"kind": "tick", "tick": tick},
            "priority": 100,
            "depends_on": [],
            "payload": {"entity": blueprint},
        })

    every = [*entities, *(copy.deepcopy(e["payload"]["entity"]) for e in events)]

    # 恶劣天气：最后三个（最难）场景按顺序**越来越早**转雨雾，形成单调的天气阶梯。
    # environment.rain-fog 会砍掉 30% 传感器探测距离、20% 探测概率、能见度 0.65，
    # 因此直接压缩我方预警窗口与拦截纵深 —— 与"提高难度"的目标同向。
    if spec.get("fog_tick") is not None:
        events.append({
            "schema_version": "2.0", "id": "event.weather-fog",
            "event_type": "weather_change",
            "trigger": {"kind": "tick", "tick": int(spec["fog_tick"])},
            "priority": 120, "depends_on": [],
            "payload": {"environment_ref": "environment.rain-fog@2.0.0"}})

    events.extend([
        {"schema_version": "2.0", "id": "event.weather-initial",
         "event_type": "weather_change", "trigger": {"kind": "tick", "tick": 0},
         "priority": 1000, "depends_on": [],
         "payload": {"environment_ref": "environment.clear@2.0.0"}},        {"schema_version": "2.0", "id": "event.marker-assess",
         "event_type": "mission_marker",
         "trigger": {"kind": "tick", "tick": duration - 1},
         "priority": 10, "depends_on": [],
         "payload": {"marker_id": "marker.assess-protected-assets"}},
        {"schema_version": "2.0", "id": "event.assets-lost",
         "event_type": "mission_marker",
         "trigger": {"kind": "tick", "tick": duration - 1},
         "priority": 11, "depends_on": [],
         "payload": {"marker_id": "marker.assets-lost"}},
        {"schema_version": "2.0", "id": "event.defence-success",
         "event_type": "mission_marker",
         "trigger": {"kind": "tick", "tick": duration - 1},
         "priority": 12, "depends_on": [],
         "payload": {"marker_id": "marker.defence-success"}},
        # 提前终局：任一方作战力量被全歼即立即中止并判定胜负
        {"schema_version": "2.0", "id": "event.intruders-destroyed",
         "event_type": "mission_marker",
         "trigger": {"kind": "tick", "tick": duration - 1},
         "priority": 13, "depends_on": [],
         "payload": {"marker_id": "marker.intruders-destroyed"}},
        {"schema_version": "2.0", "id": "event.defenders-destroyed",
         "event_type": "mission_marker",
         "trigger": {"kind": "tick", "tick": duration - 1},
         "priority": 14, "depends_on": [],
         "payload": {"marker_id": "marker.defenders-destroyed"}},
    ])

    zones = [polygon_circle(f"zone.target.{fid}", PORT_ASSETS[fid][1][0],
                            PORT_ASSETS[fid][1][1], ZONE_RADIUS_M,
                            ["target", "facility", f"target.{fid}"])
             for fid in spec["protected"]]

    return {
        "schema_version": "package@2.0",
        "scenario": {
            "schema_version": "2.0",
            "scenario_id": f"{spec['public_id'].lower()}.v1",
            "display_name": f"{spec['public_id']} {spec['zh']}（{SET_NAME}）",
            "factions": [
                {"schema_version": "2.0", "id": "coalition.defender",
                 "display_name": "防御方"},
                {"schema_version": "2.0", "id": "coalition.intruder",
                 "display_name": "突防方"},
            ],
            "relationships": [
                {"schema_version": "2.0", "source_faction_id": "coalition.defender",
                 "target_faction_id": "coalition.intruder", "relation": "hostile"},
                {"schema_version": "2.0", "source_faction_id": "coalition.intruder",
                 "target_faction_id": "coalition.defender", "relation": "hostile"},
            ],
            "entities": entities,
            "formations": [],
            "events": events,
            "world": {
                "schema_version": "2.0",
                "coordinate_system": "local_m",
                "map_ref": "map.weihai-local@2.0.0",
                "duration_ticks": duration,
                "tick_seconds": 1.0,
                "spatial_damage_policy": {
                    "schema_version": "2.0",
                    "collision_effect_ref": "effect.collision-impact@2.0.0",
                    "magnitude_model": "scaled_relative_speed",
                    "magnitude_parameters": {"scale": 0.01},
                    "output_unit": "1",
                },
                "zones": zones,
                "roe_rules": [
                    {"schema_version": "2.0", "id": "roe.defender-engage-intruder",
                     "source_faction_id": "coalition.defender",
                     "target_faction_id": "coalition.intruder",
                     "relationship": "hostile", "engagement_permitted": True},
                    {"schema_version": "2.0", "id": "roe.intruder-engage-defender",
                     "source_faction_id": "coalition.intruder",
                     "target_faction_id": "coalition.defender",
                     "relationship": "hostile", "engagement_permitted": True},
                ],
            },
            "mission_states": sorted(["state.active", "state.assets-lost",
                                      "state.defence-success",
                                      "state.intruders-destroyed",
                                      "state.defenders-destroyed"]),
            "mission_rules": [
                {
                    "schema_version": "2.0",
                    "id": "rule.assets-lost",
                    "priority": 100,
                    "depends_on": [],
                    "condition": {
                        "schema_version": "2.0",
                        "operator": "count",
                        "selector": {"schema_version": "2.0",
                                     "factions": ["coalition.defender"],
                                     "tags": ["facility"]},
                        "parameters": {"comparison": "<=", "value": 0},
                    },
                    "outcome": {"set_state": "state.assets-lost",
                                "emit_event": "event.assets-lost",
                                "terminal": True, "result": "intruder_success",
                                "ranking": {"coalition.intruder": 1,
                                            "coalition.defender": 2}},
                },
                {
                    "schema_version": "2.0",
                    "id": "rule.defenders-destroyed",
                    "priority": 90,
                    "depends_on": [],
                    "condition": {
                        "schema_version": "2.0",
                        "operator": "count",
                        # 只数我方作战单元（无人机 + 无人船）：设施与岸基传感器站
                        # 也带 defence 标签，但不是作战力量
                        "selector": {"schema_version": "2.0",
                                     "factions": ["coalition.defender"],
                                     "tags": ["combat-unit"],
                                     # 只有还能作战（active/degraded）的单元才算数
                                     "include_lifecycle": ["scheduled", "active",
                                                           "degraded"]},
                        "parameters": {"comparison": "<=", "value": 0},
                    },
                    "outcome": {"set_state": "state.defenders-destroyed",
                                "emit_event": "event.defenders-destroyed",
                                "terminal": True, "result": "intruder_success",
                                "ranking": {"coalition.intruder": 1,
                                            "coalition.defender": 2}},
                },
                {
                    "schema_version": "2.0",
                    "id": "rule.intruders-destroyed",
                    "priority": 60,
                    "depends_on": [],
                    "condition": {
                        "schema_version": "2.0",
                        "operator": "count",
                        # 威胁方全部实体（无人机 + 自爆船）都带 intruder 标签
                        "selector": {"schema_version": "2.0",
                                     "factions": ["coalition.intruder"],
                                     "tags": ["intruder"],
                                     # 失能的自爆船/无人机已无法进攻（引擎的交战门槛
                                     # 是 active/degraded），因此不再计入"还有威胁"
                                     "include_lifecycle": ["scheduled", "active",
                                                           "degraded"]},
                        "parameters": {"comparison": "<=", "value": 0},
                    },
                    "outcome": {"set_state": "state.intruders-destroyed",
                                "emit_event": "event.intruders-destroyed",
                                "terminal": True, "result": "defender_success",
                                "ranking": {"coalition.defender": 1,
                                            "coalition.intruder": 2}},
                },
                {
                    "schema_version": "2.0",
                    "id": "rule.defence-success",
                    "priority": 50,
                    "depends_on": [],
                    "condition": {
                        "schema_version": "2.0",
                        "operator": "time",
                        "selector": {"schema_version": "2.0",
                                     "factions": ["coalition.defender"]},
                        # 规则按区间起始 tick 求值，故阈值取最后一个被求值的 tick
                        "parameters": {"comparison": ">=", "tick": duration - 1},
                    },
                    "outcome": {"set_state": "state.defence-success",
                                "emit_event": "event.defence-success",
                                "terminal": True, "result": "defender_success",
                                "ranking": {"coalition.defender": 1,
                                            "coalition.intruder": 2}},
                },
            ],
            "scoring": {
                "aggregation": "sum",
                "direction": "maximize",
                "weight_policy": "normalized_sum_one",
                # 单一静态指标：存活设施计数。weight_policy 要求权重和为 1，
                # 因此必须显式声明 metrics（空 metrics 会被判
                # scenario.scoring_weight_policy_invalid）。
                "metrics": [
                    {"id": "score.facility-integrity",
                     "selector": {"schema_version": "2.0",
                                  "factions": ["coalition.defender"],
                                  "tags": ["facility"]},
                     "aggregation": "count",
                     "unit": "1",
                     "direction": "maximize",
                     "weight": 1.0,
                     "available": True,
                     "value": float(len(spec["protected"]))},
                ],
            },
            "controller_slots": controller_slots(every),
            # 显式声明控制策略：声明了 controller_slots 就必须给出该字段，
            # 否则编译期报 scenario.controller_policy_missing。
            "controller_policy": "explicit_uncontrolled",
        },
    }


# ---------------------------------------------------------------------------
# 突防方开火规则（attack.weapon_policies）
# ---------------------------------------------------------------------------
# 驱动层 `AttackProfileDriverV2._maybe_fire` 按 `match_tag` 在实体标签上匹配
# 策略，**匹配不到就永远不提交开火**；策略的唯一来源是 agents.yaml 的
# `attack.weapon_policies`。射程窗口必须等于武器资源自身的 min/max_range_m，
# 否则驱动的射程闸门与引擎包线不一致：要么把必然被拒的提交白白计进预算，
# 要么在合法窗口内反而不开火。
ATTACK_WEAPONS = {
    "ammunition.loitering-munition@2.0.0": {
        "weapon_ref": "weapon.loitering-munition@2.0.0",
        "min_range_m": 500.0,
        "max_range_m": 8000.0,
        # 1 发留给指定设施：在尚未向指定目标开火前不对其他目标打光弹药
        # （实测 2 发全花在蓝方无人机上，设施 health 始终 1.0）
        "reserve_for_assigned": 1,
    },
    "ammunition.suicide-warhead@2.0.0": {
        "weapon_ref": "weapon.suicide-warhead@2.0.0",
        "min_range_m": 0.0,
        # 射程窗口必须与 bundle 里的 `weapon.suicide-warhead.max_range_m` 一致
        # （结构自检 F 段会核对）。0–30 m 时自爆船实际是"撞上去"的，见 build_bundle。
        "max_range_m": 150.0,
        "reserve_for_assigned": 0,
    },
}


def attack_weapon_policies(spec: dict) -> list[dict]:
    """由**实际生成的威胁实体**反推开火策略，杜绝"申报了弹药却没有开火入口"。

    第 11 轮定位到的根因：7 个 IE 场景的 agents.yaml 完全没有本块，红方一路
    飞到设施 200–300 m 上空却一发未发（实测 IE-01..07 `fires_red = 0`）。
    随之而来的是设施/漏防/交换/水面四层恒为 1.0 —— 0.80 的权重完全不参与
    区分，评分卡退化成"只有纵深层在动"，同时"双方确实有交互"也不成立。

    只对带 `target.` 指派且有弹药的实体生成策略：诱饵既无弹药也无目标指派，
    本来就不该有开火入口。`shots` 取同组实体申报弹药的**最小值**，保证任何
    一架的申报量都不会被超发（弹药账目自洽是硬约束）。
    """
    counts: dict[tuple[str, str], list[int]] = {}
    for entity in spec["intruder"]:
        tags = {str(tag) for tag in entity.get("tags") or ()}
        if not any(tag.startswith("target.") for tag in tags):
            continue
        match_tag = "boat" if "boat" in tags else "uav" if "uav" in tags else None
        if match_tag is None:
            continue
        for ammo_ref, count in (entity.get("ammunition") or {}).items():
            if str(ammo_ref) not in ATTACK_WEAPONS:
                continue
            counts.setdefault((match_tag, str(ammo_ref)), []).append(int(count))

    policies: list[dict] = []
    for (match_tag, ammo_ref), declared in sorted(counts.items()):
        row = ATTACK_WEAPONS[ammo_ref]
        policies.append({
            "match_tag": match_tag,
            "weapon_ref": row["weapon_ref"],
            "min_range_m": row["min_range_m"],
            "max_range_m": row["max_range_m"],
            "shots": min(declared),
            "reserve_for_assigned": row["reserve_for_assigned"],
        })
    return policies


def build_agents(spec: dict) -> dict:
    return {
        "schema_version": "rule-agent-team@2.0",
        "set": {"name": SET_NAME, "member_index": spec["index"],
                "zh_name": spec["zh"], "notes": spec["notes"]},
        "objective_m": list(PORT_ASSETS[spec["protected"][0]][1]),
        "protected_zone_bounds_m": [
            min(PORT_ASSETS[f][1][0] for f in spec["protected"]) - ZONE_RADIUS_M,
            min(PORT_ASSETS[f][1][1] for f in spec["protected"]) - ZONE_RADIUS_M,
            max(PORT_ASSETS[f][1][0] for f in spec["protected"]) + ZONE_RADIUS_M,
            max(PORT_ASSETS[f][1][1] for f in spec["protected"]) + ZONE_RADIUS_M,
        ],
        "decision_interval_ticks": 5,
        "facility_weights": {fid: float(spec["weights"].get(fid, WEIGHTS_DEFAULT))
                             for fid in spec["protected"]},
        "defence": {
            "faction_id": "coalition.defender",
            "contact_confidence": 0.0,
            "maximum_contact_age_ticks": 8,
            "intercept_speed_mps": 43.0,
            "weapon_policies": [
                {"selector_tags": ["interceptor"],
                 "weapon_ref": "weapon.air-interceptor-munition@2.0.0",
                 "minimum_range_m": 500.0, "maximum_range_m": 8000.0,
                 "cooldown_ticks": 5},
                {"selector_tags": ["usv"],
                 "weapon_ref": "weapon.surface-missile@2.0.0",
                 "minimum_range_m": 0.0, "maximum_range_m": 3000.0,
                 "cooldown_ticks": 3},
            ],
        },
        "attack": {
            "faction_id": "coalition.intruder",
            "pattern": "direct",
            "speed_mps": 43.0,
            "split_angle_deg": 0.0,
            "serpentine_angle_deg": 0.0,
            "serpentine_period_ticks": 1,
            "routes": list(spec["routes"]),
            "timeline": list(spec["timeline"]),
            # 红方开火入口：缺了它红方就是"飞到头顶也不开火"的靶机
            "weapon_policies": attack_weapon_policies(spec),
        },
    }


def main() -> int:
    resources = build_bundle()
    OUT_BUNDLE.write_text(
        yaml.safe_dump({"schema_version": "catalog-bundle@2.0",
                        "resources": resources},
                       allow_unicode=True, sort_keys=False, width=200),
        encoding="utf-8")
    print(f"wrote {OUT_BUNDLE} ({len(resources)} resources)")

    specs = scenario_specs()
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    wanted = {spec["public_id"] for spec in specs}
    registry["scenarios"] = [item for item in registry["scenarios"]
                             if item["public_id"] not in wanted]

    for spec in specs:
        package = f"ie_{spec['index']:02d}_{spec['slug']}"
        pkg_dir = FORMAL / package
        pkg_dir.mkdir(parents=True, exist_ok=True)
        (pkg_dir / "scenario.yaml").write_text(
            yaml.safe_dump(build_scenario(spec), allow_unicode=True,
                           sort_keys=False, width=400),
            encoding="utf-8")
        (pkg_dir / "agents.yaml").write_text(
            yaml.safe_dump(build_agents(spec), allow_unicode=True,
                           sort_keys=False, width=200),
            encoding="utf-8")
        registry["scenarios"].append({
            "public_id": spec["public_id"],
            "package": package,
            "catalog_bundle": "ie_set",
        })
        print(f"wrote {pkg_dir.name}: scenario.yaml + agents.yaml  "
              f"({spec['public_id']})")

    REGISTRY.write_text(
        yaml.safe_dump(registry, allow_unicode=True, sort_keys=False, width=200),
        encoding="utf-8")
    print(f"registry now has {len(registry['scenarios'])} scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
