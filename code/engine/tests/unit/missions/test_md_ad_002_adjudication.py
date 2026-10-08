from openmdbench.core.entities import ComponentState, Domain, PlatformAsset, Side
from openmdbench.core.world import WorldState
from openmdbench.missions.md_ad_002 import MDAD002Adjudicator, MDAD002Outcome


def _blue(entity_id: str, position: tuple[float, float, float]) -> PlatformAsset:
    return PlatformAsset(
        id=entity_id,
        side=Side.BLUE,
        domain=Domain.AIR,
        position=position,
        platform_type="uav",
        components=ComponentState(),
    )


def test_breach_is_latched_and_not_rolled_back_by_same_tick_destruction() -> None:
    world = WorldState("test", tick=10)
    for index in range(3):
        world.registry.register(_blue(f"blue-{index}", (100.0 * index, 0.0, 100.0)))
    adjudicator = MDAD002Adjudicator(protected_point=(0.0, 0.0), breach_threshold=3)

    assert adjudicator.latch_breaches(world, 10) == ("blue-0", "blue-1", "blue-2")
    world.registry.destroy("blue-0")
    result = adjudicator.advance(world, tick=10, scheduled_count=12)

    assert result.outcome is MDAD002Outcome.BLUE_SUCCESS
    assert result.breach_count == 3


def test_swept_path_entry_is_latched_when_both_tick_endpoints_are_outside() -> None:
    world = WorldState("test", tick=10)
    target = _blue("blue-crossing", (-9.0, 7_999.999, 100.0))
    world.registry.register(target)
    adjudicator = MDAD002Adjudicator(protected_point=(0.0, 0.0), protection_radius_m=8_000.0)

    assert adjudicator.latch_breaches(
        world,
        10,
        previous_positions={"blue-crossing": (9.0, 7_999.999, 100.0)},
    ) == ("blue-crossing",)


def test_timeout_without_three_breaches_is_red_success() -> None:
    world = WorldState("test", tick=1_800)
    result = MDAD002Adjudicator(protected_point=(0.0, 0.0)).advance(
        world, tick=1_800, scheduled_count=15
    )
    assert result.outcome is MDAD002Outcome.RED_SUCCESS
    assert result.reason == "timeout_denial_success"


def test_administrator_termination_has_highest_priority() -> None:
    world = WorldState("test")
    adjudicator = MDAD002Adjudicator(protected_point=(0.0, 0.0), breach_threshold=1)
    adjudicator.breached_ids.add("blue-1")
    result = adjudicator.advance(world, tick=1, scheduled_count=14, administrator_terminated=True)
    assert result.outcome is MDAD002Outcome.TERMINATED
