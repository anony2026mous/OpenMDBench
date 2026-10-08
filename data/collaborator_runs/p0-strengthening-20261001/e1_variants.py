"""Authorized wave-time variants; immutable original engine, unchanged semantics.

Only a copied formal registry and newly generated scenario/profile packages are
written. No physics, policy, weapon, score, horizon or resource is changed.
"""
import argparse
import copy
from pathlib import Path
import shutil
import sys
import yaml
from common import read, write, digest

CONFIG = {
    "IE-05-MULTI-AXIS": ("ie_05_multi_axis", [0, 50, 100, 150, 200]),
    "IE-09-STAGGERED-WAVES": ("ie_09_staggered_waves", [0, 100, 200, 250, 300, 400]),
}


def transform(scene, profile, family, delay):
    s, p = copy.deepcopy(scene), copy.deepcopy(profile)
    core = s["scenario"]
    affected = []
    if family == "IE-05-MULTI-AXIS":
        # Native T0 remains byte/data equivalent; no artificial spawn-at-zero.
        affected = [e["id"] for e in core["entities"]
                    if e["faction_id"] == "coalition.intruder"
                    and e["initial_state"]["position_m"][1] < 0]
        if delay:
            retained = []
            for e in core["entities"]:
                if e["id"] not in affected:
                    retained.append(e)
                else:
                    core["events"].append({"schema_version": "2.0", "id": "spawn.e1." + e["id"],
                                           "event_type": "spawn", "trigger": {"kind": "tick", "tick": delay},
                                           "priority": 100, "depends_on": [], "payload": {"entity": e}})
            core["entities"] = retained
            p["attack"]["timeline"][1]["spawn_tick"] = delay
    else:
        for event in core["events"]:
            if event["event_type"] == "spawn":
                affected.append(event["payload"]["entity"]["id"])
                event["trigger"]["tick"] = delay
        p["attack"]["timeline"][1]["spawn_tick"] = delay
    # Compare full entity inventory including spawned entities.
    def inventory(c):
        rows = [*c["scenario"]["entities"],
                *(e["payload"]["entity"] for e in c["scenario"]["events"] if e["event_type"] == "spawn")]
        return {e["id"]: e for e in rows}
    if inventory(scene) != inventory(s):
        raise ValueError("Entity inventory/loadout/initial states changed")
    for key in core:
        if key not in ["entities", "events"] and core[key] != scene["scenario"][key]:
            raise ValueError(f"Forbidden scene change: {key}")
    for event in scene["scenario"]["events"]:
        if event["event_type"] != "spawn":
            match = next(e for e in core["events"] if e["id"] == event["id"])
            if match != event:
                raise ValueError("Non-spawn event changed (including horizon)")
    return s, p, affected


def prepare(repo, output):
    native = repo / "openmd/source-code/source_codes"
    engine = output / "experiment-engine"
    manifest_path = output / "variant_manifest.json"
    if manifest_path.exists():
        manifest = read(manifest_path)
        if digest(engine / 'scenarios/formal/registry.yaml') != manifest['registry_sha256']:
            raise ValueError('Resume registry hash mismatch')
        for name, sha in manifest['original_source_hashes'].items():
            if digest(native / name) != sha:
                raise ValueError('Original engine changed since freeze')
            if name != 'scenarios/formal/registry.yaml' and digest(engine / name) != sha:
                raise ValueError('Copied original engine changed since freeze')
        for row in manifest["variants"]:
            for name, sha in row["hashes"].items():
                if digest(engine / name) != sha:
                    raise ValueError("Resume variant hash mismatch")
        return manifest
    if engine.exists():
        raise FileExistsError("Incomplete variant preparation retained; use a new output")
    shutil.copytree(native, engine, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
    formal = engine / "scenarios/formal"
    registry_file = formal / "registry.yaml"
    registry = yaml.safe_load(registry_file.read_text(encoding="utf-8"))
    before = {str(p.relative_to(native)): digest(p) for p in native.rglob("*")
              if p.is_file() and p.suffix in [".py", ".yaml", ".json"]}
    variants = []
    for family, (slug, times) in CONFIG.items():
        entry = next(e for e in registry["scenarios"] if e["public_id"] == family)
        base_scene = yaml.safe_load((formal / slug / "scenario.yaml").read_text(encoding="utf-8"))
        base_profile = yaml.safe_load((formal / slug / "agents.yaml").read_text(encoding="utf-8"))
        for delay in times:
            name = f"e1_{slug}_t{delay:04d}"
            public = f"E1-{family}-T{delay:04d}"
            folder = formal / name
            folder.mkdir()
            scene, profile, affected = transform(base_scene, base_profile, family, delay)
            for filename, data in [("scenario.yaml", scene), ("agents.yaml", profile)]:
                (folder / filename).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            registry["scenarios"].append({**entry, "public_id": public, "package": name})
            variants.append({"family": family, "delay_ticks": delay, "public_id": public,
                             "package": name, "affected_entities": affected,
                             "hashes": {str(f.relative_to(engine)): digest(f) for f in folder.iterdir()}})
    registry_file.write_text(yaml.safe_dump(registry, allow_unicode=True, sort_keys=False), encoding="utf-8")
    # All original source/config files except the COPY's registry must match.
    copied_original = {name: digest(engine / name) for name in before}
    bad = [name for name in before if name != "scenarios/formal/registry.yaml" and before[name] != copied_original[name]]
    if bad:
        raise ValueError(f"Forbidden modifications to copied engine: {bad}")
    sys.path[:0] = [str(engine), str(repo / "openmd/code/eval")]
    __import__('os').environ['OPENMDBENCH_ROOT'] = str(engine)
    from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2
    import run_episode
    for row in variants:
        resolved, _ = compile_formal_scenario_v2(row["public_id"])
        row["resolved_hash"] = resolved.resolved_hash
        base, _ = compile_formal_scenario_v2(row["family"])
        base_profile = run_episode.load_attack_profile_data(row["family"])
        variant_profile = run_episode.load_attack_profile_data(row["public_id"])
        original_notes = run_episode._build_roe_notes(base_profile, briefing="withheld")
        variant_notes = run_episode._build_roe_notes(variant_profile, briefing="withheld")
        if original_notes != variant_notes:
            raise ValueError("Withheld prompt notes reveal treatment/changed information")
        row["withheld_notes_unchanged"] = True
        native_delay = 0 if row["family"] == "IE-05-MULTI-AXIS" else 250
        if row["delay_ticks"] == native_delay:
            if base.resolved_hash != resolved.resolved_hash:
                raise ValueError("Native timing clone is not compiled-equivalent")
            row["native_compiled_equivalent"] = True
    manifest = {"schema": "p0-e1-authorized-wave-times@1", "repo": str(repo), "engine": str(engine),
                "authorization": "User approved independent IE05/IE09 wave-time variants and frozen PPO, 2026-10-01",
                "original_source_hashes": before, "copy_only_registry_changed": True,
                "variants": variants, "registry_sha256": digest(registry_file),
                "calibration_seeds": list(range(1101, 1111)), "confirmation_seeds": list(range(1201, 1211)),
                "targets": [.4, .6, .8], "target_tolerance": .03,
                "stop_if_unreachable": True, "no_positive_outcome_guarantee": True}
    write(manifest_path, manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    print(__import__('json').dumps(prepare(a.repo.resolve(), a.output.resolve()), ensure_ascii=False)[-2500:])
