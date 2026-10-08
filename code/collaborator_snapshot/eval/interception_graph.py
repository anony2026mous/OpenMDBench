"""结构化战场关系表示模块（Graph Builder）—— 增强 LLM 规划器的输入。

职责（确定性脚本计算 + 状态转换，无训练、无决策、不改引擎/执行器/规则基线）：
1. 拦截关系邻接表：Interceptor 节点 × Target 节点，带属性边
   （distance / range_ratio / ETA / can_intercept / threat / bearing / dist_to_zone）；
2. 候选目标筛选：每拦截机只保留 Top-K（综合 threat / ETA / range_ratio / can_intercept）；
3. History Buffer：最近 N 轮分配 + 弹药 + 时刻（短期记忆）；
4. 把图序列化为 LLM 提示词段落（Interception Graph + Previous Decision）。

字段复用（不重复计算）：
- 距离/三维距离：v2_executor._dist3；
- 接触底层实体后缀：v2_executor.contact_entity_suffix；
- 弹药键映射：v2_executor.ammo_ref_for（weapon.* → ammunition.*）；
- 平台类别：v2_executor.platform_kind（域优先，不靠编号）；
- distance_to_zone / bearing 与 llm_planner 提示词中原有字段同公式。

episode reset：本模块实例随每局 `_build_defender` 新建而天然清零；若复用实例，
调用 `history.reset()`。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from v2_executor import (
    ACTIVE_LIFECYCLES,
    WeaponPolicyV2,
    _dist3,
    _heading_to,
    ammo_ref_for,
    contact_entity_suffix,
    fixed_site_weapon_policy,
    platform_kind,
)


@dataclass
class GraphConfig:
    """图构建配置（默认值与 RulePlannerConfigV2 口径一致）。"""

    confidence_min: float = 0.55
    contact_max_age_ticks: int = 10
    objective_m: Tuple[float, float] = (0.0, 0.0)
    # Optional protected-zone rectangle [min_x, min_y, max_x, max_y].  When it
    # is absent, preserve the historical radial distance-to-objective metric.
    protected_zone_bounds_m: Optional[Tuple[float, float, float, float]] = None
    # Declarative attack calendar supplied by agents.yaml.  It is context for
    # the LLM only and does not participate in rule planning or execution.
    attack_timeline: Tuple[Mapping[str, Any], ...] = ()
    top_k: int = 3
    history_size: int = 5
    threat_scale_m: float = 35000.0   # 威胁随距禁区距离线性衰减的尺度
    eta_scale_ticks: float = 600.0    # ETA 归一化尺度
    # 提前拦截视野：目标距射程 ≤ horizon tick 且正在接近时给出 prepare_intercept
    # （实测 LLM 接敌滞后 ~90 tick；60 便于后续 20/40/60/80 敏感性测试）
    pre_intercept_horizon_ticks: int = 60
    closing_eps: float = 1.0          # closing_speed 判噪阈值（m/tick）
    # 突防方假定速度（m/tick）：用于计算目标到达禁区的预计时间，
    # 与 feasible_eta_ticks 比较得到 feasible（拦截机能否先于目标进射程）。
    intruder_speed_mps: float = 45.0
    # 目标域判定阈值：接触高度高于该值即判为空中目标。
    # 观测里没有目标域字段，只能按可观测高度分类（与 rule_planner._contact_allowed 同口径）。
    air_altitude_threshold_m: float = 50.0


def weapon_target_domains(meta_entity, weapon_ref: str) -> Tuple[str, ...]:
    """该单位武器允许打击的目标域（读武器资源绑定；空=不限制）。"""

    bindings = (getattr(getattr(meta_entity, "definition", None),
                        "resource_bindings", None) or {}).get("weapons", ())
    for binding in bindings:
        if getattr(binding, "exact_ref", None) != weapon_ref:
            continue
        content = getattr(binding, "normalized_content", None) or {}
        return tuple(str(item) for item in (content.get("target_domains") or ()))
    return ()


def contact_domain_class(contact: Mapping[str, Any],
                         threshold_m: float) -> str:
    """接触的可观测域分类：按高度判空中/水面。"""

    position = contact.get("estimated_position_m") or (0.0, 0.0, 0.0)
    try:
        altitude = float(position[2])
    except (TypeError, ValueError, IndexError):
        altitude = 0.0
    return "air" if altitude > threshold_m else "surface"


def domain_pairing_allowed(domains: Tuple[str, ...], target_class: str) -> bool:
    """武器目标域是否覆盖该接触类别（空域声明=不限制）。"""

    if not domains:
        return True
    if target_class == "air":
        return "air" in domains
    # 水面/陆地共用同一"非空中"可观测类别：带 surface 或 land 的武器都算可用
    return "surface" in domains or "land" in domains


@dataclass
class InterceptorNode:
    id: str
    position_m: Tuple[float, float, float]
    speed_mps: float
    range_m: float
    remaining_ammunition: Optional[int]
    current_assignment: Optional[str]
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    # 本单位武器允许打击的目标域（空=不限制）。用于判定"这条边引擎到底会不会放行"。
    target_domains: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "position": [round(v, 1) for v in self.position_m],
            "speed": round(self.speed_mps, 1),
            "range": round(self.range_m, 1),
            "remaining_ammunition": self.remaining_ammunition,
            "current_assignment": self.current_assignment,
            "target_domains": list(self.target_domains),
            "available_targets": self.candidates,
        }


@dataclass
class ShoreSiteNode:
    """固定武装设施（岸基近防，如 CIWS）——自动近防，不进拦截机分配。"""

    id: str
    position_m: Tuple[float, float, float]
    min_range_m: float
    max_range_m: float
    remaining_ammunition: Optional[int]
    threats: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "position": [round(v, 1) for v in self.position_m],
            "min_range": round(self.min_range_m, 1),
            "max_range": round(self.max_range_m, 1),
            "remaining_ammunition": self.remaining_ammunition,
            "threats": self.threats,
        }


@dataclass
class InterceptionGraph:
    tick: int
    interceptors: List[InterceptorNode]
    target_count: int
    history: "HistoryBuffer"
    shore_sites: List[ShoreSiteNode] = field(default_factory=list)
    attack_timeline: Tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "target_count": self.target_count,
            "interceptors": [node.to_dict() for node in self.interceptors],
            "shore_sites": [site.to_dict() for site in self.shore_sites],
            "attack_timeline": [dict(item) for item in self.attack_timeline],
            "history": self.history.entries(),
        }

    def format_for_prompt(self) -> str:
        """图 → LLM 提示词段落（Interception Graph 部分）。"""
        lines: List[str] = []
        for node in self.interceptors:
            ammo = "?" if node.remaining_ammunition is None else node.remaining_ammunition
            current = node.current_assignment or "-"
            lines.append(
                f"{node.id} | pos=({node.position_m[0]:.0f},"
                f"{node.position_m[1]:.0f}) speed={node.speed_mps:.0f} "
                f"range={node.range_m:.0f} ammo={ammo} "
                f"current={current}"
            )
            if not node.candidates:
                lines.append("    (no candidates)")
                continue
            for cand in node.candidates:
                feasible = "?" if cand["feasible"] is None else str(cand["feasible"]).lower()
                lines.append(
                    f"    {cand['target']}: dist={cand['distance']:.0f}m "
                    f"range_ratio={cand['range_ratio']:.2f} eta={cand['eta']:.0f}t "
                    f"feasible_eta={cand['feasible_eta_ticks']:.0f}t "
                    f"feasible={feasible} "
                    f"can_intercept={str(cand['can_intercept']).lower()} "
                    f"domain_ok={str(cand.get('domain_ok', True)).lower()} "
                    f"target_class={cand.get('target_class', '?')} "
                    f"threat={cand['threat']:.2f} bearing={cand['bearing']:.0f} "
                    f"dist_zone={cand['distance_to_zone']:.0f}m "
                    f"observed_by={cand['observed_by']} "
                    f"observers={cand['observer_count']} "
                    f"range_gap={cand['range_gap']:.0f}m "
                    f"closing={cand['closing_speed']}m/t "
                    f"approach={cand['approach_status']} "
                    f"ttr={cand['time_to_weapon_range_ticks']} "
                    f"prepare={str(cand['prepare_intercept']).lower()}"
                )
        return "\n".join(lines)

    def format_timeline_for_prompt(self) -> str:
        """Future-wave context declared by the scenario's agent profile."""
        if not self.attack_timeline:
            return "(none declared)"
        lines: List[str] = []
        for item in self.attack_timeline:
            label = str(item.get("label", item.get("role", "wave")))
            spawn_tick = item.get("spawn_tick", "?")
            count = item.get("count", "?")
            axis = item.get("axis", "?")
            behavior = item.get("behavior", "continues toward the protected zone")
            lines.append(
                f"  {label}: spawn_tick={spawn_tick} count={count} axis={axis}; "
                f"{behavior}"
            )
        return "\n".join(lines)

    def format_shore_for_prompt(self) -> str:
        """岸基近防段（动态：无近防设施时返回 (none)）。"""
        if not self.shore_sites:
            return "(none)"
        lines: List[str] = []
        for site in self.shore_sites:
            ammo = "?" if site.remaining_ammunition is None \
                else site.remaining_ammunition
            lines.append(
                f"{site.id} | pos=({site.position_m[0]:.0f},"
                f"{site.position_m[1]:.0f}) range={site.min_range_m:.0f}-"
                f"{site.max_range_m:.0f}m ammo={ammo}"
            )
            if not site.threats:
                lines.append("    (no threats in range)")
            for threat in site.threats:
                lines.append(
                    f"    {threat['target']}: dist={threat['distance']:.0f}m "
                    f"age={threat['age_ticks']}"
                )
        return "\n".join(lines)


class HistoryBuffer:
    """短期记忆：最近 N 轮（时刻 / 分配 / 弹药 / 持续攻击目标）。"""

    def __init__(self, size: int = 5):
        self.size = max(1, int(size))
        self._entries: List[Dict[str, Any]] = []

    def record(self, tick: int, assignments: Mapping[str, str],
               ammo: Mapping[str, Optional[int]]) -> None:
        self._entries.append({
            "tick": int(tick),
            "assignments": {str(k): str(v) for k, v in assignments.items()},
            "ammo": {str(k): (None if v is None else int(v))
                     for k, v in ammo.items()},
        })
        if len(self._entries) > self.size:
            self._entries = self._entries[-self.size:]

    def last_assignment(self) -> Dict[str, str]:
        if not self._entries:
            return {}
        return dict(self._entries[-1]["assignments"])

    def entries(self) -> List[Dict[str, Any]]:
        return [dict(item) for item in self._entries]

    def reset(self) -> None:
        self._entries = []

    def format_for_prompt(self) -> str:
        """历史 → LLM 提示词段落（Previous Decision 部分）。"""
        if not self._entries:
            return "(none yet)"
        lines = []
        for item in self._entries[-3:]:  # 提示词里只给最近 3 轮，控制 token
            assignment = ", ".join(f"{u}->{t}" for u, t in item["assignments"].items()) \
                or "(no intercept)"
            ammo = ", ".join(f"{u}:{v}" for u, v in item["ammo"].items())
            lines.append(
                f"  tick {item['tick']}: assignment=[{assignment}] ammo=[{ammo}]"
            )
        return "\n".join(lines)


def _edge_approach_fields(*, distance: float, weapon_range: float,
                          closing_speed: Optional[float],
                          horizon_ticks: int, eps: float) -> Dict[str, Any]:
    """新增的短期趋势预测字段（纯函数，便于单测）。

    - range_gap: 距射程边界还差多少米（射程内为 0）
    - closing_speed: 相邻构建周期的距离变化率（m/tick，>0=接近）
    - approach_status: approaching / stable / receding（eps 防抖）
    - time_to_weapon_range_ticks: 按当前趋势还需多少 tick 进射程；
      已在射程内=0；远离或无法预测=null（序列化为 None）
    - prepare_intercept: 尚未进射程但"应该提前开始机动"的提示
      （can_intercept 语义保持原样不变）
    """
    range_gap = round(max(0.0, distance - weapon_range), 1)
    if closing_speed is None:
        approach_status = "stable"
        time_to_range = None
    elif closing_speed > eps:
        approach_status = "approaching"
        time_to_range = round(range_gap / closing_speed, 1)
    elif closing_speed < -eps:
        approach_status = "receding"
        time_to_range = None
    else:
        approach_status = "stable"
        time_to_range = None
    if distance <= weapon_range:
        time_to_range = 0.0
    prepare = bool(
        approach_status == "approaching"
        and (distance <= weapon_range
             or (time_to_range is not None and time_to_range <= horizon_ticks))
    )
    return {
        "range_gap": range_gap,
        "closing_speed": closing_speed,
        "approach_status": approach_status,
        "time_to_weapon_range_ticks": time_to_range,
        "prepare_intercept": prepare,
    }


class GraphBuilder:
    """观测 → 拦截关系图（确定性脚本，无训练、无决策）。"""

    def __init__(self, config: Optional[GraphConfig] = None, *,
                 weapon_policies: Tuple[WeaponPolicyV2, ...] = (),
                 speed_by_tag: Optional[Mapping[str, float]] = None):
        self.config = config or GraphConfig()
        self.weapon_policies = weapon_policies
        self.speed_by_tag = dict(speed_by_tag or {"uav": 40.0, "usv": 8.0})
        self.history = HistoryBuffer(self.config.history_size)
        # closing_speed 距离变化率缓存：(interceptor_id, contact_id) -> (tick, distance)
        # 每局新建 GraphBuilder → 天然清零；如需复用实例，调用 reset()
        self._prev_distance: Dict[Tuple[str, str], Tuple[int, float]] = {}

    def reset(self) -> None:
        """episode reset：清空历史与距离缓存，防止跨局污染。"""
        self.history.reset()
        self._prev_distance.clear()

    # ------------------------------------------------------------------
    # 工具（复用既有字段口径）
    # ------------------------------------------------------------------

    def _policy_for(self, tags) -> Optional[WeaponPolicyV2]:
        tagset = set(tags)
        for policy in self.weapon_policies:
            if set(policy.selector_tags) <= tagset:
                return policy
        return None

    def is_armed(self, tags) -> bool:
        """数据驱动武装判定：命中任一武器策略 selector 标签即武装（不依赖场景标签名）。"""
        return self._policy_for(tags) is not None

    def _speed_for(self, meta_entity, tags) -> float:
        kind = platform_kind(meta_entity)
        if kind in self.speed_by_tag:
            return float(self.speed_by_tag[kind])
        for tag, speed in self.speed_by_tag.items():
            if tag in tags:
                return float(speed)
        return 40.0

    @staticmethod
    def _ammo_for(meta_entity, weapon_ref: str) -> Optional[int]:
        live = getattr(getattr(meta_entity, "state", None), "ammunition", None)
        if live is None:
            return None
        ammo = {str(k): int(v) for k, v in dict(live).items()}
        resolved = ammo_ref_for(ammo, weapon_ref)
        return ammo.get(resolved) if resolved else None

    def _distance_to_zone(self, position: Sequence[float]) -> float:
        """Distance to the protected-zone boundary, or legacy objective radius."""
        bounds = self.config.protected_zone_bounds_m
        if bounds is not None:
            min_x, min_y, max_x, max_y = (float(value) for value in bounds)
            x, y = float(position[0]), float(position[1])
            dx = max(min_x - x, 0.0, x - max_x)
            dy = max(min_y - y, 0.0, y - max_y)
            return math.hypot(dx, dy)
        objective = self.config.objective_m
        return math.hypot(float(position[0]) - float(objective[0]),
                          float(position[1]) - float(objective[1]))

    def _threat_score(self, distance_to_zone: float, confidence: float) -> float:
        proximity = 1.0 - min(distance_to_zone / self.config.threat_scale_m, 1.0)
        return max(0.0, min(1.0, proximity * 0.8 + float(confidence) * 0.2))

    @staticmethod
    def _contact_entity(contact: Mapping[str, Any]) -> str:
        return contact_entity_suffix(contact)

    def _owns_entity(self, contacts, interceptor_id: str, entity_suffix: str) -> bool:
        return any(
            str(c.get("observer_entity_id")) == interceptor_id
            and self._contact_entity(c) == entity_suffix
            for c in contacts
        )

    @staticmethod
    def _dedupe_contacts(contacts: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        """Keep one LLM target node per physical entity, not per observer track."""
        grouped: Dict[str, List[Mapping[str, Any]]] = {}
        for contact in contacts:
            grouped.setdefault(contact_entity_suffix(contact), []).append(contact)
        unique: List[Dict[str, Any]] = []
        for entity_id in sorted(grouped):
            tracks = grouped[entity_id]
            canonical = min(
                tracks,
                key=lambda item: (
                    -float(item.get("confidence", 0.0)),
                    int(item.get("age_ticks", 0)),
                    str(item.get("contact_id", "")),
                ),
            )
            target = dict(canonical)
            target["observer_count"] = len({
                str(item.get("observer_entity_id", "")) for item in tracks
            })
            unique.append(target)
        return unique

    # ------------------------------------------------------------------
    # 图构建
    # ------------------------------------------------------------------

    def build(self, observation, unit_roles: Optional[Mapping[str, object]],
              meta: Optional[Mapping[str, Any]], tick: int) -> InterceptionGraph:
        cfg = self.config
        own = [
            item for item in observation.own_entities
            if item.get("lifecycle_state") in ACTIVE_LIFECYCLES
        ]
        raw_contacts = [
            c for c in observation.contacts_by_faction.get(
                observation.observer_faction_id, ())
            if float(c.get("confidence", 0.0)) >= cfg.confidence_min
            and int(c.get("age_ticks", 0)) <= cfg.contact_max_age_ticks
        ]
        contacts = self._dedupe_contacts(raw_contacts)
        last_assignment = self.history.last_assignment()

        interceptors: List[InterceptorNode] = []
        for item in own:
            uid = str(item["entity_id"])
            tags = tuple(unit_roles.get(uid, ())) if unit_roles else ()
            policy = self._policy_for(tags)
            if policy is None:
                continue  # 非武装单位（哨戒艇等）不入图，与执行层语义一致
            meta_entity = meta.get(uid) if meta else None
            position = tuple(float(v) for v in item["position_m"])
            speed = self._speed_for(meta_entity, tags)
            node = InterceptorNode(
                id=uid,
                position_m=position,
                speed_mps=speed,
                range_m=float(policy.maximum_range_m),
                remaining_ammunition=self._ammo_for(meta_entity, policy.weapon_ref),
                current_assignment=last_assignment.get(uid),
                target_domains=weapon_target_domains(meta_entity, policy.weapon_ref),
            )
            interceptors.append(node)

        # 每个拦截机 × 每个接触的带属性边
        seen_keys = set()
        for node in interceptors:
            edges: List[Dict[str, Any]] = []
            for contact in contacts:
                estimate = tuple(float(v) for v in contact["estimated_position_m"])
                distance = _dist3(node.position_m, estimate)
                range_ratio = distance / node.range_m
                eta = distance / max(node.speed_mps, 1e-9)
                entity_suffix = self._contact_entity(contact)
                # 目标域配对：射程够 + 有自持接触，并不代表引擎会放行。
                # 之前 can_intercept 只判射程与接触归属，于是图里会出现
                # "只带对空武器的无人机可以拦截水面无人艇" 这种**引擎必然拒绝**
                # 的边（纯 LLM 组据此开火，被 combat.target_domain_denied 退回；
                # 混合组据此分配目标，结果水面威胁全程无人处理）。
                target_class = contact_domain_class(contact, cfg.air_altitude_threshold_m)
                domain_ok = domain_pairing_allowed(node.target_domains, target_class)
                can_intercept = (
                    distance <= node.range_m
                    and self._owns_entity(raw_contacts, node.id, entity_suffix)
                    and domain_ok
                )
                distance_to_zone = self._distance_to_zone(estimate)
                key = (node.id, entity_suffix)
                seen_keys.add(key)
                prev = self._prev_distance.get(key)
                if prev is not None:
                    prev_tick, prev_distance = prev
                    delta_ticks = max(1, int(tick) - int(prev_tick))
                    closing_speed = round(
                        (prev_distance - distance) / delta_ticks, 2)
                else:
                    closing_speed = None  # 首个构建周期无历史 → 趋势未知
                # 可行性：拦截机赶到射程边界所需时间 vs 目标到达禁区所需时间。
                # 把"能不能赶到"变成硬数据喂给 LLM（修复 MEDIUM Hybrid 把
                # interceptor-003 留作后方预备、全程 0 开火的问题）。
                travel = max(0.0, distance - node.range_m)
                feasible_eta = round(travel / max(node.speed_mps, 1e-9), 1)
                if cfg.intruder_speed_mps > 0:
                    zone_eta = distance_to_zone / cfg.intruder_speed_mps
                    feasible = bool(feasible_eta <= zone_eta)
                else:
                    feasible = None
                # 预计拦截纵深（见 edge 里 `intercept_depth_m` 的说明）
                if cfg.intruder_speed_mps > 0 and node.speed_mps > 0:
                    meet_ticks = distance / (node.speed_mps
                                             + cfg.intruder_speed_mps)
                    intercept_depth = (distance_to_zone
                                       - cfg.intruder_speed_mps * meet_ticks)
                else:
                    intercept_depth = None
                edges.append({
                    "target": str(contact["contact_id"]),
                    "distance": round(distance, 1),
                    "range_ratio": round(range_ratio, 3),
                    "eta": round(eta, 1),
                    "feasible_eta_ticks": feasible_eta,
                    "feasible": feasible,
                    # 预计拦截点距保护区的纵深（m）：拦截机现在出发与来袭者相遇时，
                    # 来袭者距保护区还剩多少路。这正是纵深层评分所用的量，把它显式
                    # 算给前端，排序与评分口径才对得上（此前 `_top_k` 只奖励"已经
                    # 逼近保护区"和"已在射程内"，等于系统性惩罚前出拦截）。
                    # 近似：假设相向接近，相遇用时 distance/(v_拦截 + v_来袭)。
                    # 来袭者并非严格朝保护区直飞，故这是下界估计（偏保守）。
                    "intercept_depth_m": (
                        None if intercept_depth is None
                        else round(intercept_depth, 1)
                    ),
                    "target_class": target_class,
                    "domain_ok": bool(domain_ok),
                    "can_intercept": bool(can_intercept),
                    "threat": round(
                        self._threat_score(distance_to_zone,
                                           float(contact.get("confidence", 0.0))), 3),
                    "bearing": round(
                        _heading_to(node.position_m, estimate), 1),
                    "distance_to_zone": round(distance_to_zone, 1),
                    "observed_by": str(contact.get("observer_entity_id", "?")),
                    "observer_count": int(contact["observer_count"]),
                    **_edge_approach_fields(
                        distance=distance,
                        weapon_range=node.range_m,
                        closing_speed=closing_speed,
                        horizon_ticks=cfg.pre_intercept_horizon_ticks,
                        eps=cfg.closing_eps,
                    ),
                })
                self._prev_distance[key] = (int(tick), distance)
            node.candidates = self._top_k(edges)
        # 清理已消失接触的缓存，防止跨局/跨波污染
        self._prev_distance = {
            key: value for key, value in self._prev_distance.items()
            if key in seen_keys
        }
        # ---- 岸基固定武装设施（自动近防，动态发现：无近防场景为空）----
        shore_sites: List[ShoreSiteNode] = []
        for item in own:
            uid = str(item["entity_id"])
            tags = tuple(unit_roles.get(uid, ())) if unit_roles else ()
            if "fixed" not in tags:
                continue
            meta_entity = meta.get(uid) if meta else None
            policy = fixed_site_weapon_policy(meta_entity)
            if policy is None:
                continue
            position = tuple(float(v) for v in item["position_m"])
            threats = []
            for contact in contacts:
                if str(contact.get("observer_entity_id")) != uid:
                    continue
                distance = _dist3(position, tuple(
                    float(v) for v in contact["estimated_position_m"]))
                if policy.minimum_range_m <= distance <= policy.maximum_range_m:
                    threats.append({
                        "target": str(contact["contact_id"]),
                        "distance": round(distance, 1),
                        "age_ticks": int(contact.get("age_ticks", 0)),
                    })
            threats.sort(key=lambda threat: threat["distance"])
            shore_sites.append(ShoreSiteNode(
                id=uid,
                position_m=position,
                min_range_m=policy.minimum_range_m,
                max_range_m=policy.maximum_range_m,
                remaining_ammunition=self._ammo_for(meta_entity,
                                                    policy.weapon_ref),
                threats=threats,
            ))
        return InterceptionGraph(
            tick=int(tick), interceptors=interceptors,
            target_count=len(contacts), history=self.history,
            shore_sites=shore_sites, attack_timeline=cfg.attack_timeline,
        )

    def _top_k(self, edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """综合 threat / 预计拦截纵深 / range_ratio / eta / can_intercept 排序取 Top-K。

        目标域不可用的边**必须排在可用边之后**：否则最近的一批水面无人艇会把
        Top-K 名额占满，LLM 连一个"打得到"的空中目标都看不到（实测 tick 180
        每架对空无人机的 top-3 全是 domain_ok=False 的无人艇）。

        **第 14 轮加入纵深项（③ 的整改）**：原评分是
        `0.45*threat + 0.25*(1-range_ratio/2) + 0.30*(1-eta/scale)`，其中
        `threat` 随"距保护区更近"而升高、`1-range_ratio` 奖励已经贴脸的目标 ——
        两项都**奖励"来袭者已经逼近"**，等于系统性惩罚前出拦截。这与实测吻合：
        混合 LLM 臂的拦截纵深均值一度只有 10.8 km，而 rule 臂 18.3 km。
        现在把 threat 权重降到 0.35（紧迫性仍然保留：最危险的目标优先），
        并加入 0.25 权重的**预计拦截纵深**项、把"已在射程内"的奖励降到 0.20，
        使"现在出发能在多远拦住它"成为排序的显式依据，且与 depth 层评分同源。
        """

        def score(edge: Dict[str, Any]) -> float:
            depth_term = 0.0
            depth = edge.get("intercept_depth_m")
            if depth is not None:
                depth_term = max(0.0, min(depth / self.config.threat_scale_m, 1.0))
            return (
                0.35 * edge["threat"]
                + 0.20 * (1.0 - min(edge["range_ratio"], 2.0) / 2.0)
                + 0.20 * (1.0 - min(edge["eta"], self.config.eta_scale_ticks)
                          / self.config.eta_scale_ticks)
                + 0.25 * depth_term
                + (0.15 if edge["can_intercept"] else 0.0)
            )

        ranked = sorted(
            edges,
            key=lambda e: (
                0 if e.get("domain_ok", True) else 1,   # 域可用优先
                -score(e),
                e["distance"],
            ),
        )
        return ranked[: self.config.top_k]

    # ------------------------------------------------------------------
    # 决策记录（规划器在提交目标后调用）
    # ------------------------------------------------------------------

    def record_decision(self, tick: int, assignments: Mapping[str, str],
                        interceptors: Sequence[InterceptorNode]) -> None:
        ammo = {node.id: node.remaining_ammunition for node in interceptors}
        self.history.record(tick, assignments, ammo)
