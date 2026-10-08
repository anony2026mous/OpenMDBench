"""Apply the round-10 force pressurisation to the IE scenarios.

Adds a documented, table-driven force adjustment to ``_gen_ie_set.py`` so the
first seven scenarios can be pressed toward the "our best strategy just barely
intercepts" threshold without hand-editing seven dense spec literals.

The table states, per scenario index, the *target* counts.  ``apply_pressure``
then

  * trims or extends the blue force to the target counts (reusing the station
    tables, so geometry stays sane),
  * appends threat UAVs / suicide boats on the existing axes by cloning the
    nearest template and offsetting laterally,
  * lowers the threat UAV ammunition from 4 to 3 rounds (the audit in round 9
    showed 4/airframe was the reason IE-08 could put 40+ UAV missiles in the air).

Run once:
    python _w1_patch_pressure.py
"""
from __future__ import annotations

import pathlib

path = pathlib.Path("_gen_ie_set.py")
text = path.read_text(encoding="utf-8")

# ---- 1. spec() records the requested counts so the pressure pass can act -----
old_spec = '''        "defender": blue_force(blue_uavs, blue_usvs),'''
new_spec = '''        "defender": blue_force(blue_uavs, blue_usvs),
        "blue_uavs": blue_uavs, "blue_usvs": blue_usvs,
        "target_red_uav": sum(1 for e in red_uavs if "decoy" not in e["id"]),
        "target_red_boat": len(red_boats),'''
if old_spec in text and '"target_red_uav"' not in text:
    text = text.replace(old_spec, new_spec, 1)

# ---- 2. pressure table + pass at the end of scenario_specs() ---------------
PRESSURE = '''
    # ------------------------------------------------------------------
    # 编成加压表（第 10 轮）：让前 7 个场景的难度逼近
    # "我方理论最优策略刚好能够成功拦截"的临界点。
    #
    # 依据：分域火力比 = 威胁目标数 / 我方同域导弹数。对空武器打不到水面、
    # 对海武器打不到空中，因此必须分域算。第 9 轮实测前 7 个场景的比值只有
    # 0.25–0.60，而我方火力是威胁的 2–4 倍 —— 这就是它们分数高（0.75–0.86）
    # 且区分度差的根因。本表把双边数量一起抬高，并让比值逐级逼近 IE-08 的
    # 0.67（对空）/ 0.83（对海）。
    #
    # 同时把威胁无人机的载弹从 4 发降到 3 发：第 9 轮的弹药审计显示
    # 4 发/架 × 12 架 = 48 发预算才是"IE-08 打出 40+ 枚无人机导弹"的来源，
    # 3 发更贴近小型巡飞弹的现实，同时仍够红方压制设施（每设施需 2 发命中）。
    # ------------------------------------------------------------------
    pressure = {
        1: dict(red_uav=2, red_boat=0, blue_uav=2, blue_usv=2),
        2: dict(red_uav=3, red_boat=0, blue_uav=3, blue_usv=2),
        3: dict(red_uav=0, red_boat=4, blue_uav=2, blue_usv=3),
        4: dict(red_uav=4, red_boat=4, blue_uav=3, blue_usv=3),
        5: dict(red_uav=5, red_boat=4, blue_uav=4, blue_usv=3),
        6: dict(red_uav=5, red_boat=4, blue_uav=4, blue_usv=4),
        7: dict(red_uav=7, red_boat=5, blue_uav=5, blue_usv=4),
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
            clone["initial_state"]["position_m"][0] += 300.0 * (len(pool) - index + 1)
            pool.append(clone)
            index += 1
        return pool[:want]

    if uavs or target["red_uav"]:
        uavs = grow(uavs, int(target["red_uav"]), "uav", 700.0)
        # 威胁无人机载弹 4 -> 3（现实性 + 压低红方弹药总量）
        for unit in uavs:
            ammo = unit.get("ammunition")
            if ammo:
                for key in list(ammo):
                    ammo[key] = min(int(ammo[key]), 3)
    boats = grow(boats, int(target["red_boat"]), "boat", -600.0)

    item["intruder"] = uavs + boats + others

    # --- 我方兵力：按目标编成重建（沿用站位表，几何不越界）---
    item["defender"] = blue_force(int(target["blue_uav"]),
                                  int(target["blue_usv"]))
    item["blue_uavs"] = int(target["blue_uav"])
    item["blue_usvs"] = int(target["blue_usv"])
    item["pressure"] = dict(target)
'''

anchor = "    return specs"
assert anchor in text, "scenario_specs return anchor missing"
if "def apply_pressure" not in text:
    text = text.replace(anchor, PRESSURE.rstrip() + "\n", 1)

path.write_text(text, encoding="utf-8")
print("apply_pressure added =", "def apply_pressure" in text)
print("pressure table added =", "pressure = {" in text)
print("counts recorded      =", '"target_red_uav"' in text)
