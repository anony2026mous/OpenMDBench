"""Every candidate must have unambiguous declared terminal outcome evidence."""
import pytest

from tools.competition_four_categories.build import reconnaissance as recon_pilot
from tools.competition_four_categories.reconnaissance import reconnaissance
from tools.competition_four_categories.tracking import tracking
from tools.competition_four_categories.denial import denial
from tools.competition_four_categories.emergency import emergency
from tools.competition_four_categories.response import response
from tools.competition_four_categories.runtime import compile_package


CASES = ([("REC", level) for level in ("easy", "medium", "hard")]
         + [("REC", n) for n in range(2, 9)]
         + [("TRK", n) for n in range(1, 9)]
         + [("AD", n) for n in range(1, 7)]
         + [("ER", n) for n in range(1, 7)])


@pytest.mark.parametrize("family,number", CASES)
def test_all_candidates_declare_distinct_terminal_events_at_the_correct_horizon(family, number):
    if family == "REC":
        factory = recon_pilot if isinstance(number, str) else reconnaissance
    elif family == "ER":
        factory = response if number in (3, 5, 6) else emergency
    else:
        factory = {"TRK": tracking, "AD": denial}[family]
    package = factory(number)[0]
    scenario = package["scenario"]
    events = {e["id"]: e for e in scenario["events"]}
    rules = [r for r in scenario["mission_rules"] if r["outcome"]["terminal"]]
    emitted = [r["outcome"]["emit_event"] for r in rules]
    assert len(emitted) == len(set(emitted)) == 2
    assert {r["outcome"]["result"] for r in rules} == {
        "objective_complete", "objective_incomplete"}
    for identifier in emitted:
        assert events[identifier]["event_type"] == "mission_marker"
        assert events[identifier]["trigger"]["tick"] == scenario["world"]["duration_ticks"]
    resolved, _ = compile_package(package)
    assert resolved.resolved_hash.startswith("sha256:")
