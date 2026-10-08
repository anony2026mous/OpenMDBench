"""Observation allowlist and hidden-state leakage tests."""

from openmdbench.core.entities import Domain, PlatformAsset, Side
from openmdbench.core.world import ContactTrack, WorldState, observation_for_side


def _asset(entity_id: str, side: Side) -> PlatformAsset:
    return PlatformAsset(
        id=entity_id,
        side=side,
        domain=Domain.SURFACE,
        platform_type="usv",
        position=(0.0, 0.0, 0.0),
    )


def test_public_observation_does_not_leak_enemy_truth_or_future_state() -> None:
    world = WorldState(
        session_id="session-1",
        mission_briefing="public briefing",
        referee_intent={"red-usv-secret": "ambush"},
        future_events=[{"red-usv-secret": "attack-at-100"}],
        time_remaining=100,
    )
    world.registry.register(_asset("blue-usv", Side.BLUE))
    world.registry.register(_asset("red-usv-secret", Side.RED))

    encoded = observation_for_side(world, Side.BLUE).model_dump_json()
    assert "blue-usv" in encoded
    assert "red-usv-secret" not in encoded
    assert "ambush" not in encoded
    assert "attack-at-100" not in encoded


def test_contact_has_side_scoped_id_without_true_entity_reference() -> None:
    world = WorldState(session_id="session-1", time_remaining=100)
    world.contacts[Side.BLUE] = [
        ContactTrack(
            contact_id="contact-1",
            owner_side=Side.BLUE,
            estimated_domain=Domain.SURFACE,
            position=(10.0, 20.0, 0.0),
            velocity=(0.0, 0.0, 0.0),
            uncertainty_m=50.0,
            confidence=0.7,
            first_detected_tick=2,
            detected_by=("blue-radar",),
        )
    ]
    encoded = observation_for_side(world, Side.BLUE).model_dump_json()
    assert "contact-1" in encoded
    assert "true_entity" not in encoded
