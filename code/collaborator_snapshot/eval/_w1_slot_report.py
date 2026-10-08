"""Report the declared controller slots of our scenario packages and the entity
set each selector resolves to.

Needed before adding the S3-mandatory ``controller_endpoint_ref``: a slot that
covers exactly one entity can safely use that entity as its endpoint (zero-hop),
whereas a slot covering several entities needs either a representative endpoint
(which introduces a route dependency) or a split into per-entity slots.

Usage:
    python _w1_slot_report.py [package ...]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
FORMAL = ROOT / "scenarios" / "formal"

DEFAULT_PACKAGES = (
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
    factions = selector.get("factions")
    tags = selector.get("tags")
    chosen = entities
    if factions:
        allowed = {str(item) for item in factions}
        chosen = [e for e in chosen if str(e.get("faction_id")) in allowed]
    if tags:
        allowed = {str(item) for item in tags}
        chosen = [e for e in chosen if allowed <= {str(t) for t in e.get("tags", ()) or ()}]
    return chosen


def main(argv: list[str]) -> int:
    packages = argv[1:] or list(DEFAULT_PACKAGES)
    for package in packages:
        path = FORMAL / package / "scenario.yaml"
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        scenario = payload.get("scenario") or payload
        entities = declared_entities(scenario)
        slots = scenario.get("controller_slots") or []
        print(f"=== {package}: {len(slots)} slots, {len(entities)} declared entities")
        for slot in slots:
            selector = slot.get("selector") or {}
            members = resolves_to(selector, entities)
            with_comms = [e for e in members
                          if any(str(ref).startswith("communication.")
                                 for ref in e.get("component_refs", ()) or ())]
            endpoint = slot.get("controller_endpoint_ref")
            print(f"  {slot.get('id'):<44} members={len(members):<3} "
                  f"with_comms={len(with_comms):<3} endpoint={endpoint}")
            if len(members) != len(with_comms):
                missing = [str(e["id"]) for e in members if e not in with_comms]
                print(f"      no communication component: {','.join(missing)}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
