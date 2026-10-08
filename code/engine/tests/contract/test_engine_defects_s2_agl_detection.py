"""EF-04 contracts for generic AGL altitude-range sensing."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from openmdbench.catalog.formal_v2 import load_md_ad_002_catalog_v2
from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
from openmdbench.sessions.formal_v2 import create_formal_session_v2
from openmdbench.systems.generic_v2 import (
    GenericSubsystemEngineV2,
    SensorContactReceiptV2,
    SubsystemEntityFactV2,
)
from openmdbench.world.geography_v2 import GeographyServiceV2


def _facts(
    *,
    target_z_m: float,
    target_surface_elevation_m: float | None = 0.0,
    target_x_m: float = 20_000.0,
    range_m: float = 40_000.0,
    profile: object | None = None,
) -> tuple[SubsystemEntityFactV2, SubsystemEntityFactV2]:
    sensor: dict[str, object] = {
        "exact_ref": "sensor.example@2.2.0",
        "range_m": range_m,
        "detection_probability": 1.0,
        "target_domains": ("air",),
    }
    if profile is not None:
        sensor["altitude_range_profile"] = profile
    return (
        SubsystemEntityFactV2(
            entity_id="entity.sensor",
            faction_id="faction.alpha",
            position_m=(0.0, 0.0, 0.0),
            velocity_mps=(0.0, 0.0, 0.0),
            energy=None,
            domain="surface",
            sensors=(sensor,),
        ),
        SubsystemEntityFactV2(
            entity_id="entity.target",
            faction_id="faction.beta",
            position_m=(target_x_m, 0.0, target_z_m),
            velocity_mps=(0.0, 0.0, 0.0),
            energy=None,
            domain="air",
            surface_elevation_m=target_surface_elevation_m,
        ),
    )


def _profile() -> dict[str, object]:
    return {
        "reference": "agl",
        "low_altitude_ceiling_m": 300.0,
        "low_altitude_range_m": 15_000.0,
        "nominal_range_m": 40_000.0,
        "transition": "step",
    }


def _contact(*, facts: tuple[SubsystemEntityFactV2, ...]) -> SensorContactReceiptV2:
    contacts = (
        GenericSubsystemEngineV2()
        .evaluate(entities=facts, tick=4, dt_seconds=1.0, seed=17, queued_message_count=0)
        .contacts
    )
    assert len(contacts) == 1
    return contacts[0]


@pytest.mark.parametrize(
    ("target_z_m", "expected_detected"),
    ((100.0, False), (300.0, False), (301.0, True)),
)
def test_step_profile_uses_target_agl_and_includes_300_m_in_low_band(
    target_z_m: float, expected_detected: bool
) -> None:
    """S2-01/S2-02: 20 km is inside nominal and outside the 15 km low band."""

    contact = _contact(facts=_facts(target_z_m=target_z_m, profile=_profile()))
    assert contact.target_agl_m == pytest.approx(target_z_m)
    assert contact.altitude_range_reference == "agl"
    assert contact.sensor_range_m == pytest.approx(15_000.0 if target_z_m <= 300 else 40_000.0)
    assert contact.detected is expected_detected
    if expected_detected:
        assert contact.sample is not None
    else:
        assert contact.sample is None
        assert contact.measurement_position_m is None


def test_agl_uses_explicit_local_surface_not_msl_or_sensor_relative_height() -> None:
    """S2-03: an absolute Z of 20 km can still be 100 m AGL above local terrain."""

    contact = _contact(
        facts=_facts(
            target_z_m=20_000.0,
            target_surface_elevation_m=19_900.0,
            profile=_profile(),
        )
    )
    assert contact.target_agl_m == pytest.approx(100.0)
    assert contact.sensor_range_m == pytest.approx(15_000.0)
    assert contact.detected is False


def test_profile_requires_surface_elevation_evidence_instead_of_treating_z_as_agl() -> None:
    """S2-03: a missing surface source fails closed for a profile that requires AGL."""

    with pytest.raises(ValueError, match="target AGL evidence"):
        _contact(
            facts=_facts(
                target_z_m=100.0,
                target_surface_elevation_m=None,
                profile=_profile(),
            )
        )


def test_sensor_without_altitude_profile_keeps_nominal_legacy_range_behavior() -> None:
    """S2-04: no implicit 300 m threshold applies to arbitrary sensors."""

    contact = _contact(
        facts=_facts(target_z_m=100.0, target_surface_elevation_m=None, profile=None)
    )
    assert contact.target_agl_m is None
    assert contact.altitude_range_reference is None
    assert contact.sensor_range_m == pytest.approx(40_000.0)
    assert contact.detected is True


def test_environment_multiplier_is_applied_after_profile_selection() -> None:
    """S2-05: the resolved nominal 0.5 multiplier makes the low band 7.5 km."""

    low = _contact(
        facts=_facts(target_z_m=100.0, target_x_m=19_000.0, range_m=20_000.0, profile=_profile())
    )
    high = _contact(
        facts=_facts(target_z_m=301.0, target_x_m=19_000.0, range_m=20_000.0, profile=_profile())
    )
    assert low.sensor_range_m == pytest.approx(7_500.0)
    assert high.sensor_range_m == pytest.approx(20_000.0)
    assert low.detected is False
    assert high.detected is True


def test_out_of_range_altitude_gate_does_not_sample_or_drift_other_named_substreams() -> None:
    """S2-06: the low-band rejection has no probability/measurement sample."""

    out_of_range = _contact(facts=_facts(target_z_m=100.0, profile=_profile()))
    in_range = _contact(facts=_facts(target_z_m=301.0, profile=_profile()))
    reordered = _contact(facts=tuple(reversed(_facts(target_z_m=301.0, profile=_profile()))))
    assert out_of_range.sample is None
    assert out_of_range.measurement_rng_substream == ""
    assert in_range.sample == reordered.sample
    assert in_range.measurement_position_m == reordered.measurement_position_m


@pytest.mark.parametrize("scenario_id", ("MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD"))
def test_formal_scenarios_bind_versioned_agl_sensors_and_explicit_weihai_surface(
    scenario_id: str,
) -> None:
    """S2-01/S2-03: exact Catalog identities carry both range and sea-level evidence."""

    resolved, catalog = compile_formal_scenario_v2(scenario_id)
    geography = GeographyServiceV2.from_resolved_scenario(cast(Any, resolved))
    assert geography.surface_elevation_m((0.0, 0.0, 123.0)) == pytest.approx(0.0)
    assert resolved.world.map_ref == "map.weihai-local@2.1.0"

    sensors = {
        binding.exact_ref: binding
        for entity in resolved.entities
        for binding in getattr(entity, "resource_bindings", {}).get("sensors", ())
        if binding.exact_ref.startswith(("sensor.shore-early-warning@", "sensor.picket-radar@"))
    }
    assert sensors and all(reference.endswith(("@2.0.1", "@2.1.1")) for reference in sensors)
    for binding in sensors.values():
        profile = binding.normalized_content["altitude_range_profile"]
        assert profile["reference"] == "agl"
        assert profile["low_altitude_ceiling_m"] == pytest.approx(300.0)
        assert profile["transition"] == "step"
        assert (
            binding.normalized_content["parameter_annotations"][
                "altitude_range_profile.low_altitude_ceiling_m"
            ]["fidelity"]
            == "UNVALIDATED_BENCHMARK"
        )

    assert catalog.resolve("maps", "map.weihai-local@2.1.0").content_hash.startswith("sha256:")


def test_old_sensor_and_map_versions_remain_available_without_new_profile_semantics() -> None:
    """S2-07: resource evolution is append-only and old references remain resolvable."""

    catalog = load_md_ad_002_catalog_v2()
    assert (
        "altitude_range_profile"
        not in catalog.resolve("sensors", "sensor.shore-early-warning@2.0.0").content
    )
    assert "surface_elevation" not in catalog.resolve("maps", "map.weihai-local@2.0.0").content

    for scenario_id in ("easy", "medium", "hard"):
        document = yaml.safe_load(
            (Path("scenarios/formal") / f"md_ad_002_{scenario_id}" / "scenario.yaml").read_bytes()
        )
        assert document["scenario"]["world"]["map_ref"] == "map.weihai-local@2.1.0"


def test_formal_agl_receipt_and_exact_catalog_evidence_survive_checkpoint_restore() -> None:
    """S2-07: the resolved profile identity and AGL receipt remain replay-auditable."""

    session = create_formal_session_v2("MD-AD-002-EASY", session_id="ef04.agl", seed=107)
    session.load().start()
    try:
        applied = session.step(operation_id="ef04.agl.tick.0", expected_tick=0)
        contacts = applied.world_receipt.subsystem_receipts[0].contacts
        agl_contacts = tuple(
            item
            for item in contacts
            if item.sensor_ref.startswith(
                ("sensor.shore-early-warning@2.0.1", "sensor.picket-radar@2.0.1")
            )
        )
        assert agl_contacts
        assert all(item.target_agl_m is not None for item in agl_contacts)
        assert all(item.altitude_range_reference == "agl" for item in agl_contacts)

        checkpoint = session.world_view.checkpoint()
        restored = session.world_factory.restore_checkpoint(
            checkpoint,
            resolved=session.resolved,
            model_registry=session.world_factory._model_registry,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
            expected_session_id=session.session_id,
            expected_seed=session.seed,
        )
        assert restored._world_tick_ledger["ef04.agl.tick.0"][1] == applied.world_receipt
        assert restored.checkpoint().checkpoint_hash == checkpoint.checkpoint_hash
        restored.close()
    finally:
        session.stop().close()
