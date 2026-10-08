"""Diagnose harness-side classification of MD-AD-006 own entities.

Read-only: builds the session, loads it, and prints for the defender faction
   entity_id | tags | domain | platform_kind | is_mobile(agent) | dynamics model_ref
so we can see exactly which entities the executor would send motion commands to.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("OPENMDBENCH_ROOT")
            or Path(__file__).resolve().parents[2] / "source-code" / "source_codes")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from openmdbench.sessions.formal_v2 import create_formal_session_v2  # noqa: E402

from v2_agent import AgentV2  # noqa: E402
from v2_executor import platform_kind  # noqa: E402

PUBLIC_ID = os.environ.get("SMOKE_SCENARIO", "IE-08-ISLAND-STRIKE")


def main() -> int:
    session = create_formal_session_v2(PUBLIC_ID, session_id="audit.classify", seed=7)
    session.load().start()
    session.step(operation_id="audit.classify.0", expected_tick=0)
    print(f"{'entity':<26} {'tags':<46} {'domain':<8} {'kind':<6} "
          f"{'agent_mobile':<12} dynamics_model_ref")
    for entity in sorted(session.world_view.entities_stable(), key=lambda e: e.id):
        if entity.faction_id != "coalition.defender":
            continue
        bindings = (getattr(getattr(entity, "definition", None),
                            "resource_bindings", None) or {}).get("dynamics", ())
        refs = ",".join(str(getattr(b, "model_ref", "<no model_ref attr>"))
                        for b in bindings) or "-"
        print(f"{entity.id:<26} {','.join(entity.tags):<46} "
              f"{str(getattr(entity, 'domain', '') or ''):<8} "
              f"{platform_kind(entity):<6} "
              f"{str(AgentV2._is_mobile(entity)):<12} {refs}")
    session.stop()
    session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
