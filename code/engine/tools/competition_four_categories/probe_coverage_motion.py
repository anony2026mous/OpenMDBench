"""Partial native replay to inspect motion receipts; never a completed episode."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import yaml
from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2, RunnerModeV2
from openmdbench.world.factory_v2 import WorldFactoryV2

from .build import ROOT
from .runtime import compile_package
from .coverage_tracking_policy import CoverageReportingPolicy
from . import coverage_tracking_policy
from .shore_beacon_policy import ShoreBindingPolicy, BeaconIdentityReportingPolicy
from .tracking_policy import ScheduledNavigationPolicy
from . import validate_tracking as adapter, validate_response, validate_emergency
from .protected_inputs import verify
from .visibility_audit import VisibilityAudit


def probe(reference_path, stop_tick=60, policy_variant=False):
    reference_path = reference_path.resolve()
    allowed = (ROOT/"artifacts/competition_four_categories").resolve()
    if not reference_path.is_relative_to(allowed): raise ValueError("candidate artifact reference required")
    ref = json.loads(reference_path.read_text(encoding="utf-8"))
    current_policy_hash = adapter.sha(coverage_tracking_policy.__file__)
    changed_policy = ref.get("coverage_policy_sha256") != current_policy_hash
    if changed_policy and not policy_variant: raise ValueError("policy changed; use explicitly labelled policy-variant diagnostics")
    folder = (ROOT/ref["staged_input_path"]).resolve()
    if not folder.is_relative_to(allowed/"calibration_inputs"): raise ValueError("staged calibration inputs required")
    for name, digest in ref["staged_input_hashes"].items():
        if adapter.sha(folder/name) != digest: raise ValueError("staged input digest mismatch")
    package = yaml.safe_load((folder/"scenario.yaml").read_text(encoding="utf-8"))
    brief = json.loads((folder/"public_brief.json").read_text(encoding="utf-8"))
    opponent = ScheduledNavigationPolicy(json.loads((folder/"scripted_blue_policy.json").read_text(encoding="utf-8")))
    if not 1 <= stop_tick < brief["adjudication_tick"]: raise ValueError("probe must be explicitly shorter than the episode")
    policy = "coverage" if ref["policy"] == "calibration-coverage-honest" else "beacon"
    actor = CoverageReportingPolicy if policy == "coverage" else BeaconIdentityReportingPolicy
    agents = {i: actor(brief, i, "honest") for i in brief["track_reporting"]["reporter_ids"]}
    support = {i: ShoreBindingPolicy(brief, i) for i in brief["observers"] if brief["observer_domains"][i] == "shore" and i not in agents}
    controllers = {**agents, **support}
    resolved, catalog = compile_package(package)
    if resolved.resolved_hash != ref["resolved_hash"]: raise ValueError("resolved scenario differs from the original trial")
    session = SessionLifecycleV2.create(session_id=f"coverage-trk008-{ref['asset_profile']}-{policy}-honest-{ref['seed']}",
        seed=ref["seed"], resolved=resolved, expected_resolved_hash=resolved.resolved_hash,
        catalog_hash=resolved.catalog_hash, model_registry_hash=resolved.model_registry_hash,
        world_factory=WorldFactoryV2(model_registry=catalog.model_registry), runner_mode=RunnerModeV2.LOCKSTEP,
        physics_dt_seconds=resolved.world.tick_seconds, decision_interval_ticks=1).load().start()
    collisions, commands, projections = [], [], []
    matching_ticks = 0
    try:
        auditor = VisibilityAudit(session, {i:f"slot.{i}" for i in brief["observers"]}, faction_id=brief["evaluated_side"])
        red = adapter.observe(session, brief["observers"])
        assert validate_emergency.audit_observations(red, auditor=auditor) is None
        for tick in range(stop_tick):
            blue = adapter.observe(session, opponent.entity_ids)
            for identifier, command in opponent.commands(tick, blue).items():
                adapter.submit_navigation(session, identifier=identifier, faction=opponent.plan["faction_id"],
                    tick=tick, payload=command["payload"], valid_until_tick=command["valid_until_tick"])
            if tick < brief["scoring_deadline_tick"] and tick % brief["track_reporting"]["suggested_interval_ticks"] == 0:
                outgoing = []
                for identifier, agent in controllers.items():
                    decision = agent.decide(red[identifier])
                    if decision["navigation"] is not None:
                        if identifier in support: raise ValueError("support navigation is not allowed")
                        adapter.submit_navigation(session, identifier=identifier, faction=brief["evaluated_side"], tick=tick,
                            payload=decision["navigation"], valid_until_tick=min(tick+8,brief["scoring_deadline_tick"]))
                        commands.append({"tick":tick,"entity_id":identifier,"payload":decision["navigation"]})
                    if any(row["sender_id"] != identifier for row in decision["messages"]): raise ValueError("wrong sender")
                    outgoing.extend(decision["messages"])
                validate_response.submit_source_messages(session, actions=outgoing, faction=brief["evaluated_side"], tick=tick)
            step = session.step(operation_id=f"tick-{tick}", expected_tick=tick)
            for receipt in step.world_receipt.motion_receipts:
                collisions.extend(asdict(event) for event in receipt.collision_events)
            red = adapter.observe(session, brief["observers"])
            assert validate_emergency.audit_observations(red, auditor=auditor) is None
            scores, status = adapter.score_evidence(step)
            projection = {"tick":session.world_view.tick,"red_own_states":{i:o["own_entities"] for i,o in red.items()},
                "referee_blue_states":{i:o["own_entities"] for i,o in adapter.observe(session,opponent.entity_ids).items()},
                "observed_contact_counts":{i:len(o["organic_contacts"]) for i,o in red.items()},
                "scores":scores,"score_data_status":status}
            original = {k:ref["trace"][tick][k] for k in projection}
            if projection == original: matching_ticks += 1
            elif not policy_variant: raise AssertionError(f"probe diverged from original native trajectory at {tick+1}")
            projections.append(projection)
        return {"diagnostic_partial":True,"full_episode_completed":False,"final_tick":session.world_view.tick,
            "native_terminal":session.world_view.presentation_snapshot().mission_scoring_checkpoint["terminal_result"],
            "reference":reference_path.relative_to(ROOT).as_posix(),"reference_sha256":adapter.sha(reference_path),
            "probe_source_sha256":adapter.sha(__file__),"matched_original_prefix":matching_ticks==stop_tick,
            "matching_prefix_ticks":matching_ticks,"policy_variant":policy_variant,
            "current_policy_sha256":current_policy_hash,"reference_policy_sha256":ref.get("coverage_policy_sha256"),
            "control_version":coverage_tracking_policy.POLICY_VERSION,
            "comparison_scope":"entity states, contact counts and native raw scores/data status for each prefix tick",
            "collisions":collisions,"commands":commands,"trace":projections,"visibility_audit":auditor.summary()}
    finally:
        if session.state.value == "running":session.stop()
        session.close();verify()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--reference",type=Path,required=True);parser.add_argument("--ticks",type=int,default=60);parser.add_argument("--policy-variant",action="store_true");args=parser.parse_args()
    result=probe(args.reference,args.ticks,args.policy_variant);stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ");path=ROOT/"artifacts/competition_four_categories"/f"coverage-motion-probe-{stamp}.json"
    path.write_text(json.dumps(result,indent=2),encoding="utf-8");print(json.dumps({k:result[k] for k in ['diagnostic_partial','full_episode_completed','final_tick','matched_original_prefix']}));print('COLLISIONS',json.dumps(result['collisions'][:5]));print(f'evidence={path.relative_to(ROOT)}')


if __name__=="__main__":main()
