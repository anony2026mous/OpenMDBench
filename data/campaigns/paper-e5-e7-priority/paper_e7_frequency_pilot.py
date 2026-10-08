"""Bounded E7 frequency-axis pilot on frozen grid code; no engine edits."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from types import SimpleNamespace
from unittest.mock import patch


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path); temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    os.replace(temporary, path)


def verify_plan(plan, plan_path):
    if plan["intervals"] != [10, 5, 2] or len(plan["seeds"]) != 3 or len(set(plan["seeds"])) != 3:
        raise ValueError("Unexpected experiment scope")
    if plan["formal_episode_cap"] != 12 or plan["parallel_llm_cases"] != 2:
        raise ValueError("Unexpected pilot budget")
    if plan["max_tokens"] != 1024 or plan["temperature"] != .1 or plan["enable_thinking"] is not False or plan["llm_retries"] != 0:
        raise ValueError("Frozen sampling or retry settings differ")
    if plan["model"] != "Qwen3.8-27B" or len(set(plan["endpoints"])) != 2:
        raise ValueError("Expected one fixed model on two independent replicas")
    if sha(Path(__file__)) != plan["runner_sha256"]: raise ValueError("Runner changed")
    for path, digest in plan["frozen_files"].items():
        if sha(path) != digest: raise ValueError("Frozen source or weight changed: " + path)
    return sha(plan_path)


def load_runner(snapshot):
    snapshot = Path(snapshot)
    sys.path.insert(0, str(snapshot / "role_c_toolkit")); sys.path.insert(0, str(snapshot / "openmd/code"))
    spec = importlib.util.spec_from_file_location("frozen_E7_grid_runner", snapshot / "role_c_toolkit/grid_rolec6.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def observe_controller(factory, counters):
    def wrapped_factory(*args, **kwargs):
        original = factory(*args, **kwargs)
        def controller(env, unit_id, goal_state):
            result = original(env, unit_id, goal_state); counters["calls"] += 1
            if result is None:
                entity = env.entities.get(unit_id)
                counters["none_on_active_unit" if entity is not None and entity.alive else "none_on_inactive_unit"] += 1
            return result
        return controller
    return wrapped_factory


def run_case(plan_path, output, seed, interval, replica):
    plan_path, output = Path(plan_path), Path(output)
    plan = json.loads(plan_path.read_text(encoding="utf-8")); digest = verify_plan(plan, plan_path)
    if seed not in plan["seeds"] or interval not in [0, *plan["intervals"]]: raise ValueError("Case not preregistered")
    if output.exists(): raise FileExistsError("Never overwrite an episode")
    base = load_runner(plan["snapshot"]); arm = "rl" if interval == 0 else "llm-rl"
    args = SimpleNamespace(source=Path(plan["snapshot"]) / "openmd", output=output, seed=seed, arm=arm,
        difficulty=plan["difficulty"], task_mode=plan["task_mode"], checkpoint=Path(plan["checkpoint"]),
        base_url=plan["endpoints"][replica] if interval else None, model=plan["model"] if interval else None,
        plan_interval=interval or 10, pure_call_interval=1, goal_mode=plan["goal_mode"], max_steps=None,
        llm_timeout=plan["llm_timeout_seconds"], llm_retries=plan["llm_retries"])
    counters = {"calls": 0, "none_on_active_unit": 0, "none_on_inactive_unit": 0}; agents = []
    with ExitStack() as stack:
        if interval:
            from grid_env.agents import hybrid_agent, mappo_agent
            def locked_call(agent, prompt):
                if not agents: agents.append(agent)
                agent.plan_calls += 1
                return agent.llm.chat(hybrid_agent.PLANNER_SYSTEM_PROMPT, prompt,
                    max_tokens=plan["max_tokens"], temperature=plan["temperature"])
            stack.enter_context(patch.object(hybrid_agent.HybridAgent, "_call_planner_llm", locked_call))
            stack.enter_context(patch.object(mappo_agent, "make_goai_controller", observe_controller(mappo_agent.make_goai_controller, counters)))
        code = base.run_one(args)
    native_path = output / "episode.json"; native = json.loads(native_path.read_text(encoding="utf-8"))
    requests_path = output / "requests.jsonl"
    rows = [json.loads(l) for l in requests_path.open(encoding="utf-8")] if requests_path.exists() else []
    requests = [r for r in rows if r.get("kind") == "request"]; responses = [r for r in rows if r.get("kind") == "response"]
    reasons = []
    if not native.get("complete") or code: reasons.append("native_episode_or_privacy_gate_failed")
    if native["d1"].get("input_role_truth_leaks") or native["d1"].get("prompt_role_truth_leaks"): reasons.append("role_truth_leak")
    if interval:
        if not agents or not requests or not counters["calls"]: reasons.append("LLM_RL_path_not_exercised")
        if any(r.get("max_tokens") != 1024 or r.get("temperature") != .1 or r.get("enable_thinking") is not False for r in requests): reasons.append("request_lock_mismatch")
        if native["agent_stats"].get("fallback_count", 0): reasons.append("planner_rule_fallback")
        if counters["none_on_active_unit"]: reasons.append("RL_controller_fallback")
        if agents and agents[0].llm.errors: reasons.append("LLM_request_error")
        if len(requests) != len(responses) or any(r.get("empty") for r in responses): reasons.append("missing_or_empty_response")
    verify_plan(plan, plan_path)
    if sha(plan_path) != digest: raise ValueError("Frozen plan changed")
    result = {"schema": "paper-E7-frequency-case@1", "seed": seed, "interval": interval, "arm": arm,
        "replica": replica if interval else None, "native_report": str(native_path), "native_report_sha256": sha(native_path),
        "V": native.get("V"), "complete": native.get("complete"), "analysis_valid": not reasons,
        "invalid_reasons": sorted(set(reasons)), "steps": native["steps"], "plan_sha256": digest,
        "costs": {"llm_calls": len(requests),
            "actual_API_total_tokens": agents[0].llm.total_tokens if agents else 0,
            "request_seconds": sum(r["elapsed_seconds"] for r in responses),
            "prompt_text_utf8_bytes": sum(len((r["system"] + r["user"]).encode("utf-8")) for r in requests),
            "response_text_utf8_bytes": sum(len(r["text"].encode("utf-8")) for r in responses),
            "issued_goal_serialized_bytes": sum(len(json.dumps(r["issued"], sort_keys=True, separators=(",", ":")).encode("utf-8")) for r in native["goal_submissions"]),
            "episode_wall_seconds": native["elapsed_seconds"]},
        "RL_controller_observation": counters, "agent_stats": native["agent_stats"],
        "interface_content_fixed": True, "information_count_axis_executed": False,
        "new_training": False, "engine_files_unchanged": True}
    save(output / "E7-case.json", result)
    return 0 if result["analysis_valid"] else 2


def schedule(plan_path, run_dir):
    plan_path, run_dir = Path(plan_path).resolve(), Path(run_dir).resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8")); verify_plan(plan, plan_path)
    if (run_dir / "status.json").exists(): raise RuntimeError("Existing campaign state; do not duplicate")
    (run_dir / "episodes").mkdir(parents=True, exist_ok=True); (run_dir / "logs").mkdir(exist_ok=True)
    state = {"schema": "E7-frequency-campaign@1", "status": "running", "pid": os.getpid(),
        "started_utc": datetime.now(timezone.utc).isoformat(), "completed": [], "active": {}, "failures": []}
    lock = threading.Lock(); endpoints = queue.Queue()
    def persist(): save(run_dir / "status.json", state)
    persist()
    def launch(seed, interval, replica):
        case_id = f"s{seed}-" + ("rl" if not interval else f"llm-rl-k{interval}")
        output = run_dir / "episodes" / case_id
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "case", "--plan", str(plan_path),
                   "--output", str(output), "--seed", str(seed), "--interval", str(interval), "--replica", str(replica)]
        env = os.environ.copy(); env.update(MPLBACKEND="Agg", CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2", MKL_NUM_THREADS="2")
        with (run_dir / "logs" / (case_id + ".log")).open("x", encoding="utf-8") as log:
            child = subprocess.Popen(command, cwd=plan["snapshot"], env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            with lock: state["active"][case_id] = {"pid": child.pid, "replica": replica if interval else None}; persist()
            try: code = child.wait(timeout=plan["case_wall_budget_seconds"])
            except BaseException:
                child.terminate(); child.wait(timeout=30); raise
        result_path = output / "E7-case.json"
        result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else None
        valid = code == 0 and result is not None and result["analysis_valid"]
        with lock:
            state["active"].pop(case_id, None)
            row = {"case_id": case_id, "exit_code": code, "result": str(result_path), "analysis_valid": valid}
            if result_path.exists(): row["sha256"] = sha(result_path)
            state["completed"].append(row)
            if not valid: state["failures"].append(row)
            persist()
        return valid
    def llm_case(seed, interval):
        replica = endpoints.get()
        try: return launch(seed, interval, replica)
        finally: endpoints.put(replica)
    try:
        for index, seed in enumerate(plan["seeds"]):
            verify_plan(plan, plan_path)
            state["active_seed"] = seed; persist()
            reference = plan.get("existing_reference") if index == 0 else None
            if reference:
                path = Path(reference["report"])
                if sha(path) != reference["sha256"]: raise ValueError("Existing reference changed")
                r = json.loads(path.read_text(encoding="utf-8"))
                if not r["complete"] or r["config"]["seed"] != seed or r["config"]["arm"] != "rl": raise ValueError("Invalid existing reference")
                if any(r["config"][k] != plan[k] for k in ("difficulty", "task_mode", "goal_mode")): raise ValueError("Reference condition differs")
                if r["config"]["checkpoint_sha256"] != sha(plan["checkpoint"]): raise ValueError("Reference checkpoint differs")
                if r["source_hashes"] != load_runner(plan["snapshot"]).source_hashes(Path(plan["snapshot"]) / "openmd"): raise ValueError("Reference source differs")
                if r["d1"]["input_role_truth_leaks"] or r["d1"]["prompt_role_truth_leaks"]: raise ValueError("Reference privacy gate failed")
                state["completed"].append({"case_id": f"s{seed}-rl", "result": str(path), "sha256": sha(path), "reused_E7_preflight_reference": True, "analysis_valid": True}); persist()
            elif not launch(seed, 0, 0): break
            for replica in (index % 2, 1 - index % 2): endpoints.put(replica)
            intervals = [2, 5, 10]
            if index == 0:
                if not llm_case(seed, 10): break
                intervals = [2, 5]
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(llm_case, seed, interval) for interval in intervals]
                for future in as_completed(futures): future.result()
            while not endpoints.empty(): endpoints.get_nowait()
            if state["failures"]: break
        state["status"] = "complete" if len(state["completed"]) == 12 and not state["failures"] else "stopped_at_validation_gate"
        state["finished_utc"] = datetime.now(timezone.utc).isoformat(); persist()
    except BaseException as error:
        state["status"] = "controller_error"; state["error"] = {"type": type(error).__name__, "message": str(error)}; persist(); raise
    return 0 if state["status"] == "complete" else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="action", required=True)
    one = sub.add_parser("case"); one.add_argument("--plan", type=Path, required=True); one.add_argument("--output", type=Path, required=True)
    one.add_argument("--seed", type=int, required=True); one.add_argument("--interval", type=int, choices=(0, 2, 5, 10), required=True); one.add_argument("--replica", type=int, choices=(0, 1), default=0)
    run = sub.add_parser("schedule"); run.add_argument("--plan", type=Path, required=True); run.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run_case(args.plan,args.output,args.seed,args.interval,args.replica) if args.action == "case" else schedule(args.plan,args.run_dir))
