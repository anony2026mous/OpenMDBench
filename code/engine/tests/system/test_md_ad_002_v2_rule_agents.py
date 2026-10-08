"""Adversarial public-observation rule agents for the three formal V2 packages."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from openmdbench.policies.rule_v2 import (
    FormalRuleAgentTeamV2,
    load_formal_rule_agent_profile_v2,
)
from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
from openmdbench.sessions.formal_v2 import create_formal_session_v2

PUBLIC_IDS = ("MD-AD-002-EASY", "MD-AD-002-MEDIUM", "MD-AD-002-HARD")


def test_rule_agent_profiles_are_data_only_and_select_distinct_attack_patterns() -> None:
    profiles = {public_id: load_formal_rule_agent_profile_v2(public_id) for public_id in PUBLIC_IDS}
    assert {profile.attack.pattern for profile in profiles.values()} == {
        "direct",
        "split_evasion",
        "multi_axis_serpentine",
    }
    for profile in profiles.values():
        assert profile.defence.contact_confidence >= 0.0
        assert profile.defence.weapon_policies
    for public_id in PUBLIC_IDS:
        resolved, _catalog = compile_formal_scenario_v2(public_id)
        assert tuple(rule.id for rule in resolved.world.roe_rules) == (
            "roe.defender-engage-intruder",
        )
    for package in Path("scenarios/formal").glob("md_ad_002_*"):
        assert (package / "agents.yaml").is_file()
        assert not any(path.suffix == ".py" for path in package.rglob("*"))


@pytest.mark.parametrize("public_id", PUBLIC_IDS)
def test_agents_submit_only_public_v2_actions_and_move_intruders(public_id: str) -> None:
    session = create_formal_session_v2(
        public_id, session_id=f"rule-agent.{public_id.lower()}", seed=73
    )
    team = FormalRuleAgentTeamV2.for_scenario(public_id, seed=73)
    session.load().start()
    try:
        session.step(operation_id="spawn", expected_tick=0)
        before = {
            item["entity_id"]: tuple(item["position_m"])
            for item in session.world_view.observation(
                observer_faction_id="coalition.intruder"
            ).own_entities
        }
        team(session)
        receipt = session.step(operation_id="controlled.1", expected_tick=1)
        after = {
            item["entity_id"]: tuple(item["position_m"])
            for item in session.world_view.observation(
                observer_faction_id="coalition.intruder"
            ).own_entities
        }
        assert receipt.tick == 2
        assert team.last_decision is not None
        assert team.last_decision.attack_command_ids
        assert all(after[key] != before[key] for key in before)
        assert team.last_decision.observation_ticks == (1, 1)
    finally:
        session.stop().close()


def test_difficulty_patterns_produce_distinct_public_action_headings() -> None:
    headings: dict[str, tuple[float, ...]] = {}
    for public_id in PUBLIC_IDS:
        session = create_formal_session_v2(
            public_id, session_id=f"heading.{public_id.lower()}", seed=73
        )
        team = FormalRuleAgentTeamV2.for_scenario(public_id, seed=73)
        session.load().start()
        try:
            session.step(operation_id="spawn", expected_tick=0)
            team(session)
            assert team.last_decision is not None
            headings[public_id] = team.last_decision.attack_headings_deg
        finally:
            session.stop().close()
    easy = headings["MD-AD-002-EASY"]
    medium = headings["MD-AD-002-MEDIUM"]
    hard = headings["MD-AD-002-HARD"]
    assert max(easy) - min(easy) < 1.0
    assert max(medium) - min(medium) > 40.0
    assert hard != medium and hard != easy


def test_defender_uses_opaque_contact_not_target_truth() -> None:
    session = create_formal_session_v2("MD-AD-002-EASY", session_id="rule-agent.contact", seed=73)
    team = FormalRuleAgentTeamV2.for_scenario("MD-AD-002-EASY", seed=73)
    session.load().start()
    try:
        session.step(operation_id="spawn", expected_tick=0)
        observation = session.world_view.observation(observer_faction_id="coalition.defender")
        contacts = observation.contacts_by_faction["coalition.defender"]
        assert contacts
        assert all("target_id" not in contact for contact in contacts)
        assert all("observer_entity_id" in contact for contact in contacts)
        assert all("estimated_position_m" in contact for contact in contacts)
        team(session)
        assert team.last_decision is not None
        assert all(
            target.startswith("sensor.contact.") for target in team.last_decision.fire_contact_ids
        )
    finally:
        session.stop().close()


def test_v2_rule_agents_have_no_legacy_or_scenario_id_branch() -> None:
    import openmdbench.policies.rule_v2 as module

    source = inspect.getsource(module)
    assert "openmdbench.policies.md_ad_002" not in source
    assert "openmdbench.scenarios.legacy" not in source
    assert "scenario_id ==" not in source
    assert "MD-AD-002-EASY" not in source
    assert "MD-AD-002-MEDIUM" not in source
    assert "MD-AD-002-HARD" not in source
    assert "world._" not in source
