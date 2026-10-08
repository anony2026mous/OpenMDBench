"""编排器：planner（上层）+ GOAIBroker + GOAIExecutorV2（下层）绑定到一个 V2 Session。

与 grid 侧 RuleAgent.act / HybridAgent.act 的流程一致：
1. 每 plan_interval 个 tick 重规划一次（LLM/规则 planner → broker.submit_goals）；
2. 每个 tick executor.act(session, tick) 把活动目标翻译成 V2 动作批并提交；
3. 调用方随后 session.step() 推进仿真。
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from goai_protocol import GOAIBroker
from v2_executor import ExecutorConfigV2, GOAIExecutorV2


FIXED_DYNAMICS_MODEL = "models.native-fixed@2.0.0"


class AgentV2:
    """一个阵营的完整 GOAI 智能体（planner + broker + executor）。"""

    def __init__(self,
                 *,
                 planner,
                 executor_config: ExecutorConfigV2,
                 faction_id: str,
                 plan_interval: int = 10,
                 name: str = "agent",
                 goal_granularity: Optional[str] = None,
                 executor_factory=None):
        self.goal_granularity = goal_granularity
        self.planner = planner
        self.broker = GOAIBroker()
        # ``executor_factory`` lets the fifth arm (LLM plan + RL executor) swap in a
        # learned executor while keeping this orchestrator, the planner and the
        # broker identical -- which is the whole point of that ablation.  A factory
        # rather than an instance because the executor needs THIS broker, which only
        # exists once the agent is being constructed.  The default stays the rule
        # executor so the other three arms are untouched.
        self.executor = (executor_factory(self.broker)
                         if executor_factory is not None
                         else GOAIExecutorV2(self.broker, executor_config))
        self.faction_id = faction_id
        self.plan_interval = max(1, int(plan_interval))
        self.name = name
        self._last_plan_tick = -(10 ** 9)
        self._unit_roles: Dict[str, frozenset] = {}
        self._meta: Dict[str, Any] = {}
        self.stats: Dict[str, Any] = {
            "name": name,
            "faction_id": faction_id,
            "plan_cycles": 0,
            "submitted_batches": 0,
            "fires": 0,
        }

    def _refresh_unit_roles(self, session) -> None:
        entities = [
            entity for entity in session.world_view.entities_stable()
            if entity.faction_id == self.faction_id and self._is_mobile(entity)
        ]
        self._unit_roles = {entity.id: frozenset(entity.tags) for entity in entities}
        self._meta = {entity.id: entity for entity in entities}

    @staticmethod
    def _is_mobile(entity) -> bool:
        """固定设施（dynamics = native-fixed）不可机动，必须排除在受控单位之外。

        给它们下发 navigation 命令会被引擎以 capability_missing 拒绝并中断整局。
        """
        definition = getattr(entity, "definition", None)
        bindings = getattr(definition, "resource_bindings", None) or {}
        dynamics = bindings.get("dynamics", ())
        if not dynamics:
            return False
        return any(getattr(binding, "model_ref", "") != FIXED_DYNAMICS_MODEL
                   for binding in dynamics)

    def _dry_unit_ids(self) -> frozenset:
        """弹药见底的己方单位（所有弹药项均为 0）。

        D2 修复：执行层已实现"0 弹自动脱离"，但规划层仍会把进攻型目标派给
        弹尽单位 → 目标抖动、往返兜圈。弹尽是**确定性事实**，与策略无关，
        因此在编排层对三种方法一视同仁地过滤进攻型目标。
        """
        dry = set()
        for entity_id, entity in (self._meta or {}).items():
            ammunition = dict(getattr(getattr(entity, "state", None),
                                      "ammunition", {}) or {})
            if ammunition and all(int(value) <= 0 for value in ammunition.values()):
                dry.add(entity_id)
        return frozenset(dry)

    def _mobile_unit_ids(self) -> frozenset:
        """可机动的己方单位（排除固定设施）。

        固定设施（dynamics 模型为 native-fixed）没有机动能力，给它们下发
        navigation 命令会被引擎以 capability_missing 拒绝，导致整局中断。
        """
        mobile = set()
        for entity_id, entity in (self._meta or {}).items():
            definition = getattr(entity, "definition", None)
            bindings = getattr(definition, "resource_bindings", None) or {}
            dynamics = bindings.get("dynamics", ())
            if any(getattr(binding, "model_ref", "") != FIXED_DYNAMICS_MODEL
                   for binding in dynamics):
                mobile.add(entity_id)
        return frozenset(mobile)

    def plan_once(self, session, tick: int):
        """The planning half of ``__call__``, without stepping the executor.

        Split out so the fifth arm's *training* can be driven by the identical goal
        stream the hybrid arm produces at evaluation time: same planner object, same
        prompt context, same broker, same cadence, same dry-unit filter.  Duplicating
        this block in the trainer instead would let the two drift, and the ablation
        would then compare goal streams rather than executors.

        The cadence check comes FIRST.  It used to sit after the observation was
        built, so every tick paid for a full ``ObservationV2`` snapshot (contacts,
        sensors, own entities) and threw it away on all but one tick in ten.  The
        fifth arm's training drives this every tick, which turned a pre-existing
        inefficiency into a 10x slowdown of the whole run.  Reordering is
        behaviour-preserving: the observation is only read inside the planning block
        below.
        """
        if not (tick == 0 or (tick - self._last_plan_tick) >= self.plan_interval):
            return None
        observation = session.world_view.observation(
            observer_faction_id=self.faction_id
        )
        self._refresh_unit_roles(session)
        mobile = self._mobile_unit_ids()
        if mobile:
            observation = observation.model_copy(update={
                "own_entities": tuple(
                    item for item in observation.own_entities
                    if str(item["entity_id"]) in mobile
                ),
            })
        if getattr(self.planner, "wants_meta", False):
            goals = self.planner.plan(
                observation, tick, self.broker.poll_reports(),
                self._unit_roles, meta=self._meta,
            )
        else:
            goals = self.planner.plan(
                observation, tick, self.broker.poll_reports(), self._unit_roles
            )
        if self.goal_granularity is not None:
            goals = [g.to_granularity(self.goal_granularity) for g in goals]
        dry = self._dry_unit_ids()
        if dry:
            goals = [g for g in goals
                     if g.unit_id not in dry
                     or g.goal_type not in ("intercept", "ambush", "reserve")]
            self.stats["dry_unit_goals_filtered"] = (
                self.stats.get("dry_unit_goals_filtered", 0))
        submit_result = self.broker.submit_goals(goals, step=tick)
        self._last_plan_tick = tick
        self.stats["plan_cycles"] += 1
        return submit_result

    def __call__(self, session) -> Dict[str, Any]:
        tick = session.world_view.tick
        submit_result = self.plan_once(session, tick)
        exec_stats = self.executor.act(session, tick)
        self.stats["submitted_batches"] = exec_stats.get("submitted", 0) \
            + self.stats.get("submitted_batches", 0)
        self.stats["fires"] += len(exec_stats.get("fires", ()))
        return {
            "tick": tick,
            "submit_result": submit_result,
            "executor": exec_stats,
        }

    def get_stats(self) -> Dict[str, Any]:
        # ``executor.get_stats()`` when the executor provides one, falling back to
        # the raw attribute dict.  The fifth arm's executor computes derived health
        # metrics -- goal adherence above all, which is the only way to detect that
        # a learned executor ignored the plan entirely -- and reading
        # ``executor.stats`` directly silently dropped them from every report.
        executor_stats = dict(self.executor.stats)
        if hasattr(self.executor, "get_stats"):
            try:
                executor_stats.update(self.executor.get_stats() or {})
            except Exception as error:  # noqa: BLE001
                executor_stats["get_stats_error"] = (
                    f"{type(error).__name__}: {error}")
        return {
            **self.stats,
            "broker": dict(self.broker.stats),
            "executor": executor_stats,
            "planner": self.planner.get_stats(),
        }
