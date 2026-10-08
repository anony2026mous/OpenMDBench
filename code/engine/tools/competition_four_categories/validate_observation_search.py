"""Matched-speed public-observation REC trials; not competition acceptance.

The original reconnaissance policies, scenarios and execution adapters remain
unchanged. Full controller DTOs and submitted actions are streamed to a separate
referee-only JSONL artifact so interruption does not discard completed frames.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import time

from . import (denial_policy, observation_search_policy, recon_policy, runtime,
               tracking_policy, validate_denial, validate_emergency, validate_recon,
               validate_tracking, visibility_audit)
from .build import PACKAGES, ROOT
from .protected_inputs import verify

MODES = ("patrol", "adaptive")
RESULTS = ROOT / "artifacts/competition_four_categories"


def source_fingerprints():
    sha = validate_tracking.sha
    return {"validator_sha256": sha(__file__),
        "policy_source_sha256": sha(observation_search_policy.__file__),
        "base_policy_sha256": sha(recon_policy.__file__),
        "checkpoint_adapter_sha256": sha(validate_recon.__file__),
        "action_adapter_sha256": sha(validate_denial.__file__),
        "score_adapter_sha256": sha(validate_tracking.__file__),
        "privacy_validator_sha256": sha(validate_emergency.__file__),
        "visibility_validator_sha256": sha(visibility_audit.__file__),
        "navigation_validator_sha256": sha(tracking_policy.__file__),
        "wave_policy_source_sha256": sha(denial_policy.__file__),
        "runtime_source_sha256": sha(runtime.__file__)}


def run(number, mode, seed, comparison_plan):
    if number not in range(2, 9) or mode not in MODES:
        raise ValueError("observation-search trials require REC002..008 and a declared mode")
    verify()
    path = PACKAGES / f"md_rec_{number:03d}_standard"
    brief_path, opponent_path = path / "public_brief.json", path / "scripted_blue_policy.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    opponent = denial_policy.WaveNavigationPolicy(json.loads(opponent_path.read_text(encoding="utf-8")))
    controllers = {a["entity_id"]: observation_search_policy.ObservationSearchPolicy(brief, a["entity_id"], mode)
                   for a in brief["own_assets"]}
    slots = {i: f"slot.{i}" for i in controllers}
    sources = source_fingerprints()
    inputs = {p.name: validate_tracking.sha(p) for p in (path/"scenario.yaml", brief_path, opponent_path)}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    stream_path = RESULTS / f"observations-rec{number:03d}-{mode}-{seed}-{stamp}.jsonl"
    session = runtime.create_candidate(path, seed=seed, session_id=f"observation-rec{number}-{mode}-{seed}")
    trace, actions, began, failure = [], [], time.monotonic(), None
    try:
        with stream_path.open("x", encoding="utf-8") as stream:
            def emit(record):
                stream.write(json.dumps(record, sort_keys=True)+"\n")
                stream.flush()

            auditor = visibility_audit.VisibilityAudit(session, slots, faction_id=brief["evaluated_side"])
            red = validate_denial.observe_slots(session, slots)
            failure = validate_emergency.audit_observations(red, auditor=auditor)
            checked = len(red)
            emit({"type": "initial", "audience": "referee_only", "tick": 0,
                  "scenario_id": brief["scenario_id"], "mode": mode, "seed": seed,
                  "comparison_plan": comparison_plan, "source_fingerprints": sources,
                  "input_hashes": inputs, "resolved_hash": session.resolved.resolved_hash,
                  "controller_settings": observation_search_policy.SETTINGS, "observations": red})
            try:
                for tick in range(brief["adjudication_tick"]):
                    if failure:
                        break
                    submitted = []
                    released = {i: opponent.plan["controller_slots"][i] for i in opponent.active_ids(tick)}
                    blue = validate_denial.observe_slots(session, released)
                    for identifier, command in opponent.commands(tick, blue).items():
                        receipt = validate_denial.submit_navigation(session, identifier, "blue", tick, command)
                        submitted.append({"kind": "blue_navigation", "entity_id": identifier,
                            "tick": tick, "command": deepcopy(command), "status": str(receipt.status)})
                    for identifier, controller in controllers.items():
                        command = controller.navigation(red[identifier])
                        if command is not None:
                            receipt = validate_denial.submit_navigation(session, identifier, "red", tick, command)
                            submitted.append({"kind": "search_navigation", "entity_id": identifier,
                                "tick": tick, "command": deepcopy(command), "status": str(receipt.status)})
                        report = controller.report(red[identifier])
                        if report is not None:
                            receipt = validate_recon.submit_report(session, identifier, "red", tick, report)
                            submitted.append({"kind": "contact_report", "entity_id": identifier,
                                "tick": tick, "command": deepcopy(report), "status": str(receipt.status)})
                    actions.extend(submitted)
                    step = session.step(operation_id=f"tick-{tick}", expected_tick=tick)
                    red = validate_denial.observe_slots(session, slots)
                    checked += len(red)
                    failure = validate_emergency.audit_observations(red, auditor=auditor)
                    mission = session.world_view.presentation_snapshot().mission_scoring_checkpoint
                    scores, score_status = validate_tracking.score_evidence(step)
                    terminal = mission["terminal_result"]
                    row = {"tick": session.world_view.tick,
                        "own_states": {i: o["own_entities"] for i, o in red.items()},
                        "receiver_inboxes": {i: o.get("received_messages", []) for i, o in red.items()},
                        "action_receipts": [c.model_dump(mode="json") for c in step.child_receipts],
                        "scores": scores, "score_data_status": score_status,
                        "native_score_state": dict(mission["score_state"]),
                        "terminal": dict(terminal) if terminal else None}
                    trace.append(row)
                    emit({"type": "frame", **row, "observations": red, "submitted_actions": submitted,
                          "policy_diagnostics": {i: p.diagnostics() for i, p in controllers.items()}})
                    if failure or terminal:
                        break
                final = trace[-1] if trace else {"scores": {}, "terminal": None}
                if not failure and (not final["terminal"] or session.world_view.tick != brief["adjudication_tick"]):
                    raise AssertionError("recon trial must reach the unchanged natural deadline")
                checkpoint, plugin_states = validate_recon.referee_checkpoint_evidence(session)
                if failure is None and checkpoint["status"] == "FAILED_CHECKPOINT_GATE":
                    failure = checkpoint
                if sources != source_fingerprints() or inputs != {name: validate_tracking.sha(path/name) for name in inputs}:
                    raise AssertionError("trial source or canonical input changed during execution")
                emit({"type": "final", "tick": session.world_view.tick, "failure": failure,
                      "terminal": final["terminal"], "checkpoint": checkpoint})
            except Exception as error:
                emit({"type": "execution_error", "tick": session.world_view.tick,
                      "error_type": type(error).__name__, "error": str(error)})
                raise
        return {"scenario_id": brief["scenario_id"], "difficulty": brief["difficulty"],
            "policy": f"observation-{mode}", "seed": seed, "controller_settings": deepcopy(observation_search_policy.SETTINGS),
            "comparison_plan": comparison_plan, "competition_accepted": False,
            "scope": "matched-speed development baseline; not LLM/RL comparison or formal acceptance",
            "status": failure["status"] if failure else "candidate_validation_not_release", "failure": failure,
            "full_episode_completed": final["terminal"] is not None, "final_tick": session.world_view.tick,
            "scores": final["scores"], "terminal": final["terminal"], "trace": trace,
            "trace_sha256": hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest(),
            "observation_stream": stream_path.relative_to(ROOT).as_posix(),
            "observation_stream_sha256": validate_tracking.sha(stream_path),
            "submitted_actions": actions, "observations_checked": checked, "visibility_audit": auditor.summary(),
            "native_checkpoint_evidence": checkpoint, "referee_plugin_states": plugin_states,
            "elapsed_wall_seconds": round(time.monotonic()-began, 3),
            "resolved_hash": session.resolved.resolved_hash, "catalog_hash": session.resolved.catalog_hash,
            "model_registry_hash": session.resolved.model_registry_hash, **sources, "canonical_input_hashes": inputs,
            "scripted_policy_sha256": validate_tracking.sha(opponent_path),
            "public_brief_sha256": validate_tracking.sha(brief_path),
            "engine_contact_source_sha256": validate_tracking.sha(ROOT/"openmdbench/world/factory_v2.py"),
            "protected_input_integrity": verify()}
    finally:
        if session.state.value == "running":
            session.stop()
        session.close()
        verify()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=int, choices=range(2, 9), required=True)
    parser.add_argument("--seed", type=int, default=601)
    parser.add_argument("--mode", choices=(*MODES, "paired"), default="paired")
    args = parser.parse_args()
    modes = MODES if args.mode == "paired" else (args.mode,)
    RESULTS.mkdir(parents=True, exist_ok=True)
    plan = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "scenario": args.scenario,
        "seed": args.seed, "modes": modes, "settings": observation_search_policy.SETTINGS,
        "source_fingerprints": source_fingerprints(), "protocol": "development seed, matched control settings, unchanged canonical scenario"}
    plan_path = RESULTS / ("observation-search-plan-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+".json")
    plan_path.write_text(json.dumps(plan, indent=2)+"\n", encoding="utf-8")
    print(f"plan={plan_path.relative_to(ROOT)}", flush=True)
    failed = False
    for mode in modes:
        result = run(args.scenario, mode, args.seed, plan_path.relative_to(ROOT).as_posix())
        path = validate_recon.save_result(result)
        print(json.dumps({k: result[k] for k in ("scenario_id", "policy", "seed", "status", "final_tick", "scores", "terminal")}), flush=True)
        print(f"evidence={path.relative_to(ROOT)}", flush=True)
        failed |= result["failure"] is not None
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
