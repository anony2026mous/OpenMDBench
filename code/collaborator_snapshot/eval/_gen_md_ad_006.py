"""Generate the MD-AD-006 island-strike scenario package + its catalog bundle.

Run from the engine root with the engine venv:
    .venv/bin/python /mnt/c/.../_gen_md_ad_006.py

Writes (data only; no engine source is touched):
    catalog/v2/md_ad_006.yaml
    scenarios/formal/ie_08_island_strike/scenario.yaml
    scenarios/formal/ie_08_island_strike/agents.yaml
    scenarios/formal/registry.yaml  (append one entry)

Design (per B-line request):
    red:  12 UAVs (2 missiles each, 2 waves of 6) + 5 suicide USVs
    blue:  9 UAVs (2 missiles each) + 3 armed USVs (2 short-range surface missiles each)
    facilities: 3 on the island (command post / comms hub / fuel depot) + 1 submarine pier in the harbour
    UAVs strike the three island facilities; suicide USVs strike the submarine pier
"""
from __future__ import annotations

import copy
import os
import sys
import math
from pathlib import Path

import yaml

# 引擎根目录：优先取 OPENMDBENCH_ROOT，否则用本脚本所在的 openmd 检出旁的
# source-code/source_codes 子模块（Windows 与 Linux 都能直接跑，不再写死
# /root/source_codes_linux/source_codes）。
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT")
            or Path(__file__).resolve().parents[2] / "source-code" / "source_codes")
SRC_BUNDLE = ROOT / "catalog/v2/md_ad_002.yaml"
OUT_BUNDLE = ROOT / "catalog/v2/md_ad_006.yaml"
PKG_DIR = ROOT / "scenarios/formal/ie_08_island_strike"
REGISTRY = ROOT / "scenarios/formal/registry.yaml"
ENGINE_COMPAT = ">=2.0.0,<3.0.0"
MODEL = "models.formal-data@2.0.0"

PLATFORM_TYPES = [
    "fixed-sensor-site",
    "interceptor-uav",
    "armed-usv",
    "suicide-usv",
    "harbor-pier",
]

# Episode length in ticks (world.duration_ticks).
DURATION_TICKS = 1800


def load_source() -> dict:
    payload = yaml.safe_load(SRC_BUNDLE.read_text(encoding="utf-8"))
    return {f"{res['id']}@{res['version']}": res for res in payload["resources"]}


def res(resource_type: str, rid: str, content: dict, dependencies: list | None = None,
        model: str | None = None) -> dict:
    return {
        "schema_version": "2.0",
        "resource_type": resource_type,
        "id": rid,
        "version": "2.0.0",
        "engine_compatibility": ENGINE_COMPAT,
        "model_id": model or MODEL,
        "dependencies": list(dependencies or []),
        "content": content,
    }


def build_bundle() -> list[dict]:
    src = load_source()
    out: list[dict] = []

    def take(rid: str) -> dict:
        return copy.deepcopy(src[rid])

    def retarget(resource: dict, rid: str, **content_updates) -> dict:
        item = copy.deepcopy(resource)
        item["id"] = rid
        item["version"] = "2.0.0"
        item["content"].update(content_updates)
        return item

    # ---- map -------------------------------------------------------------
    out.append(take("map.weihai-local@2.0.0"))

    # ---- dynamics --------------------------------------------------------
    # Sim2Sea 的 nps 是螺旋桨每秒转数，标定关系 200 NPS <-> 15 m/s
    # （≈13.33 NPS 每 m/s）。10 m/s 的船体满车需 max_nps≈133。
    # 引擎侧的置信上限原为写死的 5.0（会导致实测航速只有 0.30 m/s），
    # 现已改为与 max_speed_mps<=12.9 自洽的 200（openmdbench/core/units.py:
    # MMG_TRUSTED_MAX_NPS）。
    USV_MAX_NPS = 200.0 / 15.0 * 10.0
    out.append(take("dynamics.fixed-site@2.0.0"))
    out.append(take("dynamics.interceptor-uav@2.0.0"))
    out.append(retarget(take("dynamics.picket-usv@2.0.0"), "dynamics.armed-usv",
                        compatible_platform_types=["armed-usv"], max_speed_mps=10.0,
                        max_nps=USV_MAX_NPS))
    out.append(retarget(take("dynamics.picket-usv@2.0.0"), "dynamics.suicide-usv",
                        compatible_platform_types=["suicide-usv"], max_speed_mps=10.0,
                        max_nps=USV_MAX_NPS))
    out.append(res("dynamics", "dynamics.static-structure",
                   {"compatible_platform_types": ["harbor-pier"], "mobile": False},
                   model="models.native-fixed@2.0.0"))

    # ---- collision shapes ------------------------------------------------
    out.append(take("shape.fixed-site@2.0.0"))
    out.append(take("shape.interceptor-uav@2.0.0"))
    out.append(take("shape.picket-usv@2.0.0"))
    out.append(res("collision_shapes", "shape.harbor-pier",
                   {"compatible_domains": ["surface"], "shape": "sphere",
                    "radius_m": 15.0}))
    # V2 的碰撞窄相只支持"球-球"，无人船与码头必须用球体，否则一旦接近就报
    # boundary.shape_sweep_unsupported
    out.append(res("collision_shapes", "shape.usv-sphere",
                   {"compatible_domains": ["surface"], "shape": "sphere",
                    "radius_m": 3.0}))

    # ---- visualization assets -------------------------------------------
    out.append(take("visual.fixed-site@2.0.0"))
    out.append(take("visual.interceptor-uav@2.0.0"))
    out.append(take("visual.picket-usv@2.0.0"))
    out.append(res("visualization_assets", "visual.harbor-pier",
                   {"compatible_domains": ["surface"], "profile": "submarine_pier_generic",
                    "length_m": 240.0, "width_m": 36.0, "color_role": "faction"}))

    # ---- energy / communications (shared by all platform types) ----------
    out.append(res("energy", "energy.normalized",
                   {"compatible_platform_types": PLATFORM_TYPES, "capacity_j": 1.0}))
    out.append(res("communications", "communication.command-network",
                   {"compatible_platform_types": PLATFORM_TYPES,
                    "slot_type": "communication",
                    "range_m": 50000.0,
                    "bandwidth_bps": 10000000,
                    "delay_ticks": 1}))

    # ---- sensors ---------------------------------------------------------
    #
    # 接触寿命必须显式声明。引擎对"传感器生成的接触"只在
    # `tick - observed_tick < stale_after_ticks` 内保留记录
    # （world/factory_v2.py:3912-3916），而 systems/generic_v2.py:213-218 的
    # 缺省值是 `confirmation_frames=1, stale_after_ticks=1,
    # engagement_max_age_ticks=stale_after_ticks=1`。
    #
    # 本场景的指挥链有 `communication.command-network` 的 `delay_ticks=1`：
    # 开火指令在提交后 1 tick 才投递，此时按缺省寿命（1 tick）该接触已被删除，
    # `contact_store.resolve` 返回 None → `contact_quality=0` →
    # 直接踩中 `contact` 阶段的首个失败条件 → 合法开火被判
    # `combat.contact_denied`。实测表现是"偶尔打得出去、多数被拒"，
    # 拒绝与否只取决于开火 tick 与传感器刷新节拍是否恰好对齐；
    # 红方对岛内设施（静止目标、接触更易过期）几乎全部被拒。
    #
    # 这里显式给出一个覆盖"指令延迟 + 传感器刷新节拍"的寿命窗口，
    # 对红蓝双方完全对称，只为消除引擎缺省值与场景指挥链之间的伪阻塞。
    CONTACT_FIELDS = {
        "confirmation_frames": 1,
        "stale_after_ticks": 12,
        "engagement_max_age_ticks": 12,
        "minimum_contact_confidence": 0.0,
    }

    def sensor(rid: str, **content_updates) -> dict:
        return retarget(take(f"{rid}@2.0.0"), rid, **CONTACT_FIELDS, **content_updates)

    out.append(sensor("sensor.shore-early-warning"))
    out.append(sensor("sensor.shore-gap-filler"))
    out.append(sensor("sensor.interceptor-radar"))
    out.append(sensor("sensor.interceptor-eo"))
    # 水面雷达：额外限定可用平台类型（武装无人艇 / 自杀艇 / 码头共用）
    out.append(retarget(take("sensor.picket-radar@2.0.0"), "sensor.usv-radar",
                        compatible_platform_types=["armed-usv", "suicide-usv", "harbor-pier"],
                        **CONTACT_FIELDS))

    # ---- platforms -------------------------------------------------------
    out.append(take("platform.shore-defence-site@2.0.0"))
    out.append(take("platform.interceptor-uav@2.0.0"))
    out.append(res("platforms", "platform.armed-usv",
                   {"platform_type": "armed-usv", "domain": "surface", "mobile": True,
                    "allowed_dynamics": ["dynamics.armed-usv@2.0.0"],
                    "component_slots": ["surface-weapon", "sensor", "communication"],
                    "loadout_slots": ["surface-weapon"],
                    "payload_capacity_kg": 350.0, "mass_kg": 5200.0,
                    "energy_ref": "energy.normalized@2.0.0",
                    "collision_shape_ref": "shape.usv-sphere@2.0.0",
                    "visualization_ref": "visual.picket-usv@2.0.0"}))
    out.append(res("platforms", "platform.suicide-usv",
                   {"platform_type": "suicide-usv", "domain": "surface", "mobile": True,
                    "allowed_dynamics": ["dynamics.suicide-usv@2.0.0"],
                    "component_slots": ["suicide-warhead", "sensor", "communication"],
                    "loadout_slots": ["suicide-warhead"],
                    "payload_capacity_kg": 300.0, "mass_kg": 2800.0,
                    "energy_ref": "energy.normalized@2.0.0",
                    "collision_shape_ref": "shape.usv-sphere@2.0.0",
                    "visualization_ref": "visual.picket-usv@2.0.0"}))
    out.append(res("platforms", "platform.harbor-pier",
                   {"platform_type": "harbor-pier", "domain": "surface", "mobile": False,
                    "allowed_dynamics": ["dynamics.static-structure@2.0.0"],
                    "component_slots": ["sensor", "communication"],
                    "loadout_slots": [],
                    "payload_capacity_kg": 0.0, "mass_kg": 20000.0,
                    "energy_ref": "energy.normalized@2.0.0",
                    "collision_shape_ref": "shape.harbor-pier@2.0.0",
                    "visualization_ref": "visual.harbor-pier@2.0.0"}))

    # ---- damage models / effects ----------------------------------------
    out.append(take("damage.kinetic-terminal@2.0.0"))
    out.append(take("damage.kinetic-partial@2.0.0"))
    out.append(take("effect.interceptor-hit@2.0.0"))
    out.append(res("effects", "effect.surface-missile-hit",
                   # 与对空弹 effect.interceptor-hit 同级：kinetic-terminal / 1.0。
                   # 用 partial 0.6 时，自爆船被打到 health 0.4 就停在"失能"，
                   # 而引擎的 count/survival 算子只把 destroyed 视为不在，
                   # 于是"场上只剩失能自爆船"时提前终局规则永远不触发
                   # （胜负已定却继续跑到时间上限）。一击即毁同时消除了这个死角。
                   {"effect_type": "kinetic",
                    "damage_model_ref": "damage.kinetic-terminal@2.0.0",
                    "magnitude": 1.0, "unit": "1"},
                   dependencies=["damage.kinetic-terminal@2.0.0"]))
    out.append(res("effects", "effect.suicide-detonation",
                   {"effect_type": "kinetic",
                    "damage_model_ref": "damage.kinetic-terminal@2.0.0",
                    "magnitude": 1.0, "unit": "1"},
                   dependencies=["damage.kinetic-terminal@2.0.0"]))
    out.append(res("effects", "effect.collision-impact",
                   {"effect_type": "kinetic",
                    "damage_model_ref": "damage.kinetic-partial@2.0.0",
                    "magnitude": 0.5, "unit": "1"},
                   dependencies=["damage.kinetic-partial@2.0.0"]))
    # 红方无人机载弹必须保持 4 发/架：实测降到 3 之后红方无法压制 4 个设施
    # （每个需 2 发命中共 8 发，而大部分弹药要在突防途中被蓝方消耗），
    # IE-08 会从 red 在 t1191 取胜变成我方守满全程，难度从 0.243 掉到 0.544。
    # 巡飞弹战斗部：0.6 毁伤 → 设施需 2 发失效、2 发摧毁（配合 kinetic-partial）
    out.append(res("effects", "effect.loitering-hit",
                   {"effect_type": "kinetic",
                    "damage_model_ref": "damage.kinetic-partial@2.0.0",
                    "magnitude": 0.6, "unit": "1"},
                   dependencies=["damage.kinetic-partial@2.0.0"]))

    # ---- weapons ---------------------------------------------------------
    out.append(take("weapon.interceptor-missile@2.0.0"))
    # 巡飞弹（敌我同构的主战武器）：对空/对海/对地通用，用来打岛上设施
    out.append(res("weapons", "weapon.loitering-munition",
                   {"allowed_platform_types": ["interceptor-uav"],
                    # 红方巡飞弹：可打空中目标，也可打岛上/水上设施
                    "target_domains": ["air", "land"],
                    "effect_ref": "effect.loitering-hit@2.0.0",
                    "min_range_m": 500.0, "max_range_m": 8000.0,
                    "hit_probability": 0.75,
                    "delivery_model": "guided_missile",
                    "missile": {
                        "launch_speed_mps": 180.0,
                        "cruise_speed_mps": 250.0,
                        "max_acceleration_mps2": 60.0,
                        "max_turn_rate_deg_s": 60.0,
                        "max_vertical_speed_mps": 120.0,
                        "seeker_range_m": 5000.0,
                        "seeker_fov_deg": 130.0,
                        "seeker_detection_probability": 0.92,
                        "fuse_radius_m": 15.0,
                        "max_flight_ticks": 80,
                    },
                    "cooldown_ticks": 5, "energy_per_shot": 0.0002,
                    "rounds_per_action": 1, "contact_required": True},
                   dependencies=["effect.loitering-hit@2.0.0"]))
    out.append(res("weapons", "weapon.surface-missile",
                   {"allowed_platform_types": ["armed-usv"],
                    "target_domains": ["surface"],
                    "effect_ref": "effect.surface-missile-hit@2.0.0",
                    # 只打水面目标；射程较小、精度有限（按需求设定）
                    # min_range 取 0：水面目标贴近快，300 m 下限会让合法开火先在包线阶段失败
                    "min_range_m": 0.0, "max_range_m": 3000.0,
                    "hit_probability": 0.5,
                    # 水面鱼雷巡航速度 15 m/s（制导导弹投送模型，
                    # 飞行时间由距离/速度自然得出，而不是固定延迟）
                    "delivery_model": "guided_missile",
                    "missile": {
                        "launch_speed_mps": 15.0,
                        "cruise_speed_mps": 15.0,
                        "max_acceleration_mps2": 5.0,
                        "max_turn_rate_deg_s": 30.0,
                        "max_vertical_speed_mps": 5.0,
                        "seeker_range_m": 4000.0,
                        "seeker_fov_deg": 120.0,
                        "seeker_detection_probability": 0.9,
                        "fuse_radius_m": 8.0,
                        # 15 m/s 走完 5 km 需要 334 tick，留足余量
                        "max_flight_ticks": 400,
                    },
                    "cooldown_ticks": 3, "energy_per_shot": 0.0002,
                    "rounds_per_action": 1, "contact_required": True},
                   dependencies=["effect.surface-missile-hit@2.0.0"]))
    # 蓝方拦截弹：只打空中目标（无人机只打无人机）
    out.append(res("weapons", "weapon.air-interceptor-munition",
                   {"allowed_platform_types": ["interceptor-uav"],
                    "target_domains": ["air"],
                    "effect_ref": "effect.loitering-hit@2.0.0",
                    "min_range_m": 500.0, "max_range_m": 8000.0,
                    "hit_probability": 0.75,
                    "delivery_model": "guided_missile",
                    "missile": {
                        "launch_speed_mps": 180.0,
                        "cruise_speed_mps": 250.0,
                        "max_acceleration_mps2": 60.0,
                        "max_turn_rate_deg_s": 60.0,
                        "max_vertical_speed_mps": 120.0,
                        "seeker_range_m": 5000.0,
                        "seeker_fov_deg": 130.0,
                        "seeker_detection_probability": 0.92,
                        "fuse_radius_m": 15.0,
                        "max_flight_ticks": 80,
                    },
                    "cooldown_ticks": 5, "energy_per_shot": 0.0002,
                    "rounds_per_action": 1, "contact_required": True},
                   dependencies=["effect.loitering-hit@2.0.0"]))
    out.append(res("weapons", "weapon.suicide-warhead",
                   {"allowed_platform_types": ["suicide-usv"],
                    "target_domains": ["surface", "land"],
                    "effect_ref": "effect.suicide-detonation@2.0.0",
                    "min_range_m": 0.0, "max_range_m": 30.0,
                    "hit_probability": 1.0,
                    "delivery_model": "contact_detonation", "impact_delay_ticks": 1,
                    "cooldown_ticks": 0, "energy_per_shot": 0.0,
                    "rounds_per_action": 1, "contact_required": True},
                   dependencies=["effect.suicide-detonation@2.0.0"]))

    # ---- ammunition ------------------------------------------------------
    out.append(take("ammunition.interceptor-missile@2.0.0"))
    out.append(res("ammunition", "ammunition.surface-missile",
                   {"weapon_ref": "weapon.surface-missile@2.0.0", "mass_per_round_kg": 12.0},
                   dependencies=["weapon.surface-missile@2.0.0"]))
    out.append(res("ammunition", "ammunition.loitering-munition",
                   {"weapon_ref": "weapon.loitering-munition@2.0.0", "mass_per_round_kg": 18.0},
                   dependencies=["weapon.loitering-munition@2.0.0"]))
    out.append(res("ammunition", "ammunition.air-interceptor-munition",
                   {"weapon_ref": "weapon.air-interceptor-munition@2.0.0",
                    "mass_per_round_kg": 18.0},
                   dependencies=["weapon.air-interceptor-munition@2.0.0"]))
    out.append(res("ammunition", "ammunition.suicide-warhead",
                   {"weapon_ref": "weapon.suicide-warhead@2.0.0", "mass_per_round_kg": 120.0},
                   dependencies=["weapon.suicide-warhead@2.0.0"]))

    # ---- loadouts --------------------------------------------------------
    out.append(take("loadout.interceptor-uav@2.0.0"))
    out.append(res("loadouts", "loadout.loitering-uav",
                   {"compatible_platform_types": ["interceptor-uav"],
                    "required_slots": ["air-weapon"], "mass_kg": 90.0,
                    "weapon_refs": ["weapon.loitering-munition@2.0.0"],
                    "ammunition_refs": ["ammunition.loitering-munition@2.0.0"]},
                   dependencies=["weapon.loitering-munition@2.0.0",
                                 "ammunition.loitering-munition@2.0.0"]))
    out.append(res("loadouts", "loadout.armed-usv",
                   {"compatible_platform_types": ["armed-usv"],
                    "required_slots": ["surface-weapon"], "mass_kg": 120.0,
                    "weapon_refs": ["weapon.surface-missile@2.0.0"],
                    "ammunition_refs": ["ammunition.surface-missile@2.0.0"]},
                   dependencies=["weapon.surface-missile@2.0.0",
                                 "ammunition.surface-missile@2.0.0"]))
    out.append(res("loadouts", "loadout.air-interceptor-uav",
                   {"compatible_platform_types": ["interceptor-uav"],
                    "required_slots": ["air-weapon"], "mass_kg": 90.0,
                    "weapon_refs": ["weapon.air-interceptor-munition@2.0.0"],
                    "ammunition_refs": ["ammunition.air-interceptor-munition@2.0.0"]},
                   dependencies=["weapon.air-interceptor-munition@2.0.0",
                                 "ammunition.air-interceptor-munition@2.0.0"]))
    out.append(res("loadouts", "loadout.suicide-usv",
                   {"compatible_platform_types": ["suicide-usv"],
                    "required_slots": ["suicide-warhead"], "mass_kg": 150.0,
                    "weapon_refs": ["weapon.suicide-warhead@2.0.0"],
                    "ammunition_refs": ["ammunition.suicide-warhead@2.0.0"]},
                   dependencies=["weapon.suicide-warhead@2.0.0",
                                 "ammunition.suicide-warhead@2.0.0"]))

    # ---- environments (NOTE: modifier keys are real, unlike md_ad_002) ----
    out.append(res("environments", "environment.clear",
                   {"weather": "clear", "visibility_scale": 1.0, "sea_state": 1,
                    "sensor_range_multiplier": 1.0,
                    "sensor_detection_probability_multiplier": 1.0}))
    out.append(res("environments", "environment.rain-fog",
                   {"weather": "rain_or_fog", "visibility_scale": 0.65, "sea_state": 4,
                    "sensor_range_multiplier": 0.7,
                    "sensor_detection_probability_multiplier": 0.8}))
    return out


# ---------------------------------------------------------------------------
# scenario package
# ---------------------------------------------------------------------------

# 四个设施的"目标区"：以设施为圆心的圆（半径 300 m），供引擎规则智能体
# 与任务规则引用；红方无人机飞入/攻击这些区域即视为攻击对应设施。
TARGET_ZONE_RADIUS_M = 300.0
TARGET_ZONES = [
    ("zone.target.command", -1200.0, -200.0, "facility.command"),
    ("zone.target.comms", -800.0, 250.0, "facility.comms"),
    ("zone.target.fuel", -500.0, -900.0, "facility.fuel"),
    ("zone.target.pier", 700.0, -1000.0, "facility.pier"),
]


def circle_zone(zone_id: str, cx: float, cy: float, radius_m: float,
                tags: list) -> dict:
    """以 (cx, cy) 为圆心、radius_m 为半径的圆区。"""
    return {
        "schema_version": "2.0",
        "id": zone_id,
        "geometry_type": "circle",
        "center_m": [cx, cy],
        "radius_m": radius_m,
        "tags": tags,
    }


def polygon_circle(zone_id: str, cx: float, cy: float, radius_m: float,
                   tags: list, segments: int = 32) -> dict:
    """圆的 32 边形近似（若引擎不接受 circle 写法时使用）。"""
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
        "tags": tags,
    }


FACILITIES = [
    # id, zh name, position, tags, component refs
    ("facility.command", "指挥所", (-1200.0, -200.0, 0.0),
     ["facility", "command", "fixed"],
     ["sensor.shore-early-warning@2.0.0", "communication.command-network@2.0.0"]),
    ("facility.comms", "通信枢纽", (-800.0, 250.0, 0.0),
     ["facility", "comms", "fixed"],
     ["communication.command-network@2.0.0"]),
    ("facility.fuel", "燃料设施", (-500.0, -900.0, 0.0),
     ["facility", "fuel", "fixed"],
     ["communication.command-network@2.0.0"]),
]

PIER = ("facility.pier", "潜艇码头", (700.0, -1000.0, 0.0),
        ["facility", "pier", "harbour", "fixed"],
        ["sensor.usv-radar@2.0.0", "communication.command-network@2.0.0"])

BLUE_UAVS = [
    (4000.0, 1500.0, 800.0, 100.0), (6000.0, 1500.0, 800.0, 100.0),
    (8000.0, 1500.0, 800.0, 100.0),
    (4000.0, 0.0, 800.0, 100.0), (6000.0, 0.0, 800.0, 100.0),
    (8000.0, 0.0, 800.0, 100.0),
    (4000.0, -1500.0, 800.0, 100.0), (6000.0, -1500.0, 800.0, 100.0),
    (8000.0, -1500.0, 800.0, 100.0),
]
BLUE_USVS = [(1500.0, -500.0), (2600.0, -1500.0), (1400.0, -2400.0)]

# 红方三路直攻：每路 4 架，各自打一个岛上设施，从不同方向进入
RED_STRIKE_GROUPS = [
    # tag, 目标设施, 出发点, 高度, 航向
    ("strike-command", "facility.command", [
        (30000.0, -1400.0), (30400.0, -600.0), (30800.0, 200.0), (31200.0, 1000.0),
    ], 100.0, 270.0),
    ("strike-comms", "facility.comms", [
        (23800.0, 4600.0), (24200.0, 5200.0), (24600.0, 5800.0), (25000.0, 6400.0),
    ], 200.0, 225.0),
    ("strike-fuel", "facility.fuel", [
        (22000.0, -6600.0), (22600.0, -7200.0), (23200.0, -7800.0), (23800.0, -8400.0),
    ], 300.0, 200.0),
]
# 场景难度/波次配比（E2）：每路第一波几架，其余归第二波（t=600）
WAVE1_PER_GROUP = 1

RED_BOATS = [
    (7000.0, -2500.0), (7700.0, -2200.0), (8400.0, -2900.0),
    (9100.0, -2400.0), (9800.0, -2700.0),
]


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


def build_scenario() -> dict:
    entities = []

    # --- 3 island facilities + harbour pier ------------------------------
    for eid, _zh, position, tags, components in FACILITIES:
        entities.append(entity_block(
            eid, "coalition.defender", "platform.shore-defence-site@2.0.0",
            "dynamics.fixed-site@2.0.0", None, components, None,
            position, 0.0, tags, None, f"controller.defender.{eid}"))

    pier_id, _zh, pier_pos, pier_tags, pier_components = PIER
    entities.append(entity_block(
        pier_id, "coalition.defender", "platform.harbor-pier@2.0.0",
        "dynamics.static-structure@2.0.0", None, pier_components, None,
        pier_pos, 0.0, pier_tags, None, f"controller.defender.{pier_id}"))

    # --- blue UAVs --------------------------------------------------------
    for index, (x, y, z, heading) in enumerate(BLUE_UAVS, 1):
        eid = f"defender.uav-{index:02d}"
        entities.append(entity_block(
            eid, "coalition.defender", "platform.interceptor-uav@2.0.0",
            "dynamics.interceptor-uav@2.0.0", "loadout.air-interceptor-uav@2.0.0",
            ["sensor.interceptor-radar@2.0.0", "sensor.interceptor-eo@2.0.0",
             "communication.command-network@2.0.0"],
            {"ammunition.air-interceptor-munition@2.0.0": 2},
            (x, y, z), heading, ["defence", "combat-unit", "interceptor"], ["air"],
            f"controller.defender.{eid}"))

    # --- blue armed USVs --------------------------------------------------
    for index, (x, y) in enumerate(BLUE_USVS, 1):
        eid = f"defender.usv-{index:02d}"
        entities.append(entity_block(
            eid, "coalition.defender", "platform.armed-usv@2.0.0",
            "dynamics.armed-usv@2.0.0", "loadout.armed-usv@2.0.0",
            ["sensor.usv-radar@2.0.0", "communication.command-network@2.0.0"],
            {"ammunition.surface-missile@2.0.0": 2},
            (x, y, 0.0), 90.0, ["defence", "combat-unit", "usv", "surface"], ["surface"],
            f"controller.defender.{eid}"))

    events = [
        {"schema_version": "2.0", "id": "event.weather-initial",
         "event_type": "weather_change", "trigger": {"kind": "tick", "tick": 0},
         "priority": 1000, "depends_on": [],
         "payload": {"environment_ref": "environment.clear@2.0.0"}},
        {"schema_version": "2.0", "id": "event.weather-rain-fog",
         "event_type": "weather_change", "trigger": {"kind": "tick", "tick": 300},
         "priority": 120, "depends_on": [],
         "payload": {"environment_ref": "environment.rain-fog@2.0.0"}},
        {"schema_version": "2.0", "id": "event.marker-facilities",
         "event_type": "mission_marker", "trigger": {"kind": "tick", "tick": 1799},
         "priority": 10, "depends_on": [],
         "payload": {"marker_id": "marker.assess-facilities"}},
        # 终局规则引用的端点事件（引擎要求 outcome 事件必须被声明）
        {"schema_version": "2.0", "id": "event.facilities-lost",
         "event_type": "mission_marker", "trigger": {"kind": "tick", "tick": 1799},
         "priority": 11, "depends_on": [],
         "payload": {"marker_id": "marker.facilities-lost"}},
        {"schema_version": "2.0", "id": "event.defence-success",
         "event_type": "mission_marker", "trigger": {"kind": "tick", "tick": 1799},
         "priority": 12, "depends_on": [],
         "payload": {"marker_id": "marker.defence-success"}},
        # 提前终局：任一方作战力量被全歼即立即中止并判定胜负
        {"schema_version": "2.0", "id": "event.intruders-destroyed",
         "event_type": "mission_marker", "trigger": {"kind": "tick", "tick": 1799},
         "priority": 13, "depends_on": [],
         "payload": {"marker_id": "marker.intruders-destroyed"}},
        {"schema_version": "2.0", "id": "event.defenders-destroyed",
         "event_type": "mission_marker", "trigger": {"kind": "tick", "tick": 1799},
         "priority": 14, "depends_on": [],
         "payload": {"marker_id": "marker.defenders-destroyed"}},
    ]

    def spawn_event(event_id: str, tick: int, priority: int, blueprint: dict) -> dict:
        return {"schema_version": "2.0", "id": event_id, "event_type": "spawn",
                "trigger": {"kind": "tick", "tick": tick}, "priority": priority,
                "depends_on": [], "payload": {"entity": blueprint}}

    # 红方全部实体均由 spawn 生成；这里按生成顺序登记 id，供下面的 per-entity
    # controller_slot 使用（spawn blueprint 的 id 在编译期即可解析为槽位选择器目标）。
    intruder_entity_ids: list[str] = []

    # 红方三路直攻：每路 4 架（2 架 t=0、2 架 t=600），各自打一个岛上设施。
    #
    # 整支红方都由 spawn 事件生成（保留原波次设计）。这依赖引擎修复：交战档案
    # 必须纳入 spawn blueprint（combat/system_v2.py 的 _combat_scope_entities），
    # 否则只由 spawn 生成的一方的武器不在档案表里，每次开火都会被
    # combat.weapon_unknown 拒绝，并连带否决同一 tick 里另一方合法的开火。
    for group_index, (strike_tag, target_id, spawns, altitude, heading) in enumerate(
        RED_STRIKE_GROUPS
    ):
        for slot, (x, y) in enumerate(spawns):
            # 波次配比 E2：第一波 1 架/路（共 3 架，t=0），第二波 3 架/路（共 9 架，t=600）。
            # 原配比是第一波 6 架、第二波 6 架：实测三臂的 18 发空射弹在 tick 260 前
            # 就全砸在第一波上打光，第二波（t=600 才到）无人拦截、全部投弹成功 ——
            # 这是三臂唯一完全没被分离的维度。把主力挪到第二波，让"是否为已声明的
            # 第二波保留弹药"成为决定性决策（场景已在 attack_timeline 里声明波次，
            # 两个 LLM 臂都能看到，规则侧没有这个概念）。
            wave = 1 if slot < WAVE1_PER_GROUP else 2
            spawn_tick = 0 if wave == 1 else 600
            eid = f"intruder.{strike_tag}-{slot + 1:02d}"
            # target_domains 声明 [air, land]：总体目标是岛上设施（land），
            # 途中遇到蓝方无人机（air）也要能打。
            tags = ["intruder", f"wave-{wave}", "uav", strike_tag, f"target.{target_id}"]
            blueprint = entity_block(
                eid, "coalition.intruder", "platform.interceptor-uav@2.0.0",
                "dynamics.interceptor-uav@2.0.0", "loadout.loitering-uav@2.0.0",
                ["sensor.interceptor-radar@2.0.0", "sensor.interceptor-eo@2.0.0",
                 "communication.command-network@2.0.0"],
                {"ammunition.loitering-munition@2.0.0": 4},
                (x, y, altitude), heading, tags, ["air", "land"],
                None, speed=-43.0)
            blueprint.pop("controller_slot", None)
            intruder_entity_ids.append(eid)
            events.append(spawn_event(
                f"strike.{strike_tag}.{slot + 1:02d}", spawn_tick,
                100 - group_index * 10 - slot, blueprint))

    # red suicide boats —— 同样由 spawn 生成（t=0）
    for index, (x, y) in enumerate(RED_BOATS, 1):
        eid = f"intruder.boat-{index:02d}"
        blueprint = entity_block(
            eid, "coalition.intruder", "platform.suicide-usv@2.0.0",
            "dynamics.suicide-usv@2.0.0", "loadout.suicide-usv@2.0.0",
            ["sensor.usv-radar@2.0.0", "communication.command-network@2.0.0"],
            {"ammunition.suicide-warhead@2.0.0": 1},
            (x, y, 0.0), 270.0,
            ["intruder", "boat", "suicide", "strike-pier", "target.facility.pier"],
            ["surface", "land"], None, speed=-10.0)
        blueprint.pop("controller_slot", None)
        intruder_entity_ids.append(eid)
        events.append(spawn_event(f"boat.{index:02d}", 0, 90 - index, blueprint))

    # 红方 controller_slot：S3 契约（ADR-ENGINE-DEFECTS-001）要求每个槽位显式声明
    # controller_endpoint_ref —— 必须是同阵营、可解析、且 composition.communication_refs
    # 非空的实体。
    #
    # 采用 **per-entity 槽位、endpoint = 被控实体自身**，与蓝方以及老师参考场景
    # md_ad_002_easy 的 per-entity 槽位约定一致：endpoint 与受控实体相同即 zero-hop，
    # 指令不经通信路由。
    #
    # 反例（实测）：若改用"阵营级单 endpoint"（例如把某架红方无人机当整支红方的指挥
    # 端点），则除该机自身外，所有红方实体的指令都需要一条"endpoint → 实体"的可用
    # 通信路由；该机一旦被击落，投递阶段的 `not zero_hop and route unavailable`
    # 立刻把整支红方的指令判为 `communication.command_blocked` ——
    # rule 臂实测 tick 400 后 fires_total 冻结在 15、红方彻底失去行动能力，
    # 整局退化为"蓝方单方面收场"，三臂对比失去意义。红方应当是一个持续有效的威胁。
    controller_slots = []
    for eid in intruder_entity_ids:
        controller_slots.append({
            "id": f"controller.intruder.{eid}",
            "controller_id": f"agent.{eid}",
            "faction_id": "coalition.intruder",
            "selector": {"schema_version": "2.0", "entity_ids": [eid]},
            "controller_endpoint_ref": eid,
            "required_capabilities": ["weapon"],
            "action_schema_ref": "action-batch@2.0",
            "observation_schema_ref": "observation@2.0",
            "exclusive": True,
        })
    for entity in entities:
        if entity.get("loadout_ref"):
            required = ["weapon"]
        elif any(str(ref).startswith("sensor.") for ref in entity.get("component_refs", ())):
            required = ["sensor"]
        else:
            required = []
        controller_slots.append({
            "id": entity["controller_slot"],
            "controller_id": f"agent.{entity['id']}",
            "faction_id": entity["faction_id"],
            "selector": {"schema_version": "2.0", "entity_ids": [entity["id"]]},
            # S3：per-entity 槽位以被控实体自身为通信端点（同阵营、有通信组件）。
            "controller_endpoint_ref": entity["id"],
            "required_capabilities": required,
            "action_schema_ref": "action-batch@2.0",
            "observation_schema_ref": "observation@2.0",
            "exclusive": True,
        })

    return {
        "schema_version": "package@2.0",
        "scenario": {
            "schema_version": "2.0",
            "scenario_id": "md-ad-006.island-strike.v1",
            "display_name": "MD-AD-006 ISLAND STRIKE（同构无人机 + 岛礁设施攻防）",
            "factions": [
                {"schema_version": "2.0", "id": "coalition.defender", "display_name": "防御方"},
                {"schema_version": "2.0", "id": "coalition.intruder", "display_name": "突防方"},
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
                "duration_ticks": DURATION_TICKS,
                "tick_seconds": 1.0,
                "spatial_damage_policy": {
                    "schema_version": "2.0",
                    "collision_effect_ref": "effect.collision-impact@2.0.0",
                    "magnitude_model": "scaled_relative_speed",
                    "magnitude_parameters": {"scale": 0.01},
                    "output_unit": "1",
                },
                "zones": [
                    polygon_circle(*item[:3], TARGET_ZONE_RADIUS_M,
                                ["target", "facility", f"target.{item[3]}"]) or {}
                    for item in TARGET_ZONES
                ],
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
            # Sorted: MissionEngineV2 hashes the declaration order at build time but
            # the checkpoint stores these sorted, so an unsorted declaration makes
            # the checkpoint fail its own integrity check ("mission definition
            # evidence hash mismatch") and every checkpoint call raises.
            "mission_states": sorted(
                ["state.active", "state.facilities-lost", "state.defence-success",
                 "state.intruders-destroyed", "state.defenders-destroyed"]
            ),
            "mission_rules": [
                {
                    "schema_version": "2.0",
                    "id": "rule.facilities-lost",
                    "priority": 100,
                    "depends_on": [],
                    "condition": {
                        "schema_version": "2.0",
                        "operator": "count",
                        "selector": {"schema_version": "2.0", "factions": ["coalition.defender"],
                                     "tags": ["facility"]},
                        "parameters": {"comparison": "<=", "value": 0},
                    },
                    "outcome": {"set_state": "state.facilities-lost",
                                "emit_event": "event.facilities-lost",
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
                        # 只数我方"作战单元"（无人机 + 无人船）：facility 与
                        # sensor-site 也带 defence 标签，但它们不是作战力量，
                        # 因此用专门的 combat-unit 标签做单一标签选择器。
                        "selector": {"schema_version": "2.0",
                                     "factions": ["coalition.defender"],
                                     "tags": ["combat-unit"],
                                     "include_lifecycle": ["scheduled", "active", "degraded"]},
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
                                     "include_lifecycle": ["scheduled", "active", "degraded"]},
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
                        "selector": {"schema_version": "2.0", "factions": ["coalition.defender"]},
                        # A rule is evaluated with the *start* tick of the interval it
                        # governs (mission/score receipts carry the pre-step tick), so an
                        # episode of DURATION_TICKS steps evaluates ticks
                        # 0..DURATION_TICKS-1.  The threshold must therefore be the last
                        # evaluated tick, not `duration_ticks` — the latter is unreachable
                        # and the scenario would never latch its designed terminal.
                        "parameters": {"comparison": ">=", "tick": DURATION_TICKS - 1},
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
                # 不声明任何评分指标：V2 的评分块读取静态 value（无动态计分插件），
                # 设施攻防的分级分由评测侧按裁判真值计算，避免误导下游。
                # 引擎要求权重和为 1；这里声明一个可用的静态指标（设施完好数），
                # 真正的设施攻防分级分由评测侧按裁判真值计算（见 README）。
                "metrics": [
                    {
                        "id": "score.facility-integrity",
                        "selector": {"schema_version": "2.0", "factions": ["coalition.defender"],
                                     "tags": ["facility"]},
                        "aggregation": "count", "unit": "1", "direction": "maximize",
                        "weight": 1.0, "available": True, "value": 4.0,
                    },
                ],
            },
            "score_metrics": [],
            "controller_policy": "explicit_uncontrolled",
            "controller_slots": controller_slots,
            "visibility": [
                {"view": "referee", "scope": "truth", "allow": True},
                {"view": "public", "scope": "public", "allow": True},
            ],
        },
    }


def build_agents() -> dict:
    return {
        "schema_version": "rule-agent-team@2.0",
        # 红方脚本航路的目标点（初步构建：先飞到岛礁上空；
        # 后续红方改为策略驱动后，这里只作为默认集结点）
        "objective_m": [-900.0, -500.0],
        "decision_interval_ticks": 5,
        # 保护目标的分级权重（用于"设施加权存活"分项）：
        # 指挥所带岸基预警雷达、通信枢纽与燃料设施是作战支撑，码头相对次要。
        # 终局规则仍按"4 个设施全部摧毁"二值判定，权重只影响分档评分。
        "facility_weights": {
            "facility.command": 2.0,
            "facility.comms": 1.5,
            "facility.fuel": 1.5,
            "facility.pier": 1.0,
        },
        "attack": {
            "faction_id": "coalition.intruder",
            # 最简单的直攻：直线飞向各自目标；三路无人机从东/东北/东南三个方向进入
            "pattern": "direct",
            "speed_mps": 43.0,
            "split_angle_deg": 0.0,
            "serpentine_angle_deg": 0.0,
            "serpentine_period_ticks": 1,
            "routes": [
                {"match_tag": "strike-command", "objective_m": [-1200.0, -200.0],
                 "pattern": "direct", "speed_mps": 43.0},
                {"match_tag": "strike-comms", "objective_m": [-800.0, 250.0],
                 "pattern": "direct", "speed_mps": 43.0},
                {"match_tag": "strike-fuel", "objective_m": [-500.0, -900.0],
                 "pattern": "direct", "speed_mps": 43.0},
                {"match_tag": "strike-pier", "objective_m": [700.0, -1000.0],
                 "pattern": "direct", "speed_mps": 10.0},
            ],
            # 波次日历（场景声明的上下文，不是执行命令）：两个 LLM 臂的前置模块会把它
        # 渲染进提示词，供其判断"是否为尚未到来的第二波保留弹药"；规则侧不消费该字段。
        # 第二波是本场景主力（9/12 架），而实测蓝方 18 发空射弹会在 tick 260 前全部
        # 打光 —— 不为第二波留弹，岛上设施就没人守。
        "timeline": [
            {"label": "wave-1 probing strike", "spawn_tick": 0, "count": 3,
             "axis": "one UAV on each of the east / north-east / south-east axes",
             "behavior": "flies straight at the island facilities"},
            {"label": "wave-2 main strike", "spawn_tick": 600, "count": 9,
             "axis": "the same three axes, three UAVs each",
             "behavior": "same routes; arrives after most of wave-1 has been engaged"},
            {"label": "suicide boats", "spawn_tick": 0, "count": 5,
             "axis": "south-east surface",
             "behavior": "runs at the submarine pier"},
        ],
        # 红方教义：**总体目标是岛上设施**（每架按 target.facility.* 标签分配
            # 一个设施），途中遇到蓝方无人机就开火；但必须为指定设施保留弹药，
            # 否则弹会在途中全打在空中目标上，飞到设施上空时已无弹可用。
            # shots=4 + reserve_for_assigned=2：2 发自卫、2 发留给指定设施
            # （单发 0.6 伤害，设施 1.0 血 → 2 发命中才能摧毁）。
            # 只留 1 发时实测 4 个设施全部被打到但只到 disabled(0.4)：
            # 引擎 count/survival 算子把 disabled 仍算作"存在"，红方的
            # rule.facilities-lost（count<=0）无法触发，必须真的摧毁。
            "weapon_policies": [
                {"match_tag": "strike-command", "weapon_ref": "weapon.loitering-munition@2.0.0",
                 "min_range_m": 500.0, "max_range_m": 8000.0, "shots": 4,
                 "reserve_for_assigned": 2},
                {"match_tag": "strike-comms", "weapon_ref": "weapon.loitering-munition@2.0.0",
                 "min_range_m": 500.0, "max_range_m": 8000.0, "shots": 4,
                 "reserve_for_assigned": 2},
                {"match_tag": "strike-fuel", "weapon_ref": "weapon.loitering-munition@2.0.0",
                 "min_range_m": 500.0, "max_range_m": 8000.0, "shots": 4,
                 "reserve_for_assigned": 2},
                {"match_tag": "strike-pier", "weapon_ref": "weapon.suicide-warhead@2.0.0",
                 "min_range_m": 0.0, "max_range_m": 30.0, "shots": 1},
            ],
        },
        "defence": {
            "faction_id": "coalition.defender",
            "intercept_speed_mps": 40.0,
            "contact_confidence": 0.62,
            "maximum_contact_age_ticks": 8,
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
    }


def main() -> None:
    resources = build_bundle()
    OUT_BUNDLE.write_text(
        yaml.safe_dump({"schema_version": "catalog-bundle@2.0", "resources": resources},
                       allow_unicode=True, sort_keys=False, width=200),
        encoding="utf-8")

    PKG_DIR.mkdir(parents=True, exist_ok=True)
    (PKG_DIR / "scenario.yaml").write_text(
        yaml.safe_dump(build_scenario(), allow_unicode=True, sort_keys=False, width=400),
        encoding="utf-8")
    (PKG_DIR / "agents.yaml").write_text(
        yaml.safe_dump(build_agents(), allow_unicode=True, sort_keys=False, width=200),
        encoding="utf-8")

    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    # Historical generator: the package now lives at
    # scenarios/formal/ie_08_island_strike/ and its scenario_id is
    # ie-08-island-strike.v1.  Re-running this file would rewrite the shipped
    # package, so it is kept for provenance only - do not re-run it.
    public_id = "IE-08-ISLAND-STRIKE"
    registry["scenarios"] = [item for item in registry["scenarios"]
                             if item["public_id"] != public_id]
    registry["scenarios"].append({"public_id": public_id,
                                 "package": "ie_08_island_strike",
                                 "catalog_bundle": "md_ad_006"})
    REGISTRY.write_text(yaml.safe_dump(registry, allow_unicode=True, sort_keys=False, width=200),
                        encoding="utf-8")

    print(f"wrote {OUT_BUNDLE} ({len(resources)} resources)")
    print(f"wrote {PKG_DIR}/scenario.yaml + agents.yaml")
    print(f"registry now has {len(registry['scenarios'])} scenarios")


if __name__ == "__main__":
    main()
