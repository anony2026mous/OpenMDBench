"""Referee-only localization error of native, controller-visible measurements.

Truth and measurement come from the SAME SensorContactReceiptV2. Never infer
truth from a contact ID, a route, or a later entity position. This diagnoses
sensor measurement error, not an agent's unreported trajectory estimate and
not a new native score, terminal condition, or authentication mechanism.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, is_dataclass
import hashlib
import json
import math

CONTRACT = "native-confirmed-contact-localization@1.0"


def plain(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return asdict(value) if is_dataclass(value) else deepcopy(value)


def vector(value):
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise ValueError("expected a three-dimensional native position")
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in value):
        raise ValueError("native positions require finite numbers")
    return tuple(float(x) for x in value)


def cohort(values):
    if isinstance(values, str):
        raise ValueError("expected explicit entity cohort")
    values = tuple(values)
    if not values or len(set(values)) != len(values) or any(not isinstance(x, str) or not x for x in values):
        raise ValueError("empty, duplicate or invalid entity cohort")
    return tuple(sorted(values))


def sensor_key(row):
    return row["owner_entity_id"], row["target_entity_id"], row["sensor_ref"], row["tick"]


def measure(evidence):
    sensor = evidence["sensor_receipt"]
    contact = evidence["native_contact"]
    visible = evidence["controller_contact"]
    captured = evidence["capture_world_tick"]
    if type(captured) is not int or type(sensor["tick"]) is not int or not 0 <= sensor["tick"] < captured:
        raise ValueError("measurement clock must precede its post-step observation")
    if sensor.get("coordinate_frame") != "local-m" or sensor.get("detected") is not True:
        raise ValueError("expected a detected native local-m sensor receipt")
    if sensor.get("sample") is None or contact.get("confirmed") is not True:
        raise ValueError("unconfirmed or unsampled contacts are not measured observations")
    if (sensor["owner_entity_id"] != contact["owner_entity_id"]
            or sensor["target_entity_id"] != contact["target_entity_id"]
            or sensor["sensor_ref"] != contact["source_sensor_ref"]
            or sensor["tick"] != contact["observed_tick"]):
        raise ValueError("native measurement and contact provenance differ")
    if (visible["observer_entity_id"] != contact["owner_entity_id"]
            or visible["contact_id"] != contact["evidence_id"]
            or visible["observed_tick"] != contact["observed_tick"]
            or visible["age_ticks"] != captured - contact["observed_tick"]):
        raise ValueError("controller contact does not match its native evidence")
    measured = vector(sensor["measurement_position_m"])
    truth = vector(sensor["target_position_m"])
    if measured != vector(contact["measurement_position_m"]) or measured != vector(visible["estimated_position_m"]):
        raise ValueError("controller measurement differs from the actual sensor receipt")
    error = tuple(m - t for m, t in zip(measured, truth))
    return {"observer_id": sensor["owner_entity_id"], "target_id": sensor["target_entity_id"],
        "contact_id": contact["evidence_id"], "observed_tick": sensor["tick"],
        "source_sensor_ref": sensor["sensor_ref"], "error_vector_m": list(error),
        "squared_3d_error_m2": math.fsum(x*x for x in error),
        "squared_horizontal_error_m2": math.fsum(x*x for x in error[:2]),
        "squared_vertical_error_m2": error[2]*error[2]}


def statistics(rows):
    count = len(rows)
    return {"sample_count": count,
        "rmse_3d_m": math.sqrt(math.fsum(r["squared_3d_error_m2"] for r in rows)/count) if count else None,
        "rmse_horizontal_m": math.sqrt(math.fsum(r["squared_horizontal_error_m2"] for r in rows)/count) if count else None,
        "rmse_vertical_m": math.sqrt(math.fsum(r["squared_vertical_error_m2"] for r in rows)/count) if count else None}


class NativeContactLocalizationAudit:
    def __init__(self, observer_ids, target_ids):
        self.observers, self.targets = cohort(observer_ids), cohort(target_ids)
        if set(self.observers) & set(self.targets):
            raise ValueError("observer and target cohorts must be disjoint")
        self.next_tick = 0
        self.sensor_history = {}
        self.samples = {}
        self.frame_sample_counts = []

    def capture(self, world_receipt, frame, observations):
        if (world_receipt.steps != 1 or world_receipt.start_tick != self.next_tick
                or world_receipt.tick != self.next_tick+1 or frame.tick != world_receipt.tick):
            raise ValueError("localization audit requires every completed native single-tick step")
        if set(observations) != set(self.observers):
            raise ValueError("localization observation cohort differs")
        history, samples = dict(self.sensor_history), dict(self.samples)
        for receipt in world_receipt.subsystem_receipts:
            for item in receipt.contacts:
                row = plain(item)
                if row["owner_entity_id"] not in self.observers or row["target_entity_id"] not in self.targets:
                    continue
                if row.get("detected") is not True or row.get("measurement_position_m") is None:
                    continue
                if row["tick"] != world_receipt.start_tick:
                    raise ValueError("sensor receipt clock differs from its native step")
                key = sensor_key(row)
                if key in history and history[key] != row:
                    raise ValueError("native sensor sample changed")
                history[key] = row
        contacts = {}
        for item in frame.combat_contact_evidence:
            row = plain(item)
            key = row["owner_entity_id"], row["evidence_id"], row["observed_tick"]
            if key in contacts and contacts[key] != row:
                raise ValueError("conflicting authoritative contact evidence")
            contacts[key] = row
        visible_keys = set()
        for identifier, observation in observations.items():
            if observation["tick"] != frame.tick:
                raise ValueError("controller observation has a different native clock")
            for visible in observation["organic_contacts"]:
                if visible["observer_entity_id"] != identifier:
                    raise ValueError("controller contact claims another observer")
                key = identifier, visible["contact_id"], visible["observed_tick"]
                if key in visible_keys:
                    raise ValueError("duplicate controller contact sample")
                visible_keys.add(key)
                if key not in contacts:
                    raise ValueError("controller contact lacks authoritative native evidence")
                contact = contacts[key]
                if contact["target_entity_id"] not in self.targets:
                    continue
                source = identifier, contact["target_entity_id"], contact["source_sensor_ref"], contact["observed_tick"]
                if source not in history:
                    raise ValueError("measurement-time sensor receipt is missing; do not substitute current truth")
                evidence = {"capture_world_tick": frame.tick, "sensor_receipt": history[source],
                    "native_contact": contact, "controller_contact": plain(visible)}
                row = measure(evidence)
                if key in samples:
                    if samples[key]["measurement"] != row:
                        raise ValueError("historical localization measurement changed")
                else:
                    samples[key] = {"evidence": evidence, "measurement": row}
        self.frame_sample_counts.append({"world_tick": frame.tick, "new_samples": len(samples)-len(self.samples)})
        self.sensor_history, self.samples = history, samples
        self.next_tick += 1

    def summary(self):
        rows = [self.samples[key]["measurement"] for key in sorted(self.samples)]
        per_target = {identifier: statistics([r for r in rows if r["target_id"] == identifier]) for identifier in self.targets}
        target_mse = [v["rmse_3d_m"]**2 for v in per_target.values() if v["sample_count"]]
        return {"contract": CONTRACT, "scope": "referee_only_native_measurement_error_not_agent_trajectory_error",
            "units": "meters", "conditional_on_detected_confirmed_contacts": True,
            "checked_steps": self.next_tick, "observer_ids": list(self.observers), "target_ids": list(self.targets),
            "pooled": statistics(rows), "per_target": per_target,
            "per_observer": {i: statistics([r for r in rows if r["observer_id"] == i]) for i in self.observers},
            "targets_without_samples": [i for i,v in per_target.items() if not v["sample_count"]],
            "macro_target_rmse_3d_m": math.sqrt(math.fsum(target_mse)/len(target_mse)) if len(target_mse)==len(self.targets) else None,
            "agent_reported_trajectory_rmse_m": None, "native_score_or_terminal_modified": False,
            "evidence_sha256": hashlib.sha256(json.dumps(self.evidence(),sort_keys=True,allow_nan=False).encode()).hexdigest()}

    def evidence(self):
        return {"observer_ids": list(self.observers), "target_ids": list(self.targets),
            "frame_sample_counts": deepcopy(self.frame_sample_counts),
            "samples": [deepcopy(self.samples[k]) for k in sorted(self.samples)]}
