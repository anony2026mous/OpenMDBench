"""纯 LLM 智能体（V2 迁移版）—— LLM 每 tick 直接输出低层执行命令，不经 GOAI 目标层。

对应论文 System B（OpenMDBench0830.md:169 "Pure LLM: LLM emits low-level actions
directly"）与 grid 的 pure_llm_agent.py（"every step, direct movement"）：
无规划层、无 GOAI 执行层，LLM 本身就是控制器。

- 输出协议：每单位一条命令 {"command": "navigate"|"fire"|"hold", ...}
- 掩码（我方强制）：固定设施不发命令；无武器策略单位不能 fire；
  fire 的接触必须是该单位自己观测到的且距离在射程内；速度按单位上限截断；
  非法命令 → 该单位 hold。被掩码命令计数 masked_count。
- 回退：LLM 失败/解析失败 → 极简规则控制器（带武器单位追最近接触+就近开火，
  其余驻守），与 grid 版一致（grid 回退同样是手写规则，不是 GOAI 栈）。
- 思考开关：统一关闭（enable_thinking=False）。千问是思考模型，开思考会吃光
  max_tokens 导致 content 为空；论文只保留"关闭思考"这一种范式。
- 调用节奏：与混合组同节奏（默认每 10 tick 一次，与论文 hybrid "replan every 10
  steps" 对齐）。论文 0820 基线 B 曾写 "every step, direct movement"（grid 实测
  一局 1331s；V2 1800 tick 每步调用 ≈ 6 小时，不采用）；两次调用之间复用上一组
  动作重新提交。

用法（run_episode.py 已接入）：
    run_episode.py --planner pure-llm --plan-interval 10
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, Mapping, Optional, Tuple

from openmdbench.schemas.interface_v2 import (
    ActionBatchV2,
    DiscreteActionV2,
    PersistentCommandV2,
)

from interception_graph import HistoryBuffer
from v2_executor import (
    ACTIVE_LIFECYCLES,
    ExecutorConfigV2,
    WeaponPolicyV2,
    _dist3,
    _heading_to,
    ammo_ref_for,
    contact_entity_suffix,
    fixed_site_weapon_policy,
    platform_kind,
)

# 默认上下文（AD-002 口径；其它场景由调用方传入 prompt_context 覆盖）
_DEFAULT_PROMPT_CONTEXT = {
    "force_desc": ("interceptor UAVs (armed, weapon range {weapon_range} m) "
                   "and picket USVs (sensors only, no weapons). "
                   "Fixed shore sites (if present) auto-fire their close-in CIWS "
                   "and need no commands."),
    "mission_desc": ("prevent 3+ intruder aircraft from entering the "
                     "protected zone around {objective}"),
    "objective": "(0,0)",
    "weapon_range": "500-8000",
    # speed_range 不再硬编码：由调用方从 speed_max_by_tag 派生后传入，
    # 未传时由 __init__ 依据实际包线填好（见 resolved 构造）。
}

SYSTEM_PROMPT = """You are a tactical controller DIRECTLY commanding every unit (no executor layer).
When enabled, the shared frontend supplies observed distance, bearing, approach trends,
ammunition and reachability estimates. These are observations, not action commands.
You output the low-level command for each unit every decision cycle.

Your force: {force_desc}
Mission: {mission_desc}

Command schema per unit:
- {{"command": "navigate", "heading_deg": <0-360, north=0 clockwise>, "speed_mps": <{speed_range}>}}
- {{"command": "fire", "contact_id": "<contact_id>"}}   (armed units only, and only
  contacts that this unit itself observes, within {weapon_range} m)
- {{"command": "hold"}}

Rules:
- Only hostile contacts appear in the report (ROE is enforced by the engine)
- Prioritize intruders closest to the protected objective {objective}, then nearest/highest-confidence threats.
- INTERCEPT EARLY: navigate armed units toward the protected-zone intercept point (about the
  final 30% of the route) before the threat reaches the boundary; use bearing, distance and ETA.
- FIRE DISCIPLINE: one interceptor fires at one target per decision cycle; spread units across
  distinct threats and prefer the closest threat. Never repeatedly fire at the same target in one tick.
- Do not command units not listed; use only the unit ids and contact ids given
- Coordinates are meters, continuous.

IMPORTANT: Output ONLY the JSON object. No explanation."""

ACTION_PROMPT = """Tick {tick}. Current Tactical Situation:
- Mission: {mission_desc}
- Weapon range: {weapon_range} m. A unit can only FIRE at contacts it observes itself within weapon range.
- Scheduled attack timeline (scenario context):
{timeline}

Your units:
{friendly}

Interception Graph (pre-computed tactical geometry per unit):
{graph}

Fixed-site summary:
{shore}

Detected contacts:
{contacts}

Previous Decision:
{history}

Command feedback from last cycle:
{feedback}

Tactical Guidance for Direct Control:
1. Bearing is the current unit-to-contact direction, NOT a solved lead heading.
   Choose navigation heading and speed yourself; north=0, east=90, south=180, west=270.
2. WEAPON/TARGET DOMAIN: each intercept edge carries `domain_ok` and `target_class`
   (air / surface). A unit may only engage contacts whose `target_class` its own weapon
   covers — `domain_ok=false` means the engine will reject that shot outright. Never spend
   a cycle firing on a `domain_ok=false` edge; re-task that unit to a `domain_ok=true`
   target instead (e.g. air-defence UAVs hunt air raiders, surface boats hunt surface boats).
3. can_intercept indicates geometric/observation availability AND a legal domain pairing.
   Choose fire only after considering ammunition, cooldown, range and ROE.
4. INTERCEPT EARLY: an edge with `prepare=true` and `feasible=true` is a threat you can still
   reach before it enters weapon range. Move such units now; do not wait until the raider is
   at the objective, where the only remaining option is a point-blank shot.
5. If no prior intelligence is disclosed, decide which contacts are real threats from your
   own observations (closing rate, distance to the protected zone, behaviour trend); be
   sparing with missiles against contacts that are not closing on the objective.

Output JSON format:
{{"actions": {{
  "defender.interceptor-001": {{"command": "navigate", "heading_deg": 270, "speed_mps": @@SPEED@@}},
  "defender.interceptor-002": {{"command": "fire",
    "contact_id": "sensor.contact.defender.interceptor-002.intruder.wave-1-003"}},
  "defender.picket-001": {{"command": "hold"}}
}}}}

One entry per unit id from the list above. Only output the JSON, nothing else."""


ACTION_PROMPT_RAW = """Tick {tick}. Current Tactical Situation:
- Mission: {mission_desc}
- Weapon range: {weapon_range} m. A unit can only FIRE at contacts it observes itself within weapon range.

Your units:
{friendly}

Detected contacts:
{contacts}

Previous Decision:
{history}

Command feedback from last cycle:
{feedback}

Tactical Guidance for Direct Control:
1. Navigate armed units toward threats that are closing on the protected objective, at maximum speed.
2. Issue "fire" with the target contact_id when the target is within weapon range and observed by that unit.
3. Use only the unit ids and contact ids given above.

Output JSON format:
{{"actions": {{
  "defender.interceptor-001": {{"command": "navigate", "heading_deg": 270, "speed_mps": @@SPEED@@}},
  "defender.interceptor-002": {{"command": "fire",
    "contact_id": "sensor.contact.defender.interceptor-002.intruder.wave-1-003"}},
  "defender.picket-001": {{"command": "hold"}}
}}}}

One entry per unit id from the list above. Only output the JSON, nothing else."""


def parse_actions(response: str, unit_ids) -> Dict[str, dict]:
    """解析 LLM 返回：找第一个含 "actions" 的 JSON 对象（兼容 reasoning 前后缀）。"""
    if not response:
        return {}
    decoder = json.JSONDecoder()
    idx = 0
    while True:
        start = response.find("{", idx)
        if start == -1:
            return {}
        try:
            obj, _ = decoder.raw_decode(response[start:])
            if isinstance(obj, dict) and "actions" in obj:
                raw = obj["actions"]
                if not isinstance(raw, dict):
                    return {}
                actions: Dict[str, dict] = {}
                for uid, spec in raw.items():
                    if uid not in unit_ids:
                        continue
                    if isinstance(spec, dict):
                        actions[str(uid)] = spec
                    elif isinstance(spec, str):
                        try:
                            parsed = json.loads(spec)
                            if isinstance(parsed, dict):
                                actions[str(uid)] = parsed
                        except json.JSONDecodeError:
                            pass
                return actions
        except (json.JSONDecodeError, ValueError):
            pass
        idx = start + 1


class PureLLMAgentV2:
    """纯 LLM 控制器：__call__(session) 每 tick 直接提交低层命令。"""

    def __init__(
        self,
        *,
        faction_id: str,
        llm=None,
        weapon_policies: Tuple[WeaponPolicyV2, ...] = (),
        speed_max_by_tag: Optional[Dict[str, float]] = None,
        call_interval: int = 10,
        name: str = "defender.pure-llm",
        prompt_context: Optional[dict] = None,
        graph_builder = None,
        include_graph: Optional[bool] = None,
        max_tokens: int = 2048,
    ):
        self.faction_id = faction_id
        self.graph_builder = graph_builder
        # 前置模块开关（对照实验用）：有图且未显式关闭 → 用带结构化图的提示词；
        # 关闭/无图 → 仅原始态势报告（裸 LLM 对照臂）。
        self.include_graph = (graph_builder is not None
                              if include_graph is None else bool(include_graph))
        self.llm = llm
        self.max_tokens = max_tokens
        self.weapon_policies = weapon_policies
        self.speed_max_by_tag = speed_max_by_tag or {
            "uav": 12.0, "usv": 12.0, "interceptor": 12.0, "picket": 12.0}
        self.call_interval = max(1, int(call_interval))
        self.name = name
        # 场景化提示词上下文（兵种/任务/保护区/射程），AD-002 为默认口径
        resolved = dict(_DEFAULT_PROMPT_CONTEXT)
        if prompt_context:
            resolved.update(prompt_context)
        resolved["force_desc"] = resolved["force_desc"].format(
            weapon_range=resolved["weapon_range"])
        # speed_range 必须与实际包线一致（此前硬编码 "0-45"，而真实上限是
        # 场景声明的 43 或 40 —— 提示词比执行层宽松，可能诱导 LLM 下达超限速度）。
        # 由 speed_max_by_tag 派生，逐平台列出，与逐单位清单同源。
        if not resolved.get("speed_range"):
            _by_kind = {k: v for k, v in self.speed_max_by_tag.items()
                        if k in ("uav", "usv")}
            _cap = max(self.speed_max_by_tag.values()) if self.speed_max_by_tag else 0.0
            if _by_kind:
                resolved["speed_range"] = ", ".join(
                    f"{k} 0-{float(v):.0f}" for k, v in sorted(_by_kind.items()))
            else:
                resolved["speed_range"] = f"0-{float(_cap):.0f}"
        # few-shot 示例里的速度值：此前固定写 40，与场景包线（43 或 40）不符。
        # 用占位符在格式化后替换，避免与模板的 JSON 双花括号冲突。
        _cap_any = max(self.speed_max_by_tag.values()) if self.speed_max_by_tag else 0.0
        self._example_speed = f"{float(_cap_any):.0f}"
        resolved["mission_desc"] = resolved["mission_desc"].format(
            objective=resolved["objective"])
        self._prompt_context = resolved
        self._system_prompt = SYSTEM_PROMPT.format(**resolved).replace(
            "@@SPEED@@", self._example_speed)
        # 保护区坐标（数值）：接触表里的 distance_to_zone / bearing / ETA 都相对它算
        objective_xy = resolved.get("objective_xy", (0.0, 0.0))
        self._objective_xy = (float(objective_xy[0]), float(objective_xy[1]))
        self._last_parsed: Dict[str, dict] = {}
        self._last_fired: Dict[Tuple[str, str], int] = {}
        self._shore_last_fire: Dict[Tuple[str, str], int] = {}
        self._ammo: Dict[str, Dict[str, int]] = {}
        # 历史记忆（纯信息输入，不施加任何一致性约束——保持 LLM 决策自由）
        self.history = HistoryBuffer(size=5)
        self._last_masked: List[str] = []
        self.llm_calls = 0
        self.fallback_count = 0
        self.masked_count = 0
        self.submitted_batches = 0
        self.fires = 0

    # ------------------------------------------------------------------
    # 提示词 / 策略匹配
    # ------------------------------------------------------------------

    def _build_prompt(self, observation, tick: int,
                      unit_roles: Mapping[str, object], meta: Mapping[str, Any],
                      graph=None,
                      history_text: str = "(none yet)",
                      feedback_text: str = "(none)") -> str:
        friendly = "\n".join(
            f"{item['entity_id']}: kind={platform_kind(meta.get(str(item['entity_id'])))} "
            f"position_m={item['position_m']} heading_deg={item.get('heading_deg')} "
            f"energy={item.get('energy')} "
            f"speed_limit_mps={self._speed_limit(meta.get(str(item['entity_id'])), unit_roles.get(str(item['entity_id']), ()))}"
            for item in observation.own_entities
            if item.get("lifecycle_state") in ACTIVE_LIFECYCLES
        ) or "(none)"
        contact_lines = []
        ox, oy = self._objective_xy
        # 来袭速度必须取场景声明值：原先硬编码 250 m/s，把 ETA 低估约 6 倍
        # （本场景红方无人机 43 m/s），会误导"什么时候该提前占位"的判断。
        intruder_speed = float(self._prompt_context.get("intruder_speed_mps", 250.0) or 250.0)
        for c in observation.contacts_by_faction.get(
                observation.observer_faction_id, ()):
            x, y = float(c["estimated_position_m"][0]), float(c["estimated_position_m"][1])
            distance_to_zone = math.hypot(x - ox, y - oy)
            contact_lines.append(
                f"  {c['contact_id']}: by {c['observer_entity_id']}, "
                f"pos=({x:.0f},{y:.0f}), "
                f"alt={float(c['estimated_position_m'][2]):.0f}, "
                f"conf={c['confidence']:.2f}, age={c['age_ticks']}, "
                f"distance_to_zone_m={distance_to_zone:.0f}, "
                f"bearing_deg={math.degrees(math.atan2(x - ox, y - oy)) % 360:.0f}, "
                f"estimated_eta_ticks={distance_to_zone / max(intruder_speed, 1e-9):.0f}"
            )
        
        graph_text = graph.format_for_prompt() if graph is not None else "(no graph available)"
        # 敌方作战时间线只在 --llm-briefing declared 时披露。默认 withheld 不给：
        # 实测确认 "armed vs decoy" 不是观测字段（观测只有位置/置信度/观测者），
        # 所以任何波次时刻/方位/兵力数字都无法从观测推导，只能来自场景声明；
        # 而 rule-rule 与 rl 两臂从不读该声明 ⇒ 给了就是特权信息，对照不再公平。
        # 此前这里 **无条件** 注入，是 pure-llm 最后一个情报通道（2026-09-27 关闭）。
        if self._prompt_context.get("briefing_declared", False):
            timeline_text = (graph.format_timeline_for_prompt()
                             if graph is not None else "(no timeline declared)")
        else:
            timeline_text = (
                "NOT DISCLOSED - no prior intelligence on the enemy is available. "
                "You are NOT told how many waves will arrive, when, from which axis, "
                "or which contacts are armed. Several waves and unarmed decoys are "
                "possible; classify every contact from your own observations.")

        if not self.include_graph:
            # 对照臂：无前置模块，仅原始态势报告
            return ACTION_PROMPT_RAW.format(
                tick=tick,
                mission_desc=self._prompt_context.get("mission_desc", "defend objective"),
                weapon_range=self._prompt_context.get("weapon_range", "500-8000"),
                friendly=friendly,
                contacts="\n".join(contact_lines) or "  None",
                history=history_text,
                feedback=feedback_text,
            ).replace("@@SPEED@@", self._example_speed)

        return ACTION_PROMPT.format(
            tick=tick,
            mission_desc=self._prompt_context.get("mission_desc", "defend objective"),
            weapon_range=self._prompt_context.get("weapon_range", "500-8000"),
            timeline=timeline_text,
            graph=graph_text,
            friendly=friendly,
            shore=graph.format_shore_for_prompt() if graph is not None else "(none)",
            contacts="\n".join(contact_lines) or "  None",
            history=history_text,
            feedback=feedback_text,
        ).replace("@@SPEED@@", self._example_speed)

    def _policy_for(self, tags) -> Optional[WeaponPolicyV2]:
        tagset = set(tags)
        for policy in self.weapon_policies:
            if set(policy.selector_tags) <= tagset:
                return policy
        return None

    def _speed_limit(self, meta_entity, tags) -> float:
        kind = platform_kind(meta_entity)
        if kind in self.speed_max_by_tag:
            return float(self.speed_max_by_tag[kind])
        for tag, limit in self.speed_max_by_tag.items():
            if tag in tags:
                return float(limit)
        # 兜底必须与执行层同源：ExecutorConfigV2.default_speed_mps（12.0）。
        # 此前硬编码 15.0，与执行层的 12.0 不一致 —— 提示词会让 LLM 以为还能跑
        # 更快。该分支只在平台类别与全部标签都未命中时触发（如岸基固定设施）。
        return float(ExecutorConfigV2.default_speed_mps)

    def _ammo_remaining(self, meta, entity_id: str, weapon_ref: str) -> Optional[int]:
        """弹药余量：优先引擎实时状态（state.ammunition），回退定义初始值。"""
        entity_view = meta.get(entity_id) if meta is not None else None
        live = getattr(getattr(entity_view, "state", None), "ammunition", None)
        if live is not None:
            self._ammo[entity_id] = {str(k): int(v) for k, v in dict(live).items()}
        elif entity_id not in self._ammo:
            definition = getattr(entity_view, "definition", None)
            initial = getattr(definition, "runtime_initial", None)
            ammo = getattr(initial, "ammunition", None)
            self._ammo[entity_id] = (
                {str(k): int(v) for k, v in dict(ammo).items()} if ammo else {}
            )
        resolved_ref = ammo_ref_for(self._ammo[entity_id], weapon_ref)
        return self._ammo[entity_id].get(resolved_ref) if resolved_ref else None

    # ------------------------------------------------------------------
    # 提交
    # ------------------------------------------------------------------

    @staticmethod
    def _tokens_by_entity(session) -> Dict[str, str]:
        return {
            grant.entity_id: token
            for token, grant in session.world_view.authority_tokens.items()
        }

    def _submit(self, session, *, entity_id: str, token: str, tick: int,
                command: PersistentCommandV2,
                action: Optional[DiscreteActionV2]) -> None:
        children = () if action is None else (action,)
        suffix = f"{entity_id}.{tick}"
        session.submit_actions(
            batch=ActionBatchV2(
                schema_version="2.0",
                session_id=session.session_id,
                batch_id=f"eval.purellm.batch.{suffix}",
                idempotency_key=f"eval.purellm.idem.{suffix}",
                faction_id=self.faction_id,
                based_on_tick=tick,
                valid_until_tick=tick + 1,
                persistent_commands=(command,),
                discrete_actions=children,
            ),
            authority_token=token,
            operation_id=f"eval.purellm.submit.{suffix}",
            expected_tick=tick,
        )
        self.submitted_batches += 1

    def _navigation(self, entity_id: str, tick: int, *, own: Mapping[str, Any],
                    speed_mps: float, heading_deg: float) -> PersistentCommandV2:
        position = tuple(float(v) for v in own["position_m"])
        return PersistentCommandV2(
            schema_version="2.0",
            command_id=f"eval.purellm.nav.{entity_id}.{tick}",
            command_type="navigation",
            entity_id=entity_id,
            faction_id=self.faction_id,
            based_on_tick=tick,
            valid_until_tick=tick + 1,
            payload={
                "speed_mps": float(speed_mps),
                "heading_deg": float(heading_deg) % 360.0,
                "altitude_m": position[2],
            },
        )

    # ------------------------------------------------------------------
    # 掩码与决策
    # ------------------------------------------------------------------

    def _decide(self, session, tick: int, parsed: Dict[str, dict],
                own: Dict[str, dict], contacts: Dict[str, dict],
                tokens: Dict[str, str], meta: Dict[str, Any],
                unit_roles: Mapping[str, object]) -> Tuple[list, list]:
        """把 LLM 动作翻译成 (entity_id, command, action)，非法→hold；返回 (提交列表, fires)。"""
        fires: list = []
        submissions = []
        fired_targets = set()
        masked: List[str] = []
        for uid, spec in parsed.items():
            entity_state = own.get(uid)
            if entity_state is None:
                continue
            if entity_state.get("lifecycle_state") not in ACTIVE_LIFECYCLES:
                continue
            token = tokens.get(uid)
            tags = tuple(getattr(meta.get(uid), "tags", ()))
            kind = platform_kind(meta.get(uid))
            if token is None or "fixed" in tags or kind == "fixed":
                continue  # 无授权 / 固定设施：不发命令（与执行层一致）
            own_pos = tuple(float(v) for v in entity_state["position_m"])
            heading = float(entity_state.get("heading_deg", 0.0))
            command_name = str(spec.get("command", "hold")) if isinstance(spec, dict) \
                else "hold"
            action: Optional[DiscreteActionV2] = None

            if command_name == "fire":
                requested = str(spec.get("contact_id", ""))
                contact = contacts.get(requested)
                if contact is None and requested:
                    # 千问常把完整 contact_id 简写为实体名后缀，这里做同样解析
                    candidates = [cid for cid in contacts if cid.endswith(requested)]
                    if len(candidates) == 1:
                        contact = contacts[candidates[0]]
                policy = self._policy_for(tags)
                if contact is not None and policy is not None:
                    distance = _dist3(
                        own_pos, tuple(float(v) for v in contact["estimated_position_m"])
                    )
                    # 开火资格：本机对同一底层实体持有自有接触（同执行层语义）
                    own_contact = next(
                        (c for c in contacts.values()
                         if c.get("observer_entity_id") == uid
                         and contact_entity_suffix(c) == contact_entity_suffix(contact)),
                        None,
                    )
                    last = self._last_fired.get((uid, policy.weapon_ref), -(10 ** 9))
                    ammo = self._ammo_remaining(meta, uid, policy.weapon_ref)
                    if (own_contact is not None
                            and policy.minimum_range_m <= distance <= policy.maximum_range_m
                            and tick - last >= policy.cooldown_ticks
                            and (ammo is None or ammo > 0)
                            and contact_entity_suffix(own_contact) not in fired_targets):
                        self._last_fired[(uid, policy.weapon_ref)] = tick
                        if ammo is not None:
                            self._ammo[uid][policy.weapon_ref] = ammo - 1
                        fire_cid = str(own_contact["contact_id"])
                        fired_targets.add(contact_entity_suffix(own_contact))
                        action = DiscreteActionV2(
                            schema_version="2.0",
                            action_id=f"eval.purellm.fire.{uid}.{tick}",
                            action_type="fire_weapon",
                            entity_id=uid,
                            faction_id=self.faction_id,
                            based_on_tick=tick,
                            valid_until_tick=tick,
                            payload={"weapon_ref": policy.weapon_ref,
                                     "contact_id": fire_cid},
                        )
                        fires.append({
                            "tick": tick, "entity_id": uid,
                            "contact_id": fire_cid,
                            "weapon_ref": policy.weapon_ref,
                            "action_id": str(action.action_id),
                        })
                        submissions.append((uid, self._navigation(
                            uid, tick, own=entity_state,
                            speed_mps=self._speed_limit(meta.get(uid), tags),
                            heading_deg=_heading_to(own_pos, contact["estimated_position_m"]),
                        ), action))
                        continue
                # 掩码：开火不合法 → hold（记录原因，下一轮反馈给 LLM）
                self.masked_count += 1
                if contact is None:
                    reason = "contact-id-not-found"
                elif policy is None:
                    reason = "unit-has-no-weapon"
                elif own_contact is None:
                    reason = "not-observed-by-this-unit"
                elif not (policy.minimum_range_m <= distance <= policy.maximum_range_m):
                    reason = "out-of-range"
                elif tick - last < policy.cooldown_ticks:
                    reason = "cooldown"
                elif ammo is not None and ammo <= 0:
                    reason = "no-ammunition"
                else:
                    reason = "already-fired-at-this-target"
                masked.append(f"{uid} -> {requested}: {reason}")
                submissions.append((uid, self._navigation(
                    uid, tick, own=entity_state, speed_mps=0.0, heading_deg=heading), None))
                continue

            if command_name == "navigate":
                try:
                    new_heading = float(spec.get("heading_deg", heading)) % 360.0
                except (TypeError, ValueError):
                    new_heading = heading
                try:
                    speed = float(spec.get("speed_mps", 0.0))
                except (TypeError, ValueError):
                    speed = 0.0
                limit = self._speed_limit(meta.get(uid), tags)
                if speed < 0.0 or speed > limit:
                    speed = min(max(speed, 0.0), limit)
                    self.masked_count += 1
                submissions.append((uid, self._navigation(
                    uid, tick, own=entity_state, speed_mps=speed,
                    heading_deg=new_heading), None))
                continue

            # hold / 其它 → 驻守
            submissions.append((uid, self._navigation(
                uid, tick, own=entity_state, speed_mps=0.0, heading_deg=heading), None))
        return submissions, fires, masked

    def _fallback(self, own: Dict[str, dict], contacts: Dict[str, dict],
                  unit_roles: Mapping[str, object]) -> Dict[str, dict]:
        """极简规则回退：带武器单位追最近接触，其余驻守（与 grid 版语义一致）。"""
        ox, oy = self._objective_xy
        ordered = sorted(
            contacts.values(),
            key=lambda c: math.dist(c["estimated_position_m"][:2], (ox, oy)),
        )
        fallback: Dict[str, dict] = {}
        for uid, state in own.items():
            roles = tuple(unit_roles.get(uid, ()))
            if "fixed" in roles or state.get("lifecycle_state") not in ACTIVE_LIFECYCLES:
                continue
            if self._policy_for(roles) is None:
                fallback[uid] = {"command": "hold"}
                continue
            contact = ordered[0] if ordered else None
            if contact is None:
                fallback[uid] = {"command": "hold"}
                continue
            if contact.get("observer_entity_id") == uid:
                fallback[uid] = {"command": "fire",
                                 "contact_id": str(contact["contact_id"])}
            else:
                own_pos = tuple(float(v) for v in state["position_m"])
                fallback[uid] = {
                    "command": "navigate",
                    "heading_deg": _heading_to(
                        own_pos, contact["estimated_position_m"]),
                    "speed_mps": self.speed_max_by_tag.get(
                        "interceptor" if "interceptor" in roles else "picket", 15.0),
                }
        return fallback

    def _shore_defence(self, session, tick: int, own, contacts, tokens,
                       meta) -> list:
        """岸基固定设施自动近防（纯 LLM 组同样接入；无近防场景天然空转）。"""
        fires: list = []
        for uid, entity_state in own.items():
            tags = tuple(getattr(meta.get(uid), "tags", ()))
            if "fixed" not in tags:
                continue
            token = tokens.get(uid)
            if token is None:
                continue
            policy = fixed_site_weapon_policy(meta.get(uid))
            if policy is None:
                continue
            last = self._shore_last_fire.get((uid, policy.weapon_ref), -(10 ** 9))
            if tick - last < policy.cooldown_ticks:
                continue
            ammo = self._ammo_remaining(meta, uid, policy.weapon_ref)
            if ammo is not None and ammo <= 0:
                continue
            position = tuple(float(v) for v in entity_state["position_m"])
            best = None
            for contact in contacts.values():
                if str(contact.get("observer_entity_id")) != uid:
                    continue
                if int(contact.get("age_ticks", 0)) > 8:
                    continue
                distance = _dist3(position, tuple(
                    float(v) for v in contact["estimated_position_m"]))
                if not (policy.minimum_range_m <= distance
                        <= policy.maximum_range_m):
                    continue
                if best is None or distance < best[0]:
                    best = (distance, str(contact["contact_id"]))
            if best is None:
                continue
            action = DiscreteActionV2(
                schema_version="2.0",
                action_id=f"eval.purellm.shore.{uid}.{tick}",
                action_type="fire_weapon",
                entity_id=uid,
                faction_id=self.faction_id,
                based_on_tick=tick,
                valid_until_tick=tick,
                payload={"weapon_ref": policy.weapon_ref,
                         "contact_id": best[1]},
            )
            self._shore_last_fire[(uid, policy.weapon_ref)] = tick
            session.submit_actions(
                batch=ActionBatchV2(
                    schema_version="2.0",
                    session_id=session.session_id,
                    batch_id=f"eval.purellm.shore.batch.{uid}.{tick}",
                    idempotency_key=f"eval.purellm.shore.idem.{uid}.{tick}",
                    faction_id=self.faction_id,
                    based_on_tick=tick,
                    valid_until_tick=tick,
                    persistent_commands=(),
                    discrete_actions=(action,),
                ),
                authority_token=token,
                operation_id=f"eval.purellm.shore.submit.{uid}.{tick}",
                expected_tick=tick,
            )
            self.submitted_batches += 1
            fires.append({
                "tick": tick, "entity_id": uid,
                "contact_id": best[1],
                "weapon_ref": policy.weapon_ref,
                "action_id": str(action.action_id),
            })
        return fires

    # ------------------------------------------------------------------
    # 每 tick
    # ------------------------------------------------------------------

    def __call__(self, session) -> Dict[str, Any]:
        tick = session.world_view.tick
        observation = session.world_view.observation(
            observer_faction_id=self.faction_id
        )
        own = {str(item["entity_id"]): item for item in observation.own_entities}
        contacts = {
            str(item["contact_id"]): item
            for item in observation.contacts_by_faction.get(self.faction_id, ())
        }
        meta = {entity.id: entity for entity in session.world_view.entities_stable()}
        unit_roles = {
            entity.id: frozenset(entity.tags)
            for entity in meta.values()
            if entity.faction_id == self.faction_id
        }
        active_ids = {
            uid for uid, state in own.items()
            if state.get("lifecycle_state") in ACTIVE_LIFECYCLES
        }

        used_fallback = False
        decided_this_tick = tick % self.call_interval == 0
        if decided_this_tick:
            parsed: Dict[str, dict] = {}
            if self.llm is not None:
                self.llm_calls += 1
                graph = None
                if self.graph_builder is not None and self.include_graph:
                    graph = self.graph_builder.build(observation, unit_roles, meta, tick)
                prompt = self._build_prompt(
                    observation, tick, unit_roles, meta,
                    graph=graph,
                    history_text=self.history.format_for_prompt(),
                    feedback_text="\n".join(self._last_masked) or "(none)",
                )
                response = self.llm.chat(
                    self._system_prompt, prompt, max_tokens=self.max_tokens, temperature=0.1
                )
                parsed = parse_actions(response, active_ids)
            if not parsed:
                used_fallback = True
                self.fallback_count += 1
                parsed = self._fallback(own, contacts, unit_roles)
            self._last_parsed = parsed
        else:
            parsed = self._last_parsed

        tokens = self._tokens_by_entity(session)
        submissions, fires_list, masked = self._decide(
            session, tick, parsed, own, contacts, tokens, meta, unit_roles
        )
        for uid, command, action in submissions:
            self._submit(session, entity_id=uid, token=tokens[uid], tick=tick,
                         command=command, action=action)
        # 岸基固定设施自动近防（与执行层共用同一套判定语义）
        shore_fires = self._shore_defence(session, tick, own, contacts, tokens, meta)
        fires_list = fires_list + shore_fires
        self.fires += len(fires_list)
        self._last_masked = masked

        # 历史记忆：每轮决策后记录（纯信息，无一致性约束——只供下一轮提示词参考）
        if decided_this_tick:
            summary: Dict[str, str] = {}
            for uid, spec in parsed.items():
                if not isinstance(spec, dict):
                    continue
                command = str(spec.get("command", "hold"))
                if command == "navigate":
                    summary[uid] = (
                        f"navigate(h={spec.get('heading_deg')},v={spec.get('speed_mps')})")
                elif command == "fire":
                    summary[uid] = f"fire({spec.get('contact_id')})"
                else:
                    summary[uid] = "hold"
            ammo_summary: Dict[str, Optional[int]] = {}
            for uid in active_ids:
                tags = tuple(getattr(meta.get(uid), "tags", ()))
                policy = self._policy_for(tags)
                if policy is not None:
                    ammo_summary[uid] = self._ammo_remaining(meta, uid, policy.weapon_ref)
            self.history.record(tick, summary, ammo_summary)
            if self.include_graph and self.graph_builder is not None:
                assignments = {
                    uid: str(spec["contact_id"])
                    for uid, spec in parsed.items()
                    if isinstance(spec, dict) and spec.get("command") == "fire"
                    and spec.get("contact_id")
                }
                self.graph_builder.history.record(tick, assignments, ammo_summary)

        # 无动作的活跃可动单位 → 驻守（防漂移）
        for uid, entity_state in own.items():
            if uid in parsed or uid not in active_ids:
                continue
            token = tokens.get(uid)
            tags = tuple(getattr(meta.get(uid), "tags", ()))
            kind = platform_kind(meta.get(uid))
            if token is None or "fixed" in tags or kind == "fixed":
                continue
            heading = float(entity_state.get("heading_deg", 0.0))
            self._submit(session, entity_id=uid, token=token, tick=tick,
                         command=self._navigation(
                             uid, tick, own=entity_state, speed_mps=0.0,
                             heading_deg=heading),
                         action=None)

        return {
            "tick": tick,
            "submit_result": None,
            "executor": {
                "fires": fires_list,
                "submitted": len(submissions),
                "safe_mode": False,
                "fallback": used_fallback,
                "masked": self.masked_count,
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "faction_id": self.faction_id,
            "planner": {"planner": "pure-llm"},
            "frontend": "graph" if self.include_graph else "raw",
            "max_tokens": self.max_tokens,
            # 速度包线必须落盘：历史上这一项没有记录，导致 2026-02-05 之前 43 局
            # pure-llm 无法区分是 45/10（旧默认）还是 43/8（对照）生的，
            # 只能整批作废重跑。其它五臂的上限来自 `ExecutorConfigV2.speed_by_tag`，
            # 由执行层自行记录；这里补上对等的一条。
            "speed_max_by_tag": {str(k): float(v)
                                 for k, v in sorted(self.speed_max_by_tag.items())},
            # 情报口径必须落盘（同 llm_planner）：declared 含敌方作战计划，
            # withheld 无情报 —— 两者分数不可混用。
            "briefing": ("declared"
                         if self._prompt_context.get("briefing_declared", False)
                         else "withheld"),
            "llm_calls": self.llm_calls,
            "fallback_count": self.fallback_count,
            "masked_count": self.masked_count,
            "submitted_batches": self.submitted_batches,
            "fires": self.fires,
        }

