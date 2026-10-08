from copy import deepcopy

import pytest

from tools.competition_four_categories.denial import denial
from tools.competition_four_categories.planning_lead_policy import PROFILE, PlanningLeadSalvoPolicy, PlanningLeadScreenPolicy
from tools.competition_four_categories.receipt_aware_screen_policy import ReceiptAwareSalvoPolicy, ReceiptAwareScreenPolicy
from tools.competition_four_categories.tests.test_salvo_guard import contact, obs
from tools.competition_four_categories.tests.test_screen_guard import observation
from tools.competition_four_categories.tests.test_receipt_aware_screen import receipt


def test_planning_is_derived_from_public_capabilities_without_mutating_the_brief():
    brief = denial(6)[1]; before = deepcopy(brief)
    surface = PlanningLeadSalvoPolicy(brief, "unit.r03")
    air = PlanningLeadSalvoPolicy(brief, "unit.r01")
    shore = PlanningLeadSalvoPolicy(brief, "unit.r02")
    assert surface.planning["nominal_range_travel_ticks"] == 67
    assert surface.planning["controller_lookahead_ticks"] == 140
    assert air.planning["controller_lookahead_ticks"] == brief["engagement_lookahead_ticks"]
    assert shore.planning["nominal_range_travel_ticks"] is None
    assert brief == before
    assert surface.inventory == brief["own_inventory"]["unit.r03"]


def test_earlier_planning_keeps_the_same_observation_only_target_rule():
    brief = denial(6)[1]
    old, new = ReceiptAwareSalvoPolicy(brief, "unit.r03"), PlanningLeadSalvoPolicy(brief, "unit.r03")
    for agent in (old, new):
        assert agent.action(obs(0, [contact(0, 806.)])) is None
    assert old.action(obs(1, [contact(1, 800.)])) is None
    assert new.action(obs(1, [contact(1, 800.)]))["contact_id"] == "opaque.one"


@pytest.mark.parametrize("positions", [((800., 1450.), (794., 1450.)), ((800., 0.), (806., 0.))])
def test_passing_and_outbound_contacts_still_do_not_trigger_actions(positions):
    agent = PlanningLeadSalvoPolicy(denial(6)[1], "unit.r03")
    for tick, (x, y) in enumerate(positions):
        assert agent.action(obs(tick, [contact(tick, x, y)])) is None


def test_navigation_remains_identical_to_the_existing_receipt_aware_control():
    brief = denial(6)[1]
    old = ReceiptAwareScreenPolicy(brief, "unit.r03")
    new = PlanningLeadScreenPolicy(brief, "unit.r03")
    for tick in range(4):
        data = observation(tick=tick)
        assert new.navigation(data) == old.navigation(data)
    assert new.brief == old.brief


def test_rejected_early_request_refunds_only_its_reservation_and_preserves_inventory():
    agent = PlanningLeadSalvoPolicy(denial(6)[1], "unit.r03")
    assert agent.action(obs(0, [contact(0, 806.)])) is None
    assert agent.action(obs(1, [contact(1, 800.)])) is not None
    agent.bind_fire_request("own.request.1"); agent.process_fire_feedback(receipt())
    assert agent.attempts == 0 and agent.pending_until == {}
    assert agent.action(obs(2, [contact(2, 794.)])) is not None
    assert sum(agent.inventory["initial_ammunition"].values()) == 6


def test_planning_horizon_respects_episode_and_declared_travel_lifetime():
    brief = denial(6)[1]; brief["scoring_deadline_tick"] = 90
    assert PlanningLeadSalvoPolicy(brief, "unit.r03").planning["controller_lookahead_ticks"] == 90
    brief = denial(6)[1]; brief["own_inventory"]["unit.r03"]["projectile_profile"]["max_flight_ticks"] = 10
    assert PlanningLeadSalvoPolicy(brief, "unit.r03").planning["nominal_range_travel_ticks"] == 10


@pytest.mark.parametrize("value", [0., -1., True, float("nan"), float("inf")])
def test_invalid_public_service_speed_fails_closed(value):
    brief = denial(6)[1]; brief["own_inventory"]["unit.r03"]["projectile_profile"]["cruise_speed_mps"] = value
    with pytest.raises(ValueError, match="positive finite"):
        PlanningLeadSalvoPolicy(brief, "unit.r03")


def test_hidden_roles_future_events_and_referee_state_are_not_controller_inputs():
    a = PlanningLeadSalvoPolicy(denial(6)[1], "unit.r03")
    b = PlanningLeadSalvoPolicy(denial(6)[1], "unit.r03")
    for tick in (0, 1):
        raw = obs(tick, [contact(tick, 806. - 6 * tick)])
        altered = deepcopy(raw); altered["organic_contacts"][0]["hidden_role"] = "private"
        altered.update(future_wave_plan={"tick": 999}, referee_active_missiles=[{"hit": True}])
        assert a.action(raw) == b.action(altered)


def test_new_reference_evidence_binds_its_source_and_fixed_profile():
    from tools.competition_four_categories.audit import denial_extension_sources
    from tools.competition_four_categories import planning_lead_policy
    from tools.competition_four_categories.validate_tracking import sha
    bindings = denial_extension_sources("planning-lead-salvo")
    assert bindings["policy_source_sha256"] == sha(planning_lead_policy.__file__)
    assert bindings["planning_lead_profile"] == PROFILE
    assert bindings["fire_feedback_protocol"] == "own-fire-execution-status@1.0"
