"""Offline tests for the scenario retuning tool.

These lock the properties that calibration depends on: idempotence (a replayed profile must not
compound a shift), refusal to guess when a unit is not where the profile expects it, and that
every lever writes only schema-legal keys (the package schema is closed, so a provenance field
in the package would be a compile error).
"""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location('competition_retune_under_test',
                                              ROOT / 'competition_retune.py')
retune = importlib.util.module_from_spec(spec)
sys.modules['competition_retune_under_test'] = retune
spec.loader.exec_module(retune)


def scenario_payload(**overrides):
    scenario = {
        "schema_version": "2.0",
        "entities": [
            {"schema_version": "2.0", "id": "unit.r01", "faction_id": "red",
             "initial_state": {"schema_version": "2.0", "position_m": [0.0, -120.0, 100.0],
                               "velocity_mps": [0.0, 0.0, 0.0]}},
            {"schema_version": "2.0", "id": "unit.r04", "faction_id": "red",
             "initial_state": {"schema_version": "2.0", "position_m": [600.0, -300.0, 0.0],
                               "velocity_mps": [0.0, 0.0, 0.0]}},
            {"schema_version": "2.0", "id": "unit.x01", "faction_id": "blue",
             "initial_state": {"schema_version": "2.0", "position_m": [300.0, 0.0, 0.0],
                               "velocity_mps": [4.0, 0.0, 0.0]}},
        ],
        "events": [
            {"schema_version": "2.0", "id": "event.spawn", "event_type": "spawn",
             "trigger": {"tick": 90},
             "payload": {"entity": {"schema_version": "2.0", "id": "unit.x02",
                                    "faction_id": "blue",
                                    "initial_state": {"schema_version": "2.0",
                                                      "position_m": [300.0, 50.0, 0.0],
                                                      "velocity_mps": [4.0, 0.0, 0.0]}}}},
        ],
        "scoring": {"metrics": [{"id": "metric.continuity", "plugin_parameters": {
            "maximum_gap_ticks": 18, "maximum_age_ticks": 2}}]},
        "mission_rules": [
            {"id": "rule.timeout", "condition": {"operator": "time",
                                                 "parameters": {"comparison": ">=", "tick": 241}}},
            {"id": "rule.success", "condition": {"operator": "all", "parameters": {"conditions": [
                {"operator": "score", "parameters": {"metric_id": "metric.continuity",
                                                     "comparison": ">=", "value": 0.7}}]}}},
        ],
        "world": {"duration_ticks": 241,
                  "zones": [{"schema_version": "2.0", "id": "zone.protected01",
                             "geometry_type": "polygon",
                             "coordinates_m": [[-160.0, -160.0], [160.0, 160.0]]}]},
    }
    scenario.update(overrides)
    return {"scenario": scenario}


class LeverTests(unittest.TestCase):
    def test_anchor_shift_moves_to_the_target_and_is_idempotent(self):
        payload = scenario_payload()
        shifts = {"unit.r01": [0.0, -1000.0], "unit.r04": [600.0, -400.0]}
        first = retune.apply_anchor_shift(payload, shifts)
        self.assertEqual(len(first), 2)
        positions = {e["id"]: e["initial_state"]["position_m"][0]
                     for e in payload["scenario"]["entities"]}
        self.assertEqual(positions["unit.r01"], -1000.0)
        self.assertEqual(positions["unit.r04"], -400.0)
        # replaying must not move anything again (this is what broke TRK-001 in calibration)
        second = retune.apply_anchor_shift(payload, shifts)
        self.assertEqual(second, [])
        self.assertEqual({e["id"]: e["initial_state"]["position_m"][0]
                          for e in payload["scenario"]["entities"]}, positions)

    def test_anchor_shift_refuses_to_guess_an_unexpected_position(self):
        payload = scenario_payload()
        payload["scenario"]["entities"][0]["initial_state"]["position_m"][0] = -777.0
        with self.assertRaises(ValueError):
            retune.apply_anchor_shift(payload, {"unit.r01": [0.0, -1000.0]})

    def test_anchor_shift_writes_no_extra_keys_into_the_package(self):
        payload = scenario_payload()
        retune.apply_anchor_shift(payload, {"unit.r01": [0.0, -1000.0]})
        state = payload["scenario"]["entities"][0]["initial_state"]
        self.assertEqual(sorted(state), ["position_m", "schema_version", "velocity_mps"])

    def test_contact_shift_moves_the_spawn_payload_too(self):
        payload = scenario_payload()
        changes = retune.apply_contact_shift(payload, 200.0)
        self.assertEqual(len(changes), 2)
        self.assertEqual(payload["scenario"]["entities"][2]["initial_state"]["position_m"][0], 500.0)
        spawned = payload["scenario"]["events"][0]["payload"]["entity"]
        self.assertEqual(spawned["initial_state"]["position_m"][0], 500.0)

    def test_zone_centroid_sets_an_absolute_position(self):
        payload = scenario_payload()
        first = retune.apply_zone_centroid(payload, {"zone.protected01": 900.0})
        self.assertEqual(len(first), 1)
        coordinates = payload["scenario"]["world"]["zones"][0]["coordinates_m"]
        centroid = sum(point[0] for point in coordinates) / len(coordinates)
        self.assertAlmostEqual(centroid, 900.0, places=3)
        self.assertEqual(retune.apply_zone_centroid(payload, {"zone.protected01": 900.0}), [])

    def test_zone_translation_is_idempotent_via_the_absolute_form(self):
        payload = scenario_payload()
        changes = retune.apply_zone_translation(payload, 70.0)
        self.assertEqual(len(changes), 1)
        before = payload["scenario"]["world"]["zones"][0]["coordinates_m"]
        self.assertAlmostEqual(before[0][0], -90.0, places=3)  # -160 + 70

    def test_suppression_appends_a_schema_legal_event_once(self):
        payload = scenario_payload()
        entry = {"id": "event.retune-suppression", "target_entity_id": "unit.r01",
                 "component_ref": "sensor.competition-denial-air@1.0.0", "tick": 1,
                 "duration_ticks": 60}
        first = retune.apply_suppression(payload, [entry])
        self.assertEqual(len(first), 1)
        self.assertEqual(retune.apply_suppression(payload, [entry]), [])
        event = payload["scenario"]["events"][-1]
        self.assertEqual(event["event_type"], "component_suppression")
        self.assertEqual(event["payload"]["component_ref"],
                         "sensor.competition-denial-air@1.0.0")

    def test_profiles_are_well_formed_and_calibration_levers_are_present(self):
        for name, profile in retune.PROFILES.items():
            self.assertTrue(profile, name)
            for package, spec in profile.items():
                self.assertTrue(package.startswith("md_"), (name, package))
                allowed = {"horizon", "maximum_gap_ticks", "maximum_age_ticks", "thresholds",
                           "zone_shifts", "zone_baseline_centroids", "zone_centroids",
                           "zone_shift_m", "suppressions", "standoff_m", "anchor_shifts",
                           "contact_shift_m", "standoff_faction", "contact_faction"}
                self.assertLessEqual(set(spec), allowed, (name, package))
        self.assertIn("unit.r01", retune.PROFILES["trk-calibrate-v1"]["md_trk_001_standard"]
                      ["anchor_shifts"])

    def test_dry_run_reports_without_touching_the_file(self):
        with tempfile.TemporaryDirectory() as folder:
            tree = Path(folder)
            package = tree / "md_trk_001_standard"
            package.mkdir()
            path = package / "scenario.yaml"
            path.write_text(yaml.safe_dump(scenario_payload(), sort_keys=False), encoding="utf-8")
            before = path.read_bytes()
            report = retune.tune(tree, "trk-calibrate-v1", dry_run=True)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(report["changed_packages"], 1)
            self.assertTrue(report["dry_run"])
            self.assertGreater(report["total_changes"], 0)

    def test_tune_is_idempotent_on_disk(self):
        with tempfile.TemporaryDirectory() as folder:
            tree = Path(folder)
            package = tree / "md_trk_001_standard"
            package.mkdir()
            (package / "scenario.yaml").write_text(
                yaml.safe_dump(scenario_payload(), sort_keys=False), encoding="utf-8")
            first = retune.tune(tree, "trk-calibrate-v1")
            after_first = (package / "scenario.yaml").read_bytes()
            second = retune.tune(tree, "trk-calibrate-v1")
            self.assertGreater(first["total_changes"], 0)
            self.assertEqual(second["total_changes"], 0)
            self.assertEqual((package / "scenario.yaml").read_bytes(), after_first)


if __name__ == "__main__":
    unittest.main()
