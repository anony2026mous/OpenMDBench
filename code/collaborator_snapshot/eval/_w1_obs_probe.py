"""Probe the V2 observation payload the RL wrapper will consume.

Prints the exact key sets and value shapes of ``own_entities`` and
``contacts_by_faction`` for a real IE scenario, so the RL observation encoder is
built on measured fields rather than guessed ones.

Windows note: this constructs a session, so everything must live inside
``main()`` behind the ``__main__`` guard -- the MMG solver runs in a
``multiprocessing`` child and ``spawn`` re-imports ``__main__``.

Usage:
    python _w1_obs_probe.py [PUBLIC_ID] [TICKS]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main(public_id: str, ticks: int) -> int:
    from openmdbench.sessions.formal_v2 import create_formal_session_v2

    session = create_formal_session_v2(public_id, session_id="probe.obs", seed=7)
    session.load().start()
    try:
        for _ in range(ticks):
            session.step(operation_id=f"probe.obs.{session.world_view.tick:08d}",
                         expected_tick=session.world_view.tick)
        obs = session.world_view.observation(observer_faction_id="coalition.defender")
        print(f"public_id={public_id}  tick={obs.tick}  "
              f"observer={obs.observer_faction_id}")
        print(f"controlled_entity_ids = {len(obs.controlled_entity_ids)}")
        print(f"own_entities={len(obs.own_entities)}  "
              f"organic_contacts={len(obs.organic_contacts)}  "
              f"shared_contacts={len(obs.shared_contacts)}  "
              f"factions_in_contacts={sorted(obs.contacts_by_faction)}")

        if obs.own_entities:
            print("\n--- own_entities[0] ---")
            for key, value in sorted(obs.own_entities[0].items()):
                print(f"  {key:<28} {type(value).__name__:<10} {str(value)[:70]}")
            print("\n--- own_entities 全部 keys 并集 ---")
            keys = sorted({k for item in obs.own_entities for k in item})
            print("  " + ", ".join(keys))

        contacts = list(obs.contacts_by_faction.get(obs.observer_faction_id, ()))
        if contacts:
            print("\n--- 一个接触的字段 ---")
            for key, value in sorted(contacts[0].items()):
                print(f"  {key:<28} {type(value).__name__:<10} {str(value)[:70]}")
            print("\n--- 接触 keys 并集 ---")
            keys = sorted({k for item in contacts for k in item})
            print("  " + ", ".join(keys))
        print(f"\n我方可见接触数 = {len(contacts)}")

        # 弹药/能量是否可从观测拿到（RL 需要知道剩余弹）
        print("\n--- 我方单元可见的弹药/能量相关字段 ---")
        sample = obs.own_entities[0] if obs.own_entities else {}
        for key in sample:
            if any(token in key.lower() for token in ("ammo", "energy", "weapon", "cooldown", "capab")):
                print(f"  {key} = {str(sample[key])[:90]}")
    finally:
        session.stop()
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "IE-01-SINGLE-TARGET",
                          int(sys.argv[2]) if len(sys.argv) > 2 else 40))
