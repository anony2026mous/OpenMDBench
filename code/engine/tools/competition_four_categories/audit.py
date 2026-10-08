"""Evidence inventory, never an automatic competition-release approver."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from .build import ROOT, PACKAGES
from .runtime import compile_candidate
from .protected_inputs import verify as verify_protected_inputs
from . import validate, validate_emergency, validate_tracking, tracking_policy, validate_denial, denial_policy
from . import validate_recon, recon_policy
from . import validate_response, response_policy, message_policy
from . import visibility_audit
from . import validate_allocated_tracking
from . import validate_tracking_reports
from . import validate_identity_tracking
from . import validate_beacon_tracking
from . import validate_coverage_tracking
from .surface_profile import read_profile, PROFILE_PATH, PLATFORM_REF, DYNAMICS_REF
from .candidate_geometry import SURFACE_SHAPE_REF, SITE_SHAPE_REF

DOCS = ROOT.parents[1] / "doc/competition_four_categories"
RESULTS = ROOT / "artifacts/competition_four_categories"


def checkpoint_record_evidence(record):
    """Normalize recorder aliases, not the underlying native result or proof."""
    candidates = [(field, record[field]) for field in
                  ("native_checkpoint_evidence", "native_terminal_checkpoint_gate")
                  if isinstance(record.get(field), dict)]
    if not candidates:
        return {"status": "not_recorded", "source_field": None,
                "restoration_equivalence_proven": False}
    field, raw = next(((field, value) for field, value in candidates
                       if value.get("status") in {"FAILED", "FAILED_CHECKPOINT_GATE"}), candidates[0])
    status = raw.get("status", "unrecognized_status")
    return {"status": "FAILED_CHECKPOINT_GATE" if status == "FAILED" else status,
            "source_field": field, "raw_evidence": raw,
            # Successful extraction by itself is never continuation/replay proof.
            "restoration_equivalence_proven": False}


def checkpoint_test_gates(tests):
    def targeted(required):
        if not tests or tests.get("source_version_status") != "current":
            return "not_proven"
        if set(required) & set(tests.get("failed_test_names", ())):
            return "FAILED"
        return ("passed_targeted_fixture_only"
                if set(required) <= set(tests.get("passed_test_names", ())) else "not_proven")

    return {
        # The restore helper excludes only adapter-instance provenance hashes.
        # That is useful semantic evidence, never byte-exact hash equality.
        "checkpoint_full_hash_gate": "not_proven",
        "checkpoint_full_hash_scope_note": ("Restore fixtures compare durable state after excluding "
            "checkpoint_hash and motion fingerprint fields; byte-exact equivalence is not established."),
        "checkpoint_semantic_restore_gate": targeted({
            "test_native_dispatch_checkpoint_preserves_partial_dwell_and_weather",
            "test_native_delivered_dwell_checkpoint_preserves_exact_plugin_state",
            "test_native_tracking_checkpoint_preserves_nonzero_per_target_history"}),
        "checkpoint_missing_plugin_evidence_gate": targeted({
            "test_native_tracking_checkpoint_preserves_nonzero_per_target_history"}),
    }


def test_provenance_status(report):
    path = report.with_suffix(".provenance.json")
    if not path.exists():
        return "unrecorded"
    provenance = json.loads(path.read_text(encoding="utf-8"))
    source_hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / "tools/competition_four_categories").rglob("*.py"))}
    matches = (provenance.get("source_hashes") == source_hashes
        and provenance.get("test_report_sha256") == hashlib.sha256(report.read_bytes()).hexdigest()
        and provenance.get("source_unchanged_during_run") is True and provenance.get("timed_out") is False)
    if "artifact_hashes" in provenance:
        paths = [ROOT / "catalog/v2/competition_four_categories.yaml"] + [p for p in PACKAGES.rglob("*")
            if p.is_file() and p.suffix in {".yaml", ".json"}]
        actual = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
        matches = matches and provenance["artifact_hashes"] == actual and provenance.get("artifacts_unchanged_during_run") is True
    return "current" if matches else "stale"


def tracking_extension_sources(policy):
    if policy == "allocated":
        return validate_allocated_tracking.source_fingerprints()
    if policy in {f"report-{mode}" for mode in validate_tracking_reports.MODES}:
        return validate_tracking_reports.source_fingerprints()
    if policy in {f"identity-{mode}" for mode in validate_identity_tracking.MODES}:
        return validate_identity_tracking.source_fingerprints()
    if policy in {f"beacon-{mode}" for mode in validate_beacon_tracking.MODES}:
        return validate_beacon_tracking.source_fingerprints()
    if policy in {f"coverage-{mode}" for mode in validate_coverage_tracking.MODES}:
        return validate_coverage_tracking.source_fingerprints()
    return {}


def tracking_policy_extension_matches(record):
    sources = tracking_extension_sources(record.get("policy"))
    if str(record.get("policy")).startswith(("report-", "identity-", "beacon-", "coverage-")) and not sources:
        return False
    return all(record.get(k) == v for k, v in sources.items())


def recon_extension_sources(policy):
    if policy in {"observation-patrol", "observation-adaptive"}:
        from .validate_observation_search import source_fingerprints
        return source_fingerprints()
    return {}


def denial_extension_sources(policy):
    if policy not in {"salvo", "guard-instrumented", "screen-guard", "screen-salvo", "approach-salvo", "receipt-aware-salvo", "planning-lead-salvo"}:
        return {}
    from . import salvo_guard_policy, screen_guard_policy, approach_screen_policy, receipt_aware_screen_policy, planning_lead_policy, validate_salvo_denial
    sha = validate_tracking.sha
    return {"validator_sha256": sha(validate_salvo_denial.__file__),
        "policy_source_sha256": sha(planning_lead_policy.__file__ if policy == "planning-lead-salvo" else
                                     receipt_aware_screen_policy.__file__ if policy == "receipt-aware-salvo" else
                                     approach_screen_policy.__file__ if policy == "approach-salvo" else
                                     screen_guard_policy.__file__ if policy.startswith("screen-") else
                                     salvo_guard_policy.__file__ if policy == "salvo" else denial_policy.__file__),
        "salvo_base_policy_sha256": sha(salvo_guard_policy.__file__),
        "screen_base_policy_sha256": sha(screen_guard_policy.__file__),
        "approach_base_policy_sha256": sha(approach_screen_policy.__file__),
        "fire_feedback_adapter_sha256": sha(receipt_aware_screen_policy.__file__),
        "fire_feedback_protocol": receipt_aware_screen_policy.FEEDBACK_PROTOCOL if policy in {"receipt-aware-salvo", "planning-lead-salvo"} else None,
        "planning_lead_profile": dict(planning_lead_policy.PROFILE) if policy == "planning-lead-salvo" else None,
        "screen_settings": dict(screen_guard_policy.SETTINGS) if policy.startswith("screen-") or policy in {"approach-salvo", "receipt-aware-salvo", "planning-lead-salvo"} else None,
        "wave_policy_source_sha256": sha(denial_policy.__file__),
        "action_adapter_sha256": sha(validate_denial.__file__)}


def response_extension_sources(policy):
    if policy not in {"watch-coordinated", "progress-watch"}:
        return {}
    from . import standing_response_policy, progress_response_policy, validate_standing_response
    sha = validate_tracking.sha
    return {"validator_sha256": sha(validate_standing_response.__file__),
        "policy_source_sha256": sha(progress_response_policy.__file__ if policy == "progress-watch" else standing_response_policy.__file__),
        "standing_policy_source_sha256": sha(standing_response_policy.__file__),
        "response_base_policy_sha256": sha(response_policy.__file__),
        "response_message_adapter_sha256": sha(validate_response.__file__),
        "controller_settings": dict(standing_response_policy.SETTINGS),
        "progress_controller_settings": dict(progress_response_policy.SETTINGS) if policy == "progress-watch" else None}


def recon_policy_extension_matches(record):
    if not str(record.get("policy")).startswith("observation-"):
        return True
    from .observation_search_policy import SETTINGS
    sources = recon_extension_sources(record.get("policy"))
    if (not sources or any(record.get(k) != v for k, v in sources.items())
        or record.get("controller_settings") != SETTINGS):
        return False
    relative = record.get("observation_stream")
    if not isinstance(relative, str):
        return False
    path = (ROOT/relative).resolve()
    if not path.is_relative_to(RESULTS.resolve()) or not path.is_file():
        return False
    if hashlib.sha256(path.read_bytes()).hexdigest() != record.get("observation_stream_sha256"):
        raise ValueError(f"invalid observation stream digest: {path.name}")
    if [row["tick"] for row in record["trace"]] != list(range(1, record["final_tick"]+1)):
        raise ValueError("observation stream trial has incomplete tick coverage")
    with path.open(encoding="utf-8") as stream:
        def read_record():
            line = next(stream, None)
            if line is None:
                raise ValueError("truncated observation stream")
            return json.loads(line)

        initial = read_record()
        if (initial.get("type") != "initial" or initial.get("tick") != 0
            or initial.get("source_fingerprints") != sources
            or initial.get("seed") != record["seed"]
            or initial.get("scenario_id") != record["scenario_id"]
            or initial.get("mode") != record["policy"].removeprefix("observation-")
            or initial.get("controller_settings") != SETTINGS):
            raise ValueError("observation stream initial provenance differs from trial")
        actions = []
        for expected in record["trace"]:
            frame = read_record()
            if (frame.get("type") != "frame" or any(frame.get(k) != v for k, v in expected.items())
                or "observations" not in frame or "submitted_actions" not in frame):
                raise ValueError("observation stream frame differs from native trace")
            observations = frame["observations"]
            if ({i: obs["own_entities"] for i, obs in observations.items()} != expected["own_states"]
                or {i: obs.get("received_messages", []) for i, obs in observations.items()} != expected["receiver_inboxes"]):
                raise ValueError("observation DTO differs from recorded state or inbox")
            actions.extend(frame["submitted_actions"])
        if actions != record["submitted_actions"]:
            raise ValueError("observation stream actions differ from trial")
        final = read_record()
        if (final.get("type") != "final" or final.get("tick") != record["final_tick"]
            or final.get("terminal") != record["terminal"] or final.get("failure") != record.get("failure")
            or next(stream, None) is not None):
            raise ValueError("observation stream final status differs from trial")
    return True


def audit() -> dict:
    surface_profile = read_profile()
    contracts = json.loads((DOCS / "SCENARIO_CONTRACTS.json").read_text(encoding="utf-8"))
    validators = {"REC": hashlib.sha256(Path(validate.__file__).read_bytes()).hexdigest(),
                  "REC_EXPANDED": hashlib.sha256(Path(validate_recon.__file__).read_bytes()).hexdigest(),
                  "ER": hashlib.sha256(Path(validate_emergency.__file__).read_bytes()).hexdigest(),
                  "ER_RESPONSE": hashlib.sha256(Path(validate_response.__file__).read_bytes()).hexdigest(),
                  "TRK": hashlib.sha256(Path(validate_tracking.__file__).read_bytes()).hexdigest(),
                  "AD": hashlib.sha256(Path(validate_denial.__file__).read_bytes()).hexdigest()}
    engine_hash = hashlib.sha256((ROOT / "openmdbench/world/factory_v2.py").read_bytes()).hexdigest()
    visibility_hash = hashlib.sha256(Path(visibility_audit.__file__).read_bytes()).hexdigest()
    privacy_failures, legacy_visibility_evidence = [], []
    def classify_visibility_failure(failure):
        if failure.get("audit_contract") == visibility_audit.CONTRACT and failure.get("audit_source_sha256") == visibility_hash:
            privacy_failures.append(failure)
        else:
            legacy_visibility_evidence.append({**failure, "classification": "identifier_format_only"
                if failure.get("violation") == "unit.x" else "older_rule_not_currently_revalidated"})
    for path in sorted(RESULTS.glob("privacy-failure-*.json")):
        failure = json.loads(path.read_text(encoding="utf-8"))
        if failure["engine_contact_source_sha256"] == engine_hash:
            classify_visibility_failure({**failure, "evidence": path.relative_to(ROOT).as_posix()})
    records = []
    for path in sorted([*RESULTS.glob("rec001-*.json"), *RESULTS.glob("er-MD-ER-*.json"),
                        *RESULTS.glob("trk-MD-TRK-*.json"), *RESULTS.glob("ad-MD-AD-*.json"),
                        *RESULTS.glob("rec-MD-REC-*.json")]):
        raw = json.loads(path.read_text(encoding="utf-8"))
        trace = raw.get("trace", [])
        if hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest() != raw.get("trace_sha256"):
            raise ValueError(f"invalid raw trace digest: {path.name}")
        if not trace and not raw.get("failure"):
            raise ValueError(f"empty trace without a failed gate: {path.name}")
        if trace and (trace[-1]["scores"] != raw["scores"] or trace[-1]["terminal"] != raw["terminal"]):
            raise ValueError(f"summary differs from native trace: {path.name}")
        if raw.get("status") == "FAILED_PRIVACY_GATE" and raw.get("engine_contact_source_sha256") == engine_hash:
            classify_visibility_failure({"scenario_id": raw["scenario_id"], "tick": raw["final_tick"],
                **raw["failure"], "evidence": path.relative_to(ROOT).as_posix()})
        records.append((path, raw))
    by_id: dict[str, list] = {}
    for path in sorted(PACKAGES.glob("*/public_brief.json")):
        brief = json.loads(path.read_text(encoding="utf-8"))
        current_validator = validators.get(brief["scenario_id"].split("-")[1])
        if brief["scenario_id"].split("-")[1] == "REC" and (path.parent / "scripted_blue_policy.json").exists():
            current_validator = validators["REC_EXPANDED"]
        if brief.get("response_protocol") == "dispatch-task@1.0":
            current_validator = validators["ER_RESPONSE"]
        resolved, _ = compile_candidate(path.parent)
        brief_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        matches = [(p, r) for p, r in records
                   if r["scenario_id"] == brief["scenario_id"]
                   and r["difficulty"] == brief["difficulty"]
                   and r["resolved_hash"] == resolved.resolved_hash
                   and r["catalog_hash"] == resolved.catalog_hash
                   and r["model_registry_hash"] == resolved.model_registry_hash
                   and r.get("validator_sha256") == (
                       tracking_extension_sources(r.get("policy")).get("validator_sha256", current_validator)
                       if brief["scenario_id"].startswith("MD-TRK-")
                       else recon_extension_sources(r.get("policy")).get("validator_sha256", current_validator)
                       if brief["scenario_id"].startswith("MD-REC-")
                       else denial_extension_sources(r.get("policy")).get("validator_sha256", current_validator)
                       if brief["scenario_id"].startswith("MD-AD-")
                       else response_extension_sources(r.get("policy")).get("validator_sha256", current_validator)
                       if brief["scenario_id"].startswith("MD-ER-") else current_validator)
                   and r.get("public_brief_sha256") == brief_hash
                   and r.get("visibility_audit", {}).get("contract") == visibility_audit.CONTRACT
                   and r.get("visibility_audit", {}).get("source_sha256") == visibility_hash]
        opponent_path = path.parent / "scripted_blue_policy.json"
        if opponent_path.exists():
            opponent_hash = hashlib.sha256(opponent_path.read_bytes()).hexdigest()
            family = brief["scenario_id"].split("-")[1]
            policy_module = {"TRK": tracking_policy, "AD": denial_policy, "REC": recon_policy}[family]
            policy_hash = hashlib.sha256(Path(policy_module.__file__).read_bytes()).hexdigest()
            matches = [(p, r) for p, r in matches if r.get("scripted_policy_sha256") == opponent_hash
                       and r.get("policy_source_sha256") == (
                           recon_extension_sources(r.get("policy")).get("policy_source_sha256", policy_hash)
                           if family == "REC" else denial_extension_sources(r.get("policy")).get("policy_source_sha256", policy_hash)
                           if family == "AD" else policy_hash)
                       and r.get("privacy_validator_sha256") == validators["ER"]]
            if family == "TRK":
                matches = [(p, r) for p, r in matches if tracking_policy_extension_matches(r)]
            if family in {"AD", "REC"}:
                navigation_hash = hashlib.sha256(Path(tracking_policy.__file__).read_bytes()).hexdigest()
                matches = [(p, r) for p, r in matches if r.get("navigation_validator_sha256") == navigation_hash
                           and r.get("score_adapter_sha256") == validators["TRK"]]
            if family == "AD":
                matches = [(p, r) for p, r in matches if all(r.get(key) == value
                    for key, value in denial_extension_sources(r.get("policy")).items())]
                from . import denial_harm_audit
                harm_hash = hashlib.sha256(Path(denial_harm_audit.__file__).read_bytes()).hexdigest()
                matches = [(p, r) for p, r in matches
                           if r.get("harm_audit_source_sha256") == harm_hash]
            if family == "REC":
                wave_hash = hashlib.sha256(Path(denial_policy.__file__).read_bytes()).hexdigest()
                matches = [(p, r) for p, r in matches if r.get("wave_policy_source_sha256") == wave_hash
                           and r.get("action_adapter_sha256") == validators["AD"]
                           and recon_policy_extension_matches(r)]
        source_path = path.parent / "scripted_message_policy.json"
        if brief.get("response_protocol") == "dispatch-task@1.0":
            nominal = json.loads(source_path.read_text(encoding="utf-8"))
            source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
            actor_hash = hashlib.sha256(Path(message_policy.__file__).read_bytes()).hexdigest()
            policy_hash = hashlib.sha256(Path(response_policy.__file__).read_bytes()).hexdigest()
            verified = []
            for record_path, record in matches:
                expected = message_policy.sample_schedule(nominal, seed=record["seed"],
                    maximum_shift_ticks=brief["notice_timing_variation_ticks"])
                if (record.get("source_plan_sha256") == source_hash and record.get("source_policy_sha256") == actor_hash
                    and record.get("policy_source_sha256") == response_extension_sources(record.get("policy")).get("policy_source_sha256", policy_hash)
                    and all(record.get(k) == v for k, v in response_extension_sources(record.get("policy")).items())
                    and record.get("source_realization") == expected
                    and record.get("source_realization_sha256") == validate_response.plan_hash(expected)
                    and record.get("privacy_validator_sha256") == validators["ER"]
                    and record.get("action_adapter_sha256") == validators["AD"]
                    and record.get("score_adapter_sha256") == validators["TRK"]
                    and record.get("checkpoint_adapter_sha256") == validators["REC_EXPANDED"]):
                    verified.append((record_path, record))
            matches = verified
        summary = []
        by_run: dict[tuple, list] = {}
        for record_path, record in matches:
            key = (record["policy"], record["seed"])
            if not record.get("failure"):
                by_run.setdefault(key, []).append(record)
            summary.append({"policy": record["policy"], "seed": record["seed"],
                            "ticks": record["final_tick"],
                            "status": record["status"], "failure": record.get("failure"),
                            "checkpoint_gate": checkpoint_record_evidence(record),
                            "full_episode_completed": record.get("full_episode_completed", record["terminal"] is not None),
                            "visibility_audit": record["visibility_audit"],
                            "outcome": record["terminal"]["outcome"] if record["terminal"] else None,
                            "scores": record["scores"], "trace_sha256": record["trace_sha256"],
                            "evidence": str(record_path.relative_to(ROOT)).replace("\\", "/")})
        repeated = [runs for runs in by_run.values() if len(runs) > 1]
        repeat_status = ("not_tested" if not repeated else "passed"
                         if all(len({r["trace_sha256"] for r in runs}) == 1 for runs in repeated)
                         else "FAILED")
        by_id.setdefault(brief["scenario_id"], []).append({
            "difficulty": brief["difficulty"], "package": str(path.parent.relative_to(ROOT)),
            "compiled": True, "resolved_hash": resolved.resolved_hash,
            "current_version_runs": summary, "repeated_run_determinism": repeat_status,
            "competition_accepted": False,
            "unmet_gates": json.loads((path.parent / "acceptance_gaps.json").read_text(encoding="utf-8"))["unmet_gates"]
                if (path.parent / "acceptance_gaps.json").exists() else ["full contract verification pending"]})
    rows = [{"scenario_id": row["id"], "template": row["template"],
             "name": row["name"], "design_contract_present": True,
             "runtime_candidates": by_id.get(row["id"], []),
             "full_contract_verified": False, "competition_accepted": False,
             "status": "candidate_partial_validation" if row["id"] in by_id else "design_only_runtime_pending"}
            for row in contracts["scenarios"]]
    test_reports = sorted(RESULTS.glob("pytest-candidate-*.xml"))
    test_path = test_reports[-1] if test_reports else RESULTS / "pytest-candidate-missing.xml"
    tests = None
    if test_path.exists():
        suite = ET.parse(test_path).getroot().find("testsuite")
        tests = {key: suite.attrib.get(key) for key in ("tests", "failures", "errors", "skipped", "time")}
        tests["scope"] = "candidate metric/compile/native regression tests only, not 28-scenario acceptance"
        tests["evidence"] = str(test_path.relative_to(ROOT))
        cases = suite.findall("testcase")
        tests["failed_test_names"] = [case.attrib["name"] for case in cases
                                       if case.find("failure") is not None or case.find("error") is not None]
        tests["nonpassing_skipped_or_xfail"] = [case.attrib["name"] for case in cases
                                                if case.find("skipped") is not None]
        tests["passed_test_names"] = [case.attrib["name"] for case in cases
                                      if case.find("failure") is None and case.find("error") is None
                                      and case.find("skipped") is None]
        tests["suite_status"] = "FAILED" if tests["failed_test_names"] else "passed_subset_only"
        provenance_path = test_path.with_suffix(".provenance.json")
        tests["source_version_status"] = test_provenance_status(test_path)
        if provenance_path.exists():
            tests["provenance_evidence"] = provenance_path.relative_to(ROOT).as_posix()
    supplements = []
    for name, scope in [
        ("pytest-screen-calibration-20260930.xml", "public own-capability metadata, screening controller, frozen seed-major calibration and resume-integrity tests; not release acceptance"),
        ("pytest-task-contract-controls-20260930.xml", "public ER standing goals, native-scene invariance, salvo/response control boundaries and checkpoint-alias interpretation; not competition acceptance"),
        ("pytest-observation-search-20260930.xml", "public-observation controller, matched settings, streamed DTO/action integrity and existing REC contracts; unit/configuration evidence only"),
        ("pytest-terminal-evidence-20260930.xml", "distinct terminal outcomes for all 30 difficulty packages, four native arbitration fixtures, affected scenario regressions; not full competition acceptance"),
        ("pytest-tracking-unit.xml", "tracking metric/config/policy/score-adapter retest"),
        ("pytest-denial-native.xml", "denial native mechanism, metric and configuration tests"),
        ("pytest-denial-exhaustion.xml", "native finite-magazine and protected-input guard retest"),
        ("pytest-protected-inputs.xml", "engine/catalog/legacy scenario freeze negative tests"),
        ("pytest-recon-metrics.xml", "grouped reconnaissance and delivered-report metric tests"),
        ("pytest-recon-unit.xml", "expanded reconnaissance metric/configuration/policy tests"),
        ("pytest-recon-all.xml", "expanded reconnaissance configuration/policy/metric/native regression"),
        ("pytest-recon-native.xml", "expanded reconnaissance native mechanisms only"),
        ("pytest-delivered-dispatch-unit.xml", "native-delivery dispatch model and message policy unit tests"),
        ("pytest-response-targeted.xml", "delivered response model and native notification integration"),
        ("pytest-response-regression.xml", "new response module plus local emergency compatibility regression"),
        ("pytest-visibility-unit.xml", "native-evidence visibility positive and injected-leak negative unit tests"),
        ("pytest-visibility-native.xml", "native sensing/sharing/inbox visibility without a recovery checkpoint"),
        ("pytest-visibility-regression.xml", "candidate unit and targeted native visibility regression"),
        ("pytest-surface-calibration-unit.xml", "native speed mapping calibration methodology tests"),
        ("pytest-surface-mapping.xml", "candidate resource evidence, conservative geometry and native collision tests"),
        ("pytest-surface-cooperative-unit.xml", "surface resource and public-information cooperative tracking unit tests"),
        ("pytest-surface-regression.xml", "surface mapping, geometry and affected candidate regression"),
        ("pytest-allocated-tracking-unit.xml", "public-observation three-dimensional allocation policy tests"),
        ("pytest-allocated-tracking-regression.xml", "all candidate unit and allocation-source-binding regression; native episodes recorded separately"),
        ("pytest-track-report-native-initial.xml", "initial native report integration attempt; historical failures retained"),
        ("pytest-track-report-regression.xml", "candidate unit and native delivered-report contract regression"),
        ("pytest-identity-regression.xml", "candidate unit and native identity/peer-report contract regression"),
        ("pytest-shore-beacon-regression.xml", "candidate unit and native shore binding/identity contract regression"),
        ("pytest-coverage-budget-regression.xml", "all candidate unit and coverage/budget configuration regression; native calibration episodes recorded separately"),
        ("pytest-coverage-range-hold-regression.xml", "all candidate unit tests for surface range-hold control; full trials and partial motion probes recorded separately"),
        ("pytest-trk008-promotion-regression.xml", "candidate input promotion, all unit tests and affected native entrypoint contracts"),
        ("pytest-denial-harm-focused.xml", "initial failed harm-attribution attempt; ordinary tick receipts omit immediate weapon damage"),
        ("pytest-denial-harm-regression.xml", "historical failed native harm fixture and diagnostic serialization; retained, not acceptance"),
        ("pytest-denial-harm-ledger-regression.xml", "all candidate unit tests and native complete-ledger harm/replay fixtures; not full competition acceptance"),
        ("pytest-denial-harm-tail-regression.xml", "all candidate units, native harm fixtures and strict noncombat-tail evidence guards; terminal checkpoint failures stay open"),
        ("pytest-localization-focused.xml", "native measurement geometry, source linkage and paired 12-tick noninterference fixture; not agent trajectory error"),
        ("pytest-localization-regression.xml", "all candidate units, native harm fixtures and paired native localization fixture; not full competition acceptance"),
    ]:
        focused_path = RESULTS / name
        if focused_path.exists():
            focused = ET.parse(focused_path).getroot().find("testsuite")
            supplements.append({**{key: focused.attrib.get(key) for key in ("tests", "failures", "errors", "skipped", "time")},
                "evidence": focused_path.relative_to(ROOT).as_posix(),
                "scope": scope + "; overlapping subsets, do not add counts",
                "source_version_status": test_provenance_status(focused_path),
                "failed_test_names": [case.attrib["name"] for case in focused.findall("testcase")
                    if case.find("failure") is not None or case.find("error") is not None]})
    return {"schema_version": "competition-evidence-inventory@1.0",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "goal_complete": False, "cloud_upload_performed": False,
            "protected_input_integrity": verify_protected_inputs(),
            "candidate_surface_profile": {"path": PROFILE_PATH.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest(), "status": surface_profile["status"],
                "fidelity": surface_profile["fidelity"], "platform_ref": PLATFORM_REF, "dynamics_ref": DYNAMICS_REF,
                "maximum_speed_mps": surface_profile["maximum_speed_mps"], "maximum_nps": surface_profile["maximum_nps"],
                "holdout_speed_mapping_passed": surface_profile["holdout_all_passed"],
                "turn_full_steady_tolerances_passed": surface_profile["turn_full_steady_tolerances_passed"],
                "conservative_collision_proxies": [SURFACE_SHAPE_REF, SITE_SHAPE_REF],
                "evidence": surface_profile["evidence"]},
            "required_base_scenarios": 28, "design_contracts": len(rows),
            "base_scenarios_with_runtime_candidates": sum(bool(r["runtime_candidates"]) for r in rows),
            "category_runtime_counts": {family: sum(bool(r["runtime_candidates"]) and r["scenario_id"].split("-")[1] == family for r in rows)
                                        for family in ("REC", "TRK", "AD", "ER")},
            "competition_accepted_base_scenarios": 0,
            "targeted_tests": tests, "targeted_test_supplements": supplements, "scenarios": rows,
            "strict_privacy_gate": "FAILED" if privacy_failures else "not_proven",
            "native_visibility_contract": visibility_audit.CONTRACT,
            "base_scenarios_with_complete_native_visibility_trace": sum(any(
                run["full_episode_completed"] and run["status"] != "FAILED_PRIVACY_GATE"
                and run["visibility_audit"]["last_tick"] == run["ticks"]
                and run["visibility_audit"]["checked_frames"] == run["ticks"]+1
                for variant in row["runtime_candidates"] for run in variant["current_version_runs"]) for row in rows),
            "message_visibility_gate": ("FAILED" if any(r["status"] == "FAILED_MESSAGE_VISIBILITY_GATE"
                for variants in by_id.values() for variant in variants for r in variant["current_version_runs"])
                else "passed_targeted_fixture_only" if tests and tests["source_version_status"] == "current"
                and "test_er003_native_source_notice_reaches_actual_authorized_controllers" in tests["passed_test_names"]
                else "not_proven"),
            "privacy_failure_evidence": privacy_failures,
            "native_checkpoint_failures": [
                {"scenario_id": sid, "policy": run["policy"], "seed": run["seed"],
                 "evidence": run["evidence"], "checkpoint_gate": run["checkpoint_gate"]}
                for sid, variants in by_id.items() for variant in variants
                for run in variant["current_version_runs"]
                if run["checkpoint_gate"]["status"] == "FAILED_CHECKPOINT_GATE"],
            "legacy_visibility_gate_evidence": legacy_visibility_evidence,
            "visibility_scope_note": "Native DTO, sensing and receiver delivery validation is not full authentication, message-semantics or hidden-role-shortcut acceptance. Historical identifier-format failures remain preserved, not counted as current leaks.",
            **checkpoint_test_gates(tests),
            "remaining": ([f"Implement {sum(not r['runtime_candidates'] for r in rows)} base scenarios without runtime candidates"]
                          if any(not r["runtime_candidates"] for r in rows) else []) + [
                          "Complete and verify all 28 full contracts; runtime candidate count is not acceptance",
                          "Complete supplemental metrics and public-instruction protocols",
                          "Validate category mechanisms, privacy and failure paths",
                          "Verify rename/reorder invariance and held-out multi-seed comparisons",
                          "Calibrate competition duration/difficulty and conduct independent review"]}

def main():
    result = audit()
    path = DOCS / "STATUS.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in
                     ("goal_complete", "required_base_scenarios", "design_contracts",
                      "base_scenarios_with_runtime_candidates", "competition_accepted_base_scenarios",
                      "targeted_tests", "strict_privacy_gate")}, indent=2))

if __name__ == "__main__":
    main()
