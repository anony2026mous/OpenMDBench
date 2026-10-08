"""Map-authoritative terrain deployment and continuous coast-crossing contracts."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from openmdbench.scenarios.declarative_v2 import (
    CompilerErrorV2,
    ScenarioCompilerV2,
    ScenarioPackageV2,
)
from openmdbench.scenarios.formal_v2 import (
    compile_formal_scenario_v2,
    load_formal_scenario_v2,
)
from openmdbench.world.boundary_v2 import (
    BoundaryEntityV2,
    BoundarySystemV2,
    MotionSegmentV2,
)
from openmdbench.world.geography_v2 import GeographyServiceV2


def _entity(resolved: Any, entity_id: str) -> Any:
    return next(item for item in resolved.entities if item.id == entity_id)


def test_map_binding_materializes_domain_specific_terrain_deployments_and_roundtrips() -> None:
    resolved, _catalog = compile_formal_scenario_v2("MD-AD-002-MEDIUM")
    resolved = cast(Any, resolved)
    terrain_ids = tuple(zone.id for zone in resolved.world.zones if "terrain:land" in zone.tags)
    assert terrain_ids
    assert resolved.world.map_ref == "map.weihai-local@2.1.0"
    assert [item.exact_ref for item in resolved.world_resource_bindings] == [
        "damage.kinetic-partial@2.0.0",
        "effect.ciws-hit@2.0.0",
        "map.weihai-local@2.1.0",
    ]
    picket = _entity(resolved, "defender.picket-001")
    assert set(picket.boundary_deployment.excluded_zone_ids) == set(terrain_ids)
    assert set(_entity(resolved, "defender.shore-ew").boundary_deployment.allowed_zone_ids) == set(
        terrain_ids
    )
    assert _entity(resolved, "defender.interceptor-001").boundary_deployment is None
    recovered_world = type(resolved.world).from_mapping(resolved.world.model_dump())
    assert recovered_world.map_ref == resolved.world.map_ref
    assert recovered_world.zones == resolved.world.zones


@pytest.mark.parametrize(
    ("entity_id", "position_m", "expected_code"),
    (
        ("defender.picket-001", [-1057.0, 222.0, 0.0], "scenario.deployment_excluded"),
        ("defender.shore-ew", [2_000.0, -1_000.0, 0.0], "scenario.deployment_outside_allowed"),
    ),
)
def test_domain_incompatible_terrain_deployment_is_rejected_at_compile_time(
    entity_id: str, position_m: list[float], expected_code: str
) -> None:
    _package, catalog = load_formal_scenario_v2("MD-AD-002-MEDIUM")
    payload = yaml.safe_load(Path("scenarios/formal/md_ad_002_medium/scenario.yaml").read_bytes())
    document = copy.deepcopy(payload["scenario"])
    entity = next(item for item in document["entities"] if item["id"] == entity_id)
    entity["initial_state"]["position_m"] = position_m
    invalid = ScenarioPackageV2.from_mapping(
        {"schema_version": "package@2.0", "scenario": document}
    )
    with pytest.raises(CompilerErrorV2) as captured:
        ScenarioCompilerV2(catalog=catalog).compile(invalid)
    assert captured.value.code == expected_code


def test_surface_coast_crossing_stops_with_damage_while_air_can_overfly_land() -> None:
    resolved, _catalog = compile_formal_scenario_v2("MD-AD-002-MEDIUM")
    resolved = cast(Any, resolved)
    geography = GeographyServiceV2.from_resolved_scenario(resolved)
    surface = _entity(resolved, "defender.picket-001")
    air = _entity(resolved, "defender.interceptor-001")
    motion = MotionSegmentV2(
        start_m=(2_000.0, -1_000.0, 0.0),
        end_m=(0.0, -1_000.0, 0.0),
        dt_seconds=1.0,
    )
    surface_system = BoundarySystemV2.from_resolved(resolved, geography=geography)
    surface_system.register_entities(
        (
            BoundaryEntityV2.from_resolved(
                surface,
                resolved_scenario=resolved,
                expected_resolved_hash=resolved.resolved_hash,
            ),
        )
    )
    impact = surface_system.evaluate({surface.id: motion}, tick=1, tick_start_time_seconds=0.0)
    assert any(item.kind == "excluded_zone" for item in impact.boundary_events)
    assert impact.policy_actions[0].policy == "effect"
    assert impact.policy_actions[0].resolved_end_m != motion.end_m
    assert impact.policy_actions[0].resolved_velocity_mps == (0.0, 0.0, 0.0)
    assert impact.damage_intents[0].effect_ref == "effect.ciws-hit@2.0.0"
    air_system = BoundarySystemV2.from_resolved(resolved, geography=geography)
    air_system.register_entities(
        (
            BoundaryEntityV2.from_resolved(
                air,
                resolved_scenario=resolved,
                expected_resolved_hash=resolved.resolved_hash,
            ),
        )
    )
    overflight = air_system.evaluate(
        {
            air.id: MotionSegmentV2(
                start_m=(2_000.0, -1_000.0, 100.0),
                end_m=(0.0, -1_000.0, 100.0),
                dt_seconds=1.0,
            )
        },
        tick=1,
        tick_start_time_seconds=0.0,
    )
    assert not overflight.boundary_events
