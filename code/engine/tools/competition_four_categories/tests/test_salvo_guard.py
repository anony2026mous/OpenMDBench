from copy import deepcopy
import json

import pytest
import yaml

from tools.competition_four_categories.build import PACKAGES, candidate_catalog
from tools.competition_four_categories.denial import denial
from tools.competition_four_categories.denial_policy import ZoneGuardPolicy
from tools.competition_four_categories.salvo_guard_policy import SalvoGuardPolicy


def contact(tick, x, y=0., token="opaque.one", z=0.):
    return {"contact_id": token, "observed_tick": tick, "age_ticks": 0,
            "estimated_position_m": [x, y, z], "observer_entity_id": "unit.r03"}


def obs(tick, contacts, owner="unit.r03"):
    return {"tick": tick, "own_entities": [{"entity_id": owner, "position_m": [0., 400., 0.]}],
            "organic_contacts": contacts}


def policy():
    return SalvoGuardPolicy(denial(6)[1], "unit.r03")


def test_same_contact_is_not_repeatedly_fired_on_while_assessment_is_pending():
    agent = policy()
    assert agent.action(obs(0, [contact(0, 600.)])) is None
    assert agent.action(obs(1, [contact(1, 592.)]))["contact_id"] == "opaque.one"
    for tick in (4, 7, 10):
        assert agent.action(obs(tick, [contact(tick, 600.-8*tick)])) is None
    assert agent.attempts == 1 and agent.pending_until["opaque.one"] > 10


def test_another_observed_incoming_contact_can_be_served_while_first_is_pending():
    agent = policy()
    for tick in (0, 1, 10):
        result = agent.action(obs(tick, [contact(tick, 600.-8*tick), contact(tick, 700.-8*tick, 850., "opaque.two")]))
        if tick == 1: assert result["contact_id"] == "opaque.one"
    assert result["contact_id"] == "opaque.two"
    assert agent.attempts == 2


def test_no_initial_ammunition_is_added_or_replenished():
    agent = policy(); commands = []
    for index in range(7):
        tick = index*4
        assert agent.action(obs(tick, [contact(tick, 300., token=f"opaque.{index}")])) is None
        commands.append(agent.action(obs(tick+1, [contact(tick+1, 290., token=f"opaque.{index}")])))
    assert sum(c is not None for c in commands) == 6
    assert commands[-1] is None and agent.attempts == 6


def test_passing_traffic_and_stale_or_future_samples_do_not_trigger_fire():
    agent = policy()
    agent.action(obs(0, [contact(0, 500., 1450.)]))
    assert agent.action(obs(1, [contact(1, 490., 1450.)])) is None
    assert agent.action(obs(2, [contact(3, 450.)])) is None
    assert agent.action(obs(8, [contact(1, 450.)])) is None


def test_hidden_roles_future_plans_and_real_missile_state_are_ignored():
    a, b = policy(), policy()
    for tick in (0, 1):
        raw = obs(tick, [contact(tick, 600.-8*tick)])
        changed = deepcopy(raw)
        changed["organic_contacts"][0].update(hidden_role="civilian", target_id="secret")
        changed.update(future_wave_plan={"spawn_tick": 4}, referee_active_missiles=[{"target_id": "secret"}])
        assert a.action(raw) == b.action(changed)
    assert a.decisions == b.decisions


def test_contact_token_text_does_not_change_kinematic_decisions():
    a, b = policy(), policy()
    for tick in (0, 1, 4):
        left = a.action(obs(tick, [contact(tick, 600.-8*tick, token="opaque.A")]))
        right = b.action(obs(tick, [contact(tick, 600.-8*tick, token="unrelated.B")]))
        assert (left is None) == (right is None)
        if left: assert left["weapon_ref"] == right["weapon_ref"]
    assert a.attempts == b.attempts


def test_foreign_ownership_is_rejected_and_direct_weapons_reuse_original_policy():
    with pytest.raises(ValueError, match="another controller"):
        policy().action(obs(1, [], owner="not.owned"))
    brief = denial(6)[1]
    a, b = SalvoGuardPolicy(brief, "unit.r02"), ZoneGuardPolicy(brief, "unit.r02", "guard")
    for tick in (0, 1):
        data = {"tick": tick, "own_entities": [{"entity_id": "unit.r02", "position_m": [-350., 0., 0.]}],
            "organic_contacts": [{"contact_id": "opaque.air", "observed_tick": tick, "age_ticks": 0,
                                  "estimated_position_m": [650.-20*tick, 0., 180.]}]}
        assert a.action(data) == b.action(data)


@pytest.mark.parametrize("number", range(1, 7))
def test_public_projectile_metadata_matches_catalog_without_changing_native_scene(number):
    package, brief, _, _ = denial(number)
    stored = yaml.safe_load((PACKAGES/f"md_ad_{number:03d}_standard"/"scenario.yaml").read_text(encoding="utf-8"))
    assert package == stored
    resources = {f"{r['id']}@{r['version']}": r["content"] for r in candidate_catalog()["resources"] if r["resource_type"] == "weapons"}
    for inventory in brief["own_inventory"].values():
        if "projectile_profile" in inventory:
            native = resources[inventory["weapon_ref"]]
            assert inventory["delivery_model"] == native["delivery_model"]
            assert all(value == native["missile"][key] for key, value in inventory["projectile_profile"].items())
    assert "unit.x" not in json.dumps(brief)


def test_isolated_validator_uses_the_original_action_api_objects():
    from tools.competition_four_categories import validate_salvo_denial, validate_denial
    assert validate_salvo_denial.observe_slots is validate_denial.observe_slots
    assert validate_salvo_denial.submit_fire is validate_denial.submit_fire
    assert validate_salvo_denial.submit_navigation is validate_denial.submit_navigation
