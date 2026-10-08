"""Required standing goals must be public without exposing future incidents."""
import json

import pytest
import yaml

from tools.competition_four_categories.build import PACKAGES
from tools.competition_four_categories.emergency import emergency
from tools.competition_four_categories.response import response


@pytest.mark.parametrize("number", [2, 6])
def test_public_standing_goal_matches_unchanged_native_requirement(number):
    package, brief, *_ = response(6) if number == 6 else emergency(2)
    standing, = brief["standing_missions"]
    metric = next(m for m in package["scenario"]["scoring"]["metrics"] if m["id"] == standing["metric_id"])
    conditions = package["scenario"]["mission_rules"][0]["condition"]["parameters"]["conditions"]
    requirement = next(c["parameters"] for c in conditions if c.get("parameters", {}).get("metric_id") == standing["metric_id"])
    assert standing["threshold"] == requirement["value"] == .65
    assert standing["comparison"] == requirement["comparison"] == ">="
    assert standing["maximum_contact_age_ticks"] == metric["plugin_parameters"]["maximum_age_ticks"]
    assert standing["measurement_window"]["end_tick_exclusive"] == metric["plugin_parameters"]["end_tick"]
    assert standing["measurement_window"]["end_tick_exclusive"] == brief["adjudication_tick"]
    assert standing["controlled_observers"] == brief["responders"]
    assert "standing" in brief["task"]


@pytest.mark.parametrize("number", [2, 6])
def test_public_goal_addition_does_not_modify_the_native_scenario(number):
    package = (response(number) if number == 6 else emergency(number))[0]
    stored = yaml.safe_load((PACKAGES/f"md_er_{number:03d}_standard"/"scenario.yaml").read_text(encoding="utf-8"))
    assert package == stored


def test_er006_standing_sector_is_not_an_exact_future_notice_or_fault_oracle():
    package, brief, _, source_plan = response(6)
    standing, = brief["standing_missions"]
    text = json.dumps(brief)
    assert "unit.x" not in text and "event.fault" not in text
    assert "start_tick" not in standing["measurement_window"]
    assert standing["measurement_window"]["start_time_is_private"] is True
    for message in source_plan["messages"]:
        assert standing["search_region"] != json.loads(message["message"])["destination"]
    assert all(e["faction_id"] == "red" for e in package["scenario"]["entities"]
               if e["id"] == standing["initial_support_station"]["entity_id"])
