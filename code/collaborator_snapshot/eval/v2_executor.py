"""V2 执行层：GOAI 目标命令 → V2 动作批（PersistentCommandV2 + DiscreteActionV2）。

这是 grid 侧 GOAIExecutor 的 V2 迁移版。与 grid 版的差异：
- 输出从 20×20 离散网格动作（STAY/UP/.../INTERCEPT）变为连续米制的
  PersistentCommandV2(navigation) + DiscreteActionV2(fire_weapon)；
- 位置/距离均为米制三维；到达判定用 arrive_radius_m；
- 射击条件：接触由本实体观测（observer_entity_id == 本实体）、
  距离在 [minimum_range_m, maximum_range_m]、冷却已过、弹药充足；
- fixed 标签实体（岸基固定设施）不接收任何运动命令（fixed dynamics 拒绝运动命令）；
- 无活动目标的单位提交 speed=0 的 navigation（否则会按初始速度漂移）。

不修改引擎：本模块只通过公开 DTO（ActionBatchV2 等）与 Session 交互。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from openmdbench.schemas.interface_v2 import (
    ActionBatchV2,
    DiscreteActionV2,
    PersistentCommandV2,
)

from goai_protocol import (
    GOAIBroker,
    GoalCommand,
    GoalExecutionState,
    PRIORITY_EPSILON,
    StatusReport,
    T_DECISION_MAX,
    T_STATUS_PERIOD,
)

ACTIVE_LIFECYCLES = {"active", "degraded"}


@dataclass(frozen=True)
class WeaponPolicyV2:
    """开火策略（数据来自场景 agents.yaml 的 defence.weapon_policies，只读）。"""

    selector_tags: Tuple[str, ...]
    weapon_ref: str
    minimum_range_m: float
    maximum_range_m: float
    cooldown_ticks: int


@dataclass
class ExecutorConfigV2:
    """执行层配置（我方新增文件内的默认值，可按场景覆盖）。"""

    faction_id: str
    weapon_policies: Tuple[WeaponPolicyV2, ...] = ()
    speed_by_tag: Dict[str, float] = field(default_factory=lambda: {
        "uav": 40.0,          # 空域平台（拦截无人机）
        "usv": 8.0,           # 水面平台（哨戒艇）
        "interceptor": 40.0,  # 旧标签兜底
        "picket": 8.0,        # 旧标签兜底
    })
    contact_confidence: float = 0.55
    default_speed_mps: float = 12.0
    arrive_radius_m: float = 500.0
    track_standoff_m: float = 2000.0
    return_anchor_m: Tuple[float, float, float] = (0.0, 6000.0, 800.0)
    # ---- 下层战术能力（B 线新增；规则组与 LLM 组共用，保证对比公平）----
    lead_pursuit: bool = True          # 拦截用提前交点（按目标速度外推），而非尾追
    fire_doctrine: str = "assess"      # assess=单发后评估再补射；salvo=连发；pk=等杀伤概率达标
    assess_window_ticks: int = 12      # "评估"窗口：窗口内不补射
    pk_hold_threshold: float = 0.6     # pk 模式的最低杀伤概率门槛
    retreat_when_out_of_ammo: bool = True   # 弹药耗尽自动脱离（转巡逻/返航）
    patrol_sweep: bool = True          # 到达巡逻锚点后按扇面扫掠，而不是停住
    patrol_sweep_half_deg: float = 60.0
    deconflict_fire: bool = True       # 认领去重（跨 tick 保持，见 _engaged_targets）
    # 射击前毁伤评估：同一目标最多投入几发。对空弹是 kinetic-partial 0.6，
    # 两发即摧毁；默认 2 表示打够两发就不再对它开火，避免多架接力把弹药
    # 全倾泻在一个目标上（实测 IE-02 三架各 1 发全打同一架、另一架一发未受）。
    overkill_cap: int = 2
    objective_m: Tuple[float, float] = (0.0, 0.0)   # 保护区中心（屏障/预备的距离基准）


def _heading_to(origin: Sequence[float], target: Sequence[float]) -> float:
    east = float(target[0]) - float(origin[0])
    north = float(target[1]) - float(origin[1])
    if math.hypot(east, north) <= 1e-9:
        return 0.0
    return math.degrees(math.atan2(east, north)) % 360.0


def _dist3(a: Sequence[float], b: Sequence[float]) -> float:
    """三维距离；b 的 z 缺省（LLM 常给 2 维 [x,y]）时按 a 的高度计。"""
    az = float(a[2])
    bz = float(b[2]) if b[2] is not None else az
    return math.dist(a, (float(b[0]), float(b[1]), bz))


def contact_entity_suffix(contact: Mapping[str, Any]) -> str:
    """从接触 id 提取底层实体 id（去掉 "sensor.contact.<observer>." 前缀）。"""
    cid = str(contact["contact_id"])
    prefix = f"sensor.contact.{contact.get('observer_entity_id', '')}."
    return cid[len(prefix):] if cid.startswith(prefix) else cid


FIXED_DYNAMICS_MODEL = "models.native-fixed@2.0.0"


def is_fixed_platform(entity_view) -> bool:
    """实体是否固定（不能接受任何运动命令）。

    判定依据按优先级：显式 `fixed` 标签 → 解析后的 dynamics 绑定是不是非机动的
    `models.native-fixed@2.0.0`。**不能只看标签**：MD-AD-006 的 `facility.pier`
    是 `platform.harbor-pier`（`domain: surface`、`mobile: false`），一旦漏标
    `fixed`，它会被当成水面艇收到 navigation 命令，引擎以 `capability_missing`
    拒绝并**中断整局**。dynamics 绑定是权威事实，标签只是可选声明。
    """
    if "fixed" in {str(tag) for tag in getattr(entity_view, "tags", ())}:
        return True
    bindings = (getattr(getattr(entity_view, "definition", None),
                        "resource_bindings", None) or {}).get("dynamics", ())
    refs = [str(getattr(binding, "model_ref", "") or "") for binding in bindings]
    return bool(refs) and all(ref == FIXED_DYNAMICS_MODEL for ref in refs)


def platform_kind(entity_view) -> str:
    """平台类别判定：优先用定义域（domain），再用标签，绝不依赖实体编号。

    返回 uav / usv / fixed / other。注意 AD-002 的 "interceptor" 是空域无人机、
    INT-003 的 "interceptor" 是水面无人艇——所以 domain 优先，标签兜底。
    固定判定必须最先做：`platform.harbor-pier` 的 domain 是 surface，否则会被
    误判成水面艇。
    """
    if is_fixed_platform(entity_view):
        return "fixed"
    domain = str(getattr(entity_view, "domain", "") or "")
    tags = {str(t) for t in getattr(entity_view, "tags", ())}
    if domain == "air" or "airborne" in tags or "scout" in tags:
        return "uav"
    if domain == "surface" or "raider" in tags or "picket" in tags or "usv" in tags:
        return "usv"
    if domain in {"shore", "land"}:
        return "fixed"
    if "interceptor" in tags:
        return "uav" if domain == "air" else ("usv" if domain == "surface" else "uav")
    return "other"


def ammo_ref_for(ammo_dict, weapon_ref: str) -> Optional[str]:
    """把 weapon.<name>@<ver> 映射到弹药表键 ammunition.<name>@<ver>。

    场景弹药键是 ammunition.* 命名空间，武器策略是 weapon.* 命名空间——
    直接 get(weapon_ref) 会查不到导致弹药限制失效。映射顺序：
    精确 → 前缀替换 → 唯一后缀匹配。
    """
    if weapon_ref in ammo_dict:
        return weapon_ref
    candidate = weapon_ref.replace("weapon.", "ammunition.", 1)
    if candidate in ammo_dict:
        return candidate
    suffix = weapon_ref.split(".", 1)[-1]
    matches = [key for key in ammo_dict if str(key).endswith(suffix)]
    return matches[0] if len(matches) == 1 else None


def fixed_site_weapon_policy(entity_view) -> Optional[WeaponPolicyV2]:
    """从实体武器绑定派生开火策略（数据驱动：无需场景策略声明，跨场景通用）。

    固定武装设施（如岸基 CIWS）的武器档案在
    entity.definition.resource_bindings["weapons"] 的 normalized_content 中：
    min_range_m / max_range_m / cooldown_ticks 直接取用，weapon_ref 用绑定
    exact_ref。无武器绑定的固定设施返回 None——场景没有近防炮时天然空转。
    """
    definition = getattr(entity_view, "definition", None)
    bindings = getattr(definition, "resource_bindings", None) or {}
    for binding in bindings.get("weapons", ()):
        content = dict(getattr(binding, "normalized_content", None)
                       or getattr(binding, "content", None) or {})
        try:
            min_range = float(content["min_range_m"])
            max_range = float(content["max_range_m"])
            cooldown = int(content["cooldown_ticks"])
        except (KeyError, TypeError, ValueError):
            continue
        if max_range > min_range:
            return WeaponPolicyV2(
                selector_tags=tuple(getattr(entity_view, "tags", ())),
                weapon_ref=str(binding.exact_ref),
                minimum_range_m=min_range,
                maximum_range_m=max_range,
                cooldown_ticks=max(1, cooldown),
            )
    return None


class GOAIExecutorV2:
    """V2 执行层：每个 tick 把 broker 里的活动目标翻译成 V2 动作并提交。"""

    def __init__(self, broker: GOAIBroker, config: ExecutorConfigV2):
        self.broker = broker
        self.config = config
        self.last_goal_tick = -(10 ** 9)
        self.safe_mode = False
        self.last_periodic_report = 0
        self._last_fired: Dict[Tuple[str, str], int] = {}  # (entity, weapon) -> tick
        self._shore_last_fire: Dict[Tuple[str, str], int] = {}  # 岸基自动近防冷却
        self._ammo: Dict[str, Dict[str, int]] = {}         # entity -> {weapon_ref: count}
        # 下层战术状态（B 线）：目标速度缓存 / 单发评估账本 / 本 tick 目标占用
        self._target_prev_pos: Dict[str, Tuple[int, Tuple[float, float, float]]] = {}
        self._shot_ledger: Dict[Tuple[str, str], Dict[str, int]] = {}  # (unit,target)->{count,last,assess_until}
        self._engaged_targets: Dict[str, str] = {}   # target_entity -> unit（认领，跨 tick 保持）
        self._shots_on_target: Dict[str, int] = {}   # target_entity -> 已投入弹数
        self.stats = {
            "batches_submitted": 0,
            "fires": 0,
            "goals_completed": 0,
            "goals_infeasible": 0,
            "goals_timeout": 0,
            "goals_failed": 0,
            "safe_mode_ticks": 0,
        }

    # ------------------------------------------------------------------
    # Session 侧只读视图
    # ------------------------------------------------------------------

    @staticmethod
    def _authority_by_entity(session) -> Dict[str, str]:
        return {
            grant.entity_id: token
            for token, grant in session.world_view.authority_tokens.items()
        }

    @staticmethod
    def _own_by_id(observation) -> Dict[str, Dict[str, Any]]:
        return {str(item["entity_id"]): item for item in observation.own_entities}

    @staticmethod
    def _contacts_by_id(observation) -> Dict[str, Dict[str, Any]]:
        faction = observation.observer_faction_id
        return {
            str(item["contact_id"]): item
            for item in observation.contacts_by_faction.get(faction, ())
        }

    @staticmethod
    def _entity_meta(session) -> Dict[str, Any]:
        return {
            entity.id: entity for entity in session.world_view.entities_stable()
        }

    def _weapon_target_domains(self, meta_entity, weapon_ref: str) -> tuple:
        """武器允许打击的目标域（从资源绑定读取；空=不限制）。"""
        definition = getattr(meta_entity, "definition", None)
        bindings = getattr(definition, "resource_bindings", None) or {}
        for binding in bindings.get("weapons", ()) or ():
            if getattr(binding, "exact_ref", None) != weapon_ref:
                continue
            content = getattr(binding, "normalized_content", None) or {}
            return tuple(str(item) for item in (content.get("target_domains") or ()))
        return ()

    def _weapon_domain_allows(self, meta_entity, weapon_ref: str,
                              target_suffix: str) -> bool:
        """水面武器只能打水面目标：开火前先按目标域过滤，避免被引擎拒绝。

        修复：此前执行层只查接触/射程/冷却/弹药，水面导弹会把空中目标也当目标，
        引擎以 combat.contact_denied 拒绝，白白消耗开火机会。
        """
        domains = self._weapon_target_domains(meta_entity, weapon_ref)
        if not domains:
            return True
        target = getattr(self, "_meta_all", {}).get(target_suffix)
        target_domain = getattr(getattr(target, "definition", None), "domain", None)
        if target_domain is None:
            return True
        return str(target_domain) in domains

    def _policy_for(self, tags) -> Optional[WeaponPolicyV2]:
        tagset = set(tags)
        for policy in self.config.weapon_policies:
            if set(policy.selector_tags) <= tagset:
                return policy
        return None

    def _ammo_for(self, meta, entity_id: str, weapon_ref: str) -> Optional[int]:
        """读取弹药余量：优先引擎实时状态（state.ammunition），回退定义初始值。

        注意：ResolvedEntityV2 没有 ammunition 字段（读 definition.ammunition 会得到
        None=不限，导致决策层弹药耗尽后仍持续空扣扳机）；正确来源是
        entity_view.state.ammunition（引擎每 tick 扣减后的真值）。
        """
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

    def _speed_for(self, meta_entity, tags, goal) -> float:
        requested = (goal.parameters or {}).get("speed_mps")
        if requested:
            try:
                return float(requested)
            except (TypeError, ValueError):
                pass
        kind = platform_kind(meta_entity)
        if kind in self.config.speed_by_tag:
            return self.config.speed_by_tag[kind]
        for tag, speed in self.config.speed_by_tag.items():
            if tag in tags:
                return speed
        return self.config.default_speed_mps

    # ------------------------------------------------------------------
    # 提交
    # ------------------------------------------------------------------

    def _submit(self, session, *, entity_id: str, token: str, tick: int,
                command: PersistentCommandV2,
                action: Optional[DiscreteActionV2]) -> None:
        children = () if action is None else (action,)
        suffix = f"{entity_id}.{tick}"
        session.submit_actions(
            batch=ActionBatchV2(
                schema_version="2.0",
                session_id=session.session_id,
                batch_id=f"eval.exec.batch.{suffix}",
                idempotency_key=f"eval.exec.idem.{suffix}",
                faction_id=self.config.faction_id,
                based_on_tick=tick,
                valid_until_tick=tick + 1,
                persistent_commands=(command,),
                discrete_actions=children,
            ),
            authority_token=token,
            operation_id=f"eval.exec.submit.{suffix}",
            expected_tick=tick,
        )
        self.stats["batches_submitted"] += 1

    def _navigation(self, entity_id: str, tick: int, *, own: Mapping[str, Any],
                    speed_mps: float, heading_deg: float) -> PersistentCommandV2:
        position = tuple(float(v) for v in own["position_m"])
        if heading_deg < 0.0:
            heading_deg = float(own.get("heading_deg", 0.0))
        return PersistentCommandV2(
            schema_version="2.0",
            command_id=f"eval.exec.nav.{entity_id}.{tick}",
            command_type="navigation",
            entity_id=entity_id,
            faction_id=self.config.faction_id,
            based_on_tick=tick,
            valid_until_tick=tick + 1,
            payload={
                "speed_mps": float(speed_mps),
                "heading_deg": float(heading_deg) % 360.0,
                "altitude_m": position[2],
            },
        )

    def _fire_action(self, entity_id: str, tick: int, *, policy: WeaponPolicyV2,
                     contact_id: str) -> DiscreteActionV2:
        return DiscreteActionV2(
            schema_version="2.0",
            action_id=f"eval.exec.fire.{entity_id}.{tick}",
            action_type="fire_weapon",
            entity_id=entity_id,
            faction_id=self.config.faction_id,
            based_on_tick=tick,
            valid_until_tick=tick,
            payload={"weapon_ref": policy.weapon_ref, "contact_id": contact_id},
        )

    # ------------------------------------------------------------------
    # 岸基固定设施自动近防（CIWS，动态适配：无近防场景空转）
    # ------------------------------------------------------------------

    def _submit_shore_fire(self, session, *, entity_id: str, token: str,
                           tick: int, action: DiscreteActionV2) -> None:
        """固定设施只提交开火离散动作，不带运动命令（fixed dynamics 拒绝运动）。"""
        suffix = f"{entity_id}.{tick}"
        session.submit_actions(
            batch=ActionBatchV2(
                schema_version="2.0",
                session_id=session.session_id,
                batch_id=f"eval.shore.batch.{suffix}",
                idempotency_key=f"eval.shore.idem.{suffix}",
                faction_id=self.config.faction_id,
                based_on_tick=tick,
                valid_until_tick=tick,
                persistent_commands=(),
                discrete_actions=(action,),
            ),
            authority_token=token,
            operation_id=f"eval.shore.submit.{suffix}",
            expected_tick=tick,
        )
        self.stats["batches_submitted"] += 1

    def _shore_defence(self, session, tick: int, own, contacts, tokens,
                       meta) -> list:
        """固定武装设施的自动近防：对进入 [min,max] 射程的自持接触开火。

        判定全部数据驱动（实体武器绑定 + 实时弹药 + 授权 token），
        场景没有岸基近防设施时本方法天然不产生任何提交。
        目标需为本设施自己观测的接触（引擎开火合法性 CONTACT_NOT_OWNED 同样要求）。
        """
        fires: list = []
        for uid, entity_state in own.items():
            tags = tuple(getattr(meta.get(uid), "tags", ()))
            if "fixed" not in tags:
                continue
            token = tokens.get(uid)
            if token is None:
                continue  # 无授权（场景未声明控制槽位）→ 跳过
            policy = fixed_site_weapon_policy(meta.get(uid))
            if policy is None:
                continue
            last = self._shore_last_fire.get((uid, policy.weapon_ref), -(10 ** 9))
            if tick - last < policy.cooldown_ticks:
                continue
            ammo = self._ammo_for(meta, uid, policy.weapon_ref)
            if ammo is not None and ammo <= 0:
                continue
            position = tuple(float(v) for v in entity_state["position_m"])
            best: Optional[Tuple[float, str]] = None
            for contact in contacts.values():
                if str(contact.get("observer_entity_id")) != uid:
                    continue
                if int(contact.get("age_ticks", 0)) > 8:
                    continue  # 新鲜度门槛：避免对陈旧位置扣扳机
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
                action_id=f"eval.shore.fire.{uid}.{tick}",
                action_type="fire_weapon",
                entity_id=uid,
                faction_id=self.config.faction_id,
                based_on_tick=tick,
                valid_until_tick=tick,
                payload={"weapon_ref": policy.weapon_ref,
                         "contact_id": best[1]},
            )
            self._shore_last_fire[(uid, policy.weapon_ref)] = tick
            self._submit_shore_fire(session, entity_id=uid, token=token,
                                    tick=tick, action=action)
            fires.append({
                "tick": tick,
                "entity_id": uid,
                "contact_id": best[1],
                "weapon_ref": policy.weapon_ref,
                "action_id": str(action.action_id),
            })
        return fires

    # ------------------------------------------------------------------
    # 每 tick 执行
    # ------------------------------------------------------------------

    def act(self, session, tick: int) -> Dict[str, Any]:
        """把当前活动目标翻译成 V2 动作并提交；返回本轮统计。

        调用方（AgentV2）在调用本方法后再 session.step()。
        """
        observation = session.world_view.observation(
            observer_faction_id=self.config.faction_id
        )
        own = self._own_by_id(observation)
        contacts = self._contacts_by_id(observation)
        tokens = self._authority_by_entity(session)
        meta = self._entity_meta(session)
        self._meta_all = meta
        fired: list = []

        # ---- 安全模式进入/退出（I.5）----
        has_fresh = any(not s.terminal and s.status == "pending"
                        for s in self.broker.active.values())
        if has_fresh:
            self.last_goal_tick = tick
            self.safe_mode = False
        elif not self.safe_mode and (tick - self.last_goal_tick) >= T_DECISION_MAX:
            self.safe_mode = True
            self.broker.post_report(StatusReport(
                task_id="safe_mode", unit_id=None, status="executing",
                progress=0.0, anomaly="comm_loss", reported_at=tick,
                anomaly_detail=f"no new goal for {tick - self.last_goal_tick} ticks"))

        if self.safe_mode:
            self.stats["safe_mode_ticks"] += 1

        # ---- 激活/可行性筛查 pending 目标 ----
        for state in list(self.broker.active.values()):
            if state.terminal or state.status != "pending":
                continue
            uid = state.command.unit_id
            entity_state = own.get(uid) if uid else None
            if entity_state is None or entity_state.get("lifecycle_state") not in ACTIVE_LIFECYCLES:
                self._post(state, "failed", tick, anomaly="platform_damaged",
                           detail=f"unit {uid} destroyed/disabled")
                continue
            infeas = self._check_feasibility(state.command, contacts)
            if infeas is not None:
                anomaly, detail = infeas
                self._post(state, "infeasible", tick, anomaly=anomaly, detail=detail)
                continue
            state.status = "executing"
            state.start_tick = tick
            target = self._goal_position(state.command, own, contacts)
            if target is not None:
                position = tuple(float(v) for v in entity_state["position_m"])
                state.initial_dist = _dist3(position, target)

        # ---- 每单位选最高优先级目标 ----
        unit_goal: Dict[str, GoalExecutionState] = {}
        for state in self.broker.active.values():
            if state.terminal:
                continue
            uid = state.command.unit_id
            if uid is None or uid not in own:
                continue
            cur = unit_goal.get(uid)
            if cur is None or state.command.priority > cur.command.priority + PRIORITY_EPSILON:
                unit_goal[uid] = state

        # ---- 认领去重（跨 tick 保持）＋ 射击前毁伤评估 ----
        # 此前这里每 tick 清空 `_engaged_targets`，去重只在"同一 tick"内生效。
        # 逐发日志证实后果：三架拦截机在 tick 146/149/151 各打 1 发，全部落在同一个
        # 来袭者身上（3 发），而另一架来袭者一发未受 —— 因为每个 tick 认领都被抹掉。
        # 现在只在目标从接触列表消失（被击毁/丢失）时释放认领；同时按"击毁所需弹数"
        # 限制对同一目标的投入，避免把弹药全倾泻在一个已经挨够弹的目标上。
        live_suffixes = {contact_entity_suffix(item)
                         for item in (contacts or {}).values()}
        self._engaged_targets = {
            key: value for key, value in self._engaged_targets.items()
            if key in live_suffixes
        }
        self._shots_on_target = {
            key: value for key, value in self._shots_on_target.items()
            if key in live_suffixes
        }
        for uid, state in unit_goal.items():
            entity_state = own[uid]
            token = tokens.get(uid)
            tags = self._tags_of(meta.get(uid))
            kind = platform_kind(meta.get(uid))
            if token is None or "fixed" in tags or kind == "fixed":
                continue  # 非我方授权实体 / 固定设施不接收运动命令
            if entity_state.get("lifecycle_state") not in ACTIVE_LIFECYCLES:
                continue
            policy = self._policy_for(tags)
            if policy is not None:
                self._ammo_for(meta, uid, policy.weapon_ref)  # 预载弹药账本
            command, action = self._execute_goal(
                session, uid, entity_state, tags, state, tick, contacts,
                meta.get(uid),
            )
            if action is not None:
                fired.append({
                    "tick": tick,
                    "entity_id": uid,
                    "contact_id": str(action.payload.get("contact_id")),
                    "weapon_ref": str(action.payload.get("weapon_ref")),
                    "action_id": str(action.action_id),
                })
            self._submit(session, entity_id=uid, token=token, tick=tick,
                         command=command, action=action)

        # ---- 无目标的活动单位：显式停下（speed=0，防止按初始速度漂移）----
        for uid, entity_state in own.items():
            if uid in unit_goal:
                continue
            token = tokens.get(uid)
            tags = self._tags_of(meta.get(uid))
            kind = platform_kind(meta.get(uid))
            if token is None or "fixed" in tags or kind == "fixed":
                continue
            if entity_state.get("lifecycle_state") not in ACTIVE_LIFECYCLES:
                continue
            heading = float(entity_state.get("heading_deg", 0.0))
            self._submit(
                session, entity_id=uid, token=token, tick=tick,
                command=self._navigation(uid, tick, own=entity_state,
                                         speed_mps=0.0, heading_deg=heading),
                action=None,
            )

        # ---- 周期上报 + 清理 ----
        if tick - self.last_periodic_report >= T_STATUS_PERIOD:
            self.last_periodic_report = tick
            for state in self.broker.active.values():
                if state.status == "executing" and not state.terminal:
                    self.broker.reports.append(StatusReport(
                        task_id=state.command.task_id,
                        unit_id=state.command.unit_id,
                        status="executing",
                        progress=state.last_progress,
                        reported_at=tick,
                    ))
        self.broker.prune_terminal()

        # ---- 岸基固定设施自动近防（CIWS）----
        # 规则组与混合组共用本执行层 → 自动获得近防；无近防场景天然空转。
        shore_fires = self._shore_defence(session, tick, own, contacts, tokens, meta)
        fired.extend(shore_fires)

        self.stats["fires"] += len(fired)
        return {"submitted": len(unit_goal), "fires": fired,
                "safe_mode": self.safe_mode}

    # ------------------------------------------------------------------
    # 可行性 / 目标位置 / 单目标执行
    # ------------------------------------------------------------------

    @staticmethod
    def _tags_of(entity_view) -> Tuple[str, ...]:
        tags = getattr(entity_view, "tags", None)
        if tags is None:
            return ()
        return tuple(tags)

    def _check_feasibility(self, cmd, contacts: Mapping[str, Mapping[str, Any]]):
        tid = (cmd.parameters or {}).get("target_id")
        if tid is not None and str(tid) not in contacts:
            return "target_lost", f"target {tid} not in current contacts"
        return None

    def _goal_position(self, cmd, own, contacts):
        params = cmd.parameters or {}
        if cmd.goal_type == "return":
            return self.config.return_anchor_m
        pos = params.get("position")
        if pos is not None:
            try:
                if len(pos) >= 3:
                    return tuple(float(pos[0]), float(pos[1]), float(pos[2]))
                return (float(pos[0]), float(pos[1]), None)
            except (TypeError, ValueError):
                return None
        tid = params.get("target_id")
        contact = contacts.get(str(tid)) if tid is not None else None
        if contact is not None:
            estimate = contact["estimated_position_m"]
            return tuple(float(v) for v in estimate)
        return None

    def _contact_owned_by(self, contacts, contact_id: str, entity_id: str) -> bool:
        contact = contacts.get(contact_id)
        return bool(contact and contact.get("observer_entity_id") == entity_id)

    @staticmethod
    def _contact_entity_suffix(contact: Mapping[str, Any]) -> str:
        return contact_entity_suffix(contact)

    def _own_contact_for_entity(self, contacts, entity_id: str,
                                target_contact: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
        """找本机对同一底层实体的自有接触（用于开火载荷，满足引擎契约）。

        规划层（尤其 LLM）常把别人观测的航迹分给拦截机；执行层允许"借别人的航迹
        追击、用自己的火控接触开火"（对应 grid 的 standoff 锁定语义）。找不到自有
        接触时返回 None → 继续追击不开火。
        """
        target_suffix = self._contact_entity_suffix(target_contact)
        for contact in contacts.values():
            if (contact.get("observer_entity_id") == entity_id
                    and self._contact_entity_suffix(contact) == target_suffix):
                return contact
        return None

    def _post(self, state: GoalExecutionState, status: str, tick: int,
              progress: float = 0.0, anomaly: str = "none", detail: str = ""):
        self.broker.post_report(StatusReport(
            task_id=state.command.task_id,
            unit_id=state.command.unit_id,
            status=status,
            progress=max(0.0, min(1.0, progress)),
            anomaly=anomaly,
            anomaly_detail=detail,
            reported_at=tick,
        ))
        if status == "completed":
            self.stats["goals_completed"] += 1
        elif status == "infeasible":
            self.stats["goals_infeasible"] += 1
        elif status == "timeout":
            self.stats["goals_timeout"] += 1
        elif status == "failed":
            self.stats["goals_failed"] += 1

    # ------------------------------------------------------------------
    # 下层战术辅助（B 线新增；规则组与 LLM 组共用）
    # ------------------------------------------------------------------

    def _target_velocity(self, entity_suffix: str, position, tick: int):
        """用相邻两次观测差分估计目标速度（m/tick）；无历史返回 None。"""
        prev = self._target_prev_pos.get(entity_suffix)
        current = tuple(float(v) for v in position)
        self._target_prev_pos[entity_suffix] = (int(tick), current)
        if prev is None:
            return None
        prev_tick, prev_pos = prev
        delta = max(1, int(tick) - int(prev_tick))
        if delta > 60:
            return None
        return tuple((current[i] - prev_pos[i]) / delta for i in range(3))

    def _lead_point(self, own_pos, target_pos, velocity, own_speed: float):
        """提前交点：pos + v·t，两次迭代。velocity 为 None（无历史）时退化为当前位置。"""
        if velocity is None:
            return tuple(float(v) for v in target_pos)
        lead = [float(v) for v in target_pos]
        for _ in range(2):
            distance = math.dist(own_pos, lead)
            t_go = distance / max(own_speed, 1e-6)
            lead = [float(target_pos[i]) + velocity[i] * t_go for i in range(3)]
        return tuple(lead)

    def _pk_estimate(self, meta_entity, policy: WeaponPolicyV2,
                     distance: float) -> float:
        """命中概率代理：档案 hit_probability × 距离衰减（与引擎同式）。"""
        hit_prob = 0.8
        definition = getattr(meta_entity, "definition", None)
        for binding in (getattr(definition, "resource_bindings", None) or {}).get(
                "weapons", ()):
            content = dict(getattr(binding, "normalized_content", None)
                           or getattr(binding, "content", None) or {})
            try:
                hit_prob = float(content.get("hit_probability", hit_prob))
            except (TypeError, ValueError):
                pass
            break
        decay = max(0.5, 1.0 - 0.5 * distance / max(policy.maximum_range_m, 1e-6))
        return hit_prob * decay

    def _doctrine_allows(self, *, unit_id: str, target_entity: str, tick: int,
                         policy: WeaponPolicyV2, meta_entity, distance: float,
                         fire_policy: str) -> bool:
        """开火教义：assess=单发后评估窗口内不补射；salvo=最多连发 2；pk=等杀伤概率达标。"""
        ledger = self._shot_ledger.setdefault(
            (unit_id, target_entity), {"count": 0, "last": -(10 ** 9),
                                       "assess_until": -(10 ** 9)})
        mode = (fire_policy or self.config.fire_doctrine or "assess").lower()
        if mode == "pk" and self._pk_estimate(meta_entity, policy, distance) < \
                self.config.pk_hold_threshold:
            return False
        if mode == "salvo":
            return ledger["count"] < 2
        # assess（默认）：单发后进入评估窗口，窗口内不补射
        return not (ledger["count"] >= 1 and tick < ledger["assess_until"])

    def _record_shot(self, unit_id: str, target_entity: str, tick: int,
                     policy: WeaponPolicyV2) -> None:
        ledger = self._shot_ledger.setdefault(
            (unit_id, target_entity), {"count": 0, "last": -(10 ** 9),
                                       "assess_until": -(10 ** 9)})
        ledger["count"] += 1
        ledger["last"] = tick
        ledger["assess_until"] = tick + max(policy.cooldown_ticks,
                                            self.config.assess_window_ticks)

    def _distance_to_objective(self, position) -> float:
        ox, oy = self.config.objective_m
        return math.hypot(float(position[0]) - float(ox),
                          float(position[1]) - float(oy))

    def _execute_goal(self, session, entity_id: str, entity_state: Mapping[str, Any],
                      tags: Tuple[str, ...], state: GoalExecutionState, tick: int,
                      contacts: Mapping[str, Mapping[str, Any]], meta_entity=None):
        """返回 (PersistentCommandV2, DiscreteActionV2 | None)。"""
        cmd = state.command
        params = cmd.parameters or {}
        own_pos = tuple(float(v) for v in entity_state["position_m"])
        heading = float(entity_state.get("heading_deg", 0.0))
        speed = self._speed_for(meta_entity, tags, cmd)
        action: Optional[DiscreteActionV2] = None

        if cmd.deadline is not None and (tick - cmd.issued_at) > cmd.deadline:
            self._post(state, "timeout", tick, progress=state.last_progress,
                       detail=f"deadline {cmd.deadline} exceeded")
            return (self._navigation(entity_id, tick, own=entity_state,
                                     speed_mps=0.0, heading_deg=heading), None)

        if cmd.goal_type in ("intercept", "ambush"):
            tid = params.get("target_id")
            contact = contacts.get(str(tid))
            if contact is None:
                self._post(state, "completed", tick, progress=1.0,
                           anomaly="target_lost", detail=f"target {tid} gone")
                return (self._navigation(entity_id, tick, own=entity_state,
                                         speed_mps=0.0, heading_deg=heading), None)
            target = tuple(float(v) for v in contact["estimated_position_m"])
            entity_suffix = contact_entity_suffix(contact)
            policy = self._policy_for(tags)
            if policy is not None and self.config.retreat_when_out_of_ammo:
                # 弹药耗尽 → 脱离（修复"0 弹仍伴飞"）
                ammo_dict = self._ammo.get(entity_id, {})
                resolved_now = ammo_ref_for(ammo_dict, policy.weapon_ref)
                if resolved_now is not None and ammo_dict.get(resolved_now, 1) <= 0:
                    self._post(state, "completed", tick, progress=1.0,
                               detail="out of ammunition - disengage")
                    anchor = self.config.return_anchor_m
                    return (self._navigation(entity_id, tick, own=entity_state,
                                             speed_mps=speed,
                                             heading_deg=_heading_to(own_pos, anchor)),
                            None)
            # 提前交点（修复尾追）：按目标速度外推，伏击模式到占位后悬停
            velocity = self._target_velocity(entity_suffix, target, tick)
            aim = (self._lead_point(own_pos, target, velocity, speed)
                   if self.config.lead_pursuit else target)
            distance = _dist3(own_pos, target)
            action: Optional[DiscreteActionV2] = None
            if policy is not None:
                # 开火资格：本机对同一底层实体持有自有接触（借别人航迹追、用自己
                # 火控接触打——对应 grid 的 standoff 锁定语义）
                # 引擎要求 contact_owner_id == attacker_id：阵营共享池里的接触可能
                # 是别人观测的，必须先按 observer_entity_id 过滤出"本单位自持接触"，
                # 否则会被 combat.contact_denied 拒绝（水面目标几乎总是先被别人看到）
                self_owned = {
                    key: value for key, value in (contacts or {}).items()
                    if str((value or {}).get("observer_entity_id") or "") == entity_id
                }
                own_contact = self._own_contact_for_entity(self_owned, entity_id, contact)
                # 与引擎 contact 阶段对齐：接触年龄不得超过传感器允许的最大年龄，
                # 否则引擎会以 combat.contact_denied 拒绝（水面雷达刷新慢、最易触发）
                if own_contact is not None:
                    age = float(own_contact.get("age_ticks", 0) or 0.0)
                    age_cap = float(getattr(self.config, "contact_max_age_ticks", 8))
                    if age > age_cap:
                        own_contact = None
                last = self._last_fired.get((entity_id, policy.weapon_ref), -(10 ** 9))
                # 弹药键映射：弹药表是 ammunition.* 命名空间，武器策略是 weapon.*
                ammo_dict = self._ammo.get(entity_id, {})
                resolved_ref = ammo_ref_for(ammo_dict, policy.weapon_ref)
                ammo = ammo_dict.get(resolved_ref) if resolved_ref else None
                # 本地门槛不应高于引擎门槛（引擎用传感器声明的 minimum_contact_confidence），
                # 取较低值，避免"本地合格、引擎拒绝"的错配
                min_conf = min(0.30, float(getattr(self.config, "contact_confidence", 0.55)))
                contact_conf = float(own_contact.get("confidence", 0.0)) if own_contact else 0.0
                occupied = (self.config.deconflict_fire
                            and self._engaged_targets.get(entity_suffix)
                            not in (None, entity_id))
                if (own_contact is not None
                        and self._weapon_domain_allows(
                            meta_entity, policy.weapon_ref, entity_suffix)
                        and contact_conf >= min_conf
                        and policy.minimum_range_m <= distance <= policy.maximum_range_m
                        and tick - last >= policy.cooldown_ticks
                        and (ammo is None or ammo > 0)
                        and not occupied
                        # 射击前毁伤评估：同一目标已挨够"击毁所需弹数"就不再投入
                        and self._shots_on_target.get(entity_suffix, 0)
                        < self.config.overkill_cap
                        and self._doctrine_allows(
                            unit_id=entity_id, target_entity=entity_suffix, tick=tick,
                            policy=policy, meta_entity=meta_entity, distance=distance,
                            fire_policy=str(params.get("fire_policy", "")))):
                    self._last_fired[(entity_id, policy.weapon_ref)] = tick
                    self._record_shot(entity_id, entity_suffix, tick, policy)
                    self._engaged_targets[entity_suffix] = entity_id
                    self._shots_on_target[entity_suffix] = (
                        self._shots_on_target.get(entity_suffix, 0) + 1)
                    if ammo is not None and resolved_ref is not None:
                        self._ammo[entity_id][resolved_ref] = ammo - 1
                    action = self._fire_action(
                        entity_id, tick, policy=policy,
                        contact_id=str(own_contact["contact_id"]),
                    )
            if cmd.goal_type == "ambush":
                standoff = float(params.get(
                    "standoff_m",
                    0.9 * policy.maximum_range_m if policy is not None else 6000.0))
                if action is None and _dist3(own_pos, aim) <= standoff:
                    return (self._navigation(entity_id, tick, own=entity_state,
                                             speed_mps=0.0, heading_deg=heading), None)
            if action is not None:
                # 开火当拍保持航向逼近（维持目标进入杀伤区）
                return (self._navigation(entity_id, tick, own=entity_state,
                                         speed_mps=speed,
                                         heading_deg=_heading_to(own_pos, aim)),
                        action)
            return (self._navigation(entity_id, tick, own=entity_state,
                                     speed_mps=speed,
                                     heading_deg=_heading_to(own_pos, aim)), None)

        if cmd.goal_type == "track":
            tid = params.get("target_id")
            contact = contacts.get(str(tid))
            if contact is None:
                self._post(state, "completed", tick, progress=1.0,
                           anomaly="target_lost", detail=f"target {tid} gone")
                return (self._navigation(entity_id, tick, own=entity_state,
                                         speed_mps=0.0, heading_deg=heading), None)
            target = tuple(float(v) for v in contact["estimated_position_m"])
            distance = _dist3(own_pos, target)
            if distance <= self.config.track_standoff_m:
                return (self._navigation(entity_id, tick, own=entity_state,
                                         speed_mps=0.0, heading_deg=heading), None)
            return (self._navigation(entity_id, tick, own=entity_state,
                                     speed_mps=speed,
                                     heading_deg=_heading_to(own_pos, target)), None)

        if cmd.goal_type == "hold":
            if state.hold_until is None:
                dur = float(params.get("duration", 30))
                state.hold_until = tick + max(1, int(dur))
            if tick >= state.hold_until:
                self._post(state, "completed", tick, progress=1.0)
            return (self._navigation(entity_id, tick, own=entity_state,
                                     speed_mps=0.0, heading_deg=heading), None)

        if cmd.goal_type in ("waypoint", "patrol", "loiter", "return"):
            target = self._goal_position(cmd, None, contacts)
            if target is None:
                self._post(state, "infeasible", tick, anomaly="constraint_violation",
                           detail="missing position")
                return (self._navigation(entity_id, tick, own=entity_state,
                                         speed_mps=0.0, heading_deg=heading), None)
            tx, ty = float(target[0]), float(target[1])
            if len(target) >= 3 and target[2] is not None:
                tz = float(target[2])
            else:
                tz = own_pos[2]
            tgt3 = (tx, ty, tz)
            distance = _dist3(own_pos, tgt3)
            if cmd.goal_type == "waypoint" and distance <= self.config.arrive_radius_m:
                self._post(state, "completed", tick, progress=1.0)
                return (self._navigation(entity_id, tick, own=entity_state,
                                         speed_mps=0.0, heading_deg=heading), None)
            if cmd.goal_type == "return" and distance <= self.config.arrive_radius_m:
                self._post(state, "completed", tick, progress=1.0,
                           detail="at return anchor")
                return (self._navigation(entity_id, tick, own=entity_state,
                                         speed_mps=0.0, heading_deg=heading), None)
            if cmd.goal_type in ("patrol", "loiter") and distance <= self.config.arrive_radius_m:
                if not self.config.patrol_sweep:
                    # v1：到达锚点后原地待命
                    return (self._navigation(entity_id, tick, own=entity_state,
                                             speed_mps=0.0, heading_deg=heading), None)
                # 扫掠：以锚点—保护区连线为基准，左右交替沿切线巡逻（形成警戒幕）
                inward = _heading_to(tgt3, (self.config.objective_m[0],
                                            self.config.objective_m[1], tz))
                tangent = (inward + (self.config.patrol_sweep_half_deg
                                     if (tick // 60) % 2 == 0
                                     else -self.config.patrol_sweep_half_deg)) % 360.0
                return (self._navigation(entity_id, tick, own=entity_state,
                                         speed_mps=speed, heading_deg=tangent), None)
            return (self._navigation(entity_id, tick, own=entity_state,
                                     speed_mps=speed,
                                     heading_deg=_heading_to(own_pos, tgt3)), None)

        if cmd.goal_type == "barrier":
            # 屏障：保护区外侧按威胁方位布防；到位后沿扇面扫掠
            axis = float(params.get("axis_deg", 270.0))
            radius = float(params.get("radius_m", 12000.0))
            ox, oy = self.config.objective_m
            station = (ox + radius * math.sin(math.radians(axis)),
                       oy + radius * math.cos(math.radians(axis)),
                       own_pos[2])
            if _dist3(own_pos, station) <= self.config.arrive_radius_m:
                tangent = (axis + (90.0 if (tick // 60) % 2 == 0 else -90.0)) % 360.0
                return (self._navigation(entity_id, tick, own=entity_state,
                                         speed_mps=speed, heading_deg=tangent), None)
            return (self._navigation(entity_id, tick, own=entity_state,
                                     speed_mps=speed,
                                     heading_deg=_heading_to(own_pos, station)), None)

        if cmd.goal_type == "reserve":
            # 预备：驻留后方锚点；威胁进入 commit_within_m 时自动前出接战
            anchor = self._goal_position(cmd, None, contacts) or self.config.return_anchor_m
            commit = float(params.get("commit_within_m", 9000.0))
            threats = [
                contact for contact in contacts.values()
                if self._distance_to_objective(contact["estimated_position_m"]) <= commit
            ]
            threats.sort(key=lambda contact: self._distance_to_objective(
                contact["estimated_position_m"]))
            if threats:
                proxy = GoalCommand(
                    task_id=cmd.task_id, goal_type="intercept",
                    parameters={"unit_id": entity_id,
                                "target_id": str(threats[0]["contact_id"]),
                                "fire_policy": params.get("fire_policy", "")},
                    priority=cmd.priority, issued_at=cmd.issued_at)
                saved = state.command
                state.command = proxy
                try:
                    return self._execute_goal(session, entity_id, entity_state, tags,
                                              state, tick, contacts, meta_entity)
                finally:
                    state.command = saved
            if _dist3(own_pos, anchor) <= self.config.arrive_radius_m:
                return (self._navigation(entity_id, tick, own=entity_state,
                                         speed_mps=0.0, heading_deg=heading), None)
            return (self._navigation(entity_id, tick, own=entity_state,
                                     speed_mps=speed,
                                     heading_deg=_heading_to(own_pos, anchor)), None)

        if cmd.goal_type == "disengage":
            anchor = self._goal_position(cmd, None, contacts) or self.config.return_anchor_m
            if _dist3(own_pos, anchor) <= self.config.arrive_radius_m:
                self._post(state, "completed", tick, progress=1.0, detail="disengaged")
                return (self._navigation(entity_id, tick, own=entity_state,
                                         speed_mps=0.0, heading_deg=heading), None)
            return (self._navigation(entity_id, tick, own=entity_state,
                                     speed_mps=speed,
                                     heading_deg=_heading_to(own_pos, anchor)), None)

        self._post(state, "infeasible", tick, anomaly="constraint_violation",
                   detail=f"unsupported goal_type {cmd.goal_type}")
        return (self._navigation(entity_id, tick, own=entity_state,
                                 speed_mps=0.0, heading_deg=heading), None)




