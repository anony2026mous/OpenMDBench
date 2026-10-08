"""规则规划层（V2 迁移版）—— grid rule_agent 的"最近威胁优先"规则，输出 GOAI 目标命令。

与 grid 版差异：
- 观测为 V2 ObservationV2：连续米制位置、能量、接触（无 type/civilian 字段，
  交战合法性由引擎 ROE 规则保证，本层不区分平民/未知目标）；
- 港口 (1,18) → 保护目标 objective_m（MD-AD-002-EASY 为 zone.denial 中心 (0,0)）；
- 拦截点 = 接触位置向保护目标方向移动 intercept_fraction（30%）；
- 单位角色由 unit_roles（entity_id → tags，由编排器从 entities_stable 提供）决定：
  带武器策略 selector 标签的单位拿 intercept，其余可动单位拿巡逻；
- fixed 单位不分配目标（执行层也会跳过它们）；
- 能量低于阈值 → return 目标；无接触 → 巡逻锚点。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from goai_protocol import GoalCommand


@dataclass
class RulePlannerConfigV2:
    """规则规划器配置（默认口径为 MD-AD-002 通道走廊；其它场景由调用方覆盖）。"""

    objective_m: Tuple[float, float] = (0.0, 0.0)
    intercept_fraction: float = 0.3
    confidence_min: float = 0.55
    contact_max_age_ticks: int = 10
    energy_low: float = 0.3
    weapon_tags: Tuple[str, ...] = ("interceptor",)
    # 数据驱动的武器策略（鸭子类型：仅用 selector_tags 属性）。提供时优先按
    # 策略标签判定武装单位，weapon_tags 仅作无策略时的兜底——与 Graph Builder
    # / 执行层的武装判定同口径，场景换标签名也无需改代码。
    weapon_policies: Tuple[object, ...] = ()
    patrol_anchors_weapon: Tuple[Tuple[float, float, float], ...] = (
        (15000.0, 0.0, 800.0),
        (15000.0, 2500.0, 800.0),
        (18000.0, -1500.0, 800.0),
    )
    patrol_anchors_sensor: Tuple[Tuple[float, float, float], ...] = (
        (12334.0, 4995.0, 0.0),
        (17620.0, -1110.0, 0.0),
    )
    # 同一锚点上多个单位之间的站位间距（米）：防止"多单位共用一个坐标点"导致
    # 相向汇聚相撞（见 _anchor_for）。
    station_separation_m: float = 1500.0
    # 不同单位拦截点之间的最小间距（米）：成对来袭目标相距只有几百米时，两台
    # 拦截机若飞向同一空域会相撞（见 _deconflicted_intercept）。
    intercept_separation_m: float = 1500.0
    # 接触高度高于该值即判为空中目标（米）：观测只有三维位置，没有目标域字段，
    # 高度是可用的分类依据（见 _contact_allowed）。
    air_altitude_threshold_m: float = 50.0
    rear_anchor_m: Tuple[float, float, float] = (0.0, 6000.0, 800.0)
    # ---- 弹药教义（fire_policy）----
    # 作为 goal 参数下发，与混合组**对等**：规则侧用确定性映射，LLM 侧自由选择。
    # 默认 "salvo" = 恢复规则基线的历史语义（每目标连发 2 发），避免下层默认值
    # 悄悄改变基线口径。None = 不下发参数（由执行层默认教义决定）。
    fire_policy: Optional[str] = "salvo"
    # 可选确定性映射：目标距禁区 ETA ≤ 阈值时改用该教义（None = 关闭映射）
    fire_policy_urgent: Optional[str] = None
    fire_policy_urgent_eta_ticks: int = 240
    intruder_speed_mps: float = 45.0

    def is_weapon_unit(self, roles) -> bool:
        """武装判定：先查武器策略 selector 标签，再回退 weapon_tags 标签集合。"""
        tagset = set(roles or ())
        if self.weapon_policies:
            for policy in self.weapon_policies:
                if set(getattr(policy, "selector_tags", ())) <= tagset:
                    return True
            return False
        return bool(tagset & set(self.weapon_tags))


class RulePlannerV2:
    """规则 planner：每轮输出该阵营完整目标集（协议要求）。"""

    # 需要 entity view（meta）才能读武器目标域；编排器 AgentV2 已支持该开关。
    wants_meta = True

    def __init__(self, config: Optional[RulePlannerConfigV2] = None):
        self.config = config or RulePlannerConfigV2()
        self._task_seq = 0
        self._track_target: Optional[str] = None
        # 接触 id → 单位 id：上一轮的拦截配对，用于滞回（避免每轮重匹配导致航向抖动）
        self._assignments: dict[str, str] = {}

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    def _next_task_id(self, prefix: str) -> str:
        self._task_seq += 1
        return f"{prefix}_{self._task_seq:03d}"

    @staticmethod
    def _dist_xy(pos: Sequence[float], target: Sequence[float]) -> float:
        return math.hypot(float(pos[0]) - float(target[0]),
                          float(pos[1]) - float(target[1]))

    def _fire_policy_for(self, contact: Mapping[str, object]) -> Optional[str]:
        """确定性教义映射（规则侧的"弹药怎么花"）——与 LLM 侧动作空间对等。

        - 基准教义 cfg.fire_policy（默认 salvo = 规则基线历史语义：每目标连发 2 发）
        - 若配置了 cfg.fire_policy_urgent，且目标距禁区 ETA ≤ 阈值 → 改用该教义
          （典型用法：base=assess 省弹、urgent=salvo 对即将破防的目标确保击毁）
        返回 None 表示不下发参数、由执行层默认教义决定。
        """
        cfg = self.config
        doctrine = cfg.fire_policy
        if cfg.fire_policy_urgent:
            distance = self._dist_xy(contact["estimated_position_m"],
                                     cfg.objective_m)
            eta = distance / max(cfg.intruder_speed_mps, 1e-6)
            if eta <= cfg.fire_policy_urgent_eta_ticks:
                doctrine = cfg.fire_policy_urgent
        return doctrine

    def _roles(self, unit_roles: Optional[Mapping[str, object]],
               entity_id: str) -> Tuple[str, ...]:
        if unit_roles is None:
            return ()
        roles = unit_roles.get(entity_id)
        return tuple(roles) if roles else ()

    @staticmethod
    def _entity_id_from_contact(contact: Mapping[str, object]) -> str:
        """从接触 id 还原底层实体 id。

        必须用**本接触自己的观测者 id** 去前缀：实体 id 里带点
        （``defender.uav-01``），按第一个点切分会得到
        ``uav-01.intruder.boat-01`` 这种错值。
        """
        cid = str(contact.get("contact_id") or "")
        observer = str(contact.get("observer_entity_id") or "")
        prefix = f"sensor.contact.{observer}."
        if observer and cid.startswith(prefix):
            return cid[len(prefix):]
        return cid

    @staticmethod
    def _target_domains(meta, unit_id: str) -> Tuple[str, ...]:
        """本单位武器允许打击的目标域（与执行层同源：读武器资源绑定）。"""
        entity = (meta or {}).get(unit_id)
        bindings = (getattr(getattr(entity, "definition", None),
                            "resource_bindings", None) or {}).get("weapons", ())
        domains = set()
        for binding in bindings:
            content = getattr(binding, "normalized_content", None) or {}
            domains.update(str(item) for item in (content.get("target_domains") or ()))
        return tuple(sorted(domains))

    def _contact_allowed(self, contact: Mapping[str, object], domains) -> bool:
        """接触是否落在本单位武器的目标域内。

        观测里**没有**目标域字段，而 meta 只含己方实体（拿不到来袭方的 domain），
        所以只能用可观测的高度判类：雷达给出三维位置，空中目标高度 > 0，水面/地面
        目标高度 ≈ 0。这等价于真实传感器的高度分类，不依赖真值。

        这个门必须存在：否则纯对空的无人机也会被派去"拦截"水面无人艇 —— 飞得到、
        打不了，只在目标上空以最大转弯率兜圈（实测蓝方 9 架无人机全部被派去打 5 艘
        无人艇，真正的空中威胁反而无人拦截）。
        """
        if not domains:
            return True
        altitude = float((contact.get("estimated_position_m") or (0.0, 0.0, 0.0))[2])
        is_air = altitude > self.config.air_altitude_threshold_m
        if is_air:
            return "air" in domains
        return "surface" in domains or "land" in domains

    @staticmethod
    def _per_station(unit_count: int, station_count: int) -> int:
        """每个巡逻锚点需要容纳的单位数（锚点不足时单位必须错开站位）。"""
        if station_count <= 0:
            return 1
        return max(1, math.ceil(unit_count / station_count))

    @staticmethod
    def _deconflicted_intercept(base_xy: Tuple[float, float],
                                approach_xy: Tuple[float, float],
                                claimed: List[Tuple[float, float]],
                                separation_m: float) -> Tuple[float, float]:
        """把拦截点沿垂直于来袭方向的轴错开，避免两台拦截机飞向同一点。

        成对来袭的两个目标相距可能只有几百米，两台拦截机各自飞向"最近拦截点"会在
        同一空域汇合相撞。垂直方向错开可以在不改变拦截纵深的条件下把站位分开。
        """
        if separation_m <= 0.0 or not claimed:
            return base_xy
        if all(math.dist(base_xy, point) >= separation_m for point in claimed):
            return base_xy
        dx, dy = approach_xy
        norm = math.hypot(dx, dy)
        if norm <= 1e-9:
            px, py = 0.0, 1.0
        else:
            px, py = -dy / norm, dx / norm
        for step in range(1, 9):
            for sign in (1.0, -1.0):
                candidate = (base_xy[0] + sign * step * separation_m * px,
                             base_xy[1] + sign * step * separation_m * py)
                if all(math.dist(candidate, point) >= separation_m
                       for point in claimed):
                    return candidate
        return base_xy

    @staticmethod
    def _min_anchor_spacing(anchors) -> float:
        """配置锚点之间的最小间距（米）；只有一个锚点或重合时取 0。"""
        points = [(float(a[0]), float(a[1])) for a in anchors]
        spacings = [
            math.dist(points[i], points[j])
            for i in range(len(points))
            for j in range(i + 1, len(points))
        ]
        return min(spacings) if spacings else 0.0

    def _anchor_for(self, anchors, i: int, radius_m: float,
                    altitude_m: float,
                    per_station: int = 1) -> Tuple[float, float, float]:
        """巡逻锚点：配置了就用配置；为空时按保护目标合成环形锚点（场景通用兜底）。

        ``per_station`` 是"每个锚点要容纳多少单位"。配置里的锚点数量通常远少于
        己方单位数（本场景 3 个锚点 / 9 架无人机），若直接 ``anchors[i % n]`` 就会
        把多个单位指派到**同一个坐标点**，它们相向汇聚后在空中相撞
        （实测 tick 74 两架蓝方无人机被 ``effect.collision-impact`` 同时打到
        health 0.293 并 disabled）。因此同一锚点上的第 k 个单位沿小半径圆环错开
        一个站位，保证任何两个单位的目标点不重合。
        """
        if anchors:
            base = tuple(float(v) for v in anchors[i % len(anchors)])
            lane = i // len(anchors)
            if per_station <= 1 or lane == 0:
                return base
            # 错开半径必须小于锚点间距的一半，否则相邻锚点的错开圆会相交、
            # 不同锚点的站位反而靠到一起（实测 1500 m 半径会让两个站位只差 98 m）。
            radius = min(self.config.station_separation_m,
                         0.25 * self._min_anchor_spacing(anchors))
            angle = 2.0 * math.pi * lane / float(per_station)
            return (
                base[0] + radius * math.cos(angle),
                base[1] + radius * math.sin(angle),
                base[2],
            )
        ox, oy = self.config.objective_m
        angle = math.radians(60.0 + 120.0 * i)
        return (ox + radius_m * math.cos(angle),
                oy + radius_m * math.sin(angle),
                altitude_m)

    # ------------------------------------------------------------------
    # 规划
    # ------------------------------------------------------------------

    def plan(self, observation, tick: int,
             reports: Optional[list] = None,
             unit_roles: Optional[Mapping[str, object]] = None,
             meta: Optional[Mapping[str, Any]] = None) -> List[GoalCommand]:
        """观测 → 该阵营完整目标命令集。"""
        cfg = self.config
        own = [
            item for item in observation.own_entities
            if item.get("lifecycle_state") in {"active", "degraded"}
        ]
        contacts = [
            c for c in observation.contacts_by_faction.get(
                observation.observer_faction_id, ()
            )
            if float(c.get("confidence", 0.0)) >= cfg.confidence_min
            and int(c.get("age_ticks", 0)) <= cfg.contact_max_age_ticks
        ]
        contacts.sort(
            key=lambda c: self._dist_xy(c["estimated_position_m"], cfg.objective_m)
        )

        weapon_units = [
            a for a in own
            if cfg.is_weapon_unit(self._roles(unit_roles, str(a["entity_id"])))
        ]
        sensor_units = [a for a in own if a not in weapon_units]

        low_ids = {
            str(a["entity_id"]) for a in own
            if a.get("energy") is not None and float(a["energy"]) < cfg.energy_low
        }

        commands: List[GoalCommand] = []

        # ---- 拦截分配：贪心最近匹配（接触按距保护目标由近及远）----
        # 两个修正（都是"交战逻辑"层面的缺陷，实测后果见注释）：
        # 1) 滞回：优先保留上一轮仍然有效的"单位→接触"配对。纯贪心重匹配会随接触
        #    列表重排而换人，实测蓝方 uav-08 在 tick 45–73 之间航向反复掉头
        #    （176.9°→326.9°→64.9°→247.1°→342.3°），既飞不到位也耗能。
        # 2) 拦截点去冲突：红方无人机成对进入（相距约 400–500 m），两台拦截机各自
        #    飞向一对相邻目标时会在同一空域汇合 —— 实测 tick 74 uav-05 与 uav-08
        #    相距 6 m 相撞，双方被 effect.collision-impact 打到 health 0.293 并
        #    disabled。因此拦截点必须彼此保持最小间距，沿垂直来袭方向错开。
        previous = dict(self._assignments)
        armed_ids = {str(a["entity_id"]) for a in weapon_units}
        preferred: dict[str, str] = {}
        rest: List[Mapping[str, object]] = []
        for contact in contacts:
            cid = str(contact["contact_id"])
            keeper = previous.get(cid)
            if keeper in armed_ids and keeper not in low_ids:
                preferred[cid] = keeper
            else:
                rest.append(contact)
        ordered_contacts = (
            [c for c in contacts if str(c["contact_id"]) in preferred] + rest
        )

        assigned = set()
        claimed: List[Tuple[float, float]] = []
        new_assignments: dict[str, str] = {}
        objective = (float(cfg.objective_m[0]), float(cfg.objective_m[1]))
        for contact in ordered_contacts:
            if len(assigned) >= len(weapon_units):
                break
            cx, cy = float(contact["estimated_position_m"][0]), \
                float(contact["estimated_position_m"][1])
            ix = cx + (objective[0] - cx) * cfg.intercept_fraction
            iy = cy + (objective[1] - cy) * cfg.intercept_fraction
            ix, iy = self._deconflicted_intercept(
                (ix, iy), (cx - objective[0], cy - objective[1]),
                claimed, cfg.intercept_separation_m,
            )
            best, best_d = None, float("inf")
            keeper = preferred.get(str(contact["contact_id"]))
            for a in weapon_units:
                aid = str(a["entity_id"])
                if aid in assigned or aid in low_ids:
                    continue
                if keeper is not None and aid != keeper:
                    continue
                # 目标域门：只把本单位"打得到"的接触派给它（见 _contact_allowed）
                if not self._contact_allowed(contact,
                                             self._target_domains(meta, aid)):
                    continue
                d = self._dist_xy(a["position_m"], (ix, iy))
                if d < best_d:
                    best_d, best = d, a
            if best is None and keeper is not None:
                # 保留的单位本轮不可用（弹尽/能量低）→ 退回最近可用单位
                for a in weapon_units:
                    aid = str(a["entity_id"])
                    if aid in assigned or aid in low_ids:
                        continue
                    if not self._contact_allowed(contact,
                                                 self._target_domains(meta, aid)):
                        continue
                    d = self._dist_xy(a["position_m"], (ix, iy))
                    if d < best_d:
                        best_d, best = d, a
            if best is not None:
                assigned.add(str(best["entity_id"]))
                claimed.append((ix, iy))
                new_assignments[str(contact["contact_id"])] = str(best["entity_id"])
                params = {"unit_id": str(best["entity_id"]),
                          "target_id": str(contact["contact_id"])}
                doctrine = self._fire_policy_for(contact)
                if doctrine:
                    params["fire_policy"] = doctrine
                commands.append(GoalCommand(
                    task_id=self._next_task_id("intercept"),
                    goal_type="intercept",
                    parameters=params,
                    priority=0.8,
                ))
        self._assignments = new_assignments

        # ---- 未分配的武器单位 → 巡逻锚点 ----
        # 站位索引取"己方武装单位稳定排序后的下标"，而不是本轮未分配单位的计数：
        # 后者会随拦截分配/释放而漂移，导致单位的目标点在两次规划之间跳变（往返兜圈）。
        weapon_ids = sorted(str(a["entity_id"]) for a in weapon_units)
        weapon_per_station = self._per_station(len(weapon_ids),
                                               len(cfg.patrol_anchors_weapon))
        for a in weapon_units:
            aid = str(a["entity_id"])
            if aid in assigned or aid in low_ids:
                continue
            anchor = self._anchor_for(cfg.patrol_anchors_weapon,
                                      weapon_ids.index(aid), 15000.0, 800.0,
                                      weapon_per_station)
            commands.append(GoalCommand(
                task_id=self._next_task_id("patrol"),
                goal_type="patrol",
                parameters={"unit_id": aid,
                            "position": [float(v) for v in anchor]},
                priority=0.3,
            ))

        # ---- 传感器单位 → 各自巡逻锚点（fixed 单位不分配目标）----
        sensor_ids = sorted(str(a["entity_id"]) for a in sensor_units)
        sensor_per_station = self._per_station(len(sensor_ids),
                                               len(cfg.patrol_anchors_sensor))
        for a in sensor_units:
            aid = str(a["entity_id"])
            if aid in low_ids or "fixed" in self._roles(unit_roles, aid):
                continue
            anchor = self._anchor_for(cfg.patrol_anchors_sensor,
                                      sensor_ids.index(aid), 18000.0, 0.0,
                                      sensor_per_station)
            commands.append(GoalCommand(
                task_id=self._next_task_id("patrol"),
                goal_type="patrol",
                parameters={"unit_id": aid,
                            "position": [float(v) for v in anchor]},
                priority=0.3,
            ))

        # ---- 低能量 → return ----
        for aid in sorted(low_ids):
            commands.append(GoalCommand(
                task_id=self._next_task_id("return"),
                goal_type="return",
                parameters={"unit_id": aid},
                priority=0.95,
                constraints=[{"type": "fuel_reserve", "value": cfg.energy_low}],
            ))

        return commands

    def get_stats(self) -> dict:
        return {"planner": "rule", "task_seq": self._task_seq}
