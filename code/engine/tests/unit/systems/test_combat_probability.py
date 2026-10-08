"""Per-round combat probability, guidance weather, and damage tests."""

from openmdbench.core.entities import Domain, Side
from openmdbench.core.rng import SessionRNG
from openmdbench.core.world import ContactTrack
from openmdbench.systems.combat import Combatant, engage
from openmdbench.systems.weather import Weather


def test_each_round_draws_independently_and_accumulates_damage() -> None:
    attacker = Combatant(
        "blue-uav-1",
        Side.BLUE,
        (0.0, 0.0, 1_200.0),
        1.0,
        {"uav_interceptor_missile": 2},
        "uav",
    )
    contact = ContactTrack(
        "contact-blue-1",
        Side.BLUE,
        Domain.AIR,
        (1_000.0, 0.0, 1_200.0),
        (0.0, 0.0, 0.0),
        10.0,
        1.0,
        0,
        ("eo",),
    )
    result = engage(
        attacker,
        contact,
        target_side=Side.RED,
        target_health=1.0,
        weapon_id="uav_interceptor_missile",
        count=2,
        weather=Weather.CLEAR,
        rng=SessionRNG(7),
        target_domain=Domain.AIR,
        target_truth_position=contact.position,
    )
    assert len(result.shots) == 2
    assert result.shots[0].random_sample != result.shots[1].random_sample
    assert result.total_damage == sum(shot.damage for shot in result.shots if shot.hit)
    assert result.target_health == max(0.0, 1.0 - result.total_damage)


def test_eo_ir_guided_weapon_uses_eo_ir_weather_degradation() -> None:
    attacker = Combatant(
        "blue-uav-1",
        Side.BLUE,
        (0.0, 0.0, 1_200.0),
        1.0,
        {"uav_interceptor_missile": 1},
        "uav",
    )
    contact = ContactTrack(
        "contact-blue-1",
        Side.BLUE,
        Domain.AIR,
        (0.0, 0.0, 1_200.0),
        (0.0, 0.0, 0.0),
        1.0,
        1.0,
        0,
        ("eo",),
    )
    clear = engage(
        attacker,
        contact,
        target_side=Side.RED,
        target_health=1.0,
        weapon_id="uav_interceptor_missile",
        count=1,
        weather=Weather.CLEAR,
        rng=SessionRNG(3),
        target_domain=Domain.AIR,
    )
    rain = engage(
        attacker,
        contact,
        target_side=Side.RED,
        target_health=1.0,
        weapon_id="uav_interceptor_missile",
        count=1,
        weather=Weather.LIGHT_RAIN,
        rng=SessionRNG(3),
        target_domain=Domain.AIR,
    )
    assert rain.shots[0].probability == clear.shots[0].probability * 0.6
