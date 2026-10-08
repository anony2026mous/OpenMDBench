import pytest

from tools.competition_four_categories.reconnaissance import reconnaissance
from tools.competition_four_categories.recon_policy import SearchPolicy
from tools.competition_four_categories.tracking import tracking
from tools.competition_four_categories.tracking_policy import ContactFollowPolicy, ScheduledNavigationPolicy


def test_search_stops_actions_for_inactive_owned_entity():
    p = SearchPolicy(reconnaissance(3)[1], "unit.r02", "coordinated")
    empty = {"tick": 50, "own_entities": [], "organic_contacts": []}
    assert p.navigation(empty) is None and p.report(empty) is None
    with pytest.raises(ValueError, match="another controller"):
        p.navigation({**empty, "own_entities": [{"entity_id": "unowned"}]})


def test_tracking_stops_inactive_entity_without_authorizing_other_entities():
    p = ContactFollowPolicy(tracking(1)[1], "unit.r01")
    assert p.command({"own_entities": []}) is None
    with pytest.raises(ValueError, match="different controller"):
        p.command({"own_entities": [{"entity_id": "unowned"}]})


def test_scripted_navigation_does_not_issue_commands_for_lost_actor():
    plan = tracking(1)[3]
    p = ScheduledNavigationPolicy(plan)
    observations = {i: {"own_entities": []} for i in p.entity_ids}
    assert p.commands(0, observations) == {}
    identifier = p.entity_ids[0]
    observations[identifier] = {"own_entities": [{"entity_id": "unowned"}]}
    with pytest.raises(ValueError, match="unowned"):
        p.commands(0, observations)
