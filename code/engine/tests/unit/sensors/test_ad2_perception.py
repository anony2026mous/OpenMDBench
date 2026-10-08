"""AD2-04 probability modifiers and public track lifecycle."""

from openmdbench.core.entities import ComponentState, Domain, Lifecycle, PlatformAsset, Side
from openmdbench.scenarios.runtime import ScenarioRuntime, create_scenario_runtime
from openmdbench.systems.sensors.ad2 import AD2Perception, detection_probability


def _near_target(runtime: ScenarioRuntime, distance: float) -> tuple[PlatformAsset, PlatformAsset]:
    platform = runtime.world.registry.get("red-island-radar-2")
    assert isinstance(platform, PlatformAsset)
    # Scheduled blue assets are intentionally absent from the initial runtime world.
    target = PlatformAsset(
        id="private-truth",
        side=Side.BLUE,
        domain=Domain.AIR,
        platform_type="uav",
        position=(platform.position[0] + distance, platform.position[1], 100.0),
        components=ComponentState(),
    )
    return platform, target


def test_probability_range_boundary_and_modifiers() -> None:
    runtime = create_scenario_runtime("MD-AD-002-EASY", seed=1)
    assert runtime.md_ad_config is not None
    profile = next(item for item in runtime.md_ad_config.sensors if item.sensor_id == "radar_gap")
    platform, inside = _near_target(runtime, 1_000.0)
    _, boundary = _near_target(runtime, profile.range_m)
    clear = detection_probability(profile, platform, inside, weather="clear")
    assert clear > 0
    assert detection_probability(profile, platform, boundary, weather="clear") == 0
    degraded = platform.model_copy(update={"lifecycle": Lifecycle.DEGRADED})
    assert detection_probability(profile, degraded, inside, weather="clear") < clear
    assert (
        detection_probability(profile, platform, inside, weather="clear", target_rcs_m2=0.01)
        < clear
    )
    usv_profile = next(
        item for item in runtime.md_ad_config.sensors if item.sensor_id == "radar_usv"
    )
    moving_usv = runtime.world.registry.get("red-picket-usv-1")
    assert isinstance(moving_usv, PlatformAsset)
    usv_target = inside.model_copy(
        update={
            "position": (
                moving_usv.position[0] + 1_000.0,
                moving_usv.position[1],
                20.0,
            )
        }
    )
    stopped_usv = moving_usv.model_copy(update={"velocity": (0.0, 0.0, 0.0)})
    moving = detection_probability(usv_profile, moving_usv, usv_target, weather="clear")
    assert moving < detection_probability(usv_profile, stopped_usv, usv_target, weather="clear")
    assert (
        detection_probability(usv_profile, moving_usv, usv_target, weather="high_sea_state")
        < moving
    )


def test_three_frame_confirmation_five_frame_deletion_and_no_truth_leak() -> None:
    runtime = create_scenario_runtime("MD-AD-002-EASY", seed=2)
    assert runtime.md_ad_config is not None
    platform, target = _near_target(runtime, 0.0)
    runtime.world.registry.register(target)
    config = runtime.md_ad_config.model_copy(
        update={
            "sensors": tuple(
                profile.model_copy(update={"base_detection_probability": 1.0})
                if profile.sensor_id == "radar_gap"
                else profile
                for profile in runtime.md_ad_config.sensors
            )
        }
    )
    tracker = AD2Perception(config, seed=2)
    for tick in (2, 4):
        assert tracker.update(runtime.world, tick) == ()
    contacts = tracker.update(runtime.world, 6)
    assert len(contacts) == 1
    assert target.id not in contacts[0].contact_id
    assert target.id not in str(contacts[0])
    for entity in runtime.world.entities_for_side("red"):
        assert isinstance(entity, PlatformAsset)
        runtime.world.registry.update(
            entity.model_copy(
                update={"components": entity.components.model_copy(update={"sensor_mode": "off"})}
            )
        )
    for tick in (8, 10, 12, 14):
        assert tracker.update(runtime.world, tick)
    assert tracker.update(runtime.world, 16) == ()
    for entity in runtime.world.entities_for_side("red"):
        assert isinstance(entity, PlatformAsset)
        runtime.world.registry.update(
            entity.model_copy(
                update={
                    "components": entity.components.model_copy(
                        update={"sensor_mode": "active_search"}
                    )
                }
            )
        )
    assert tracker.update(runtime.world, 18) == ()
    assert tracker.update(runtime.world, 20) == ()
    assert tracker.update(runtime.world, 22)


def test_multi_sensor_fusion_preserves_contact_id_and_records_sources() -> None:
    runtime = create_scenario_runtime("MD-AD-002-EASY", seed=3)
    assert runtime.md_ad_config is not None
    _, target = _near_target(runtime, 0.0)
    runtime.world.registry.register(target)
    config = runtime.md_ad_config.model_copy(
        update={
            "sensors": tuple(
                profile.model_copy(update={"base_detection_probability": 1.0})
                for profile in runtime.md_ad_config.sensors
            )
        }
    )
    tracker = AD2Perception(config, seed=3)
    for tick in range(2, 32, 2):
        contacts = tracker.update(runtime.world, tick)
    assert len(contacts) == 1
    assert any(source.endswith(":radar_ew") for source in contacts[0].detected_by)
    assert any(source.endswith(":radar_gap") for source in contacts[0].detected_by)
    assert contacts[0].contact_id == "contact-red-1"
