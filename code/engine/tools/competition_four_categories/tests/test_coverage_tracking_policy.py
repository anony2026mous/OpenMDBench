from copy import deepcopy

import pytest

from tools.competition_four_categories.coverage_tracking_policy import CoverageTrackPolicy, CoverageReportingPolicy
from tools.competition_four_categories.tracking_budget_profile import load_profile


HEIGHTS = [0., 0., 200., 260., 320., 380.]


def data(profile="DEF-P3", owner="unit.r01", tick=4):
    _, brief, _, _ = load_profile(profile=profile)
    contacts = []
    for index, region in enumerate(brief["initial_designation_regions"]):
        points=region["coordinates_m"];position=[sum(p[a] for p in points)/len(points) for a in (0,1)]+[HEIGHTS[index]]
        contacts.append({"observer_entity_id":owner,"contact_id":f"opaque.{index}","observed_tick":tick-1,
                         "estimated_position_m":position,"confidence":.9})
    obs={"tick":tick,"own_entities":[{"entity_id":owner,"position_m":[0.,0.,150. if brief["observer_domains"][owner]=="air" else 0.]}],
         "organic_contacts":contacts,"shared_contacts":[],"received_messages":[]}
    return brief,obs


def test_def_p3_assigns_ground_and_low_air_contacts_to_available_surface_assets():
    brief,observation=data();p=CoverageTrackPolicy(brief,"unit.r01");p.command(observation);g=p._groups()
    assert g["unit.r03"]==[0,1] and g["unit.r05"]==[2] and g["unit.r06"]==[3]
    assert g["unit.r01"]==[4] and g["unit.r02"]==[5]


def test_sparse_profile_groups_air_contacts_by_predicted_spatial_coverage():
    brief,observation=data("legacy-four-observers");p=CoverageTrackPolicy(brief,"unit.r01");p.command(observation)
    for index in [2,3]:p.tracks[index]["velocity"]=[7.,0.,0.]
    for index in [4,5]:p.tracks[index]["velocity"]=[-7.,0.,0.]
    groups=p._groups()
    assert groups["unit.r01"]==[4,5] and groups["unit.r02"]==[2,3]


def test_recent_peer_estimates_do_not_pretend_to_be_fresh_own_sensor_samples():
    brief,first=data();p=CoverageTrackPolicy(brief,"unit.r01");p.command(first)
    later=deepcopy(first);later["tick"]=12;later["organic_contacts"]=[]
    later["shared_contacts"]=[{**r,"observer_entity_id":"unit.r02","source_contact_id":r["contact_id"],"observed_tick":11} for r in first["organic_contacts"]]
    p.command(later)
    assert p.tracks[4]["observed_tick"]==11
    assert p.samples_by_owner[4]["unit.r01"]==3
    assert p.acquisition_mode


@pytest.mark.parametrize("owner,limit", [("unit.r01",80.),("unit.r05",12.9),("unit.r06",12.9)])
def test_commands_remain_within_existing_resource_limits(owner,limit):
    brief,observation=data(owner=owner);p=CoverageTrackPolicy(brief,owner);command=p.command(observation)
    assert 0.<=command["speed_mps"]<=limit and 0.<=command["heading_deg"]<360.
    if brief["observer_domains"][owner]=="air":assert 60.<=command["altitude_m"]<=500.
    else:assert "altitude_m" not in command


def test_joint_coverage_uses_three_dimensional_sensor_distance():
    brief,observation=data(owner="unit.r05");p=CoverageTrackPolicy(brief,"unit.r05");p.command(observation)
    p.tracks[4]["position"]=[100.,0.,600.]
    assert not p._joint_cover([4],0.,4)[0]


def test_extra_referee_fields_and_token_text_do_not_control_assignment_or_navigation():
    brief,a=data();b=deepcopy(a);b["referee_truth"]={"goal":[999,999]}
    for n,row in enumerate(b["organic_contacts"]):row["contact_id"]=f"unit.x{n}.hidden-intent"
    p,q=CoverageTrackPolicy(brief,"unit.r01"),CoverageTrackPolicy(brief,"unit.r01")
    assert p.command(a)==q.command(b)
    assert p.primary_designations==q.primary_designations


def test_inactive_and_foreign_controller_states_are_handled_without_extra_control():
    brief,observation=data();p=CoverageTrackPolicy(brief,"unit.r01")
    assert p.command({"own_entities":[]}) is None
    observation["own_entities"][0]["entity_id"]="someone-else"
    with pytest.raises(ValueError,match="unowned"):p.command(observation)


def test_sink_silent_and_swapped_modes_preserve_navigation():
    brief,observation=data();results={m:CoverageReportingPolicy(brief,"unit.r01",m).decide(observation) for m in ["honest","silent","swapped"]}
    assert results["honest"]["navigation"]==results["silent"]["navigation"]==results["swapped"]["navigation"]


def test_surface_holds_when_current_location_covers_predicted_track():
    brief,observation=data(owner="unit.r05");p=CoverageTrackPolicy(brief,"unit.r05");p.command(observation)
    p.tracks[2].update(position=[300.,-100.,200.],velocity=[7.,4.,0.],observed_tick=3)
    goal=p._surface_observation_goal([2],[250.,-100.,0.],4)
    assert goal==pytest.approx([250.,-100.])


def test_surface_goal_is_forward_when_more_coverage_is_needed_not_a_reverse_trailing_point():
    brief,observation=data(owner="unit.r05");p=CoverageTrackPolicy(brief,"unit.r05");p.command(observation)
    p.tracks[2].update(position=[500.,-50.,200.],velocity=[7.,4.,0.],observed_tick=20)
    goal=p._surface_observation_goal([2],[250.,-100.,0.],20)
    assert goal is not None and goal[0]>250. and goal[1]>-100.


def test_surface_initial_hold_does_not_invent_a_target_altitude():
    brief,observation=data(owner="unit.r05",tick=0);observation["organic_contacts"]=[];observation["own_entities"][0]["heading_deg"]=90.
    result=CoverageTrackPolicy(brief,"unit.r05").command(observation)
    assert result=={"speed_mps":0.,"heading_deg":90.}
