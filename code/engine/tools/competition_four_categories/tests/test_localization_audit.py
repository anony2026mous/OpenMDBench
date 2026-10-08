"""Pure evidence checks; real native runs live in test_native_localization.py."""
from copy import deepcopy
from types import SimpleNamespace as NS

import pytest

from tools.competition_four_categories.native_localization_audit import NativeContactLocalizationAudit, measure


def evidence(tick=0, measured=(3.,4.,12.), truth=(0.,0.,0.)):
    sensor = {"owner_entity_id": "observer", "target_entity_id": "target", "sensor_ref": "sensor@1.0",
        "tick": tick, "detected": True, "sample": 0.2, "coordinate_frame": "local-m",
        "measurement_position_m": list(measured), "target_position_m": list(truth)}
    contact = {"owner_entity_id": "observer", "target_entity_id": "target", "source_sensor_ref": "sensor@1.0",
        "observed_tick": tick, "evidence_id": "opaque-label-972", "confirmed": True,
        "measurement_position_m": list(measured)}
    visible = {"observer_entity_id": "observer", "contact_id": "opaque-label-972",
        "observed_tick": tick, "age_ticks": 1, "estimated_position_m": list(measured)}
    return {"capture_world_tick": tick+1, "sensor_receipt": sensor, "native_contact": contact, "controller_contact": visible}


def capture(a, e, *, start=None, sensor=True):
    start = e["capture_world_tick"]-1 if start is None else start
    world = NS(start_tick=start, tick=start+1, steps=1,
        subsystem_receipts=[NS(contacts=[e["sensor_receipt"]] if sensor else [])])
    frame = NS(tick=start+1, combat_contact_evidence=[e["native_contact"]])
    observations = {"observer": {"tick": start+1, "organic_contacts": [e["controller_contact"]]}}
    a.capture(world, frame, observations)


def test_same_native_receipt_computes_exact_3d_horizontal_and_vertical_errors():
    a = NativeContactLocalizationAudit(["observer"],["target"]); capture(a,evidence())
    assert a.summary()["pooled"] == {"sample_count":1,"rmse_3d_m":13.,"rmse_horizontal_m":5.,"rmse_vertical_m":12.}
    assert a.summary()["agent_reported_trajectory_rmse_m"] is None
    assert a.summary()["native_score_or_terminal_modified"] is False


def test_stale_visible_measurement_is_not_recounted_or_joined_to_current_truth():
    a = NativeContactLocalizationAudit(["observer"],["target"]); e=evidence();capture(a,e)
    e["capture_world_tick"]=2;e["controller_contact"]["age_ticks"]=2;capture(a,e,sensor=False)
    assert a.summary()["checked_steps"]==2 and a.summary()["pooled"]["sample_count"]==1
    assert a.summary()["pooled"]["rmse_3d_m"]==13.


def test_no_observation_is_missing_not_zero_and_missing_targets_block_macro_metric():
    a = NativeContactLocalizationAudit(["observer"],["target","missing-target"])
    assert a.summary()["pooled"]["rmse_3d_m"] is None
    capture(a,evidence());v=a.summary()
    assert v["targets_without_samples"]==["missing-target"]
    assert v["macro_target_rmse_3d_m"] is None


def test_rmse_uses_mean_squared_error_not_mean_absolute_or_mean_rmse():
    a=NativeContactLocalizationAudit(["observer"],["target"])
    capture(a,evidence(measured=(0.,0.,0.)));capture(a,evidence(tick=1,measured=(0.,0.,10.)))
    assert a.summary()["pooled"]["rmse_3d_m"]==pytest.approx(50.**0.5)


@pytest.mark.parametrize("field,value", [("coordinate_frame","lat-lon"),("detected",False),("sample",None),
    ("tick",2),("owner_entity_id","other"),("target_entity_id","other"),("sensor_ref","other"),
    ("measurement_position_m",[0.,0.,0.]),("target_position_m",[0.,float('nan'),0.])])
def test_sensor_provenance_or_geometry_mutation_cannot_pass(field,value):
    e=evidence();e["sensor_receipt"][field]=value
    with pytest.raises(ValueError):measure(e)


@pytest.mark.parametrize("field,value", [("observer_entity_id","other"),("contact_id","invented"),
    ("observed_tick",9),("age_ticks",0),("estimated_position_m",[0.,0.,0.])])
def test_controller_sample_must_match_actual_native_evidence(field,value):
    e=evidence();e["controller_contact"][field]=value
    with pytest.raises(ValueError):measure(e)


def test_missing_native_sensor_sample_fails_without_mutating_previous_audit():
    a=NativeContactLocalizationAudit(["observer"],["target"]);before=a.summary()
    with pytest.raises(ValueError,match="sensor receipt is missing"):capture(a,evidence(),sensor=False)
    assert a.summary()==before


def test_opaque_ids_need_no_target_name_or_semantic_parsing():
    e=evidence();original=measure(e);e["native_contact"]["evidence_id"]="arbitrary-other-format"
    e["controller_contact"]["contact_id"]="arbitrary-other-format"
    assert measure(e)["squared_3d_error_m2"]==original["squared_3d_error_m2"]


def test_returned_evidence_cannot_mutate_internal_sensor_history():
    a=NativeContactLocalizationAudit(["observer"],["target"]);e=evidence();before=deepcopy(e);capture(a,e)
    assert e==before;stored=a.evidence();stored["samples"][0]["evidence"]["sensor_receipt"]["target_position_m"][0]=1e9
    assert a.summary()["pooled"]["rmse_3d_m"]==13.
