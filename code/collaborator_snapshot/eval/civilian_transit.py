"""Deterministic transit driver for the neutral civilian faction.

Why this exists: the session materialises one control command per motion-eligible
entity every tick.  An entity that received no navigation/patrol/hold command is
driven by ``MotionEligibilityEntryV2.fallback_controls``, and for the MMG surface
model that fallback is ``{"nps": 0.0, "rudder_rad": 0.0}`` — i.e. the ship is
stopped.  A civilian lane therefore needs *someone* to command it, otherwise the
ships stand still and no longer cross the engagement corridor.

The driver is deliberately deterministic and stateless beyond its own bookkeeping:

* straight-line legs only (a leg fixes heading and speed, no steering logic);
* commands are refreshed every ``decision_interval_ticks`` and stay valid across
  the interval, exactly like the attack driver's persistent navigation batches;
* it submits through the public DTOs only and reads each civilian's own authority
  token, so it needs no engine internals.

It never touches weapons: firing at neutral shipping is blocked by the scenario's
ROE (``engagement_permitted: false``), not by this driver's restraint.

Usage:
    driver = CivilianTransitDriverV2(faction_id="coalition.civilian",
                                     routes={"civilian.ship-01": (180.0, 6.0), ...})
    driver(session)   # once per tick, before session.step()
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

from openmdbench.schemas.interface_v2 import ActionBatchV2, PersistentCommandV2

ACTIVE_LIFECYCLES = {"active", "degraded"}


class CivilianTransitDriverV2:
    """Steam each civilian along a fixed heading/speed leg."""

    def __init__(
        self,
        *,
        faction_id: str,
        routes: Mapping[str, Tuple[float, float]],
        decision_interval_ticks: int = 5,
        altitude_m: float = 0.0,
    ) -> None:
        self.faction_id = str(faction_id)
        # entity_id -> (heading_deg, speed_mps)
        self.routes = {str(k): (float(v[0]), abs(float(v[1])))
                       for k, v in routes.items()}
        self.decision_interval_ticks = max(1, int(decision_interval_ticks))
        self.altitude_m = float(altitude_m)
        self.stats: Dict[str, int] = {"submitted_batches": 0, "commanded_entities": 0}

    @staticmethod
    def _authority_by_entity(session) -> Dict[str, str]:
        return {
            grant.entity_id: token
            for token, grant in session.world_view.authority_tokens.items()
        }

    def __call__(self, session) -> Dict[str, Any]:
        tick = int(session.world_view.tick)
        if tick % self.decision_interval_ticks != 0:
            return {"submitted": 0, "refresh": False}

        valid_until = tick + self.decision_interval_ticks
        tokens = self._authority_by_entity(session)
        submitted = 0
        for item in session.world_view.entities_stable():
            entity_id = str(item.id)
            if str(item.faction_id) != self.faction_id:
                continue
            if str(item.state.lifecycle) not in ACTIVE_LIFECYCLES:
                continue
            route = self.routes.get(entity_id)
            if route is None:
                continue
            token = tokens.get(entity_id)
            if token is None:
                continue
            heading_deg, speed_mps = route
            suffix = f"{entity_id}.{tick}"
            session.submit_actions(
                batch=ActionBatchV2(
                    schema_version="2.0",
                    session_id=session.session_id,
                    batch_id=f"eval.civilian.batch.{suffix}",
                    idempotency_key=f"eval.civilian.idem.{suffix}",
                    faction_id=self.faction_id,
                    based_on_tick=tick,
                    valid_until_tick=valid_until,
                    persistent_commands=(
                        PersistentCommandV2(
                            schema_version="2.0",
                            command_id=f"eval.civilian.nav.{suffix}",
                            command_type="navigation",
                            entity_id=entity_id,
                            faction_id=self.faction_id,
                            based_on_tick=tick,
                            valid_until_tick=valid_until,
                            payload={
                                "speed_mps": speed_mps,
                                "heading_deg": heading_deg,
                                "altitude_m": self.altitude_m,
                            },
                        ),
                    ),
                    discrete_actions=(),
                ),
                authority_token=token,
                operation_id=f"eval.civilian.submit.{suffix}",
                expected_tick=tick,
            )
            submitted += 1

        self.stats["submitted_batches"] += 1
        self.stats["commanded_entities"] = submitted
        return {"submitted": submitted, "refresh": True}


def civilian_routes(profile_data: Mapping[str, Any]) -> Dict[str, Tuple[float, float]]:
    """Read the civilian lane declaration from ``agents.yaml``.

    Declared as an ``attack.timeline`` entry is *not* enough — that only tells the
    LLM what the traffic is.  The motion declaration lives under
    ``civilian_lane`` so the scenario owns both halves of the fact:
    ``routes`` here and the non-threat statement in the timeline.
    """

    lane = dict(profile_data.get("civilian_lane") or {})
    routes: Dict[str, Tuple[float, float]] = {}
    for entry in lane.get("routes", ()) or ():
        entity_id = entry.get("entity_id")
        if not entity_id:
            continue
        routes[str(entity_id)] = (float(entry.get("heading_deg", 180.0)),
                                  float(entry.get("speed_mps", 6.0)))
    return routes


def optional_route_heading(entry: Mapping[str, Any]) -> Optional[float]:
    heading = entry.get("heading_deg")
    return None if heading is None else float(heading)
