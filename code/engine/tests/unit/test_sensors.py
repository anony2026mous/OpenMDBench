"""Cross-domain sensor, contact lifecycle, audit, and determinism tests."""

from openmdbench.core.entities import Domain, Side
from openmdbench.core.rng import SessionRNG
from openmdbench.systems.sensors import (
    DetectionEngine,
    Sensor,
    SensorKind,
    SensorPlatform,
    TargetTruth,
)
from openmdbench.systems.weather import Weather


def _uav_sensor() -> SensorPlatform:
    return SensorPlatform(
        platform_id="uav-blue",
        platform_type="uav",
        side=Side.BLUE,
        domain=Domain.AIR,
        position=(0.0, 0.0, 1000.0),
        sensor=Sensor("eo-blue", SensorKind.EO_IR, 15_000.0, 1.0),
    )


def test_cross_domain_detection_hides_truth_id_and_is_seed_deterministic() -> None:
    target = TargetTruth("red-usv-secret", Domain.SURFACE, (1000.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    first = DetectionEngine(SessionRNG(7))
    second = DetectionEngine(SessionRNG(7))
    first_tracks = first.scan(_uav_sensor(), (target,), tick=0, weather=Weather.CLEAR)
    second_tracks = second.scan(_uav_sensor(), (target,), tick=0, weather=Weather.CLEAR)
    assert first_tracks == second_tracks
    assert first_tracks[0].contact_id == "contact-blue-1"
    assert "red-usv-secret" not in repr(first_tracks[0])
    assert first.audit_log[0]["target_entity_id"] == "red-usv-secret"
    assert first.truth_by_contact() == {"contact-blue-1": "red-usv-secret"}


def test_normal_depth_auv_is_not_visible_to_surface_radar() -> None:
    radar = SensorPlatform(
        "blue-usv",
        "usv",
        Side.BLUE,
        Domain.SURFACE,
        (0.0, 0.0, 0.0),
        Sensor("radar-blue", SensorKind.RADAR, 20_000.0, 0.5),
    )
    auv = TargetTruth("red-auv", Domain.UNDERWATER, (100.0, 0.0, -50.0), (0.0, 0.0, 0.0))
    engine = DetectionEngine(SessionRNG(7))
    assert engine.scan(radar, (auv,), tick=0, weather=Weather.CLEAR) == ()


def test_lost_contact_uncertainty_increases_and_confidence_falls() -> None:
    target = TargetTruth("red-usv", Domain.SURFACE, (1000.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    engine = DetectionEngine(SessionRNG(7))
    detected = engine.scan(_uav_sensor(), (target,), tick=0, weather=Weather.CLEAR)[0]
    lost = engine.scan(_uav_sensor(), (), tick=1, weather=Weather.CLEAR)[0]
    assert lost.contact_id == detected.contact_id
    assert lost.uncertainty_m > detected.uncertainty_m
    assert lost.confidence < detected.confidence


def test_lost_contact_eventually_expires() -> None:
    target = TargetTruth("red-usv", Domain.SURFACE, (1000.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    engine = DetectionEngine(SessionRNG(7))
    tracks = engine.scan(_uav_sensor(), (target,), tick=0, weather=Weather.CLEAR)
    assert tracks
    for tick in range(1, 9):
        tracks = engine.scan(_uav_sensor(), (), tick=tick, weather=Weather.CLEAR)
    assert tracks == ()


def test_sensor_frequency_skips_non_update_tick() -> None:
    radar = SensorPlatform(
        "blue-usv",
        "usv",
        Side.BLUE,
        Domain.SURFACE,
        (0.0, 0.0, 0.0),
        Sensor("radar-blue", SensorKind.RADAR, 20_000.0, 0.5),
    )
    target = TargetTruth("red-usv", Domain.SURFACE, (100.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    engine = DetectionEngine(SessionRNG(7))
    assert engine.scan(radar, (target,), tick=1, weather=Weather.CLEAR) == ()
    assert engine.audit_log == []


def test_uav_eo_ir_detects_air_target_only_inside_its_field_of_view() -> None:
    platform = SensorPlatform(
        "blue-uav",
        "uav",
        Side.BLUE,
        Domain.AIR,
        (0.0, 0.0, 1000.0),
        Sensor("eo-blue", SensorKind.EO_IR, 15_000.0, 1.0, field_of_view_deg=60.0),
        heading_deg=0.0,
    )
    ahead = TargetTruth("red-ahead", Domain.AIR, (0.0, 1000.0, 1000.0), (0.0, 0.0, 0.0))
    behind = TargetTruth("red-behind", Domain.AIR, (0.0, -1000.0, 1000.0), (0.0, 0.0, 0.0))
    engine = DetectionEngine(SessionRNG(17))
    tracks = engine.scan(platform, (ahead, behind), tick=0, weather=Weather.CLEAR)
    assert len(tracks) == 1
    assert engine.audit_log[0]["target_entity_id"] == "red-ahead"
