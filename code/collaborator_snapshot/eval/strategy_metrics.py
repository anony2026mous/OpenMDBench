"""Multi-dimensional strategy metrics for the island-strike class of scenarios.

The scorecard is deliberately computed from **authoritative engine evidence**
(per-tick lifecycle transitions, executed fire receipts, terminal receipts), not
from harness-side intentions, so a method cannot score well by merely issuing
commands.

Layers (each normalised to ``[0, 1]``; 1.0 = best for the side being scored):

  terminal   终局是否正确落定，以及胜负方向
  facilities 设施加权存活（health × 权重，按设施归一）
  depth      拦截纵深：来袭无人机被击落处到其目标设施的距离（越远越好）
  leak       漏防：抵达设施打击半径内的来袭无人机比例（越少越好）
  exchange   兵力交换比（本方损失 vs 对方损失）
  ammo       弹药效率（击毁数 / 发射数）
  surface    水面层：来袭无人船在其目标被摧毁前被拦下的比例

``overall`` is a fixed, documented weighted sum of the layers.  Every layer is
also reported raw so a reader can re-weight or drop layers without rerunning.

The module is scenario-agnostic: unit roles are derived from the resolved
platform domain plus the scenario's own tags (``target.<id>`` for the assigned
objective, ``facility`` for scoreable structures).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Sequence

# Roles a unit can take in this scenario class.
ROLE_UAV = "uav"
ROLE_USV = "usv"
ROLE_FACILITY = "facility"
# 中立民用目标（第三个阵营）。必须与 usv 区分开：民用船没有武器、不参与交战，
# 若被计入某一方的 usv 战损，会同时污染"无人船战损"分项与拦截纵深的分母。
ROLE_CIVILIAN = "civilian"
ROLE_OTHER = "other"

# 判定中立民用单位的场景标签（与场景自身声明的 civilian 标签一致）。
CIVILIAN_TAGS = frozenset({"civilian", "neutral-civilian"})

# Lifecycle states that mean the unit is out of the fight.
LOST_STATES = frozenset({"disabled", "destroyed", "wreck", "despawned"})
DEAD_STATES = frozenset({"destroyed", "wreck", "despawned"})

TARGET_TAG_PREFIX = "target."


@dataclass(frozen=True)
class LayerWeights:
    """Weights of the defender-side overall score.  Fixed a priori on purpose.

    The weights encode the scenario's own mission logic: holding the facilities
    and interdicting the raiders far from them matter more than the exchange
    ratio, which is why ``facilities`` and ``depth`` carry the largest weight.
    """

    terminal: float = 0.20
    facilities: float = 0.25
    depth: float = 0.20
    leak: float = 0.10
    exchange: float = 0.10
    ammo: float = 0.05
    surface: float = 0.10

    def total(self) -> float:
        return (self.terminal + self.facilities + self.depth + self.leak
                + self.exchange + self.ammo + self.surface)


@dataclass
class MetricsConfig:
    """Scenario-agnostic knobs, all in metres / counts."""

    # A raider this close to its assigned facility counts as a "leaker" that got
    # into weapons-release range of the objective.
    strike_radius_m: float = 8000.0
    # Interception depth is normalised against this distance: interdicting a
    # raider at (or beyond) this range from the facility scores a full 1.0.
    reference_depth_m: float = 20000.0
    # A raider stopped at or beyond this distance from its objective counts as a
    # "deep" interception.  The depth layer combines the *median* interception
    # distance with the deep-interception rate, because the mean is dominated by
    # a few long-range kills: an arm that stops most raiders 200 m from the
    # facility and a few at 18 km has a healthy mean but no real depth.
    deep_interception_m: float = 5000.0
    # Ammo efficiency: kills per shot at or above this ratio scores a full 1.0.
    reference_kills_per_shot: float = 0.5
    # Exchange ratio: defender kills per defender loss at or above this scores 1.0.
    reference_exchange_ratio: float = 2.0
    weights: LayerWeights = field(default_factory=LayerWeights)


@dataclass(frozen=True)
class UnitState:
    entity_id: str
    faction: str
    role: str
    domain: str
    tags: tuple[str, ...]
    lifecycle: str
    health: float
    position_m: tuple[float, float, float]

    @property
    def assigned_target(self) -> Optional[str]:
        for tag in self.tags:
            if tag.startswith(TARGET_TAG_PREFIX):
                return tag[len(TARGET_TAG_PREFIX):]
        return None


def classify_role(domain: str, tags: Iterable[str]) -> str:
    """Derive the unit role from the resolved domain plus scenario tags.

    ``domain`` comes from the platform definition (``air`` / ``surface`` /
    ``land``); tags decide between a scoreable structure and a mobile unit.
    """
    tagset = {str(tag) for tag in tags}
    # A shore sensor / C2 site is friendly infrastructure: it is neither a
    # scoreable protected asset nor a combat unit, so it must not enter the
    # facility layer or inflate either side's force totals.  It has to be tested
    # BEFORE the land/fixed fallback, which would otherwise call it a facility.
    if "sensor-site" in tagset:
        return ROLE_OTHER
    if "facility" in tagset or domain == "land" or "fixed" in tagset:
        return ROLE_FACILITY
    # 中立民用必须先于 usv 判定：否则民用船会被算成"无人船战损"，并进入
    # raiders_total 分母，把拦截纵深指标算错。
    if tagset & CIVILIAN_TAGS:
        return ROLE_CIVILIAN
    if domain == "air":
        return ROLE_UAV
    if domain in {"surface", "subsurface", "underwater"}:
        return ROLE_USV
    return ROLE_OTHER


def _clamp01(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, value))


def _distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.dist(tuple(float(v) for v in a[:3]), tuple(float(v) for v in b[:3]))


def _median(values: list[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _parse_terminal_blob(blob: str) -> dict[str, Any]:
    """Recover terminal fields from a ``repr`` of the engine's frozen receipt."""

    import re

    fields: dict[str, Any] = {}
    match = re.search(r"rule_id='([^']+)'", blob)
    if match:
        fields["rule_id"] = match.group(1)
    match = re.search(r"outcome='([^']+)'", blob) or re.search(r"result='([^']+)'", blob)
    if match:
        fields["outcome"] = match.group(1)
    match = re.search(r"tick=(\d+)", blob)
    if match:
        fields["tick"] = int(match.group(1))
    fields["latched"] = "latched=True" in blob
    return fields


def _looks_like_receipt_blob(value: Any) -> bool:
    text = str(value or "")
    return "TerminalMissionResultV2(" in text or "mappingproxy(" in text


def coerce_terminal(terminal_result: Any) -> tuple[dict[str, Any], bool]:
    """Normalise a terminal receipt into ``{outcome, rule_id, tick, latched}``.

    Returns ``(fields, unstructured)``.  ``unstructured`` is True when the fields
    had to be recovered from text — which is what runs recorded before the
    harness expanded the engine's frozen ``MappingProxyType`` receipt look like
    (they carry ``{"result": "<repr of the model>"}``).

    Callers must not fall back to substring matching on the raw blob: the blob
    also contains the ranking map (``'coalition.intruder': 2``), which silently
    flips a defender hold into an attacker win.
    """

    if terminal_result is None:
        return {}, False

    if isinstance(terminal_result, Mapping):
        has_fields = any(
            key in terminal_result for key in ("rule_id", "tick", "latched")
        )
        candidate = terminal_result.get("outcome") or terminal_result.get("result")
        if has_fields and not _looks_like_receipt_blob(candidate):
            return {
                "outcome": candidate,
                "rule_id": terminal_result.get("rule_id"),
                "tick": terminal_result.get("tick"),
                "latched": bool(terminal_result.get("latched")),
            }, False
        if _looks_like_receipt_blob(candidate):
            return _parse_terminal_blob(str(candidate)), True
        # a mapping with only an outcome label
        return {"outcome": candidate, "rule_id": None, "tick": None,
                "latched": False}, False

    return _parse_terminal_blob(str(terminal_result)), True


def classify_terminal_state(outcome: Any) -> str:
    """Map an outcome label to a terminal state without blob substring guessing."""

    text = str(outcome or "").strip().lower()
    if not text:
        return "undecided"
    if text in {"defender_success", "defence_success", "timeout", "timeout_defender"}:
        return "defender_success"
    if text in {"intruder_success", "attacker_success", "breach_failure"}:
        return "attacker_success"
    if "intruder" in text or "attacker" in text:
        return "attacker_success"
    if "defender" in text or "defence" in text or "defense" in text:
        return "defender_success"
    return str(text)


def terminal_layer_score(
    *,
    terminal_result: Any,
    facility_rows: Sequence[Mapping[str, Any]],
    aborted: Optional[str],
) -> dict[str, Any]:
    """Terminal layer: correctness of the latch, plus an evidence consistency gate."""

    fields, unstructured = coerce_terminal(terminal_result)
    outcome = fields.get("outcome")
    if aborted:
        state = "aborted"
    else:
        state = classify_terminal_state(outcome)

    destroyed = sum(1 for row in facility_rows
                    if row.get("lifecycle") in DEAD_STATES)
    consistent = True
    if state == "defender_success" and facility_rows and destroyed == len(facility_rows):
        # declared a hold while every protected structure is gone
        consistent = False
    if state == "attacker_success" and destroyed == 0:
        consistent = False

    score = {
        "defender_success": 1.0,
        "attacker_success": 0.0,
        "undecided": 0.5,
        "aborted": 0.0,
    }.get(state, 0.5)
    if not consistent:
        score *= 0.5

    return {
        "state": state,
        "outcome": outcome,
        "rule_id": fields.get("rule_id"),
        "tick": fields.get("tick"),
        "latched": bool(fields.get("latched")),
        "consistent_with_evidence": consistent,
        "unstructured_receipt": unstructured,
        "score": round(score, 4),
    }


def depth_layer_score(depths: Sequence[float],
                      config: MetricsConfig,
                      raiders_total: Optional[int] = None) -> tuple[float, dict[str, Any]]:
    """Interception-depth layer = share of raiders stopped ``deep_interception_m``
    or farther from the objective they were attacking.

    Defined over **all** raiders, not only the intercepted ones: a raider that got
    through counts as a failure of depth.  Scoring only the intercepted subset has
    a perverse incentive — a defence that stops 4 of 12 raiders far out would score
    higher than one that stops 7 of 12 (measured: the weakest arm scored 0.96 on
    the earlier median-based layer).  ``median_m`` / ``mean_m`` are still reported
    as evidence, computed over the intercepted subset.
    """

    values = sorted(float(value) for value in depths)
    total = max(int(raiders_total or len(values)), len(values), 0)
    if total <= 0:
        return 0.0, {
            "intercepted": 0, "raiders_total": 0,
            "median_m": None, "mean_m": None,
            "reference_depth_m": config.reference_depth_m,
            "deep_threshold_m": config.deep_interception_m,
            "deep_interceptions": 0, "legacy_deep_rate": 0.0,
            "legacy_binary_score": 0.0, "mean_normalized_depth": 0.0,
            "deep_rate": 0.0,
        }
    median = _median(values) if values else None
    mean = (sum(values) / len(values)) if values else None
    deep = sum(1 for value in values
               if value >= config.deep_interception_m)
    legacy_deep_rate = deep / total
    # 连续口径：每个来袭者按"被拦下的距离 / 参考纵深"给分，漏防计 0；
    # 层分数对**全部来袭者**取平均。这样 reference_depth_m 这个此前声明了却
    # 从未参与计算的参数真正投入使用，并消除 5 km 硬阈值的断崖
    # （旧口径下 3.4 km 记 0、5.1 km 记满分，1.6 km 之差等于整个 0.20 权重）。
    reference = max(float(config.reference_depth_m), 1.0)
    mean_normalized = sum(min(1.0, value / reference) for value in values) / total
    return _clamp01(mean_normalized), {
        "intercepted": len(values),
        "raiders_total": total,
        "median_m": None if median is None else round(median, 1),
        "mean_m": None if mean is None else round(mean, 1),
        "reference_depth_m": config.reference_depth_m,
        "deep_threshold_m": config.deep_interception_m,
        "deep_interceptions": deep,
        "legacy_deep_rate": round(legacy_deep_rate, 4),
        "legacy_binary_score": round(_clamp01(legacy_deep_rate), 4),
        "mean_normalized_depth": round(mean_normalized, 4),
        "deep_rate": round(legacy_deep_rate, 4),
    }


def compute_scorecard(
    *,
    units: Mapping[str, UnitState],
    losses: Sequence[Mapping[str, Any]],
    fires: Sequence[Mapping[str, Any]],
    facilities: Sequence[Mapping[str, Any]],
    defender_faction: str,
    attacker_faction: str,
    terminal_result: Optional[Mapping[str, Any]],
    aborted: Optional[str],
    ticks_run: int,
    max_ticks: int,
    config: Optional[MetricsConfig] = None,
) -> dict[str, Any]:
    """Build the full scorecard from engine evidence.

    ``units`` is the final entity state keyed by id; ``losses`` is one record per
    lifecycle transition into a lost state (``tick``, ``entity_id``,
    ``position_m``, ``lifecycle``, ``previous_lifecycle``); ``fires`` is one
    record per *executed* shot; ``facilities`` lists ``{"id", "position_m",
    "weight"}`` entries the defender is protecting.
    """

    cfg = config or MetricsConfig()
    weights = cfg.weights
    facility_by_id = {str(item["id"]): item for item in facilities}

    def facility_position(facility_id: str) -> Optional[tuple[float, float, float]]:
        item = facility_by_id.get(facility_id)
        if item is None:
            return None
        return tuple(float(v) for v in item["position_m"])

    units_by_faction: dict[str, list[UnitState]] = {}
    for unit in units.values():
        units_by_faction.setdefault(unit.faction, []).append(unit)

    def count(faction: str, role: str, states: frozenset[str]) -> int:
        return sum(
            1 for unit in units_by_faction.get(faction, ())
            if unit.role == role and unit.lifecycle in states
        )

    # ---- force accounting -------------------------------------------------
    force: dict[str, dict[str, Any]] = {}
    for faction in (defender_faction, attacker_faction):
        roster = units_by_faction.get(faction, [])
        entry: dict[str, Any] = {}
        for role in (ROLE_UAV, ROLE_USV, ROLE_FACILITY):
            total = sum(1 for unit in roster if unit.role == role)
            lost = sum(1 for unit in roster if unit.role == role
                       and unit.lifecycle in LOST_STATES)
            dead = sum(1 for unit in roster if unit.role == role
                       and unit.lifecycle in DEAD_STATES)
            entry[role] = {
                "total": total,
                "lost": lost,
                "destroyed": dead,
                "surviving": total - lost,
                "loss_rate": round(lost / total, 4) if total else 0.0,
            }
        force[faction] = entry

    # ---- facilities: weighted survival ------------------------------------
    facility_rows: list[dict[str, Any]] = []
    weighted_sum = 0.0
    weight_total = 0.0
    for item in facilities:
        facility_id = str(item["id"])
        weight = float(item.get("weight", 1.0))
        unit = units.get(facility_id)
        health = 0.0 if unit is None else _clamp01(float(unit.health))
        if unit is not None and unit.lifecycle in DEAD_STATES:
            health = 0.0
        weighted_sum += weight * health
        weight_total += weight
        facility_rows.append({
            "id": facility_id,
            "weight": weight,
            "health": round(health, 4),
            "lifecycle": None if unit is None else unit.lifecycle,
            "shots_taken": sum(1 for fire in fires
                               if str(fire.get("target")) == facility_id),
        })
    weighted_survival = (weighted_sum / weight_total) if weight_total else 0.0
    facilities_destroyed = sum(1 for row in facility_rows
                               if row["lifecycle"] in DEAD_STATES)
    facilities_lost = sum(1 for row in facility_rows
                          if row["lifecycle"] in LOST_STATES)

    # ---- interception depth + leakage ------------------------------------
    leaks = 0
    released = 0
    raider_total = 0
    unresolved = 0
    raider_rows: list[dict[str, Any]] = []
    for unit in units_by_faction.get(attacker_faction, ()):
        if unit.role != ROLE_UAV:
            continue
        raider_total += 1
        target_id = unit.assigned_target
        target_position = facility_position(target_id) if target_id else None
        if target_position is None:
            # A raider with no resolvable objective cannot be scored on depth or
            # leakage; count it explicitly instead of silently scoring zero.
            unresolved += 1
            raider_rows.append({
                "entity_id": unit.entity_id,
                "assigned_target": target_id,
                "lifecycle": unit.lifecycle,
                "final_range_to_target_m": None,
                "released_on_target": False,
                "lost": unit.lifecycle in LOST_STATES,
            })
            continue
        final_range = _distance(unit.position_m, target_position)
        if final_range <= cfg.strike_radius_m:
            leaks += 1
        # The sharper penetration signal: did this raider actually release a
        # weapon on its assigned objective?  A raider shot down *after* getting
        # into release range still penetrated the outer layer.
        did_release = any(
            str(fire.get("shooter")) == unit.entity_id
            and str(fire.get("target")) == target_id
            for fire in fires
        )
        if did_release:
            released += 1
        raider_rows.append({
            "entity_id": unit.entity_id,
            "assigned_target": target_id,
            "lifecycle": unit.lifecycle,
            "final_range_to_target_m": round(final_range, 1),
            "released_on_target": did_release,
            "lost": unit.lifecycle in LOST_STATES,
        })
    # Loss events give the position *at the moment* the raider left the fight,
    # which is the authoritative interception point.
    depth_by_entity: dict[str, float] = {}
    for record in losses:
        if str(record.get("faction")) != attacker_faction:
            continue
        entity_id = str(record.get("entity_id"))
        unit = units.get(entity_id)
        if unit is None or unit.role != ROLE_UAV:
            continue
        target_id = unit.assigned_target
        target_position = facility_position(target_id) if target_id else None
        if target_position is None:
            continue
        depth_by_entity[entity_id] = _distance(record["position_m"], target_position)

    interception_depths = sorted(depth_by_entity.values())
    mean_depth = (sum(interception_depths) / len(interception_depths)
                  if interception_depths else None)
    intercepted = len(interception_depths)
    leak_rate = (leaks / raider_total) if raider_total else 0.0
    release_rate = (released / raider_total) if raider_total else 0.0

    # ---- ammunition / fire accounting ------------------------------------
    fire_rows: dict[str, dict[str, Any]] = {}
    for faction in (defender_faction, attacker_faction):
        shots = [fire for fire in fires if str(fire.get("side_faction")) == faction]
        fire_rows[faction] = {
            "shots": len(shots),
            "shots_by_weapon": _count_by(shots, "weapon"),
            "shots_by_target_role": _count_by(shots, "target_role"),
        }

    # ---- kill attribution -------------------------------------------------
    # 击杀必须按**死因**归因，不能把所有损失都算成对方战果。实测反例（IE-03）：
    # 我方只开火 2 发，却有 4 艘自爆船落损（其余是碰撞/搁浅），旧口径直接记
    # "4 个击杀"，弹药效率虚高到 2.0、`ammo` 层饱和，交换比也被放大 2 倍。
    #
    # 归因规则：某实体落损时，其"死因"取引擎同一 tick 的 DamageIntentV2
    # （source_kind ∈ {weapon, collision, environment}）与来源阵营。
    #   * weapon 且来源阵营为对方且非自伤  → 记对方一个击杀；
    #   * collision / environment / 自伤   → 非战斗损失，任何一方都不记击杀。
    # 老报告没有归因字段（没有任何一条损失带 damage_source_kind）时回退到旧
    # 口径，保证历史结果仍可复算对照。
    attributed = any(record.get("damage_source_kind") is not None
                     for record in losses)

    def kills_by(killer_faction: str, victim_faction: str) -> int:
        """victim_faction 的落损中，由 killer_faction 的火力造成的数量。"""
        total = 0
        for record in losses:
            if str(record.get("faction")) != victim_faction:
                continue
            if not attributed:
                total += 1
                continue
            if str(record.get("damage_source_kind")) != "weapon":
                continue
            if record.get("self_inflicted"):
                continue
            if str(record.get("killer_faction")) != killer_faction:
                continue
            total += 1
        return total

    def losses_of(faction: str) -> int:
        return sum(1 for record in losses
                   if str(record.get("faction")) == faction)

    defender_kills = kills_by(defender_faction, attacker_faction)
    attacker_kills = kills_by(attacker_faction, defender_faction)
    defender_losses = losses_of(defender_faction)
    attacker_losses = losses_of(attacker_faction)
    non_combat_losses = attacker_losses + defender_losses - (
        defender_kills + attacker_kills) if attributed else 0
    defender_shots = fire_rows[defender_faction]["shots"]
    attacker_shots = fire_rows[attacker_faction]["shots"]
    defender_ammo_eff = (defender_kills / defender_shots) if defender_shots else 0.0
    attacker_ammo_eff = (attacker_kills / attacker_shots) if attacker_shots else 0.0

    # ---- terminal correctness --------------------------------------------
    terminal_info = terminal_layer_score(
        terminal_result=terminal_result,
        facility_rows=facility_rows,
        aborted=aborted,
    )
    terminal_state = terminal_info["state"]
    consistent = terminal_info["consistent_with_evidence"]
    terminal_score = terminal_info["score"]

    facilities_score = _clamp01(
        weighted_survival if weight_total else 0.0
    )
    depth_score, depth_evidence = depth_layer_score(
        interception_depths, cfg, raiders_total=raider_total)
    leak_score = _clamp01(1.0 - release_rate)
    exchange_ratio = (defender_kills / attacker_kills) if attacker_kills else (
        float(defender_kills) if defender_kills else 0.0
    )
    exchange_score = _clamp01(exchange_ratio / cfg.reference_exchange_ratio)
    ammo_score = _clamp01(defender_ammo_eff / cfg.reference_kills_per_shot)

    # Surface layer: did the defender stop the raider boats before their target
    # was destroyed?  Scored as share of attacker USVs that never reached their
    # assigned objective.
    boat_total = sum(1 for unit in units_by_faction.get(attacker_faction, ())
                     if unit.role == ROLE_USV)
    boats_lost = sum(1 for unit in units_by_faction.get(attacker_faction, ())
                     if unit.role == ROLE_USV and unit.lifecycle in LOST_STATES)
    surface_score = (boats_lost / boat_total) if boat_total else 1.0

    layers = {
        "terminal": round(terminal_score, 4),
        "facilities": round(facilities_score, 4),
        "depth": round(depth_score, 4),
        "leak": round(leak_score, 4),
        "exchange": round(exchange_score, 4),
        "ammo": round(ammo_score, 4),
        "surface": round(surface_score, 4),
    }

    # ---- applicability: an undefined layer must not be scored -------------
    # 平台规则要求"N/A 不自动计零"。反过来同样成立：N/A 也不能自动计满分。
    # 此前两处都犯了：IE-03（纯水面突袭、`raider_total == 0`）的纵深与漏防两层
    # 取 0.0，等于因为"没有空中来袭者"扣掉 0.30 权重；而 IE-01/IE-02（没有
    # 水面来袭者）的水面层取 1.0，白送 0.10 权重。两种情况都让该层对区分度
    # 毫无贡献，却系统性地偏移了绝对分。
    #
    # 修正口径：不适用的层**退出加权平均**，剩余权重重新归一化；同时保留
    # 旧口径 `legacy_defender_score_all_layers`（全层恒定分母）以便新旧对照。
    applicable = {
        "terminal": True,
        "facilities": True,
        # 没有空中来袭者就没有"拦截纵深"可评
        "depth": raider_total > 0,
        "leak": raider_total > 0,
        "exchange": True,
        # 我方没开火且场上本就没有可打目标 → 弹药效率无定义；有目标而不开火
        # 仍然计 0（消极防守必须被扣分）
        "ammo": not (defender_shots == 0
                     and raider_total == 0 and boat_total == 0),
        # 来袭方没有水面平台时，水面层无定义
        "surface": boat_total > 0,
    }
    weighted = {
        "terminal": weights.terminal,
        "facilities": weights.facilities,
        "depth": weights.depth,
        "leak": weights.leak,
        "exchange": weights.exchange,
        "ammo": weights.ammo,
        "surface": weights.surface,
    }
    scored_weight = sum(weighted[name] for name in layers if applicable[name])
    overall = (
        sum(layers[name] * weighted[name] for name in layers if applicable[name])
        / scored_weight
    ) if scored_weight > 0 else 0.0
    legacy_overall = (sum(layers[name] * weighted[name] for name in layers)
                      / weights.total())
    attacker_overall = 1.0 - overall  # zero-sum framing for the head-to-head score

    return {
        "schema_version": "strategy-scorecard@1.0",
        "scenario_horizon": {"ticks_run": ticks_run, "max_ticks": max_ticks,
                             "aborted": aborted},
        "terminal": {
            "state": terminal_state,
            "outcome": terminal_info["outcome"],
            "rule_id": terminal_info["rule_id"],
            "tick": terminal_info["tick"],
            "latched": terminal_info["latched"],
            "consistent_with_evidence": consistent,
            "unstructured_receipt": terminal_info["unstructured_receipt"],
        },
        "force": force,
        "facilities": {
            "rows": facility_rows,
            "weighted_survival": round(weighted_survival, 4),
            "destroyed": facilities_destroyed,
            "out_of_action": facilities_lost,
        },
        "air_layer": {
            "raiders_total": raider_total,
            "raiders_intercepted": intercepted,
            "interception_rate": round(intercepted / raider_total, 4) if raider_total else 0.0,
            "interception_depth_m": {
                "mean": None if mean_depth is None else round(mean_depth, 1),
                "median": None if _median(interception_depths) is None
                else round(_median(interception_depths) or 0.0, 1),
                "min": round(interception_depths[0], 1) if interception_depths else None,
                "max": round(interception_depths[-1], 1) if interception_depths else None,
                "per_entity": {key: round(value, 1)
                               for key, value in sorted(depth_by_entity.items())},
            },
            "strike_radius_m": cfg.strike_radius_m,
            "depth_layer": depth_evidence,
            # 几何漏防：飞进打击半径（含被击落前突入）的来袭无人机比例
            "leakers": leaks,
            "leak_rate": round(leak_rate, 4),
            # 实质破防：真的对指定设施投放过武器的来袭无人机比例（漏防层用它评分）
            "released_on_target": released,
            "release_rate": round(release_rate, 4),
            "raiders": sorted(raider_rows, key=lambda row: row["entity_id"]),
            "unresolved_assignments": unresolved,
        },
        "fire": {
            "by_faction": fire_rows,
            # 按死因归因后的击杀数（只有 weapon 且在对方名下、且非自伤才计数）
            "defender_kills": defender_kills,
            "attacker_kills": attacker_kills,
            # 全部落损数（含碰撞/搁浅/自爆）——旧口径下的"击杀"就是这个数
            "defender_kills_all_causes": attacker_losses,
            "attacker_kills_all_causes": defender_losses,
            "defender_losses": defender_losses,
            "attacker_losses": attacker_losses,
            "non_combat_losses": non_combat_losses,
            "kill_attribution": "damage_intent" if attributed else "legacy_all_causes",
            "defender_shots_per_kill": (
                round(defender_shots / defender_kills, 3) if defender_kills else None
            ),
            "attacker_shots_per_kill": (
                round(attacker_shots / attacker_kills, 3) if attacker_kills else None
            ),
            "defender_ammo_efficiency": round(defender_ammo_eff, 4),
            "attacker_ammo_efficiency": round(attacker_ammo_eff, 4),
        },
        "layers": layers,
        "layer_weights": weighted,
        # 哪些层真正参与了加权平均（不适用的层已退出并重新归一化）
        "layer_applicability": applicable,
        "scored_weight": round(scored_weight, 4),
        "defender_score": round(overall, 4),
        # 旧口径（全部 7 层恒定分母）保留以便与历史结果对照
        "legacy_defender_score_all_layers": round(legacy_overall, 4),
        "attacker_score": round(attacker_overall, 4),
    }


def _count_by(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        name = str(row.get(key) or "unknown")
        counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items()))


def format_scorecard_line(scorecard: Mapping[str, Any], label: str) -> str:
    """One-line summary used by the comparison table across methods.

    Layers that do not apply to this episode print ``n/a`` instead of a number:
    they are excluded from the weighted average, so showing a numeric value
    would imply a contribution that is not actually there.
    """

    layers = scorecard["layers"]
    air = scorecard["air_layer"]
    applicable = scorecard.get("layer_applicability") or {}

    def show(name: str) -> str:
        if not applicable.get(name, True):
            return " n/a"
        return f"{layers[name]:.2f}"

    return (
        f"{label:<10} overall={scorecard['defender_score']:.3f} "
        f"w={scorecard.get('scored_weight', 1.0):.2f} "
        f"term={show('terminal')} fac={show('facilities')} "
        f"depth={show('depth')} leak={show('leak')} "
        f"exch={show('exchange')} ammo={show('ammo')} "
        f"surf={show('surface')} | "
        f"depth_mean={air['interception_depth_m']['mean']} "
        f"intercept={air['interception_rate']:.2f} release={air['release_rate']:.2f}"
    )


__all__ = [
    "DEAD_STATES",
    "LOST_STATES",
    "LayerWeights",
    "MetricsConfig",
    "ROLE_FACILITY",
    "ROLE_UAV",
    "ROLE_USV",
    "UnitState",
    "classify_role",
    "classify_terminal_state",
    "coerce_terminal",
    "compute_scorecard",
    "depth_layer_score",
    "format_scorecard_line",
    "rescore_report",
    "rescore_report_terminal",
    "terminal_layer_score",
]


def rescore_report(report: dict[str, Any],
                   config: Optional[MetricsConfig] = None) -> dict[str, Any]:
    """Re-derive the terminal and depth layers of an existing report in place.

    Needed for two kinds of already-recorded runs:

    * runs whose terminal receipt was stored as a ``repr`` blob before the
      harness expanded the engine's frozen receipt (their ``layers.terminal``
      came from a misclassified state);
    * runs scored with the earlier mean-based depth layer, whose evidence
      (``air_layer.interception_depth_m.per_entity``) is stored in the report so
      the robust layer can be recomputed exactly.

    Every other layer is left untouched, and the overall score is rebuilt from
    the stored weights, so old and new arms stay comparable without re-running
    the episode.
    """

    cfg = config or MetricsConfig()
    scorecard = report.get("strategy_scorecard")
    if not isinstance(scorecard, dict):
        return report

    facility_rows = (scorecard.get("facilities") or {}).get("rows") or []
    info = terminal_layer_score(
        terminal_result=report.get("terminal_result"),
        facility_rows=facility_rows,
        aborted=report.get("aborted"),
    )

    air_layer = scorecard.get("air_layer") or {}
    depth_evidence_in = air_layer.get("interception_depth_m") or {}
    depths = list(depth_evidence_in.get("per_entity", {}).values())
    raiders_total = int(air_layer.get("raiders_total") or len(depths))
    depth_score, depth_evidence = depth_layer_score(
        depths, cfg, raiders_total=raiders_total)

    layers = dict(scorecard.get("layers") or {})
    layers["terminal"] = info["score"]
    layers["depth"] = round(depth_score, 4)
    scorecard["layers"] = layers
    scorecard["terminal"] = {
        "state": info["state"],
        "outcome": info["outcome"],
        "rule_id": info["rule_id"],
        "tick": info["tick"],
        "latched": info["latched"],
        "consistent_with_evidence": info["consistent_with_evidence"],
        "unstructured_receipt": info["unstructured_receipt"],
        "rescored_offline": True,
    }
    air_layer["depth_layer"] = depth_evidence
    scorecard["air_layer"] = air_layer

    weights = scorecard.get("layer_weights") or {}
    applicable = scorecard.get("layer_applicability")
    if not isinstance(applicable, dict):
        # 老报告没有该块：由证据重新推导，保证离线复算与新口径一致（否则
        # 复算会把不适用的层重新算回加权平均里，静默退回旧口径）。
        force = scorecard.get("force") or {}
        attacker_key = next((str(k) for k in force if "intruder" in str(k)), "")
        defender_key = next((str(k) for k in force if "defender" in str(k)), "")
        boat_total = int(((force.get(attacker_key) or {}).get("usv") or {})
                         .get("total") or 0)
        raiders_evidence = int(air_layer.get("raiders_total") or 0)
        defender_shots = int(
            (((scorecard.get("fire") or {}).get("by_faction") or {})
             .get(defender_key) or {}).get("shots") or 0)
        applicable = {
            "terminal": True,
            "facilities": True,
            "depth": raiders_evidence > 0,
            "leak": raiders_evidence > 0,
            "exchange": True,
            "ammo": not (defender_shots == 0 and raiders_evidence == 0
                         and boat_total == 0),
            "surface": boat_total > 0,
        }
    scored_weight = sum(float(weight) for name, weight in weights.items()
                        if applicable.get(name, True))
    overall = (
        sum(float(layers.get(name, 0.0)) * float(weight)
            for name, weight in weights.items() if applicable.get(name, True))
        / scored_weight
    ) if scored_weight > 0 else 0.0
    total = sum(float(value) for value in weights.values()) or 1.0
    scorecard["layer_applicability"] = applicable
    scorecard["scored_weight"] = round(scored_weight, 4)
    scorecard["defender_score"] = round(overall, 4)
    scorecard["legacy_defender_score_all_layers"] = round(
        sum(float(layers.get(name, 0.0)) * float(weight)
            for name, weight in weights.items()) / total, 4)
    scorecard["attacker_score"] = round(1.0 - overall, 4)
    return report


# 旧名保留，避免既有脚本失效
rescore_report_terminal = rescore_report
