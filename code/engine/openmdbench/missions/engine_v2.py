"""Resolved-only authoritative mission evaluation and scoring for schema v2."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field, fields, is_dataclass
from types import MappingProxyType
from typing import Any, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_serializer, model_validator

from openmdbench.scenarios.declarative_v2 import ResolvedScenarioV2

MISSION_CONDITION_OPERATORS_V2 = frozenset(
    {
        "zone",
        "state",
        "any",
        "all",
        "count",
        "survival",
        "time",
        "event",
        "wave",
        "contact",
        "communication",
        "resource",
        "score",
        "not",
    }
)

LEGACY_AGGREGATION_VERSION_V1 = "legacy-v1"
RAW_AGGREGATION_VERSION_V1 = "raw-v1"
UTILITY_AGGREGATION_VERSION_V1 = "utility-v1"


def _plain(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return {str(key): _plain(item) for key, item in value.__dict__.items()}
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _plain(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_plain(item) for item in value]
    return value


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        _plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(_freeze(item) for item in value)
    return value


def _record_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    values = value.values
    if not isinstance(values, Mapping):
        raise ValueError("resolved record does not contain mapping values")
    return values


def _resolved_plain(value: Any) -> Any:
    """Serialize nested compiler records without exposing their wrapper layout."""

    values = getattr(value, "values", None)
    if is_dataclass(value) and not isinstance(value, type) and isinstance(values, Mapping):
        return {str(key): _resolved_plain(item) for key, item in values.items()}
    if isinstance(value, Mapping):
        return {str(key): _resolved_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_resolved_plain(item) for item in value]
    if isinstance(value, BaseModel):
        return {str(key): _resolved_plain(item) for key, item in value.__dict__.items()}
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _resolved_plain(getattr(value, item.name)) for item in fields(value)}
    return value


@dataclass(frozen=True, slots=True)
class ConditionSchemaV2:
    operator: str
    required_fields: tuple[str, ...]
    extra_forbidden: bool = True


_CONDITION_FIELDS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "zone": ("zone_id",),
        "state": ("state",),
        "any": ("conditions",),
        "all": ("conditions",),
        "count": ("comparison", "value"),
        "survival": ("comparison", "value"),
        "time": ("comparison", "tick"),
        "event": ("event_id",),
        "wave": ("wave_id",),
        "contact": ("minimum_count",),
        "communication": ("minimum_count",),
        "resource": ("resource_ref", "comparison", "value"),
        "score": ("metric_id", "comparison", "value"),
        "not": ("conditions",),
    }
)


def condition_schema_v2(operator: str) -> ConditionSchemaV2:
    if operator not in MISSION_CONDITION_OPERATORS_V2:
        raise ValueError("mission condition operator is not whitelisted")
    return ConditionSchemaV2(operator=operator, required_fields=_CONDITION_FIELDS[operator])


class CompiledSelectorV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    selector_id: str = Field(min_length=1, max_length=256)
    entity_ids: tuple[str, ...] = ()
    faction_ids: tuple[str, ...] = ()
    controller_ids: tuple[str, ...] = ()
    visibility_scope: Literal["referee", "public", "faction", "controller"]

    @model_validator(mode="after")
    def canonicalize(self) -> Self:
        for name in ("entity_ids", "faction_ids", "controller_ids"):
            values = tuple(sorted(set(getattr(self, name))))
            object.__setattr__(self, name, values)
        return self


class MissionVisibilityViewV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    faction_id: str | None
    controller_id: str | None
    scope: Literal["referee", "public", "faction", "controller"]
    visible_entity_ids: tuple[str, ...] = ()
    visible_metric_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MissionEvaluationSnapshotV2:
    tick: int
    entity_states: Mapping[str, Mapping[str, Any]]
    zone_membership: Mapping[str, tuple[str, ...]]
    event_ids: tuple[str, ...]
    mission_states: tuple[str, ...]
    contacts: Mapping[str, tuple[str, ...]]
    communications: tuple[Mapping[str, Any], ...]
    resources: Mapping[str, Mapping[str, float]]
    scores: Mapping[str, float | None]
    zone_transitions: tuple[ZoneTransitionEvidenceV2, ...] = ()
    selection_evidence: tuple[EntitySelectionEvidenceV2, ...] = ()
    contact_facts: tuple[MissionContactFactV2, ...] = ()
    resource_facts: tuple[MissionResourceFactV2, ...] = ()
    wave_lifecycle: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    zone_activation: Mapping[str, bool] = field(default_factory=lambda: MappingProxyType({}))


class ZoneTransitionEvidenceV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    entity_id: str = Field(min_length=1, max_length=256)
    zone_id: str = Field(min_length=1, max_length=256)
    transition: Literal["entered", "left"]
    tick: StrictInt = Field(ge=0)
    time_fraction: float = Field(ge=0.0, le=1.0)
    evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class EntitySelectionEvidenceV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    entity_id: str = Field(min_length=1, max_length=256)
    faction_id: str = Field(min_length=1, max_length=256)
    platform_ref: str = Field(default="unbound", min_length=1, max_length=256)
    domain: str = Field(default="unbound", min_length=1, max_length=128)
    controller_id: str | None = None
    tags: tuple[str, ...] = ()
    direct_capabilities: tuple[str, ...] = ()
    dependency_capabilities: tuple[str, ...] = ()
    lifecycle: Literal["scheduled", "active", "degraded", "disabled", "destroyed", "despawned"]

    @model_validator(mode="after")
    def canonicalize(self) -> Self:
        for name in ("tags", "direct_capabilities", "dependency_capabilities"):
            object.__setattr__(self, name, tuple(sorted(set(getattr(self, name)))))
        return self


class MissionContactFactV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    evidence_id: str = Field(min_length=1, max_length=256)
    owner_entity_id: str = Field(min_length=1, max_length=256)
    target_entity_id: str = Field(min_length=1, max_length=256)
    observed_tick: StrictInt = Field(ge=0)
    max_age_ticks: StrictInt = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    minimum_confidence: float = Field(ge=0.0, le=1.0)
    selector_id: str = Field(min_length=1, max_length=256)

    def is_valid(self, *, expected_tick: int, owner_entity_id: str) -> bool:
        return (
            expected_tick >= self.observed_tick
            and expected_tick - self.observed_tick <= self.max_age_ticks
            and self.owner_entity_id == owner_entity_id
            and self.confidence >= self.minimum_confidence
        )


class MissionResourceFactV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    entity_id: str = Field(min_length=1, max_length=256)
    resource_ref: str | None = None
    field: str = Field(min_length=1, max_length=256)
    value: float
    unit: str = Field(min_length=1, max_length=64)


def _evaluation_snapshot_from_evidence(
    value: Mapping[str, Any],
) -> MissionEvaluationSnapshotV2:
    return MissionEvaluationSnapshotV2(
        tick=int(value["tick"]),
        entity_states=_freeze(value["entity_states"]),
        zone_membership=_freeze(value["zone_membership"]),
        event_ids=tuple(value["event_ids"]),
        mission_states=tuple(value["mission_states"]),
        contacts=_freeze(value["contacts"]),
        communications=tuple(_freeze(item) for item in value["communications"]),
        resources=_freeze(value["resources"]),
        scores=_freeze(value["scores"]),
        zone_transitions=tuple(
            ZoneTransitionEvidenceV2.model_validate(item)
            for item in value.get("zone_transitions", ())
        ),
        selection_evidence=tuple(
            EntitySelectionEvidenceV2.model_validate(item)
            for item in value.get("selection_evidence", ())
        ),
        contact_facts=tuple(
            MissionContactFactV2.model_validate(item) for item in value.get("contact_facts", ())
        ),
        resource_facts=tuple(
            MissionResourceFactV2.model_validate(item) for item in value.get("resource_facts", ())
        ),
        wave_lifecycle=_freeze(value.get("wave_lifecycle", {})),
        zone_activation=_freeze(value.get("zone_activation", {})),
    )


class RuntimeSelectorV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    selector_id: str = Field(min_length=1, max_length=256)
    entity_ids: tuple[str, ...] = ()
    faction_ids: tuple[str, ...] = ()
    platform_refs: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    controller_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    include_lifecycle: tuple[str, ...] = ("scheduled", "active", "degraded", "disabled")

    @model_validator(mode="after")
    def canonicalize(self) -> Self:
        for name in (
            "entity_ids",
            "faction_ids",
            "platform_refs",
            "domains",
            "controller_ids",
            "tags",
            "capabilities",
            "include_lifecycle",
        ):
            object.__setattr__(self, name, tuple(sorted(set(getattr(self, name)))))
        return self

    def accepts(self, evidence: EntitySelectionEvidenceV2) -> bool:
        available = set(evidence.direct_capabilities) | set(evidence.dependency_capabilities)
        return not (
            (self.entity_ids and evidence.entity_id not in self.entity_ids)
            or (self.faction_ids and evidence.faction_id not in self.faction_ids)
            or (self.platform_refs and evidence.platform_ref not in self.platform_refs)
            or (self.domains and evidence.domain not in self.domains)
            or (self.controller_ids and evidence.controller_id not in self.controller_ids)
            or any(tag not in evidence.tags for tag in self.tags)
            or any(capability not in available for capability in self.capabilities)
            or evidence.lifecycle not in self.include_lifecycle
        )

    matches = accepts


@dataclass(frozen=True, slots=True)
class MissionFactSnapshotV2:
    tick: int
    entity_states: Mapping[str, Mapping[str, Any]]
    zone_membership: Mapping[str, tuple[str, ...]]
    zone_transitions: tuple[ZoneTransitionEvidenceV2, ...]
    event_ids: tuple[str, ...]
    contacts: Mapping[str, tuple[str, ...]]
    communications: tuple[Mapping[str, Any], ...]
    wave_lifecycle: Mapping[str, str]
    resources: Mapping[str, Mapping[str, float]]
    event_receipts: tuple[Mapping[str, Any], ...]
    selection_evidence: tuple[EntitySelectionEvidenceV2, ...]
    contact_facts: tuple[MissionContactFactV2, ...]
    resource_facts: tuple[MissionResourceFactV2, ...]
    zone_activation: Mapping[str, bool]
    fact_hash: str


@dataclass(frozen=True, slots=True)
class TerminalMissionResultV2:
    rule_id: str
    outcome: str
    priority: int
    tick: int
    latched: bool
    trigger_evidence: Mapping[str, Any]
    ranking: Mapping[str, int] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class TerminalCandidateV2:
    rule_id: str
    priority: int
    event_id: str
    result: str | None = None
    ranking: Mapping[str, int] = field(default_factory=lambda: MappingProxyType({}))


def select_terminal_result_v2(
    candidates: Sequence[TerminalCandidateV2], *, tick: int
) -> TerminalMissionResultV2:
    if not candidates:
        raise ValueError("terminal selection requires at least one candidate")
    if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
        raise ValueError("terminal selection tick must be a nonnegative integer")
    selected = min(candidates, key=lambda item: (-item.priority, item.rule_id, item.event_id))
    evidence = MappingProxyType(
        {
            "event_id": selected.event_id,
            "candidate_hash": _canonical_hash(candidates),
            "selection_policy": "priority_desc_rule_id_asc_event_id_asc",
        }
    )
    return TerminalMissionResultV2(
        rule_id=selected.rule_id,
        outcome=selected.result or selected.event_id,
        priority=selected.priority,
        tick=tick,
        latched=True,
        trigger_evidence=evidence,
        ranking=MappingProxyType(dict(sorted(selected.ranking.items()))),
    )


@dataclass(frozen=True, slots=True)
class MissionTickReceiptV2:
    tick: int
    operation_id: str
    triggered_rule_ids: tuple[str, ...]
    mission_states: tuple[str, ...]
    emitted_event_ids: tuple[str, ...]
    terminal_result: TerminalMissionResultV2 | None
    snapshot_hash: str


class ScoreInputV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    metric_id: str = Field(min_length=1, max_length=256)
    value: float | None
    weight: float = Field(ge=0.0)
    unit: str = Field(min_length=1, max_length=64)
    aggregation: Literal["sum", "mean", "min", "max", "count"] = "sum"
    direction: Literal["maximize", "minimize"] = "maximize"
    normalization_lower_bound: float | None = None
    normalization_upper_bound: float | None = None
    not_applicable_reason: str | None = None
    missing_inputs: tuple[str, ...] = ()
    missing_evidence_source: str | None = None

    @model_validator(mode="after")
    def finite_values(self) -> Self:
        if not math.isfinite(self.weight) or (
            self.value is not None and not math.isfinite(self.value)
        ):
            raise ValueError("score input must be finite")
        lower = self.normalization_lower_bound
        upper = self.normalization_upper_bound
        if (lower is None) != (upper is None):
            raise ValueError("score normalization bounds must be supplied together")
        zero_cardinality_na = (
            lower == 0.0
            and upper == 0.0
            and self.value is None
            and self.not_applicable_reason == "selector_cardinality_zero"
        )
        if (
            lower is not None
            and upper is not None
            and (
                not math.isfinite(lower)
                or not math.isfinite(upper)
                or (lower >= upper and not zero_cardinality_na)
            )
        ):
            raise ValueError("score normalization bounds must be finite and increasing")
        if self.not_applicable_reason is not None and (
            self.value is not None
            or not isinstance(self.not_applicable_reason, str)
            or not self.not_applicable_reason
        ):
            raise ValueError("N/A score reason requires an unavailable metric")
        inputs = tuple(sorted(set(self.missing_inputs)))
        if any(not isinstance(item, str) or not item or len(item) > 256 for item in inputs):
            raise ValueError("missing score input identities are invalid")
        object.__setattr__(self, "missing_inputs", inputs)
        if inputs:
            if (
                self.value != 0.0
                or not isinstance(self.missing_evidence_source, str)
                or not self.missing_evidence_source
            ):
                raise ValueError("missing score data must produce numeric zero with evidence")
        elif self.missing_evidence_source is not None:
            raise ValueError("available or N/A score data cannot carry missing evidence")
        if inputs and self.not_applicable_reason is not None:
            raise ValueError("missing score data cannot be N/A")
        return self


@dataclass(frozen=True, slots=True)
class MetricScoreReceiptV2:
    metric_id: str
    value: float | None
    weight: float
    unit: str
    aggregation: Literal["sum", "mean", "min", "max", "count"]
    direction: Literal["maximize", "minimize"]
    data_status: Literal["available", "not_applicable", "missing"] = "available"
    raw_value: float | None = None
    utility_value: float | None = None
    effective_weight: float = 0.0
    weighted_contribution: float | None = None
    aggregation_version: str = LEGACY_AGGREGATION_VERSION_V1
    not_applicable_reason: str | None = None


@dataclass(frozen=True, slots=True)
class MetricDataMissingReceiptV2:
    """Audit evidence for a metric that should exist but lacks its authority input."""

    metric_id: str
    missing_inputs: tuple[str, ...]
    tick: int | None
    evidence_source: str


@dataclass(frozen=True, slots=True)
class MetricValueOutOfRangeReceiptV2:
    """Audit evidence that an available raw metric was clamped to its declared range."""

    metric_id: str
    raw_value: float
    lower_bound: float
    upper_bound: float
    tick: int | None


@dataclass(frozen=True, slots=True)
class ScoreReceiptV2:
    metrics: tuple[ScoreInputV2, ...]
    total: float | None
    effective_weights: Mapping[str, float]
    aggregation: str
    direction: str
    aggregation_version: str = LEGACY_AGGREGATION_VERSION_V1
    metric_receipts: tuple[MetricScoreReceiptV2, ...] = ()
    metric_data_missing: tuple[MetricDataMissingReceiptV2, ...] = ()
    metric_value_out_of_range: tuple[MetricValueOutOfRangeReceiptV2, ...] = ()
    mission_outcome: TerminalMissionResultV2 | None = None
    competition_scores: Mapping[str, float | None] = field(
        default_factory=lambda: MappingProxyType({})
    )
    training_rewards: Mapping[str, float] = field(default_factory=lambda: MappingProxyType({}))
    tick: int | None = None
    operation_id: str | None = None


class ScoringSystemV2:
    """Pure deterministic scoring with explicit unavailable-value semantics."""

    @staticmethod
    def evaluate(
        metrics: Sequence[ScoreInputV2],
        *,
        aggregation: Literal["sum", "mean", "min", "max", "count"],
        direction: Literal["maximize", "minimize"],
        aggregation_version: str = LEGACY_AGGREGATION_VERSION_V1,
        mission_outcome: TerminalMissionResultV2 | None = None,
        tick: int | None = None,
        operation_id: str | None = None,
    ) -> ScoreReceiptV2:
        if aggregation_version not in {
            LEGACY_AGGREGATION_VERSION_V1,
            RAW_AGGREGATION_VERSION_V1,
            UTILITY_AGGREGATION_VERSION_V1,
        }:
            raise ValueError("score aggregation version is unsupported")
        if aggregation_version == UTILITY_AGGREGATION_VERSION_V1 and (
            aggregation != "sum" or direction != "maximize"
        ):
            raise ValueError("utility-v1 requires sum aggregation and maximize total direction")
        ordered = tuple(sorted(metrics, key=lambda item: item.metric_id))
        if len({item.metric_id for item in ordered}) != len(ordered):
            raise ValueError("score metric identities must be unique")
        available = tuple(item for item in ordered if item.value is not None)
        weight_sum = math.fsum(item.weight for item in available)
        effective = (
            {}
            if weight_sum == 0.0
            else {item.metric_id: item.weight / weight_sum for item in available}
        )
        utilities: dict[str, float | None] = {item.metric_id: None for item in ordered}
        out_of_range: list[MetricValueOutOfRangeReceiptV2] = []
        values = tuple(cast(float, item.value) for item in available)
        if aggregation_version == UTILITY_AGGREGATION_VERSION_V1:
            for item in available:
                lower = item.normalization_lower_bound
                upper = item.normalization_upper_bound
                if lower is None or upper is None:
                    raise ValueError("utility-v1 score metric lacks declared normalization bounds")
                raw = cast(float, item.value)
                if item.missing_inputs:
                    utility = 0.0
                else:
                    if raw < lower or raw > upper:
                        out_of_range.append(
                            MetricValueOutOfRangeReceiptV2(
                                metric_id=item.metric_id,
                                raw_value=raw,
                                lower_bound=lower,
                                upper_bound=upper,
                                tick=tick,
                            )
                        )
                    normalized = min(1.0, max(0.0, (raw - lower) / (upper - lower)))
                    utility = normalized if item.direction == "maximize" else 1.0 - normalized
                utilities[item.metric_id] = utility
            total = (
                None
                if not available
                else math.fsum(
                    cast(float, utilities[item.metric_id]) * effective.get(item.metric_id, 0.0)
                    for item in available
                )
            )
            competition = MappingProxyType(dict(utilities))
            rewards = MappingProxyType({"aggregate": 0.0 if total is None else total})
        else:
            if not values:
                total = None
            elif aggregation == "sum":
                total = math.fsum(
                    value * effective.get(item.metric_id, 0.0)
                    for item, value in zip(available, values, strict=True)
                )
            elif aggregation == "mean":
                total = math.fsum(values) / len(values)
            elif aggregation == "min":
                total = min(values)
            elif aggregation == "max":
                total = max(values)
            else:
                total = float(len(values))
            competition = MappingProxyType({item.metric_id: item.value for item in ordered})
            rewards = MappingProxyType(
                {
                    "aggregate": 0.0
                    if total is None
                    else total * (-1.0 if direction == "minimize" else 1.0)
                }
            )
        metric_receipts = tuple(
            MetricScoreReceiptV2(
                metric_id=item.metric_id,
                value=item.value,
                weight=item.weight,
                unit=item.unit,
                aggregation=item.aggregation,
                direction=item.direction,
                data_status=(
                    "missing"
                    if item.missing_inputs
                    else "not_applicable"
                    if item.value is None
                    else "available"
                ),
                raw_value=item.value,
                utility_value=utilities[item.metric_id]
                if aggregation_version == UTILITY_AGGREGATION_VERSION_V1
                else None,
                effective_weight=effective.get(item.metric_id, 0.0),
                weighted_contribution=(
                    None
                    if aggregation_version != UTILITY_AGGREGATION_VERSION_V1
                    or utilities[item.metric_id] is None
                    else cast(float, utilities[item.metric_id]) * effective.get(item.metric_id, 0.0)
                ),
                aggregation_version=aggregation_version,
                not_applicable_reason=item.not_applicable_reason,
            )
            for item in ordered
        )
        missing_receipts = tuple(
            MetricDataMissingReceiptV2(
                metric_id=item.metric_id,
                missing_inputs=item.missing_inputs,
                tick=tick,
                evidence_source=cast(str, item.missing_evidence_source),
            )
            for item in ordered
            if item.missing_inputs
        )
        return ScoreReceiptV2(
            metrics=ordered,
            total=total,
            effective_weights=MappingProxyType(dict(sorted(effective.items()))),
            aggregation=aggregation,
            direction=direction,
            aggregation_version=aggregation_version,
            metric_receipts=metric_receipts,
            metric_data_missing=missing_receipts,
            metric_value_out_of_range=tuple(out_of_range),
            mission_outcome=mission_outcome,
            competition_scores=competition,
            training_rewards=rewards,
            tick=tick,
            operation_id=operation_id,
        )


@dataclass(frozen=True, slots=True)
class EventScoreReceiptV2:
    metric_id: str
    event_id: str
    tick: int
    value: float
    accumulated_value: float
    source_evidence_hash: str


class EventScoreInputReceiptV2(BaseModel):
    """Resolved policy plus the exact World-owned typed event used as score input."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    metric_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    event_type: str = Field(min_length=1, max_length=128)
    tick: StrictInt = Field(ge=0)
    value_path: str = Field(
        pattern=r"^payload\.[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$"
    )
    value: float
    unit: str = Field(min_length=1, max_length=64)
    aggregation: Literal["sum"] = "sum"
    resolved_policy: dict[str, Any]
    resolved_policy_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    world_event_receipt: dict[str, Any]
    world_event_receipt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    input_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        policy = _plain(self.resolved_policy)
        world_receipt = _plain(self.world_event_receipt)
        expected_policy = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "value_path": self.value_path,
            "source": "world_typed_event_receipt",
            "unit": self.unit,
            "aggregation": self.aggregation,
        }
        payload = world_receipt.get("payload") if isinstance(world_receipt, Mapping) else None
        if (
            policy != expected_policy
            or self.resolved_policy_hash != _canonical_hash(policy)
            or not isinstance(world_receipt, Mapping)
            or set(world_receipt)
            != {
                "event_id",
                "event_type",
                "tick",
                "payload",
                "payload_hash",
                "owner_state_hash_before",
                "owner_state_hash_after",
            }
            or world_receipt.get("event_id") != self.event_id
            or world_receipt.get("event_type") != self.event_type
            or world_receipt.get("tick") != self.tick
            or world_receipt.get("payload_hash") != _canonical_hash(payload)
            or self.world_event_receipt_hash != _canonical_hash(world_receipt)
            or not math.isfinite(self.value)
        ):
            raise ValueError("event score input evidence is not canonical")
        input_payload = self.model_dump(mode="json", exclude={"input_hash"})
        if self.input_hash != _canonical_hash(input_payload):
            raise ValueError("event score input receipt hash mismatch")
        object.__setattr__(self, "resolved_policy", _freeze(policy))
        object.__setattr__(self, "world_event_receipt", _freeze(world_receipt))
        return self

    @field_serializer("resolved_policy", "world_event_receipt")
    def serialize_frozen_evidence(self, value: Any) -> Any:
        return _plain(value)


class EventScoreAccumulatorV2:
    """Session-local exactly-once accumulator for authoritative event identities."""

    def __init__(self, *, metric_id: str, unit: str) -> None:
        if not metric_id or not unit:
            raise ValueError("event score accumulator identity and unit are required")
        self.metric_id = metric_id
        self.unit = unit
        self.value = 0.0
        self._ledger: dict[str, tuple[tuple[float, int, str], EventScoreReceiptV2]] = {}

    def apply(
        self,
        *,
        event_id: str,
        value: float,
        tick: int,
        source_evidence_hash: str | None = None,
    ) -> EventScoreReceiptV2:
        if (
            not event_id
            or not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or not isinstance(tick, int)
            or isinstance(tick, bool)
            or tick < 0
        ):
            raise ValueError("event score evidence must be finite and canonical")
        source_hash = source_evidence_hash or _canonical_hash(
            {"event_id": event_id, "tick": tick, "kind": "typed-event-input"}
        )
        if (
            not isinstance(source_hash, str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", source_hash) is None
        ):
            raise ValueError("event score source evidence hash is invalid")
        fingerprint = (float(value), tick, source_hash)
        prior = self._ledger.get(event_id)
        if prior is not None:
            if prior[0] != fingerprint:
                raise ValueError("event identity conflicts with prior score evidence")
            return prior[1]
        self.value = math.fsum((self.value, float(value)))
        receipt = EventScoreReceiptV2(
            metric_id=self.metric_id,
            event_id=event_id,
            tick=tick,
            value=float(value),
            accumulated_value=self.value,
            source_evidence_hash=source_hash,
        )
        self._ledger[event_id] = (fingerprint, receipt)
        return receipt

    def checkpoint(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "unit": self.unit,
            "value": self.value,
            "ledger": tuple(
                {
                    "event_id": event_id,
                    "input_value": fingerprint[0],
                    "tick": fingerprint[1],
                    "source_evidence_hash": fingerprint[2],
                    "receipt": _plain(receipt),
                }
                for event_id, (fingerprint, receipt) in sorted(self._ledger.items())
            ),
        }

    @classmethod
    def restore(cls, checkpoint: Mapping[str, Any]) -> EventScoreAccumulatorV2:
        accumulator = cls(metric_id=str(checkpoint["metric_id"]), unit=str(checkpoint["unit"]))
        for item in checkpoint.get("ledger", ()):
            accumulator.apply(
                event_id=str(item["event_id"]),
                value=float(item["input_value"]),
                tick=int(item["tick"]),
                source_evidence_hash=str(item["source_evidence_hash"]),
            )
        if not math.isclose(
            accumulator.value, float(checkpoint["value"]), rel_tol=0.0, abs_tol=0.0
        ):
            raise ValueError("event score accumulator checkpoint is inconsistent")
        return accumulator


class MissionScoringCheckpointV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    resolved_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    tick: StrictInt = Field(ge=0)
    mission_states: tuple[str, ...]
    terminal_result: dict[str, Any] | None
    rule_ledger: tuple[dict[str, Any], ...]
    score_state: dict[str, float | None]
    score_ledger: tuple[dict[str, Any], ...]
    operation_receipts: tuple[dict[str, Any], ...]
    event_accumulators: tuple[dict[str, Any], ...]
    event_score_input_receipts: tuple[dict[str, Any], ...]
    plugin_states: tuple[dict[str, Any], ...]
    plugin_output_receipts: tuple[dict[str, Any], ...]
    fact_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mission_definition_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    resolved_mission_states: tuple[str, ...]
    resolved_metric_ids: tuple[str, ...]
    resolved_mission_rules: tuple[dict[str, Any], ...]
    resolved_scoring: dict[str, Any] | None
    checkpoint_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def deep_freeze(self) -> Self:
        for name, value in tuple(self.__dict__.items()):
            object.__setattr__(self, name, _freeze(value))
        return self

    @field_serializer(
        "terminal_result",
        "rule_ledger",
        "score_state",
        "score_ledger",
        "operation_receipts",
        "event_accumulators",
        "event_score_input_receipts",
        "plugin_states",
        "plugin_output_receipts",
        "resolved_mission_rules",
        "resolved_scoring",
    )
    def serialize_frozen_evidence(self, value: Any) -> Any:
        return _plain(value)

    @staticmethod
    def compute_hash(value: Mapping[str, Any] | MissionScoringCheckpointV2) -> str:
        payload = (
            value.model_dump(mode="json")
            if isinstance(value, MissionScoringCheckpointV2)
            else dict(value)
        )
        payload.pop("checkpoint_hash", None)
        return _canonical_hash(payload)

    def validate_integrity(self) -> None:
        if self.checkpoint_hash != self.compute_hash(self):
            raise ValueError("mission scoring checkpoint hash mismatch")
        if self.mission_definition_hash != _canonical_hash(
            {
                "states": self.resolved_mission_states,
                "rules": self.resolved_mission_rules,
                "scoring": self.resolved_scoring,
            }
        ):
            raise ValueError("mission definition evidence hash mismatch")
        rule_ids = tuple(str(item.get("rule_id", "")) for item in self.rule_ledger)
        score_operations = tuple(str(item.get("operation_id", "")) for item in self.score_ledger)
        receipt_keys = tuple(
            (str(item.get("kind", "")), str(item.get("operation_id", "")))
            for item in self.operation_receipts
        )
        if (
            self.mission_states != tuple(sorted(set(self.mission_states)))
            or not all(rule_ids)
            or rule_ids != tuple(sorted(rule_ids))
            or len(rule_ids) != len(set(rule_ids))
            or not all(score_operations)
            or score_operations != tuple(sorted(score_operations))
            or len(score_operations) != len(set(score_operations))
            or any(
                kind not in {"mission", "score"} or not operation
                for kind, operation in receipt_keys
            )
            or receipt_keys != tuple(sorted(receipt_keys))
            or len(receipt_keys) != len(set(receipt_keys))
            or self.resolved_mission_states != tuple(sorted(set(self.resolved_mission_states)))
            or self.resolved_metric_ids != tuple(sorted(set(self.resolved_metric_ids)))
        ):
            raise ValueError("mission scoring checkpoint ledgers are not canonical")
        expected_states = set(self.resolved_mission_states[:1])
        expected_states.update(str(item.get("state", "")) for item in self.rule_ledger)
        if set(self.mission_states) != expected_states:
            raise ValueError("mission states cannot be reconstructed from resolved rule evidence")
        if self.terminal_result is not None:
            terminal = self.terminal_result
            evidence = terminal.get("trigger_evidence")
            if (
                set(terminal)
                != {
                    "rule_id",
                    "outcome",
                    "priority",
                    "tick",
                    "latched",
                    "trigger_evidence",
                    "ranking",
                }
                or not terminal.get("rule_id")
                or not terminal.get("outcome")
                or terminal.get("latched") is not True
                or not isinstance(terminal.get("priority"), int)
                or isinstance(terminal.get("priority"), bool)
                or not isinstance(terminal.get("tick"), int)
                or isinstance(terminal.get("tick"), bool)
                or int(terminal["tick"]) > self.tick
                or not isinstance(evidence, Mapping)
                or not evidence.get("event_id")
                or not isinstance(terminal.get("ranking", {}), Mapping)
            ):
                raise ValueError("mission scoring terminal evidence is invalid")
        for item in self.operation_receipts:
            receipt = item.get("receipt")
            kind = item.get("kind")
            operation_id = item.get("operation_id")
            receipt_tick = receipt.get("tick") if isinstance(receipt, Mapping) else None
            if (
                not isinstance(receipt, Mapping)
                or receipt.get("operation_id") != operation_id
                or not isinstance(receipt_tick, int)
                or isinstance(receipt_tick, bool)
                or receipt_tick > self.tick
                or item.get("fingerprint")
                != _canonical_hash([receipt_tick, operation_id, self.resolved_hash])
                or (kind == "mission" and "terminal_result" not in receipt)
                or (kind == "score" and "competition_scores" not in receipt)
            ):
                raise ValueError("mission scoring receipt evidence is inconsistent")
        score_receipts = {
            str(item["operation_id"]): item["receipt"]
            for item in self.operation_receipts
            if item["kind"] == "score"
        }
        if set(score_operations) != set(score_receipts):
            raise ValueError("score ledger differs from authoritative score receipts")
        for item in self.score_ledger:
            receipt = score_receipts[str(item["operation_id"])]
            if (
                set(item) != {"operation_id", "tick", "total", "metrics"}
                or item.get("tick") != receipt.get("tick")
                or item.get("total") != receipt.get("total")
                or item.get("metrics") != receipt.get("competition_scores")
            ):
                raise ValueError("score ledger differs from authoritative score receipt")
        for item in self.rule_ledger:
            if (
                set(item) != {"rule_id", "tick", "state", "event_id", "snapshot_hash"}
                or item.get("state") not in self.mission_states
                or not item.get("event_id")
                or not isinstance(item.get("tick"), int)
                or isinstance(item.get("tick"), bool)
                or int(item["tick"]) > self.tick
                or not isinstance(item.get("snapshot_hash"), str)
                or len(str(item["snapshot_hash"])) != 71
            ):
                raise ValueError("mission rule ledger evidence is inconsistent")
        resolved_rules = {str(item["id"]): item for item in self.resolved_mission_rules}
        if len(resolved_rules) != len(self.resolved_mission_rules):
            raise ValueError("resolved mission rule evidence is not unique")
        for item in self.rule_ledger:
            definition = resolved_rules.get(str(item["rule_id"]))
            outcome = None if definition is None else definition.get("outcome")
            if (
                not isinstance(outcome, Mapping)
                or item["state"] != outcome.get("set_state")
                or item["event_id"] != outcome.get("emit_event")
            ):
                raise ValueError("mission rule ledger differs from Resolved outcome")
        for item in self.operation_receipts:
            if item["kind"] != "mission":
                continue
            receipt = item["receipt"]
            triggered = tuple(receipt["triggered_rule_ids"])
            if any(rule_id not in resolved_rules for rule_id in triggered):
                raise ValueError("mission receipt references an undeclared Resolved rule")
            emitted = tuple(
                sorted(
                    str(resolved_rules[rule_id]["outcome"]["emit_event"]) for rule_id in triggered
                )
            )
            if tuple(receipt["emitted_event_ids"]) != emitted:
                raise ValueError("mission receipt differs from Resolved outcome events")
        if self.terminal_result is not None:
            terminal_receipt = next(
                (
                    item["receipt"]
                    for item in self.operation_receipts
                    if item["kind"] == "mission"
                    and item["receipt"].get("tick") == self.terminal_result["tick"]
                    and self.terminal_result["rule_id"]
                    in item["receipt"].get("triggered_rule_ids", ())
                ),
                None,
            )
            candidates: list[TerminalCandidateV2] = []
            if isinstance(terminal_receipt, Mapping):
                for rule_id in terminal_receipt["triggered_rule_ids"]:
                    definition = resolved_rules[str(rule_id)]
                    outcome = definition["outcome"]
                    if outcome.get("terminal") is True:
                        candidates.append(
                            TerminalCandidateV2(
                                rule_id=str(rule_id),
                                priority=int(definition["priority"]),
                                event_id=str(outcome["emit_event"]),
                                result=(
                                    None
                                    if outcome.get("result") is None
                                    else str(outcome["result"])
                                ),
                                ranking=MappingProxyType(dict(outcome.get("ranking", {}))),
                            )
                        )
            if not isinstance(terminal_receipt, Mapping) or not candidates:
                raise ValueError("terminal checkpoint lacks a Resolved candidate receipt")
            expected_terminal = _plain(
                select_terminal_result_v2(candidates, tick=int(self.terminal_result["tick"]))
            )
            if (
                _plain(self.terminal_result) != expected_terminal
                or _plain(terminal_receipt.get("terminal_result")) != expected_terminal
            ):
                raise ValueError("terminal result differs from Resolved candidate selection")
            terminal_rule = next(
                (
                    item
                    for item in self.rule_ledger
                    if item["rule_id"] == self.terminal_result["rule_id"]
                ),
                None,
            )
            if (
                terminal_rule is None
                or terminal_rule["event_id"] != self.terminal_result["trigger_evidence"]["event_id"]
            ):
                raise ValueError("terminal result differs from authoritative rule ledger")
        accumulator_ids = tuple(str(item.get("metric_id", "")) for item in self.event_accumulators)
        plugin_ids = tuple(str(item.get("plugin_id", "")) for item in self.plugin_states)
        if (
            not all(accumulator_ids)
            or accumulator_ids != tuple(sorted(set(accumulator_ids)))
            or not all(plugin_ids)
            or plugin_ids != tuple(sorted(set(plugin_ids)))
        ):
            raise ValueError("mission extension checkpoint identities are not canonical")
        plugin_outputs = tuple(self.plugin_output_receipts)
        if tuple(int(item.get("sequence", -1)) for item in plugin_outputs) != tuple(
            range(len(plugin_outputs))
        ):
            raise ValueError("mission plugin output receipt sequence is not canonical")
        for item in plugin_outputs:
            expected_output_hash = _canonical_hash(
                {
                    key: item[key]
                    for key in (
                        "operation_id",
                        "plugin_id",
                        "metric_id",
                        "tick",
                        "input_fact_hash",
                        "input_snapshot",
                        "input_snapshot_hash",
                        "plugin_state_hash_before",
                        "output_value",
                        "plugin_state_hash_after",
                        "sequence",
                    )
                }
            )
            if (
                set(item)
                != {
                    "operation_id",
                    "plugin_id",
                    "metric_id",
                    "tick",
                    "input_fact_hash",
                    "input_snapshot",
                    "input_snapshot_hash",
                    "plugin_state_hash_before",
                    "output_value",
                    "plugin_state_hash_after",
                    "sequence",
                    "output_hash",
                }
                or item.get("plugin_id") != item.get("metric_id")
                or item.get("output_hash") != expected_output_hash
                or item.get("input_snapshot_hash") != _canonical_hash(item.get("input_snapshot"))
                or item.get("operation_id") not in score_receipts
                or item.get("plugin_id") not in plugin_ids
                or (
                    item.get("output_value") is not None
                    and (
                        not isinstance(item.get("output_value"), (int, float))
                        or isinstance(item.get("output_value"), bool)
                        or not math.isfinite(float(item["output_value"]))
                    )
                )
            ):
                raise ValueError("mission plugin output evidence is invalid")
        plugin_state_hashes = {
            str(item["plugin_id"]): str(item["checkpoint"]["state_hash"])
            for item in self.plugin_states
        }
        for plugin_id, final_state_hash in plugin_state_hashes.items():
            owned_outputs = tuple(item for item in plugin_outputs if item["plugin_id"] == plugin_id)
            if owned_outputs and (
                any(
                    current["plugin_state_hash_before"] != previous["plugin_state_hash_after"]
                    for previous, current in zip(owned_outputs, owned_outputs[1:], strict=False)
                )
                or owned_outputs[-1]["plugin_state_hash_after"] != final_state_hash
            ):
                raise ValueError("mission plugin output state chain is inconsistent")
        scoring = self.resolved_scoring
        resolved_metrics = {
            str(item["id"]): item
            for item in (() if scoring is None else scoring.get("metrics", ()))
        }
        typed_event_inputs = tuple(
            EventScoreInputReceiptV2.model_validate(item)
            for item in self.event_score_input_receipts
        )
        input_keys = tuple((item.metric_id, item.event_id) for item in typed_event_inputs)
        if input_keys != tuple(sorted(input_keys)) or len(input_keys) != len(set(input_keys)):
            raise ValueError("event score input receipts are not canonical")
        event_input_index = {(item.metric_id, item.event_id): item for item in typed_event_inputs}
        for typed_input in typed_event_inputs:
            definition = resolved_metrics.get(typed_input.metric_id)
            event_source = None if definition is None else definition.get("event_source")
            if (
                definition is None
                or _plain(event_source) != _plain(typed_input.resolved_policy)
                or definition.get("unit") != typed_input.unit
                or definition.get("available") is not False
                or definition.get("value") is not None
            ):
                raise ValueError("event score input differs from Resolved scoring policy")
        accumulator_input_keys: set[tuple[str, str]] = set()
        for item in self.event_accumulators:
            restored = EventScoreAccumulatorV2.restore(item)
            if _plain(restored.checkpoint()) != _plain(item):
                raise ValueError("event score accumulator checkpoint differs after restore")
            for ledger_item in item.get("ledger", ()):
                key = (restored.metric_id, str(ledger_item.get("event_id", "")))
                input_receipt = event_input_index.get(key)
                receipt = ledger_item.get("receipt", {})
                if (
                    input_receipt is None
                    or ledger_item.get("input_value") != input_receipt.value
                    or ledger_item.get("tick") != input_receipt.tick
                    or ledger_item.get("source_evidence_hash") != input_receipt.input_hash
                    or receipt.get("source_evidence_hash") != input_receipt.input_hash
                ):
                    raise ValueError("event score accumulator lacks authoritative input evidence")
                accumulator_input_keys.add(key)
        if accumulator_input_keys != set(event_input_index):
            raise ValueError("event score input receipts differ from accumulator ledger")
        accumulator_values = {
            str(item["metric_id"]): float(item["value"]) for item in self.event_accumulators
        }
        score_state = dict(self.score_state)
        if set(score_state) - set(self.resolved_metric_ids):
            raise ValueError("score state contains an undeclared resolved metric")
        reconstructed_states: list[dict[str, float | None]] = []
        if not score_receipts:
            reconstructed_states.append(dict(accumulator_values))
        for receipt in score_receipts.values():
            # ``score_state`` is the public competition-score presentation.
            # Event accumulators retain their raw values independently; mixing
            # those raw values into this utility-valued view would make a
            # checkpoint reinterpret the presentation as a raw metric source.
            reconstructed_states.append(dict(receipt["competition_scores"]))
        if score_state not in reconstructed_states:
            raise ValueError("score state cannot be reconstructed from score evidence")
        if set(resolved_metrics) != set(self.resolved_metric_ids):
            raise ValueError("resolved metric evidence identities are inconsistent")
        accumulator_ids_set = set(accumulator_values)
        plugin_ids_set = {str(item["plugin_id"]) for item in self.plugin_states}
        for receipt in score_receipts.values():
            raw_metrics = tuple(receipt["metrics"])
            if {str(item["metric_id"]) for item in raw_metrics} != set(resolved_metrics):
                raise ValueError("score receipt metric set differs from Resolved scoring")
            for metric in raw_metrics:
                metric_id = str(metric["metric_id"])
                definition = resolved_metrics[metric_id]
                normalization = definition.get("normalization")
                normalization_values = _plain(normalization)
                expected_lower = (
                    None
                    if not isinstance(normalization_values, Mapping)
                    else normalization_values.get("lower_bound")
                )
                expected_upper = (
                    None
                    if not isinstance(normalization_values, Mapping)
                    else normalization_values.get("upper_bound")
                )
                if (
                    metric.get("weight") != definition.get("weight")
                    or metric.get("unit") != definition.get("unit")
                    or metric.get("aggregation") != definition.get("aggregation")
                    or metric.get("direction") != definition.get("direction")
                    or metric.get("normalization_lower_bound") != expected_lower
                    or metric.get("normalization_upper_bound") != expected_upper
                    or metric.get("not_applicable_reason")
                    != definition.get("not_applicable_reason")
                    or (
                        metric_id not in accumulator_ids_set | plugin_ids_set
                        and metric.get("value") != definition.get("value")
                    )
                ):
                    raise ValueError("score receipt metric differs from Resolved definition")
                if (
                    metric_id in accumulator_ids_set
                    and metric.get("value") != accumulator_values[metric_id]
                ):
                    raise ValueError("event score input differs from authoritative accumulator")
                if metric_id in plugin_ids_set:
                    plugin_output = next(
                        (
                            item
                            for item in plugin_outputs
                            if item["operation_id"] == receipt["operation_id"]
                            and item["plugin_id"] == metric_id
                        ),
                        None,
                    )
                    if plugin_output is None or metric.get("value") != plugin_output.get(
                        "output_value"
                    ):
                        raise ValueError("plugin score input lacks authoritative output evidence")
            expected_aggregation = "sum" if scoring is None else scoring.get("aggregation")
            expected_direction = "maximize" if scoring is None else scoring.get("direction")
            expected_aggregation_version = (
                LEGACY_AGGREGATION_VERSION_V1
                if scoring is None
                else scoring.get("aggregation_version", LEGACY_AGGREGATION_VERSION_V1)
            )
            if (
                receipt.get("aggregation") != expected_aggregation
                or receipt.get("direction") != expected_direction
                or receipt.get("aggregation_version", expected_aggregation_version)
                != expected_aggregation_version
            ):
                raise ValueError("score receipt total policy differs from Resolved scoring")
            raw_terminal = receipt.get("mission_outcome")
            recomputed = ScoringSystemV2.evaluate(
                tuple(ScoreInputV2.model_validate(item) for item in raw_metrics),
                aggregation=cast(
                    Literal["sum", "mean", "min", "max", "count"],
                    expected_aggregation,
                ),
                direction=cast(Literal["maximize", "minimize"], expected_direction),
                aggregation_version=str(expected_aggregation_version),
                mission_outcome=(
                    None if raw_terminal is None else TerminalMissionResultV2(**raw_terminal)
                ),
                tick=receipt.get("tick"),
                operation_id=receipt.get("operation_id"),
            )
            recomputed_values = _plain(recomputed)
            for field_name in (
                "effective_weights",
                "total",
                "competition_scores",
                "training_rewards",
                "metric_value_out_of_range",
            ):
                if (
                    field_name in receipt
                    and _plain(receipt.get(field_name)) != recomputed_values[field_name]
                ):
                    raise ValueError("score receipt derived evidence failed pure recomputation")
            stored_metric_receipts = receipt.get("metric_receipts", ())
            expected_metric_receipts = recomputed_values["metric_receipts"]
            if len(stored_metric_receipts) != len(expected_metric_receipts) or any(
                not isinstance(actual, Mapping)
                or any(actual.get(key) != expected.get(key) for key in actual)
                for actual, expected in zip(
                    stored_metric_receipts, expected_metric_receipts, strict=True
                )
            ):
                raise ValueError("score receipt derived evidence failed pure recomputation")
        for item in self.plugin_states:
            if set(item) != {"plugin_id", "checkpoint"}:
                raise ValueError("mission plugin checkpoint record is invalid")
            MissionPluginCheckpointV2.model_validate(item["checkpoint"])


class MissionPluginCheckpointV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    plugin_ref: str = Field(min_length=1, max_length=256)
    artifact_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    interface_version: Literal["2.0"] = "2.0"
    deterministic: bool
    trusted: bool
    session_state: dict[str, Any]
    state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_and_freeze(self) -> Self:
        if not self.deterministic or not self.trusted:
            raise ValueError("mission plugin checkpoint is not trusted deterministic evidence")
        if self.state_hash != _canonical_hash(self.session_state):
            raise ValueError("mission plugin state hash mismatch")
        object.__setattr__(self, "session_state", _freeze(self.session_state))
        return self

    @field_serializer("session_state")
    def serialize_frozen_state(self, value: Any) -> Any:
        return _plain(value)


class TrustedMissionPluginFactoryV2:
    """Create a fresh trusted deterministic mission plugin for each session."""

    def __init__(
        self,
        *,
        plugin_ref: str,
        artifact_sha256: str,
        interface_version: str,
        deterministic: bool,
        trusted: bool,
        factory: Any,
    ) -> None:
        if (
            not plugin_ref
            or not artifact_sha256.startswith("sha256:")
            or interface_version != "2.0"
            or not deterministic
            or not trusted
            or not callable(factory)
        ):
            raise ValueError("mission plugin factory evidence is not trusted")
        self.plugin_ref = plugin_ref
        self.artifact_sha256 = artifact_sha256
        self.interface_version = interface_version
        self.deterministic = deterministic
        self.trusted = trusted
        self._factory = factory
        self._instances: list[Any] = []

    def create(self, *, session_id: str, seed: int) -> Any:
        plugin = self._factory(session_id=session_id, seed=seed)
        if any(plugin is item for item in self._instances):
            raise ValueError("mission plugin factory reused mutable session state")
        self._instances.append(plugin)
        return plugin

    def checkpoint(self, plugin: Any) -> MissionPluginCheckpointV2:
        snapshot = getattr(plugin, "snapshot", None)
        if not callable(snapshot):
            raise ValueError("mission plugin lacks checkpoint snapshot protocol")
        session_state = _plain(snapshot())
        if not isinstance(session_state, dict):
            raise ValueError("mission plugin snapshot must be a mapping")
        return MissionPluginCheckpointV2(
            plugin_ref=self.plugin_ref,
            artifact_sha256=self.artifact_sha256,
            interface_version="2.0",
            deterministic=self.deterministic,
            trusted=self.trusted,
            session_state=session_state,
            state_hash=_canonical_hash(session_state),
        )

    def restore(self, checkpoint: MissionPluginCheckpointV2, *, session_id: str, seed: int) -> Any:
        if (
            checkpoint.plugin_ref != self.plugin_ref
            or checkpoint.artifact_sha256 != self.artifact_sha256
            or checkpoint.interface_version != self.interface_version
            or checkpoint.deterministic != self.deterministic
            or checkpoint.trusted != self.trusted
        ):
            raise ValueError("mission plugin checkpoint differs from trusted factory evidence")
        plugin = self.create(session_id=session_id, seed=seed)
        restore = getattr(plugin, "restore", None)
        if not callable(restore):
            raise ValueError("mission plugin lacks checkpoint restore protocol")
        restore(_plain(checkpoint.session_state))
        return plugin


def _compare(actual: float, operator: str, expected: float) -> bool:
    return {
        ">=": actual >= expected,
        ">": actual > expected,
        "==": actual == expected,
        "<=": actual <= expected,
        "<": actual < expected,
    }.get(operator, False)


class MissionEngineV2:
    """Session-local mission authority over compiler-resolved rule endpoints."""

    def __init__(self, *, resolved: ResolvedScenarioV2, world: Any) -> None:
        self._resolved = resolved
        self._world = world
        self.resolved_hash = resolved.resolved_hash
        self._states: set[str] = set(resolved.mission_states[:1])
        self._terminal_result: TerminalMissionResultV2 | None = None
        self._rule_ledger: dict[str, dict[str, Any]] = {}
        self._score_state: dict[str, float | None] = {}
        self._score_ledger: dict[str, dict[str, Any]] = {}
        self._operation_receipts: dict[str, tuple[str, MissionTickReceiptV2]] = {}
        self._score_receipts: dict[str, tuple[str, ScoreReceiptV2]] = {}
        self._event_accumulators: dict[str, EventScoreAccumulatorV2] = {}
        self._event_score_input_receipts: dict[tuple[str, str], EventScoreInputReceiptV2] = {}
        self._plugins: dict[str, tuple[TrustedMissionPluginFactoryV2, Any]] = {}
        self._plugin_output_receipts: list[dict[str, Any]] = []
        self._authorized_plugin_factories: dict[str, TrustedMissionPluginFactoryV2] = {}
        self._fact_hash = world.mission_fact_snapshot(tick=int(world.tick)).fact_hash
        self._resolved_rule_evidence = tuple(
            _resolved_plain(_record_mapping(item)) for item in resolved.mission_rules
        )
        self._resolved_scoring_evidence = (
            None if resolved.scoring is None else _resolved_plain(_record_mapping(resolved.scoring))
        )
        self._mission_definition_hash = _canonical_hash(
            {
                # Canonical (sorted) order: the checkpoint stores
                # ``resolved_mission_states`` sorted, and ``validate_integrity``
                # recomputes this hash from that stored field.  Hashing the raw
                # declaration order makes the checkpoint self-inconsistent for
                # any scenario that declares its mission states unsorted.
                "states": tuple(sorted(resolved.mission_states)),
                "rules": self._resolved_rule_evidence,
                "scoring": self._resolved_scoring_evidence,
            }
        )

    @classmethod
    def from_resolved(
        cls,
        *,
        resolved: ResolvedScenarioV2,
        world: Any,
        expected_resolved_hash: str,
    ) -> MissionEngineV2:
        resolved.validate_integrity()
        if (
            expected_resolved_hash != resolved.resolved_hash
            or getattr(world, "resolved_hash", None) != resolved.resolved_hash
        ):
            raise ValueError("mission runtime anchors differ from Resolved and World")
        return cls(resolved=resolved, world=world)

    def _snapshot(self, tick: int) -> MissionEvaluationSnapshotV2:
        # Built-in mission conditions consume current entity/contact/resource
        # facts and authoritative event identities, not the recursively
        # serialised historical receipt payload.  Trusted scoring plugins may
        # inspect that audit evidence, so retain it whenever one is installed.
        facts = self._world.mission_fact_snapshot(
            tick=tick,
            include_event_receipts=bool(self._plugins),
        )
        self._fact_hash = facts.fact_hash
        return MissionEvaluationSnapshotV2(
            tick=facts.tick,
            entity_states=facts.entity_states,
            zone_membership=facts.zone_membership,
            event_ids=facts.event_ids,
            mission_states=tuple(sorted(self._states)),
            contacts=facts.contacts,
            communications=facts.communications,
            resources=facts.resources,
            scores=MappingProxyType(dict(sorted(self._score_state.items()))),
            zone_transitions=facts.zone_transitions,
            selection_evidence=facts.selection_evidence,
            contact_facts=facts.contact_facts,
            resource_facts=facts.resource_facts,
            wave_lifecycle=facts.wave_lifecycle,
            zone_activation=facts.zone_activation,
        )

    def install_plugin(
        self,
        *,
        plugin_id: str,
        factory: TrustedMissionPluginFactoryV2,
        session_id: str,
        seed: int,
    ) -> MissionPluginCheckpointV2:
        declared = () if self._resolved.scoring is None else self._resolved.scoring.metrics
        metric = next((item for item in declared if str(item.id) == plugin_id), None)
        plugin_ref = None if metric is None else metric.get("plugin_ref")
        raw_evidence = None if metric is None else metric.get("plugin_evidence")
        evidence = None if raw_evidence is None else _record_mapping(raw_evidence)
        if (
            not plugin_id
            or plugin_id in self._plugins
            or metric is None
            or plugin_ref is None
            or not isinstance(evidence, Mapping)
            or factory.plugin_ref != plugin_ref
            or factory.artifact_sha256 != evidence.get("artifact_sha256")
            or factory.interface_version != evidence.get("interface_version")
            or factory.deterministic != evidence.get("deterministic")
            or factory.trusted != evidence.get("trusted")
            or self._authorized_plugin_factories.get(plugin_id) is not factory
        ):
            raise ValueError("mission plugin identity is absent or already installed")
        plugin = factory.create(session_id=session_id, seed=seed)
        try:
            checkpoint = factory.checkpoint(plugin)
        except Exception:
            close = getattr(plugin, "close", None)
            if callable(close):
                with suppress(Exception):
                    close()
            raise
        self._plugins[plugin_id] = (factory, plugin)
        return checkpoint

    def _bind_resolved_plugin_factories(
        self, factories: Mapping[str, TrustedMissionPluginFactoryV2]
    ) -> None:
        expected = {
            str(item.id)
            for item in (() if self._resolved.scoring is None else self._resolved.scoring.metrics)
            if item.get("plugin_ref") is not None
        }
        if self._authorized_plugin_factories or set(factories) != expected:
            raise ValueError("mission plugin factories differ from Resolved scoring bindings")
        self._authorized_plugin_factories = dict(factories)

    def close_plugins(self) -> tuple[str, ...]:
        """Close every session-owned plugin and return stable cleanup diagnostics."""

        errors: list[str] = []
        for plugin_id, (_factory, plugin) in reversed(tuple(sorted(self._plugins.items()))):
            close = getattr(plugin, "close", None)
            if not callable(close):
                continue
            try:
                close()
            except Exception as error:
                errors.append(f"{plugin_id}:{type(error).__name__}:{error}")
        self._plugins.clear()
        return tuple(errors)

    @property
    def event_score_policy_event_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    str(item.event_source.event_id)
                    for item in (
                        () if self._resolved.scoring is None else self._resolved.scoring.metrics
                    )
                    if item.get("event_source") is not None
                }
            )
        )

    @staticmethod
    def _event_score_value(receipt: Mapping[str, Any], value_path: str) -> float:
        value: Any = receipt
        for component in value_path.split("."):
            if not isinstance(value, Mapping) or component not in value:
                raise ValueError("World event receipt lacks the Resolved score value path")
            value = value[component]
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
        ):
            raise ValueError("World event score value must be finite numeric evidence")
        return float(value)

    def apply_authoritative_event(
        self,
        *,
        event_receipt: Any,
    ) -> tuple[EventScoreReceiptV2, ...]:
        """Consume only a World-owned typed receipt under exact Resolved score policies."""

        from openmdbench.world.factory_v2 import TypedEventExecutionReceiptV2

        if not isinstance(event_receipt, TypedEventExecutionReceiptV2):
            raise TypeError("event scoring requires TypedEventExecutionReceiptV2")
        validate = getattr(self._world, "authoritative_typed_event_receipt", None)
        if not callable(validate):
            raise ValueError("event scoring requires a World receipt authority")
        authoritative = validate(event_receipt)
        source_record = _plain(authoritative)
        event_id = str(source_record.get("event_id", ""))
        event_type = str(source_record.get("event_type", ""))
        tick = source_record.get("tick")
        if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
            raise ValueError("authoritative World event tick is invalid")
        policies = tuple(
            item
            for item in (() if self._resolved.scoring is None else self._resolved.scoring.metrics)
            if item.get("event_source") is not None
            and item.event_source.event_id == event_id
            and item.event_source.event_type == event_type
        )
        if not policies:
            raise ValueError("World event has no exact Resolved scoring policy")
        results: list[EventScoreReceiptV2] = []
        for metric in sorted(policies, key=lambda item: item.id):
            policy = cast(dict[str, Any], _resolved_plain(metric.event_source))
            value = self._event_score_value(source_record, str(policy["value_path"]))
            input_payload: dict[str, Any] = {
                "metric_id": str(metric.id),
                "event_id": event_id,
                "event_type": event_type,
                "tick": tick,
                "value_path": str(policy["value_path"]),
                "value": value,
                "unit": str(policy["unit"]),
                "aggregation": str(policy["aggregation"]),
                "resolved_policy": policy,
                "resolved_policy_hash": _canonical_hash(policy),
                "world_event_receipt": source_record,
                "world_event_receipt_hash": _canonical_hash(source_record),
            }
            input_payload["input_hash"] = _canonical_hash(input_payload)
            input_receipt = EventScoreInputReceiptV2.model_validate(input_payload)
            key = (input_receipt.metric_id, input_receipt.event_id)
            prior = self._event_score_input_receipts.get(key)
            if prior is not None and prior != input_receipt:
                raise ValueError("event score identity conflicts with prior authoritative input")
            accumulator = self._event_accumulators.get(input_receipt.metric_id)
            if accumulator is None:
                accumulator = EventScoreAccumulatorV2(
                    metric_id=input_receipt.metric_id,
                    unit=input_receipt.unit,
                )
                self._event_accumulators[input_receipt.metric_id] = accumulator
            elif accumulator.unit != input_receipt.unit:
                raise ValueError("event score unit differs from Resolved accumulator")
            result = accumulator.apply(
                event_id=input_receipt.event_id,
                value=input_receipt.value,
                tick=input_receipt.tick,
                source_evidence_hash=input_receipt.input_hash,
            )
            self._event_score_input_receipts[key] = input_receipt
            results.append(result)
        # Event-score accumulation needs the current World-owned fact anchor,
        # but built-in score policies do not consume serialised historical
        # receipt payloads.  Rebuilding that immutable audit history here for
        # every scoreable event makes long matches progressively slower.  Full
        # receipt evidence remains available to public snapshots and is
        # deliberately re-anchored by snapshot_state() for checkpoints.
        self._fact_hash = self._world.mission_fact_snapshot(
            tick=int(getattr(self._world, "tick", 0)),
            include_event_receipts=False,
        ).fact_hash
        return tuple(results)

    @staticmethod
    def _selected_entity_ids(rule: Any, snapshot: MissionEvaluationSnapshotV2) -> tuple[str, ...]:
        if not snapshot.selection_evidence:
            return tuple(rule.selector_resolution.entity_ids)
        raw = rule.condition.selector.values
        selector = RuntimeSelectorV2(
            selector_id=f"{rule.id}.runtime",
            entity_ids=tuple(raw.get("entity_ids", ())),
            faction_ids=tuple(raw.get("factions", ())),
            platform_refs=tuple(raw.get("platforms", ())),
            domains=tuple(raw.get("domains", ())),
            controller_ids=tuple(raw.get("controllers", ())),
            tags=tuple(raw.get("tags", ())),
            capabilities=tuple(raw.get("capabilities", ())),
            # Carry the declarative lifecycle filter through to the runtime
            # selector.  Omitting it silently restored the default (which includes
            # ``disabled``), so a rule such as "no enemy combat power left" could
            # not fire while a merely disabled unit was still on the field.
            include_lifecycle=tuple(raw.get("include_lifecycle", ())) or (
                RuntimeSelectorV2.model_fields["include_lifecycle"].default
            ),
        )
        return tuple(
            item.entity_id for item in snapshot.selection_evidence if selector.accepts(item)
        )

    def _condition(self, rule: Any, snapshot: MissionEvaluationSnapshotV2) -> bool:
        condition = rule.condition
        operator = str(condition.operator)
        if operator not in MISSION_CONDITION_OPERATORS_V2:
            raise ValueError("resolved mission condition operator is unsupported")
        parameters = condition.parameters.values
        selected = self._selected_entity_ids(rule, snapshot)
        return self._condition_expression(operator, parameters, selected, snapshot)

    def _condition_expression(
        self,
        operator: str,
        parameters: Mapping[str, Any],
        selected: tuple[str, ...],
        snapshot: MissionEvaluationSnapshotV2,
    ) -> bool:
        if operator == "count":
            zone_id = parameters.get("zone_id")
            active = sum(
                snapshot.entity_states[item]["lifecycle"] != "destroyed"
                and (zone_id is None or str(zone_id) in snapshot.zone_membership.get(item, ()))
                for item in selected
                if item in snapshot.entity_states
            )
            return _compare(
                float(active), str(parameters["comparison"]), float(parameters["value"])
            )
        if operator == "survival":
            active = sum(
                snapshot.entity_states[item]["lifecycle"] != "destroyed"
                for item in selected
                if item in snapshot.entity_states
            )
            return _compare(
                float(active), str(parameters["comparison"]), float(parameters["value"])
            )
        if operator == "state":
            return str(parameters["state"]) in snapshot.mission_states
        if operator == "event":
            return str(parameters["event_id"]) in snapshot.event_ids
        if operator == "time":
            return _compare(
                float(snapshot.tick), str(parameters["comparison"]), float(parameters["tick"])
            )
        if operator == "zone":
            zone_id = str(parameters["zone_id"])
            if not snapshot.zone_activation.get(zone_id, True):
                return False
            selected_set = set(selected)
            transition = str(parameters.get("transition", "entered"))
            swept = any(
                item.transition == transition
                and item.zone_id == zone_id
                and item.entity_id in selected_set
                and item.tick == snapshot.tick
                for item in snapshot.zone_transitions
            )
            inside = any(zone_id in snapshot.zone_membership.get(item, ()) for item in selected)
            if transition == "inside":
                return inside
            if transition == "outside":
                return any(
                    zone_id not in snapshot.zone_membership.get(item, ()) for item in selected
                )
            return swept or (transition == "entered" and inside)
        if operator == "contact":
            maximum_age = int(parameters.get("maximum_age_ticks", snapshot.tick))
            count = sum(
                1
                for fact in snapshot.contact_facts
                if fact.owner_entity_id in selected
                and fact.is_valid(
                    expected_tick=snapshot.tick,
                    owner_entity_id=fact.owner_entity_id,
                )
                and snapshot.tick - fact.observed_tick <= maximum_age
            )
            return count >= int(parameters["minimum_count"])
        if operator == "communication":
            owner = parameters.get("owner_entity_id")
            messages = (
                snapshot.communications
                if owner is None
                else tuple(
                    item
                    for item in snapshot.communications
                    if item.get("sender_entity_id") == owner
                )
            )
            return len(messages) >= int(parameters["minimum_count"])
        if operator == "resource":
            matching = tuple(
                fact
                for fact in snapshot.resource_facts
                if fact.entity_id in selected
                and fact.resource_ref == str(parameters["resource_ref"])
                and fact.field == str(parameters.get("field", ""))
                and fact.unit == str(parameters.get("unit", ""))
            )
            total = math.fsum(item.value for item in matching)
            return _compare(total, str(parameters["comparison"]), float(parameters["value"]))
        if operator == "score":
            value = snapshot.scores.get(str(parameters["metric_id"]))
            return value is not None and _compare(
                value, str(parameters["comparison"]), float(parameters["value"])
            )
        if operator == "wave":
            wave_id = str(parameters["wave_id"])
            return snapshot.wave_lifecycle.get(wave_id) == "applied"
        conditions = tuple(parameters.get("conditions", ()))
        results = tuple(
            (
                item in self._rule_ledger
                if isinstance(item, str)
                else self._condition_expression(
                    str(item.operator), item.parameters.values, selected, snapshot
                )
            )
            for item in conditions
        )
        if operator == "all":
            return all(results)
        if operator == "any":
            return any(results)
        return not any(results)

    def evaluate_tick(self, *, expected_tick: int, operation_id: str) -> MissionTickReceiptV2:
        fingerprint = _canonical_hash([expected_tick, operation_id, self.resolved_hash])
        prior = self._operation_receipts.get(operation_id)
        if prior is not None:
            if prior[0] != fingerprint:
                raise ValueError("mission operation identity conflicts with prior evidence")
            return prior[1]
        snapshot = self._snapshot(expected_tick)
        if expected_tick != getattr(self._world, "tick", None):
            raise ValueError("mission expected tick differs from World")
        triggered: list[tuple[int, str, Any]] = []
        for rule in self._resolved.mission_rules:
            dependencies = tuple(getattr(rule, "depends_on", ()))
            if (
                hasattr(rule, "selector_resolution")
                and all(item in self._rule_ledger for item in dependencies)
                and self._condition(rule, snapshot)
            ):
                triggered.append((int(rule.priority), str(rule.id), rule))
        emitted: list[str] = []
        for _priority, identifier, rule in sorted(triggered, key=lambda item: (-item[0], item[1])):
            state = str(rule.outcome.set_state)
            self._states.add(state)
            event_id = str(rule.outcome.emit_event)
            emitted.append(event_id)
            self._rule_ledger[identifier] = {
                "tick": expected_tick,
                "state": state,
                "event_id": event_id,
                "snapshot_hash": _canonical_hash(snapshot),
            }
        terminal_rules = tuple(
            (priority, identifier, rule)
            for priority, identifier, rule in triggered
            if bool(rule.outcome.terminal)
        )
        if self._terminal_result is None and terminal_rules:
            self._terminal_result = select_terminal_result_v2(
                tuple(
                    TerminalCandidateV2(
                        rule_id=identifier,
                        priority=priority,
                        event_id=str(rule.outcome.emit_event),
                        result=str(rule.outcome.result),
                        ranking=_record_mapping(rule.outcome.ranking),
                    )
                    for priority, identifier, rule in terminal_rules
                ),
                tick=expected_tick,
            )
        receipt = MissionTickReceiptV2(
            tick=expected_tick,
            operation_id=operation_id,
            triggered_rule_ids=tuple(sorted(identifier for _, identifier, _ in triggered)),
            mission_states=tuple(sorted(self._states)),
            emitted_event_ids=tuple(sorted(set(emitted))),
            terminal_result=self._terminal_result,
            snapshot_hash=_canonical_hash(snapshot),
        )
        self._operation_receipts[operation_id] = (fingerprint, receipt)
        return receipt

    def evaluate_scoring(self, *, expected_tick: int, operation_id: str) -> ScoreReceiptV2:
        fingerprint = _canonical_hash([expected_tick, operation_id, self.resolved_hash])
        prior = self._score_receipts.get(operation_id)
        if prior is not None:
            if prior[0] != fingerprint:
                raise ValueError("score operation identity conflicts with prior evidence")
            return prior[1]
        if expected_tick != getattr(self._world, "tick", None):
            raise ValueError("score expected tick differs from World")
        declared = () if self._resolved.scoring is None else self._resolved.scoring.metrics
        declared_metric_ids = {str(item.id) for item in declared}
        dynamic_values = {
            metric_id: accumulator.value
            for metric_id, accumulator in self._event_accumulators.items()
            if metric_id in declared_metric_ids
        }
        missing_metric_inputs: dict[str, tuple[str, ...]] = {}
        missing_metric_sources: dict[str, str] = {}
        if self._plugins:
            snapshot = self._snapshot(expected_tick)
            for plugin_id, (_factory, plugin) in sorted(self._plugins.items()):
                evaluate = getattr(plugin, "evaluate", None)
                if not callable(evaluate):
                    raise ValueError("mission plugin lacks deterministic evaluate protocol")
                factory = self._plugins[plugin_id][0]
                state_before = factory.checkpoint(plugin)
                input_snapshot = _plain(snapshot)
                produced = evaluate(snapshot)
                if not isinstance(produced, Mapping) or set(produced) != {plugin_id}:
                    raise ValueError("mission plugin score output must be a mapping")
                for metric_id, value in produced.items():
                    if metric_id not in {str(item.id) for item in declared} or (
                        value is not None
                        and (
                            not isinstance(value, (int, float))
                            or isinstance(value, bool)
                            or not math.isfinite(float(value))
                        )
                    ):
                        raise ValueError(
                            f"mission plugin {plugin_id} returned invalid score evidence"
                        )
                    dynamic_values[str(metric_id)] = 0.0 if value is None else float(value)
                    output_value = None if value is None else float(value)
                    state_after = factory.checkpoint(plugin)
                    output_evidence = {
                        "operation_id": operation_id,
                        "plugin_id": plugin_id,
                        "metric_id": str(metric_id),
                        "tick": expected_tick,
                        "input_fact_hash": self._fact_hash,
                        "input_snapshot": input_snapshot,
                        "input_snapshot_hash": _canonical_hash(input_snapshot),
                        "plugin_state_hash_before": state_before.state_hash,
                        "output_value": output_value,
                        "plugin_state_hash_after": state_after.state_hash,
                        "sequence": len(self._plugin_output_receipts),
                    }
                    output_evidence["output_hash"] = _canonical_hash(output_evidence)
                    self._plugin_output_receipts.append(output_evidence)
                    if value is None:
                        missing_metric_inputs[str(metric_id)] = (f"plugin_output:{plugin_id}",)
                        missing_metric_sources[str(metric_id)] = str(output_evidence["output_hash"])
        metrics = tuple(
            ScoreInputV2(
                metric_id=str(item.id),
                value=(
                    dynamic_values[str(item.id)]
                    if str(item.id) in dynamic_values
                    else None
                    if not item.available
                    else float(item.value)
                ),
                weight=float(item.weight),
                unit=str(item.unit),
                aggregation=cast(
                    Literal["sum", "mean", "min", "max", "count"],
                    str(item.aggregation),
                ),
                direction=cast(Literal["maximize", "minimize"], str(item.direction)),
                normalization_lower_bound=(
                    None
                    if item.get("normalization") is None
                    else float(item.normalization.lower_bound)
                ),
                normalization_upper_bound=(
                    None
                    if item.get("normalization") is None
                    else float(item.normalization.upper_bound)
                ),
                not_applicable_reason=item.get("not_applicable_reason"),
                missing_inputs=missing_metric_inputs.get(str(item.id), ()),
                missing_evidence_source=missing_metric_sources.get(str(item.id)),
            )
            for item in declared
        )
        aggregation = (
            "sum" if self._resolved.scoring is None else self._resolved.scoring.aggregation
        )
        direction = (
            "maximize" if self._resolved.scoring is None else self._resolved.scoring.direction
        )
        aggregation_version = (
            LEGACY_AGGREGATION_VERSION_V1
            if self._resolved.scoring is None
            else self._resolved.scoring.get("aggregation_version", LEGACY_AGGREGATION_VERSION_V1)
        )
        receipt = ScoringSystemV2.evaluate(
            metrics,
            aggregation=cast(Literal["sum", "mean", "min", "max", "count"], aggregation),
            direction=cast(Literal["maximize", "minimize"], direction),
            aggregation_version=str(aggregation_version),
            mission_outcome=self._terminal_result,
            tick=expected_tick,
            operation_id=operation_id,
        )
        self._score_state = dict(receipt.competition_scores)
        self._score_ledger[operation_id] = {
            "tick": expected_tick,
            "total": receipt.total,
            "metrics": dict(receipt.competition_scores),
        }
        self._score_receipts[operation_id] = (fingerprint, receipt)
        return receipt

    def presentation_snapshot(self) -> Mapping[str, Any]:
        """Return only current display fields without encoding a checkpoint."""

        return MappingProxyType(
            {
                "mission_states": tuple(sorted(self._states)),
                "terminal_result": (
                    None if self._terminal_result is None else _plain(self._terminal_result)
                ),
                "score_state": dict(sorted(self._score_state.items())),
            }
        )

    def snapshot_state(self) -> MissionScoringCheckpointV2:
        self._fact_hash = self._world.mission_fact_snapshot(
            tick=int(getattr(self._world, "tick", 0))
        ).fact_hash
        payload: dict[str, Any] = {
            "resolved_hash": self.resolved_hash,
            "tick": int(getattr(self._world, "tick", 0)),
            "mission_states": tuple(sorted(self._states)),
            "terminal_result": None
            if self._terminal_result is None
            else _plain(self._terminal_result),
            "rule_ledger": tuple(
                {"rule_id": key, **value} for key, value in sorted(self._rule_ledger.items())
            ),
            "score_state": dict(sorted(self._score_state.items())),
            "score_ledger": tuple(
                {"operation_id": key, **value} for key, value in sorted(self._score_ledger.items())
            ),
            "operation_receipts": tuple(
                sorted(
                    (
                        *(
                            {
                                "kind": "mission",
                                "operation_id": key,
                                "fingerprint": fingerprint,
                                "receipt": _plain(receipt),
                            }
                            for key, (fingerprint, receipt) in self._operation_receipts.items()
                        ),
                        *(
                            {
                                "kind": "score",
                                "operation_id": key,
                                "fingerprint": fingerprint,
                                "receipt": _plain(receipt),
                            }
                            for key, (fingerprint, receipt) in self._score_receipts.items()
                        ),
                    ),
                    key=lambda item: (item["kind"], item["operation_id"]),
                )
            ),
            "event_accumulators": tuple(
                accumulator.checkpoint()
                for _metric_id, accumulator in sorted(self._event_accumulators.items())
            ),
            "event_score_input_receipts": tuple(
                receipt.model_dump(mode="json")
                for _key, receipt in sorted(self._event_score_input_receipts.items())
            ),
            "plugin_states": tuple(
                {
                    "plugin_id": plugin_id,
                    "checkpoint": factory.checkpoint(plugin).model_dump(mode="json"),
                }
                for plugin_id, (factory, plugin) in sorted(self._plugins.items())
            ),
            "plugin_output_receipts": tuple(self._plugin_output_receipts),
            "fact_hash": self._fact_hash,
            "mission_definition_hash": self._mission_definition_hash,
            "resolved_mission_states": tuple(sorted(self._resolved.mission_states)),
            "resolved_metric_ids": tuple(
                sorted(
                    str(item.id)
                    for item in (
                        () if self._resolved.scoring is None else self._resolved.scoring.metrics
                    )
                )
            ),
            "resolved_mission_rules": self._resolved_rule_evidence,
            "resolved_scoring": self._resolved_scoring_evidence,
            "checkpoint_hash": "sha256:" + "0" * 64,
        }
        payload["checkpoint_hash"] = MissionScoringCheckpointV2.compute_hash(payload)
        return MissionScoringCheckpointV2.model_validate(payload)

    checkpoint = snapshot_state

    def restore_state(self, checkpoint: MissionScoringCheckpointV2) -> None:
        checkpoint.validate_integrity()
        if (
            checkpoint.resolved_hash != self.resolved_hash
            or checkpoint.mission_definition_hash != self._mission_definition_hash
            or checkpoint.resolved_mission_states != tuple(sorted(self._resolved.mission_states))
            or checkpoint.resolved_metric_ids
            != tuple(
                sorted(
                    str(item.id)
                    for item in (
                        () if self._resolved.scoring is None else self._resolved.scoring.metrics
                    )
                )
            )
        ):
            raise ValueError("mission scoring checkpoint Resolved anchor mismatch")
        self._states = set(checkpoint.mission_states)
        self._terminal_result = (
            None
            if checkpoint.terminal_result is None
            else TerminalMissionResultV2(**checkpoint.terminal_result)
        )
        self._rule_ledger = {
            str(item["rule_id"]): {key: value for key, value in item.items() if key != "rule_id"}
            for item in checkpoint.rule_ledger
        }
        self._score_state = dict(checkpoint.score_state)
        self._score_ledger = {
            str(item["operation_id"]): {
                key: value for key, value in item.items() if key != "operation_id"
            }
            for item in checkpoint.score_ledger
        }
        self._event_accumulators = {
            str(item["metric_id"]): EventScoreAccumulatorV2.restore(item)
            for item in checkpoint.event_accumulators
        }
        self._event_score_input_receipts = {
            (receipt.metric_id, receipt.event_id): receipt
            for receipt in (
                EventScoreInputReceiptV2.model_validate(item)
                for item in checkpoint.event_score_input_receipts
            )
        }
        validate_event = getattr(self._world, "authoritative_typed_event_receipt", None)
        if self._event_score_input_receipts and not callable(validate_event):
            raise ValueError("event score restore requires World receipt authority")
        for event_input in self._event_score_input_receipts.values():
            authoritative = cast(Any, validate_event)(event_input.world_event_receipt)
            if _canonical_hash(authoritative) != event_input.world_event_receipt_hash:
                raise ValueError("event score input differs from authoritative World receipt")
        restored_plugins: dict[str, tuple[TrustedMissionPluginFactoryV2, Any]] = {}
        expected_plugin_ids = {
            str(metric.id)
            for metric in (() if self._resolved.scoring is None else self._resolved.scoring.metrics)
            if metric.get("plugin_ref") is not None
        }
        if {str(item["plugin_id"]) for item in checkpoint.plugin_states} != expected_plugin_ids:
            raise ValueError("mission plugin checkpoint differs from Resolved scoring bindings")
        for item in checkpoint.plugin_states:
            plugin_id = str(item["plugin_id"])
            installed = self._plugins.get(plugin_id)
            if installed is None:
                raise ValueError(
                    "mission plugin restore requires its installed trusted session factory"
                )
            factory, plugin = installed
            plugin_checkpoint = MissionPluginCheckpointV2.model_validate(item["checkpoint"])
            if (
                plugin_checkpoint.plugin_ref != factory.plugin_ref
                or plugin_checkpoint.artifact_sha256 != factory.artifact_sha256
            ):
                raise ValueError("mission plugin checkpoint differs from trusted factory")
            replay_plugin = factory.create(
                session_id=str(getattr(self._world, "session_id", "session.default")),
                seed=int(getattr(self._world, "_session_seed", 0)),
            )
            try:
                for output in (
                    record
                    for record in checkpoint.plugin_output_receipts
                    if record["plugin_id"] == plugin_id
                ):
                    replay_before = factory.checkpoint(replay_plugin)
                    if replay_before.state_hash != output["plugin_state_hash_before"]:
                        raise ValueError("fresh mission plugin replay state-before mismatch")
                    input_snapshot = _evaluation_snapshot_from_evidence(output["input_snapshot"])
                    evaluate = getattr(replay_plugin, "evaluate", None)
                    if not callable(evaluate):
                        raise ValueError("mission plugin lacks deterministic replay protocol")
                    replay_output = evaluate(input_snapshot)
                    if (
                        not isinstance(replay_output, Mapping)
                        or set(replay_output) != {plugin_id}
                        or replay_output[plugin_id] != output["output_value"]
                    ):
                        raise ValueError("fresh mission plugin output replay mismatch")
                    replay_after = factory.checkpoint(replay_plugin)
                    if replay_after.state_hash != output["plugin_state_hash_after"]:
                        raise ValueError("fresh mission plugin replay state-after mismatch")
                if factory.checkpoint(replay_plugin).state_hash != plugin_checkpoint.state_hash:
                    raise ValueError("fresh mission plugin replay final state mismatch")
            finally:
                close_replay = getattr(replay_plugin, "close", None)
                if callable(close_replay):
                    with suppress(Exception):
                        close_replay()
            restore = getattr(plugin, "restore", None)
            if not callable(restore):
                raise ValueError("mission plugin lacks checkpoint restore protocol")
            restore(_plain(plugin_checkpoint.session_state))
            restored_plugins[plugin_id] = installed
        self._plugins = restored_plugins
        self._plugin_output_receipts = [dict(item) for item in checkpoint.plugin_output_receipts]
        self._fact_hash = checkpoint.fact_hash
        self._operation_receipts = {}
        self._score_receipts = {}
        for item in checkpoint.operation_receipts:
            raw = item["receipt"]
            if item.get("kind") == "score":
                terminal = raw.get("mission_outcome")
                score_receipt = ScoreReceiptV2(
                    metrics=tuple(ScoreInputV2.model_validate(value) for value in raw["metrics"]),
                    total=raw["total"],
                    effective_weights=MappingProxyType(dict(raw["effective_weights"])),
                    aggregation=str(raw["aggregation"]),
                    direction=str(raw["direction"]),
                    aggregation_version=str(
                        raw.get("aggregation_version", LEGACY_AGGREGATION_VERSION_V1)
                    ),
                    metric_receipts=tuple(
                        MetricScoreReceiptV2(**value) for value in raw.get("metric_receipts", ())
                    ),
                    metric_data_missing=tuple(
                        MetricDataMissingReceiptV2(**value)
                        for value in raw.get("metric_data_missing", ())
                    ),
                    metric_value_out_of_range=tuple(
                        MetricValueOutOfRangeReceiptV2(**value)
                        for value in raw.get("metric_value_out_of_range", ())
                    ),
                    mission_outcome=(
                        None if terminal is None else TerminalMissionResultV2(**terminal)
                    ),
                    competition_scores=MappingProxyType(dict(raw["competition_scores"])),
                    training_rewards=MappingProxyType(dict(raw["training_rewards"])),
                    tick=raw.get("tick"),
                    operation_id=raw.get("operation_id"),
                )
                self._score_receipts[str(item["operation_id"])] = (
                    str(item["fingerprint"]),
                    score_receipt,
                )
                continue
            terminal = raw.get("terminal_result")
            mission_receipt = MissionTickReceiptV2(
                tick=int(raw["tick"]),
                operation_id=str(raw["operation_id"]),
                triggered_rule_ids=tuple(raw["triggered_rule_ids"]),
                mission_states=tuple(raw["mission_states"]),
                emitted_event_ids=tuple(raw["emitted_event_ids"]),
                terminal_result=(None if terminal is None else TerminalMissionResultV2(**terminal)),
                snapshot_hash=str(raw["snapshot_hash"]),
            )
            self._operation_receipts[str(item["operation_id"])] = (
                str(item["fingerprint"]),
                mission_receipt,
            )

    @classmethod
    def restore_checkpoint(
        cls,
        *,
        checkpoint: MissionScoringCheckpointV2,
        resolved: ResolvedScenarioV2,
        world: Any,
        expected_resolved_hash: str,
        expected_checkpoint_hash: str,
        plugin_factories: Mapping[str, TrustedMissionPluginFactoryV2] | None = None,
        session_id: str | None = None,
        seed: int | None = None,
    ) -> MissionEngineV2:
        if checkpoint.checkpoint_hash != expected_checkpoint_hash:
            raise ValueError("mission scoring checkpoint external anchor mismatch")
        if checkpoint.tick != getattr(world, "tick", None):
            raise ValueError("mission scoring checkpoint World tick anchor mismatch")
        engine = cls.from_resolved(
            resolved=resolved,
            world=world,
            expected_resolved_hash=expected_resolved_hash,
        )
        if checkpoint.plugin_states:
            if plugin_factories is None or session_id is None or seed is None:
                raise ValueError(
                    "mission plugin restore requires explicit trusted session factories"
                )
            engine._bind_resolved_plugin_factories(plugin_factories)
            for item in checkpoint.plugin_states:
                plugin_id = str(item["plugin_id"])
                factory = plugin_factories.get(plugin_id)
                if factory is None:
                    raise ValueError("mission plugin restore factory is absent")
                plugin_checkpoint = MissionPluginCheckpointV2.model_validate(item["checkpoint"])
                if (
                    plugin_checkpoint.plugin_ref != factory.plugin_ref
                    or plugin_checkpoint.artifact_sha256 != factory.artifact_sha256
                ):
                    raise ValueError("mission plugin restore evidence differs from factory")
                engine.install_plugin(
                    plugin_id=plugin_id,
                    factory=factory,
                    session_id=session_id,
                    seed=seed,
                )
        engine.restore_state(checkpoint)
        if world.mission_fact_snapshot(tick=world.tick).fact_hash != checkpoint.fact_hash:
            raise ValueError("mission scoring checkpoint fact anchor mismatch")
        return engine


__all__ = [
    "MISSION_CONDITION_OPERATORS_V2",
    "CompiledSelectorV2",
    "EntitySelectionEvidenceV2",
    "EventScoreAccumulatorV2",
    "EventScoreInputReceiptV2",
    "EventScoreReceiptV2",
    "MissionEngineV2",
    "MissionEvaluationSnapshotV2",
    "MissionFactSnapshotV2",
    "MissionContactFactV2",
    "MissionPluginCheckpointV2",
    "MissionResourceFactV2",
    "MissionScoringCheckpointV2",
    "MissionTickReceiptV2",
    "MissionVisibilityViewV2",
    "MetricScoreReceiptV2",
    "MetricDataMissingReceiptV2",
    "MetricValueOutOfRangeReceiptV2",
    "RuntimeSelectorV2",
    "ScoreInputV2",
    "ScoreReceiptV2",
    "ScoringSystemV2",
    "TerminalCandidateV2",
    "TerminalMissionResultV2",
    "TrustedMissionPluginFactoryV2",
    "ZoneTransitionEvidenceV2",
    "condition_schema_v2",
    "select_terminal_result_v2",
]
