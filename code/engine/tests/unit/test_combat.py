"""Combat visibility, range, ammunition, ROE, and determinism tests."""

import pytest
from openmdbench.core.entities import Domain, Side
from openmdbench.core.rng import SessionRNG
from openmdbench.core.world import ContactTrack
from openmdbench.systems.combat import Combatant, engage
from openmdbench.systems.weather import Weather


def _attacker() -> Combatant:
    return Combatant("blue-usv", Side.BLUE, (0.0, 0.0, 0.0), 1.0, {"usv_rws": 2})


def _contact(distance: float = 1000.0) -> ContactTrack:
    return ContactTrack(
        contact_id="contact-blue-1",
        owner_side=Side.BLUE,
        estimated_domain=Domain.SURFACE,
        position=(distance, 0.0, 0.0),
        velocity=(0.0, 0.0, 0.0),
        uncertainty_m=10.0,
        confidence=0.9,
        first_detected_tick=0,
        detected_by=("radar",),
    )


def test_invisible_and_out_of_range_contacts_cannot_be_engaged() -> None:
    with pytest.raises(ValueError, match="visible contact"):
        engage(
            _attacker(),
            None,
            target_side=Side.RED,
            target_health=1.0,
            weapon_id="usv_rws",
            count=1,
            weather=Weather.CLEAR,
            rng=SessionRNG(7),
        )
    with pytest.raises(ValueError, match="outside"):
        engage(
            _attacker(),
            _contact(3001.0),
            target_side=Side.RED,
            target_health=1.0,
            weapon_id="usv_rws",
            count=1,
            weather=Weather.CLEAR,
            rng=SessionRNG(7),
        )


def test_roe_rejects_friendly_and_neutral_targets() -> None:
    for side in (Side.BLUE, Side.NEUTRAL):
        with pytest.raises(ValueError, match="ROE"):
            engage(
                _attacker(),
                _contact(),
                target_side=side,
                target_health=1.0,
                weapon_id="usv_rws",
                count=1,
                weather=Weather.CLEAR,
                rng=SessionRNG(7),
            )


def test_hit_and_damage_are_reproducible_and_consume_ammunition() -> None:
    arguments = {
        "target_side": Side.RED,
        "target_health": 1.0,
        "weapon_id": "usv_rws",
        "count": 1,
        "weather": Weather.LIGHT_RAIN,
    }
    first = engage(_attacker(), _contact(), rng=SessionRNG(7), **arguments)  # type: ignore[arg-type]
    second = engage(_attacker(), _contact(), rng=SessionRNG(7), **arguments)  # type: ignore[arg-type]
    assert first == second
    assert first.attacker.ammunition["usv_rws"] == 1
    assert first.event["random_sample"] == second.event["random_sample"]
