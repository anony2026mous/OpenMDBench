"""LLM 规划层（V2 迁移版）—— grid hybrid_agent 的 LLM planner，输出同样的 GOAI 目标命令。

- 默认后端 Qwen3.8-27B（llm_client_hifi.LLMClient，内置并发闸门 ≤2，符合 B 线复用约定）；
- 输出协议与 RulePlannerV2 完全一致（GoalCommand 列表），可与 GOAIExecutorV2 互换；
- LLM 失败/输出无法解析/命令为空时回退到 fallback（默认 RulePlannerV2），
  并计 fallback_count，与 grid hybrid 的降级语义一致；
- 规划层不接触引擎：只消费 ObservationV2 与 unit_roles。
"""

from __future__ import annotations

import json
import math
import os
from typing import List, Mapping, Optional

from goai_protocol import GOAL_TYPES, GoalCommand
from rule_planner import RulePlannerConfigV2, RulePlannerV2

# 逐边诊断日志默认关闭：每个规划周期最多 12×top_k 行，1800 tick 会打出上万行，
# 把控制台和日志淹没（实测一次混合组刷出 6k+ 行）。需要时设
# OPENMDBENCH_GRAPH_VERBOSE=1 打开。
_GRAPH_VERBOSE = os.environ.get("OPENMDBENCH_GRAPH_VERBOSE", "").strip().lower() not in (
    "", "0", "false", "no", "off",
)

PLANNER_SYSTEM_PROMPT = """You are a strategic commander issuing GOAL COMMANDS through the GOAI interface.
You do NOT control individual movements — the execution layer translates goals into control.

Your force: {force_desc}
Mission: prevent 3+ intruders from entering the protected zone around {objective}.

Every decision cycle you output the complete set of goal commands (one per unit).
The execution layer may report goals as INFEASIBLE (missing target, dead unit, bad position).
You must then RE-PLAN with modified parameters — never reissue an identical infeasible goal.

goal_type options:
- "intercept": engage parameters.target_id (armed units only)
- "ambush": go to the LEAD intercept point of parameters.target_id (computed from the
  target's estimated velocity) and wait there; fire when the target enters the weapon
  envelope. Use it when the target is fast and far — it beats tail-chasing.
  optional: parameters.standoff_m (hold-off distance before committing)
- "barrier": station one unit as a screen on the arc facing the threat axis:
  parameters.axis_deg (bearing FROM which the threats come), parameters.radius_m
  (distance from the protected objective). Once on station it sweeps sideways
  automatically. Use it for the axis no interceptor is currently covering.
- "reserve": keep a unit at parameters.position (a rear anchor) but with an automatic
  commit trigger: it will move out and engage the closest threat that comes within
  parameters.commit_within_m of the objective (default 9000 m). Use it instead of a
  plain "hold" when you want a genuine reserve that still reacts.
- "disengage": break off the current task and return to parameters.position
  (or the rear anchor). Use it for units with ammo=0 or damaged units.
- "track": shadow parameters.target_id at distance
- "patrol": move to parameters.position and hold (now sweeps on arrival)
- "waypoint": go to parameters.position
- "hold": stay for parameters.duration ticks
- "return": head to the rear anchor
- "loiter": move to parameters.position and hold

Optional per-goal parameter `fire_policy` on intercept/ambush/reserve
(the executor uses `{default_fire_policy}` when you omit it):
- "assess": fire ONE missile, then wait ~12 ticks to assess the effect before
  firing again — conserves scarce ammunition; use it under tight ammo budgets.
- "salvo": fire up to two missiles quickly — use it for the single most dangerous target.
- "pk": hold fire until the range-dependent kill probability is good — use it when you
  have time and want every shot to count.
This parameter is part of the shared action space: the deterministic rule baseline can
issue it too (via its own fixed mapping), so choose it on merit, not to imitate.

Rules:
- Only hostile contacts appear in the report (ROE is enforced by the engine)
- Prioritize intruders closest to the protected objective {objective}, then nearest/highest-confidence threats.
- INTERCEPT TRIGGER: issue intercept immediately when `can_intercept=true` OR
  `prepare_intercept=true` (see Interception timing rule below); do not keep that
  unit on patrol/hold.
- Aim to meet threats before they reach the protected-zone boundary (roughly the final 30%
  of their route). Use position, bearing, distance-to-zone, and ETA to choose an interceptor.
- AMMUNITION BUDGET: count missiles you have already spent (see Previous Decision) and the
  waves still to come. Do not spend the last missiles on low-threat targets; prefer
  ambush/barrier for far targets and save intercept/salvo for those about to cross the boundary.
- FIRE DISCIPLINE: spread interceptors across distinct threats; do not assign multiple units
  to the same target unless there are more threats than armed units. Prefer the closest threat.
- INTERFACE RULE (critical): a unit can only FIRE at contacts it observes itself.
  Each contact line shows "by <observer_unit>" — issue "intercept" for unit U only
  against contacts with by=U. For contacts observed by someone else, either assign
  "intercept" to the observer unit (if armed) or use "track" for a sensor unit.
- task_id format: lowercase_words_001 (pattern ^[a-z_]+_[0-9]{{3}}$)
- Coordinates are meters, continuous.

### Interception timing rule

`can_intercept` and `prepare_intercept` represent two different phases:
- `can_intercept=true`: the target is already inside the effective intercept/fire window.
- `prepare_intercept=true`: the target may still be outside range, but it is approaching and
  is expected to enter the intercept window soon.

**Do NOT treat `can_intercept=false` as "no interception needed".**

When you see `can_intercept=false` AND `prepare_intercept=true`, treat that target as one
that needs interception EARLY: for any idle interceptor, if a high-threat target has
`prepare_intercept=true`, issue "intercept" NOW so the interceptor maneuvers toward the
target (or expected intercept area) in advance. It is FORBIDDEN to keep using patrol/track
just because `can_intercept=false`.

Only when `prepare_intercept=false` and no other threat needs handling should you prefer
patrol/track. Decision priority:
1. high-threat targets with `can_intercept=true`;
2. high-threat targets with `prepare_intercept=true`;
3. other targets that need continuous monitoring;
4. patrol.

`prepare_intercept=true` means "start intercept maneuvering NOW", not "wait until the target
enters range". For example, distance=8816, range_gap=816, closing_speed=16.3,
time_to_weapon_range=50 ticks, can_intercept=false, prepare_intercept=true — the correct
action is to issue "intercept" now, NOT continue patrol/track waiting for can_intercept.

This rule only affects planning timing; it does NOT change fire conditions. Actual firing
remains decided by the Executor based on range, observation, cooldown and ammunition."""

# 默认上下文（AD-002 口径；其它场景由调用方传入 prompt_context 覆盖）
_DEFAULT_PROMPT_CONTEXT = {
    "force_desc": ("interceptor UAVs (armed, engage contacts they detect themselves, "
                   "weapon range {weapon_range} m) and picket USVs (sensors only). "
                   "Fixed shore sites auto-fire their close-in CIWS and need no "
                   "commands."),
    "objective": "(0,0)",
    "weapon_range": "500-8000",
    "default_fire_policy": "assess",
    # 目标分类/ROE 指引必须由场景声明驱动，见下方 PLANNER_USER_TEMPLATE_GRAPH。
    "roe_notes": (
        "  * This scenario declares no diversion, feint or civilian wave: EVERY detected "
        "contact is a hostile threat. Engage it as soon as the graph shows "
        "can_intercept=true or prepare_intercept=true."
    ),
}

PLANNER_USER_TEMPLATE = """Tick {tick}. Situation report:

Your units (id, position_m, energy):
{friendly}

Detected contacts (contact_id, observer_unit, estimated_position_m, confidence, age_ticks,
distance_to_zone_m, bearing_deg, estimated_eta_ticks):
{contacts}

Recent execution-layer status reports:
{reports}

Output JSON only:
{{
  "goal_commands": [
    {{"task_id": "intercept_001", "goal_type": "intercept",
      "parameters": {{"unit_id": "defender.interceptor-001",
                      "target_id": "intruder.wave-1-001"}},
      "priority": 0.9, "deadline": 120}},
    {{"task_id": "patrol_001", "goal_type": "patrol",
      "parameters": {{"unit_id": "defender.picket-001",
                      "position": [12334.0, 4995.0]}},
      "priority": 0.5}}
  ],
  "reasoning": "brief explanation"
}}

Use only unit ids and contact ids from the lists above. Only output JSON."""

# 三段式提示词（Graph Builder 注入时使用）：任务状态 + 拦截关系图 + 历史决策
PLANNER_USER_TEMPLATE_GRAPH = """Tick {tick}. Current Situation:
- Mission: prevent 3+ intruders from entering the protected zone around {objective}.
- Weapon range {weapon_range} m; a unit can only FIRE at contacts it observes itself
  (can_intercept already accounts for observation ownership).
- Edge fields: feasible_eta=ticks for the interceptor to reach weapon range;
  feasible=false means the target reaches the protected zone BEFORE this interceptor
  can engage it (eta/dist_zone are the target's current values).
- Prioritize: targets with can_intercept=true first; then high-threat targets with
  prepare_intercept=true (issue intercept NOW, do not wait); then lowest ETA.
- Spread interceptors across distinct targets (fire discipline).
- ROE & TARGET CLASSIFICATION (scenario-declared; authoritative for THIS scenario):
{roe_notes}
- Shore close-in defence (auto-fires, needs no command; "(none)" if absent):
{shore}
- Prefer spending interceptors on targets OUTSIDE shore coverage when a shore site
  already has the target inside its listed range.
- Scheduled attack timeline (scenario-declared context, not an execution command):

Interception Graph:
{graph}

Previous Decision:
{history}

Output JSON only:
{{
  "goal_commands": [
    {{"task_id": "intercept_001", "goal_type": "intercept",
      "parameters": {{"unit_id": "defender.interceptor-001",
                      "target_id": "intruder.wave-1-001"}},
      "priority": 0.9, "deadline": 120}},
    {{"task_id": "patrol_001", "goal_type": "patrol",
      "parameters": {{"unit_id": "defender.picket-001",
                      "position": [12334.0, 4995.0]}},
      "priority": 0.5}}
  ],
  "reasoning": "brief explanation"
}}

Use only unit ids and contact ids from the graph above. Only output JSON."""


class LLMPlannerV2:
    """LLM planner：plan() 返回 GoalCommand 列表，与规则规划器同接口。

    wants_meta=True：告知编排器本规划器需要实体元数据（domain/tags/实时弹药），
    用于 Graph Builder；规则规划器保持 wants_meta 缺省（False），零改动。
    """

    wants_meta = True

    def __init__(self,
                 config: Optional[RulePlannerConfigV2] = None,
                 llm=None,
                 fallback_planner: Optional[RulePlannerV2] = None,
                 max_tokens: int = 2048,
                 temperature: float = 0.1,
                 graph_builder=None,
                 prompt_context: Optional[dict] = None,
                 armed_tags: Optional[tuple] = None):
        self.config = config or RulePlannerConfigV2()
        self.fallback = fallback_planner or RulePlannerV2(self.config)
        self.llm = llm
        self.max_tokens = max_tokens
        self.temperature = temperature
        # 结构化战场关系图（可选注入）：提供时用三段式提示词并维护 History
        self.graph_builder = graph_builder
        # 场景化提示词上下文（兵种描述/保护区坐标/武器射程），AD-002 为默认口径
        resolved = dict(_DEFAULT_PROMPT_CONTEXT)
        if prompt_context:
            resolved.update(prompt_context)
        resolved["force_desc"] = resolved["force_desc"].format(
            weapon_range=resolved["weapon_range"])
        self._prompt_context = resolved
        self._system_prompt = PLANNER_SYSTEM_PROMPT.format(**resolved)
        self._armed_tags = armed_tags
        self.plan_calls = 0
        self.fallback_count = 0
        self.parse_failures = 0
        # D1 修复：跨周期记忆——解析失败时沿用上一轮已校验目标集，而不是整局
        # 掉回规则（此前一次 JSON 抖动会让混合组"掉线一个周期"，却记在 LLM 账上）
        self.stale_plan_reuse = 0
        self._last_plan: List[GoalCommand] = []
        self._task_seq = 0

    def _armed_unit(self, roles) -> bool:
        """数据驱动武装判定：有图时按武器策略 selector 标签，否则按 armed_tags 兜底。"""
        if self.graph_builder is not None and hasattr(self.graph_builder, "is_armed"):
            return bool(self.graph_builder.is_armed(roles))
        tags = set(self._armed_tags) if self._armed_tags else {"interceptor"}
        return bool(tags & set(roles))

    def _next_task_id(self, prefix: str) -> str:
        self._task_seq += 1
        return f"{prefix}_{self._task_seq:03d}"

    # ------------------------------------------------------------------
    # 提示词
    # ------------------------------------------------------------------

    def _build_prompt(self, observation, tick: int,
                      reports: list,
                      unit_roles: Optional[Mapping[str, object]]) -> str:
        friendly_lines = [
            f"  {item['entity_id']}: pos=({item['position_m'][0]:.0f},"
            f"{item['position_m'][1]:.0f},{item['position_m'][2]:.0f}) "
            f"energy={item.get('energy')}"
            for item in observation.own_entities
            if item.get("lifecycle_state") in {"active", "degraded"}
        ]
        contact_lines = [
            f"  {c['contact_id']}: by={c.get('observer_entity_id', '?')} "
            f"pos=({c['estimated_position_m'][0]:.0f},{c['estimated_position_m'][1]:.0f}) "
            f"conf={c['confidence']:.2f} age={c['age_ticks']} "
            f"distance_to_zone_m={(float(c['estimated_position_m'][0]) ** 2 + float(c['estimated_position_m'][1]) ** 2) ** 0.5:.0f} "
            f"bearing_deg={math.degrees(math.atan2(float(c['estimated_position_m'][0]), float(c['estimated_position_m'][1]))) % 360:.0f} "
            f"estimated_eta_ticks={(float(c['estimated_position_m'][0]) ** 2 + float(c['estimated_position_m'][1]) ** 2) ** 0.5 / 250:.0f}"
            for c in observation.contacts_by_faction.get(
                observation.observer_faction_id, ()
            )
        ]
        report_lines = [
            f"  [{r.reported_at}] {r.task_id}: {r.status} progress={r.progress:.2f}"
            + (f" anomaly={r.anomaly}" if r.anomaly != "none" else "")
            for r in (reports or [])[-8:]
        ] or ["  (none)"]
        return PLANNER_USER_TEMPLATE.format(
            tick=tick,
            friendly="\n".join(friendly_lines) or "  None",
            contacts="\n".join(contact_lines) or "  None",
            reports="\n".join(report_lines),
        )

    # ------------------------------------------------------------------
    # 解析与校验
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_plan(response: str) -> Optional[dict]:
        if not response:
            return None
        decoder = json.JSONDecoder()
        idx = 0
        while True:
            start = response.find("{", idx)
            if start == -1:
                return None
            try:
                obj, _ = decoder.raw_decode(response[start:])
                if isinstance(obj, dict) and "goal_commands" in obj:
                    return obj
            except (json.JSONDecodeError, ValueError):
                pass
            idx = start + 1

    @staticmethod
    def _resolve_contact_id(tid: str, contacts_by_id, unit_id: str) -> Optional[str]:
        """把 LLM 输出的 target_id 规范化到完整 contact_id。

        千问常把 "sensor.contact.<owner>.<entity>" 简写成 "<entity>"。
        匹配顺序：
        1. 完全一致；
        2. 唯一后缀匹配；
        3. 多观测者持有同一实体（歧义）：优先"命令单位自己观测"的接触，
           其次置信度最高者——这是执行层开火所需要的火控接触。
        """
        if tid in contacts_by_id:
            return tid
        candidates = [cid for cid in contacts_by_id if cid.endswith(tid)]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            def rank(cid: str) -> tuple:
                contact = contacts_by_id[cid]
                owner = str(contact.get("observer_entity_id", ""))
                confidence = float(contact.get("confidence", 0.0))
                return (0 if owner == unit_id else 1, -confidence)
            return min(candidates, key=rank)
        return None

    def _validate_commands(self, plan: dict, observation, unit_roles) -> List[GoalCommand]:
        unit_ids = {
            str(item["entity_id"]) for item in observation.own_entities
            if item.get("lifecycle_state") in {"active", "degraded"}
        }
        contacts_by_id = {
            str(c["contact_id"]): c
            for c in observation.contacts_by_faction.get(
                observation.observer_faction_id, ()
            )
        }
        commands: List[GoalCommand] = []
        armed_units = {
            str(uid)
            for uid, roles in (unit_roles or {}).items()
            if self._armed_unit(set(roles)) and "fixed" not in set(roles)
        }
        for raw in plan.get("goal_commands", []):
            if not isinstance(raw, dict):
                continue
            cmd = GoalCommand.from_dict(raw)
            if cmd.goal_type not in GOAL_TYPES:
                continue
            if cmd.unit_id is None or cmd.unit_id not in unit_ids:
                continue
            tid = cmd.parameters.get("target_id")
            if tid is not None:
                resolved = self._resolve_contact_id(str(tid), contacts_by_id,
                                                   str(cmd.unit_id))
                if resolved is None:
                    continue
                cmd.parameters["target_id"] = resolved  # 重写为完整 id
            if cmd.goal_type == "intercept" and tid is not None:
                contact = contacts_by_id.get(str(cmd.parameters.get("target_id")))
                # ROE 约束过滤：若该接触已被标记为中立民用 (civilian)，禁止下达截击开火命令，自动降级为跟踪
                tags = tuple(contact.get("tags", ())) if contact else ()
                if "civilian" in tags:
                    cmd.goal_type = "track"
                else:
                    observer = str(contact.get("observer_entity_id")) if contact else ""
                    if observer in armed_units:
                        cmd.parameters["unit_id"] = observer
                    elif cmd.unit_id not in armed_units:
                        continue
            commands.append(cmd)
        return commands

    # ------------------------------------------------------------------
    # 规划
    # ------------------------------------------------------------------

    def plan(self, observation, tick: int,
             reports: Optional[list] = None,
             unit_roles: Optional[Mapping[str, object]] = None,
             meta: Optional[Mapping[str, object]] = None) -> List[GoalCommand]:
        commands: List[GoalCommand] = []
        graph = None
        if self.llm is not None:
            self.plan_calls += 1
            if self.graph_builder is not None and meta is not None:
                graph = self.graph_builder.build(observation, unit_roles, meta, tick)
                # 最小诊断日志：只打印值得关注的边（能打 / 该提前准备）
                for node in graph.interceptors:
                    for cand in node.candidates:
                        if _GRAPH_VERBOSE and (cand["can_intercept"]
                                               or cand["prepare_intercept"]):
                            print(
                                f"[graph t{tick}] {node.id}->{cand['target']} "
                                f"dist={cand['distance']:.0f} "
                                f"can={cand['can_intercept']} "
                                f"range_gap={cand['range_gap']:.0f} "
                                f"closing={cand['closing_speed']} "
                                f"approach={cand['approach_status']} "
                                f"ttr={cand['time_to_weapon_range_ticks']} "
                                f"prepare={cand['prepare_intercept']} "
                                f"feasible_eta={cand['feasible_eta_ticks']:.0f} "
                                f"feasible={cand['feasible']}",
                                flush=True,
                            )
                prompt = PLANNER_USER_TEMPLATE_GRAPH.format(
                    tick=tick,
                    graph=graph.format_for_prompt(),
                    history=graph.history.format_for_prompt(),
                    objective=self._prompt_context["objective"],
                    weapon_range=self._prompt_context["weapon_range"],
                    shore=graph.format_shore_for_prompt(),
                    roe_notes=self._prompt_context["roe_notes"],
                )
                # 会话声明的攻击时间线：仅在 --llm-briefing declared 时披露。
                # 默认 withheld：不给未来波次的时刻/方位/意图，否则等于把敌方作战
                # 计划提前交给 LLM（defender 在 tick 0 的观测接触数为 0），
                # 而规则规划器与 RL 执行层拿不到同一文本，对照不对等。
                _tl_header = ("- Scheduled attack timeline "
                              "(scenario-declared context, not an execution command):")
                if self._prompt_context.get("briefing_declared", False):
                    prompt = prompt.replace(
                        _tl_header, _tl_header + "\n" + graph.format_timeline_for_prompt())
                else:
                    prompt = prompt.replace(
                        _tl_header,
                        "- Enemy wave timing and axes: NOT DISCLOSED. Expect several "
                        "waves and possible unarmed decoys; classify every contact from "
                        "your own observations, not from prior knowledge.")
            else:
                prompt = self._build_prompt(observation, tick, reports or [], unit_roles)
            response = self.llm.chat(
                self._system_prompt, prompt,
                max_tokens=self.max_tokens, temperature=self.temperature,
            )
            plan = self._parse_plan(response)
            if plan is not None:
                commands = self._validate_commands(plan, observation, unit_roles)
            else:
                self.parse_failures += 1
        if not commands:
            # D1 修复：优先沿用上一轮已校验目标集（旧目标继续执行），
            # 只有在本局还没有任何可用目标时才回退到规则规划器。
            if self._last_plan:
                self.stale_plan_reuse += 1
                commands = list(self._last_plan)
            else:
                self.fallback_count += 1
                commands = self.fallback.plan(observation, tick, reports, unit_roles)
        else:
            self._last_plan = list(commands)
        # 记录本轮决策（分配 + 弹药）进 History，供下一轮"Previous Decision"
        if graph is not None:
            assignments = {
                str(cmd.unit_id): str(cmd.parameters["target_id"])
                for cmd in commands
                if cmd.goal_type in ("intercept", "ambush") and cmd.unit_id is not None
            }
            self.graph_builder.record_decision(tick, assignments, graph.interceptors)
        return commands

    def get_stats(self) -> dict:
        return {
            "planner": "llm",
            "plan_calls": self.plan_calls,
            "fallback_count": self.fallback_count,
            "parse_failures": self.parse_failures,
            "stale_plan_reuse": self.stale_plan_reuse,
            # 情报口径必须落盘：否则事后无法判断一局是在 --llm-briefing declared
            # （含敌方作战计划）还是 withheld（无情报）下跑的 —— 这两者的分数
            # 不可混用，而历史数据正因缺少该字段而无法复核。
            "briefing": ("declared"
                         if self._prompt_context.get("briefing_declared", False)
                         else "withheld"),
            "fallback": self.fallback.get_stats(),
        }

