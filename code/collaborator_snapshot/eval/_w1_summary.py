"""Summarize a run_episode report: two-sided interaction evidence.

Reads the JSON report produced by ``run_episode.py --output`` and prints, per
side, the executed-fire count, first-fire tick, surviving/destroyed units and
the facilities' health, so "did both sides actually interact" is answerable
from one command.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))

    metrics = report.get("layered_metrics", {})
    print(f"scenario      : {report.get('scenario')}  seed={report.get('seed')}")
    print(f"planner       : {report.get('planner')}")
    print(f"ticks_run     : {report.get('ticks_run')}  "
          f"aborted={report.get('aborted')}  error={report.get('error')}")
    print(f"terminal      : {(report.get('terminal_result') or {}).get('result')} "
          f"/ {(report.get('terminal_result') or {}).get('rule_id')}")
    print(f"outcome       : {metrics.get('outcome')} "
          f"mission_success={metrics.get('mission_success')}")
    print()
    print("--- two-sided interaction ---")
    print(f"executed fires total    : {report.get('total_fires')}")
    print(f"  defender (blue)       : {report.get('total_fires_defender')} "
          f"first tick={metrics.get('first_fire_tick_defender')}")
    print(f"  intruder (red)        : {report.get('total_fires_intruder')} "
          f"first tick={metrics.get('first_fire_tick_intruder')}")
    print(f"attacker submissions    : {report.get('attack')}")
    print(f"defender fires (planner): "
          f"{metrics.get('fires_threat')} threat / {metrics.get('fires_decoy')} decoy "
          f"/ {metrics.get('fires_civilian')} civilian")
    print()

    entities = report.get("entities", ())
    print("--- force state at end of episode ---")
    by_faction: dict[str, Counter] = {}
    for entity in entities:
        by_faction.setdefault(str(entity.get("faction")), Counter())[
            str(entity.get("lifecycle"))] += 1
    for faction, counts in sorted(by_faction.items()):
        print(f"  {faction:<10} {dict(sorted(counts.items()))}")
    print()
    print("--- facilities (id prefix facility.) ---")
    for entity in sorted(entities, key=lambda item: str(item.get("entity_id"))):
        if str(entity.get("entity_id", "")).startswith("facility."):
            print(f"  {entity['entity_id']:<20} lifecycle={entity['lifecycle']:<10} "
                  f"health={entity['health']}")
    print()
    print("--- losses by side ---")
    for faction in sorted({str(e.get("faction")) for e in entities}):
        units = [e for e in entities if str(e.get("faction")) == faction]
        destroyed = [e for e in units
                     if str(e.get("lifecycle")) in {"destroyed", "wreck", "despawned"}]
        disabled = [e for e in units if str(e.get("lifecycle")) == "disabled"]
        print(f"  {faction:<10} total={len(units):<3} destroyed={len(destroyed):<3} "
              f"disabled={len(disabled):<3} active={len(units) - len(destroyed) - len(disabled)}")
    print()
    print("--- units with health < 1.0 ---")
    for entity in sorted(entities, key=lambda item: float(item.get("health", 1.0))):
        if float(entity.get("health", 1.0)) < 1.0:
            print(f"  {entity['entity_id']:<28} {entity['faction']:<10} "
                  f"lifecycle={entity['lifecycle']:<10} health={entity['health']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
