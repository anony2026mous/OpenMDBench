"""Migrate our scenario packages to the S3 explicit-controller-endpoint contract.

``formal_v2.compile_formal_scenario_v2`` now rejects any compiled controller slot
without an explicit ``controller_endpoint_ref`` that resolves to a same-faction
entity carrying a communication component.  Our four other packages declare
``controller_slots`` but predate that field, so they no longer compile.

Migration rules, both validated on MD-AD-006:

* a slot covering exactly one entity gets ``controller_endpoint_ref =`` that
  entity (zero-hop);
* a slot covering several entities is SPLIT into one slot per entity, each with
  its own endpoint.  A shared endpoint would require an available
  ``endpoint -> entity`` communication route for every other member, and when
  that endpoint dies the whole group's command delivery turns into
  ``communication.command_blocked`` — measured on MD-AD-006, where the intruder
  force went inert from tick 400 onward for exactly this reason.

Usage:
    python _w1_migrate_controller_slots.py            # dry run, report only
    python _w1_migrate_controller_slots.py --apply    # write the packages
"""
from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

import yaml

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
FORMAL = ROOT / "scenarios" / "formal"

TARGETS = (
    "md_ad_004_deception",
    "md_int_002_air_surface",
    "md_int_005_stealth_multi_axis",
    "md_int_006_saturation_roe",
)


def declared_entities(scenario: dict) -> list[dict]:
    found = [item for item in scenario.get("entities", ()) if isinstance(item, dict)]
    for event in scenario.get("events", ()) or ():
        if not isinstance(event, dict) or event.get("event_type") != "spawn":
            continue
        blueprint = (event.get("payload") or {}).get("entity")
        if isinstance(blueprint, dict):
            found.append(blueprint)
    return found


def resolves_to(selector: dict, entities: list[dict]) -> list[dict]:
    ids = selector.get("entity_ids")
    if ids:
        wanted = {str(item) for item in ids}
        return [e for e in entities if str(e["id"]) in wanted]
    chosen = entities
    factions = selector.get("factions")
    if factions:
        allowed = {str(item) for item in factions}
        chosen = [e for e in chosen if str(e.get("faction_id")) in allowed]
    tags = selector.get("tags")
    if tags:
        allowed = {str(item) for item in tags}
        chosen = [e for e in chosen if allowed <= {str(t) for t in e.get("tags", ()) or ()}]
    return chosen


def communicates(entity: dict) -> bool:
    return any(str(ref).startswith("communication.")
               for ref in entity.get("component_refs", ()) or ())


def migrate_slots(slots: list[dict], entities: list[dict]) -> tuple[list[dict], list[str]]:
    migrated: list[dict] = []
    notes: list[str] = []
    for slot in slots:
        if slot.get("controller_endpoint_ref"):
            migrated.append(copy.deepcopy(slot))
            continue
        members = sorted(resolves_to(slot.get("selector") or {}, entities),
                         key=lambda item: str(item["id"]))
        usable = [member for member in members if communicates(member)]
        if not usable:
            notes.append(f"{slot.get('id')}: no member can be an endpoint -> dropped")
            continue
        if len(usable) < len(members):
            missing = ",".join(str(m["id"]) for m in members if m not in usable)
            notes.append(f"{slot.get('id')}: members without a communication component "
                         f"are left uncontrolled: {missing}")
        # Deep-copy per emitted slot: a shallow copy would share the nested
        # ``selector`` / ``required_capabilities`` objects between slots, and
        # PyYAML then serialises them as anchors + aliases, which the package
        # loader rejects ("YAML aliases and anchors are not supported").
        if len(usable) == 1:
            single = copy.deepcopy(slot)
            single["controller_endpoint_ref"] = str(usable[0]["id"])
            migrated.append(single)
            continue
        # Split: one slot per entity, each zero-hop, each with a unique controller_id.
        for member in usable:
            entity_id = str(member["id"])
            split = copy.deepcopy(slot)
            split["id"] = f"{slot.get('id')}.{entity_id}"
            split["controller_id"] = f"agent.{entity_id}"
            split["selector"] = {"schema_version": "2.0", "entity_ids": [entity_id]}
            split["controller_endpoint_ref"] = entity_id
            migrated.append(split)
        notes.append(f"{slot.get('id')}: {len(usable)} entities -> split into "
                     f"{len(usable)} per-entity zero-hop slots")
    return migrated, notes


def main(argv: list[str]) -> int:
    apply_changes = "--apply" in argv
    print(f"formal scenario root = {FORMAL}")
    print(f"mode = {'APPLY' if apply_changes else 'DRY RUN'}\n")

    touched = 0
    for package in TARGETS:
        path = FORMAL / package / "scenario.yaml"
        if not path.exists():
            print(f"=== {package}: MISSING {path}")
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        scenario = payload.get("scenario") or payload
        entities = declared_entities(scenario)
        slots = list(scenario.get("controller_slots") or [])
        migrated, notes = migrate_slots(slots, entities)
        print(f"=== {package}: {len(slots)} slots -> {len(migrated)}")
        for note in notes:
            print(f"    note: {note}")
        already = sum(1 for slot in slots if slot.get("controller_endpoint_ref"))
        if already:
            print(f"    {already} slot(s) already declared an endpoint")
        if apply_changes:
            scenario["controller_slots"] = migrated
            if "scenario" in payload:
                payload["scenario"] = scenario
            else:
                payload = scenario
            path.write_text(
                yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=400),
                encoding="utf-8")
            touched += 1
            print(f"    WROTE {path}")
        print()

    if not apply_changes:
        print("dry run only; re-run with --apply to write the packages")
    else:
        print(f"updated {touched} package(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
