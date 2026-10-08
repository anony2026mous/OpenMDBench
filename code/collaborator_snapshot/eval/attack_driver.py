"""突防方（蓝方脚本）驱动 —— 读取场景 agents.yaml 的 attack 数据（只读），驱动 intruder 阵营。

与引擎自带的 FormalRuleAgentTeamV2 的 attack 侧行为等价（direct / split / serpentine
航向 + 速度循环），但作为我方 eval 族的一部分独立实现：只通过公开 DTO 提交 navigation
命令，不修改、不依赖引擎内部实现。数据文件 agents.yaml 只读。

用法：
    driver = AttackProfileDriverV2("MD-AD-002-EASY", seed=7)
    driver(session)   # 每个 tick 调用一次，内部按 decision_interval 刷新持久命令
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, Mapping, Tuple

import yaml

from openmdbench.scenarios.formal_v2 import formal_scenario_registry_v2
from openmdbench.schemas.interface_v2 import (
    ActionBatchV2,
    DiscreteActionV2,
    PersistentCommandV2,
)

ACTIVE_LIFECYCLES = {"active", "degraded"}


def load_attack_profile_data(public_id: str) -> Dict[str, Any]:
    """读取场景正式包旁的 agents.yaml（rule-agent-team@2.0 数据，只读）。"""
    registry = formal_scenario_registry_v2()
    if public_id not in registry:
        # 把实际查到的 id 与可用 id 一起报出来：此前只报"unknown scenario"，
        # 排查时无法区分"名字打错"与"注册表读到的是另一份"。
        keys = sorted(registry)
        close = [k for k in keys if str(public_id).split("-")[0].lower()
                 in k.lower()][:6]
        raise ValueError(
            f"unknown formal V2 scenario: {public_id!r} "
            f"(type={type(public_id).__name__}, len={len(str(public_id))}); "
            f"registry has {len(keys)} entries; similar={close}")
    path = registry[public_id].package_root / "agents.yaml"
    if not path.is_file():
        raise ValueError(f"no agents.yaml next to {public_id}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "rule-agent-team@2.0":
        raise ValueError("agents.yaml is not a rule-agent-team@2.0 profile")
    return payload


def _heading_to(origin: Tuple[float, ...], target: Tuple[float, ...]) -> float:
    east = float(target[0]) - float(origin[0])
    north = float(target[1]) - float(origin[1])
    if math.hypot(east, north) <= 1e-9:
        return 0.0
    return math.degrees(math.atan2(east, north)) % 360.0


class AttackProfileDriverV2:
    """按数据文件中的 attack 规则驱动突防方每艘平台直扑 objective。"""

    def __init__(self, public_id: str, *, seed: int = 7):
        payload = load_attack_profile_data(public_id)
        attack = payload["attack"]
        self.faction_id = str(attack["faction_id"])
        self.objective_m = (float(payload["objective_m"][0]),
                            float(payload["objective_m"][1]))
        self.pattern = str(attack.get("pattern", "direct"))
        self.speed_mps = float(attack.get("speed_mps", 12.0))
        self.split_angle_deg = float(attack.get("split_angle_deg", 0.0))
        self.serpentine_angle_deg = float(attack.get("serpentine_angle_deg", 0.0))
        self.serpentine_period_ticks = max(1, int(attack.get("serpentine_period_ticks", 1)))
        self.speed_cycle_mps = tuple(
            float(v) for v in attack.get("speed_cycle_mps", ()) or ()
        )
        self.speed_cycle_ticks = max(1, int(attack.get("speed_cycle_ticks", 1) or 1))
        self.routes = tuple(
            dict(route) for route in attack.get("routes", ()) or ()
            if isinstance(route, dict) and route.get("match_tag")
        )
        # 最简开火规则（A 方案）：按标签匹配武器，进入射程且持有自持接触即开火
        self.weapon_policies = tuple(
            dict(policy) for policy in attack.get("weapon_policies", ()) or ()
            if isinstance(policy, dict) and policy.get("match_tag")
        )
        self._fired: dict[str, int] = {}
        # 引擎侧武器冷却：提交被引擎以 combat.cooldown_denied 拒绝也会消耗
        # shots 预算，导致"2 发只打出去 1 发"。冷却从武器资源绑定读取（与执行层
        # 同一数据源），在本地按 tick 闸门，避免把弹药浪费在必然被拒的提交上。
        self._last_fire_tick: dict[tuple[str, str], int] = {}
        # 已向"指定设施目标"开过火的单位：之后不再保留弹药（可以自由对空射击）
        self._assigned_engaged: set[str] = set()
        self.decision_interval_ticks = max(1, int(payload.get("decision_interval_ticks", 5)))
        self.seed = seed
        self._commanded: set[str] = set()
        self.stats = {"submitted_batches": 0, "fires_submitted": 0}
        # 每 tick 重置：本 tick 提交的开火明细（与执行层 fires 同形状），
        # 供 run_episode 用引擎 child_receipts 判定"提交 ≠ 执行"。
        self._fire_actions: list[dict] = []

    # ------------------------------------------------------------------
    # 航向 / 速度（与数据文件的 pattern 语义一致）
    # ------------------------------------------------------------------

    def _lane(self, entity_id: str) -> Tuple[int, float]:
        digest = hashlib.sha256(entity_id.encode("utf-8")).digest()
        sign = -1 if digest[-1] % 2 else 1
        phase = int.from_bytes(digest[1:5], "big") / float(2 ** 32)
        return sign, phase

    def _route_for(self, tags, tick: int) -> Dict[str, Any]:
        """Select a declarative route segment by entity tag and simulation tick."""
        tagset = {str(tag) for tag in tags}
        for route in self.routes:
            if str(route["match_tag"]) not in tagset:
                continue
            start_tick = int(route.get("start_tick", 0))
            until_tick = route.get("until_tick")
            if tick < start_tick:
                continue
            if until_tick is not None and tick >= int(until_tick):
                continue
            return route
        return {}

    def _attack_heading(self, entity_id: str, position, tick: int,
                        route: Mapping[str, Any]) -> float:
        objective = route.get("objective_m", self.objective_m)
        base = _heading_to(position, objective)
        pattern = str(route.get("pattern", self.pattern))
        split_angle = float(route.get("split_angle_deg", self.split_angle_deg))
        serpentine_angle = float(
            route.get("serpentine_angle_deg", self.serpentine_angle_deg)
        )
        serpentine_period = max(
            1, int(route.get("serpentine_period_ticks", self.serpentine_period_ticks))
        )
        if pattern == "direct":
            return base
        sign, phase = self._lane(entity_id)
        if pattern == "split_evasion":
            return (base + sign * split_angle) % 360.0
        cycle = 2.0 * math.pi * (tick / serpentine_period + phase)
        return (base + sign * split_angle
                + serpentine_angle * math.sin(cycle)) % 360.0

    def _attack_speed(self, entity_id: str, tick: int,
                      route: Mapping[str, Any]) -> float:
        values = tuple(float(value) for value in route.get(
            "speed_cycle_mps", self.speed_cycle_mps
        ) or ()) or (float(route.get("speed_mps", self.speed_mps)),)
        cycle_ticks = max(
            1, int(route.get("speed_cycle_ticks", self.speed_cycle_ticks))
        )
        digest = hashlib.sha256(f"{self.seed}:{entity_id}".encode()).digest()
        phase = int.from_bytes(digest[:4], "big") % len(values)
        return values[(phase + tick // cycle_ticks) % len(values)]

    # ------------------------------------------------------------------
    # 最简开火规则（A 方案，只为让红方"打得出去"）
    # ------------------------------------------------------------------

    def _weapon_for(self, tags) -> dict | None:
        tagset = {str(tag) for tag in tags}
        for policy in self.weapon_policies:
            if str(policy["match_tag"]) in tagset:
                return policy
        return None

    @staticmethod
    def _contact_target(contact_id: str, observer: str) -> str:
        prefix = f"sensor.contact.{observer}."
        return contact_id[len(prefix):] if contact_id.startswith(prefix) else ""

    @staticmethod
    def _weapon_cooldown(entity_view, weapon_ref: str) -> int:
        """引擎侧武器冷却 tick 数（从实体武器资源绑定读取；读不到=0 不限制）。"""
        definition = getattr(entity_view, "definition", None)
        bindings = getattr(definition, "resource_bindings", None) or {}
        for binding in bindings.get("weapons", ()) or ():
            if getattr(binding, "exact_ref", None) != weapon_ref:
                continue
            content = getattr(binding, "normalized_content", None) or {}
            try:
                return max(0, int(content.get("cooldown_ticks", 0)))
            except (TypeError, ValueError):
                return 0
        return 0

    def _fire_action(self, entity_id: str, tick: int, weapon_ref: str,
                     contact_id: str) -> DiscreteActionV2:
        return DiscreteActionV2(
            schema_version="2.0",
            action_id=f"eval.attack.fire.{entity_id}.{tick}",
            action_type="fire_weapon",
            entity_id=entity_id,
            faction_id=self.faction_id,
            based_on_tick=tick,
            valid_until_tick=tick,
            payload={"weapon_ref": weapon_ref, "contact_id": contact_id},
        )

    def _maybe_fire(self, session, entity_id: str, position, tags, token: str,
                    tick: int, entity_view=None) -> int:
        """开火：总体目标是分配到的设施；途中遇到敌方无人机也打，但为设施留弹。

        优先级：指定目标（`target.facility.*` 对应的接触）→ 射程内任意可打目标。
        `reserve_for_assigned` 是"必须留给指定目标的弹数"：在还没向指定目标开过火
        之前，对**非**指定目标的射击不能把弹打光，否则飞机制导到设施上空时已无弹
        可用（实测 2 发弹全花在蓝方无人机上，3 个岛上设施 health 始终 1.0）。
        """
        policy = self._weapon_for(tags)
        if policy is None:
            return 0
        shots = int(policy.get("shots", 1))
        used = self._fired.get(entity_id, 0)
        if shots - used <= 0:
            return 0
        reserve = max(0, int(policy.get("reserve_for_assigned", 0)))
        weapon_ref = str(policy["weapon_ref"])
        last_tick = self._last_fire_tick.get((entity_id, weapon_ref))
        if last_tick is not None:
            cooldown = self._weapon_cooldown(entity_view, weapon_ref)
            if tick - last_tick < max(1, cooldown):
                return 0
        target_tag = next(
            (str(tag) for tag in tags if str(tag).startswith("target.")), None)
        if target_tag is None:
            return 0
        wanted = target_tag.split(".", 1)[1]
        minimum = float(policy.get("min_range_m", 0.0))
        maximum = float(policy.get("max_range_m", 1.0e9))
        observation = session.world_view.observation(observer_faction_id=self.faction_id)
        # 先找"指定目标"的接触；找不到则退化为"射程内任意可打目标"（B2 编组分配优先，
        # 但保证红方真的会开火；目标域与交战合法性仍由引擎裁决）
        mine = [c for c in observation.contacts_by_faction.get(self.faction_id, ())
                if str(c.get("observer_entity_id") or "") == entity_id]
        ordered = ([c for c in mine
                    if self._contact_target(str(c.get("contact_id") or ""), entity_id) == wanted]
                   + [c for c in mine
                      if self._contact_target(str(c.get("contact_id") or ""), entity_id) != wanted])
        chosen = None
        for contact in ordered:
            estimated = contact.get("estimated_position_m")
            if not estimated:
                continue
            is_assigned = (self._contact_target(
                str(contact.get("contact_id") or ""), entity_id) == wanted)
            if (not is_assigned and reserve > 0
                    and entity_id not in self._assigned_engaged
                    and used >= shots - reserve):
                continue  # 保留弹药给指定设施目标
            distance = math.dist(position, tuple(float(v) for v in estimated))
            if not minimum <= distance <= maximum:
                continue
            chosen = contact
            break
        for contact in (() if chosen is None else (chosen,)):
            contact_id = str(contact.get("contact_id") or "")
            action = self._fire_action(entity_id, tick,
                                       str(policy["weapon_ref"]), contact_id)
            session.submit_actions(
                batch=ActionBatchV2(
                    schema_version="2.0",
                    session_id=session.session_id,
                    batch_id=f"eval.attack.firebatch.{entity_id}.{tick}",
                    idempotency_key=f"eval.attack.fireidem.{entity_id}.{tick}",
                    faction_id=self.faction_id,
                    based_on_tick=tick,
                    valid_until_tick=tick,
                    persistent_commands=(),
                    discrete_actions=(action,),
                ),
                authority_token=token,
                operation_id=f"eval.attack.firesubmit.{entity_id}.{tick}",
                expected_tick=tick,
            )
            if self._contact_target(contact_id, entity_id) == wanted:
                self._assigned_engaged.add(entity_id)
            self._fired[entity_id] = self._fired.get(entity_id, 0) + 1
            self._last_fire_tick[(entity_id, str(policy["weapon_ref"]))] = tick
            self.stats["fires_submitted"] += 1
            self._fire_actions.append({
                "tick": tick,
                "entity_id": entity_id,
                "contact_id": contact_id,
                "weapon_ref": str(policy["weapon_ref"]),
                "action_id": str(action.action_id),
            })
            return 1
        return 0

    # ------------------------------------------------------------------
    # 每 tick 驱动
    # ------------------------------------------------------------------

    def __call__(self, session) -> Dict[str, Any]:
        tick = session.world_view.tick
        self._fire_actions = []
        refresh = tick % self.decision_interval_ticks == 0
        valid_until = tick + self.decision_interval_ticks
        observation = session.world_view.observation(
            observer_faction_id=self.faction_id
        )
        tokens = {
            grant.entity_id: token
            for token, grant in session.world_view.authority_tokens.items()
        }
        tags_by_entity = {
            entity.id: tuple(entity.tags)
            for entity in session.world_view.entities_stable()
            if entity.faction_id == self.faction_id
        }
        meta_by_entity = {
            entity.id: entity
            for entity in session.world_view.entities_stable()
            if entity.faction_id == self.faction_id
        }
        submitted = 0
        fires = 0
        for item in observation.own_entities:
            entity_id = str(item["entity_id"])
            if item.get("lifecycle_state") not in ACTIVE_LIFECYCLES:
                continue
            token = tokens.get(entity_id)
            if token is None:
                continue
            position = tuple(float(v) for v in item["position_m"])
            entity_tags = tags_by_entity.get(entity_id, ())
            # 开火判定必须每 tick 做：自爆窗口只有 0–30 m，而决策间隔是 5 tick
            # （10 m/s 的船两次决策之间已前进 50 m，会直接冲过窗口）
            fires += self._maybe_fire(session, entity_id, position, entity_tags, token,
                                      tick, meta_by_entity.get(entity_id))
            if entity_id in self._commanded and not refresh:
                continue
            route = self._route_for(tags_by_entity.get(entity_id, ()), tick)
            heading = self._attack_heading(entity_id, position, tick, route)
            speed = self._attack_speed(entity_id, tick, route)
            suffix = f"{entity_id}.{tick}"
            session.submit_actions(
                batch=ActionBatchV2(
                    schema_version="2.0",
                    session_id=session.session_id,
                    batch_id=f"eval.attack.batch.{suffix}",
                    idempotency_key=f"eval.attack.idem.{suffix}",
                    faction_id=self.faction_id,
                    based_on_tick=tick,
                    valid_until_tick=valid_until,
                    persistent_commands=(
                        PersistentCommandV2(
                            schema_version="2.0",
                            command_id=f"eval.attack.nav.{suffix}",
                            command_type="navigation",
                            entity_id=entity_id,
                            faction_id=self.faction_id,
                            based_on_tick=tick,
                            valid_until_tick=valid_until,
                            payload={
                                "speed_mps": speed,
                                "heading_deg": heading,
                                "altitude_m": position[2],
                            },
                        ),
                    ),
                    discrete_actions=(),
                ),
                authority_token=token,
                operation_id=f"eval.attack.submit.{suffix}",
                expected_tick=tick,
            )
            self._commanded.add(entity_id)
            submitted += 1
        self.stats["submitted_batches"] += submitted
        return {"submitted": submitted, "fires": fires,
                "fire_actions": list(self._fire_actions), "refresh": refresh}

    def get_stats(self) -> Dict[str, Any]:
        return dict(self.stats)
