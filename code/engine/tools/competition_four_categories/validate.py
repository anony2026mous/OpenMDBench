"""Bounded native validation; policies receive controller observations and public briefs only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time

from openmdbench.schemas.interface_v2 import ActionBatchV2, PersistentCommandV2
from .build import ROOT, PACKAGES
from .runtime import create_candidate
from .protected_inputs import verify as verify_protected_inputs
from .visibility_audit import VisibilityAudit


class PrivacyGateError(AssertionError):
    def __init__(self, evidence: dict):
        super().__init__(f"private field leaked: {evidence['violation']}")
        self.evidence = evidence


def public_route(brief: dict) -> list[tuple[float, float]]:
    centers = [(sum(v[0] for v in z["coordinates_m"])/4,
                sum(v[1] for v in z["coordinates_m"])/4) for z in brief["search_zones"]]
    # Sweep the last public sector perimeter after visiting the centers. No target truth.
    last = brief["search_zones"][-1]["coordinates_m"]
    return centers + [(float(x), float(y)) for x, y in last]

def navigate(observation: dict, brief: dict, waypoint: int):
    own = observation["own_entities"][0]
    x, y, _ = own["position_m"]
    route = public_route(brief)
    tx, ty = route[waypoint % len(route)]
    distance = math.hypot(tx-x, ty-y)
    if distance < 60:
        waypoint += 1
        tx, ty = route[waypoint % len(route)]
        distance = math.hypot(tx-x, ty-y)
    heading = math.degrees(math.atan2(tx-x, ty-y)) % 360
    return {"speed_mps": min(22., max(3., distance/3)),
            "heading_deg": heading, "altitude_m": 100.}, waypoint

def run(level: str, policy: str, seed: int) -> dict:
    path = PACKAGES / f"md_rec_001_{level}"
    brief = json.loads((path / "public_brief.json").read_text(encoding="utf-8"))
    session = create_candidate(path, seed=seed, session_id=f"candidate-{level}-{policy}-{seed}")
    began = time.monotonic()
    waypoint = 0
    trace = []
    terminal = None
    observations_checked = 0
    action_statuses = []
    try:
        auditor = VisibilityAudit(session, {"unit.r01": "slot.unit.r01"}, faction_id=brief["evaluated_side"])
        def checked_observation():
            observed = session.world_view.controller_observation(controller_slot_id="slot.unit.r01").model_dump(mode="json")
            failure = auditor.check({"unit.r01": observed})
            if failure:
                raise PrivacyGateError({**failure, "scenario_id": brief["scenario_id"], "difficulty": level, "policy": policy,
                    "seed": seed, "resolved_hash": session.resolved.resolved_hash, "model_registry_hash": session.resolved.model_registry_hash,
                    "engine_contact_source": "openmdbench/world/factory_v2.py", "engine_contact_source_sha256": hashlib.sha256((ROOT / "openmdbench/world/factory_v2.py").read_bytes()).hexdigest()})
            return observed
        for tick in range(brief["duration_seconds"] + 1):
            observation = checked_observation()
            observations_checked += 1
            if policy == "sweep" and tick < brief["scoring_deadline_tick"] and tick % 4 == 0:
                payload, waypoint = navigate(observation, brief, waypoint)
                command = PersistentCommandV2(schema_version="2.0", entity_id="unit.r01",
                    faction_id="red", based_on_tick=tick, valid_until_tick=tick+8,
                    command_id=f"nav-{tick}", command_type="navigation", payload=payload)
                batch = ActionBatchV2(schema_version="2.0", session_id=session.session_id,
                    batch_id=f"batch-{tick}", idempotency_key=f"batch-{tick}", faction_id="red",
                    based_on_tick=tick, valid_until_tick=tick+8, persistent_commands=(command,))
                grant = next(g for g in session.world_view.authority_tokens.values()
                             if g.controller_id == "agent.unit.r01" and g.entity_ids == ("unit.r01",))
                receipt = session.submit_actions(batch=batch, authority_token=grant.token,
                    operation_id=f"submit-{tick}", expected_tick=tick)
                action_statuses.append(str(receipt.status))
            session.step(operation_id=f"tick-{tick}", expected_tick=tick)
            mission = session.world_view.presentation_snapshot().mission_scoring_checkpoint
            terminal = mission["terminal_result"]
            own = checked_observation()["own_entities"][0]
            trace.append({"tick": session.world_view.tick, "position_m": own["position_m"],
                          "scores": dict(mission["score_state"]),
                          "terminal": dict(terminal) if terminal else None})
            if terminal:
                break
        if terminal is None:
            raise AssertionError("native mission did not terminate at its configured horizon")
        return {"scenario_id": "MD-REC-001", "difficulty": level, "policy": policy,
                "seed": seed, "status": "candidate_validation_not_release",
                "elapsed_wall_seconds": round(time.monotonic()-began, 3),
                "final_tick": session.world_view.tick, "terminal": dict(terminal),
                "scores": dict(mission["score_state"]),
                "trace_sha256": hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest(),
                "trace": trace, "resolved_hash": session.resolved.resolved_hash,
                "catalog_hash": session.resolved.catalog_hash,
                "model_registry_hash": session.resolved.model_registry_hash,
                "validator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "public_brief_sha256": hashlib.sha256((path / "public_brief.json").read_bytes()).hexdigest(),
                "observations_checked": auditor.checked_observations, "visibility_audit": auditor.summary(),
                "action_statuses": sorted(set(action_statuses))}
    finally:
        if session.state.value == "running":
            session.stop()
        session.close()
        verify_protected_inputs()

def save_result(result: dict) -> Path:
    directory = ROOT / "artifacts/competition_four_categories"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = directory / f"rec001-{result['difficulty']}-{result['policy']}-{result['seed']}-{stamp}.json"
    target.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    return target

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="easy")
    parser.add_argument("--policy", choices=["idle", "sweep"], default="idle")
    parser.add_argument("--seed", type=int, default=601)
    parser.add_argument("--pilot-matrix", action="store_true",
                        help="Six bounded pilot episodes plus one deterministic easy/sweep repeat.")
    args = parser.parse_args()
    cases = ([(level, policy) for level in ("easy", "medium", "hard")
              for policy in ("idle", "sweep")] + [("easy", "sweep")]
             if args.pilot_matrix else [(args.difficulty, args.policy)])
    first_hash = None
    for level, policy in cases:
        try:
            result = run(level, policy, args.seed)
        except PrivacyGateError as error:
            directory = ROOT / "artifacts/competition_four_categories"
            directory.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            failure = directory / f"privacy-failure-{level}-{policy}-{args.seed}-{stamp}.json"
            failure.write_text(json.dumps(error.evidence, indent=2)+"\n", encoding="utf-8")
            print(f"FAILED_PRIVACY_GATE evidence={failure.relative_to(ROOT)}", flush=True)
            raise
        target = save_result(result)
        if level == "easy" and policy == "sweep":
            if first_hash is not None and first_hash != result["trace_sha256"]:
                raise AssertionError("same seed/resolved pilot replay differed")
            first_hash = result["trace_sha256"]
        print(json.dumps({"level": level, "policy": policy, "seed": args.seed,
                          "ticks": result["final_tick"], "outcome": result["terminal"]["outcome"],
                          "scores": result["scores"], "evidence": str(target.relative_to(ROOT))}), flush=True)

if __name__ == "__main__":
    main()
