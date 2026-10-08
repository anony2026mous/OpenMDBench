"""E6 model-invariance scan: two models, one frozen grid pipeline, no engine edits.

Every case is a grid medium/continuous episode on the ``llm-rl`` stack
(LLM planner + pinned v9 RL executor).  The only axis is the served model and the
goal-mode condition (``strong`` / ``hold``); seeds are shared so the two models are
compared seed-pairwise.

Sub-commands
    plan      write the frozen plan (refuses to overwrite)
    probe     verify each endpoint's identity (weight root, context, served name)
    case      run exactly one preregistered case
    schedule  run every preregistered case across the model replicas
    status    print a compact progress line

Run on the server with the snapshot as the working copy; see E6_结果汇总.md.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from types import SimpleNamespace
from unittest.mock import patch

SCHEMA_PLAN = "E6-model-invariance-plan@1"
SCHEMA_CASE = "E6-model-invariance-case@1"
SCHEMA_STATUS = "E6-model-invariance-status@1"
SCHEMA_PROBE = "E6-model-invariance-probe@1"
CONDITIONS = ("strong", "hold")
SERVED = {"27b": "Qwen3.8-27B", "8b": "Qwen3-8B"}
MODEL_DIRS = {"27b": "models/Qwen3.8-27B-BF16", "8b": "models/Qwen3-8B-BF16"}
# The 8B checkpoint declares max_position_embeddings = 40960, so its own architectural
# limit is served as-is instead of forcing VLLM_ALLOW_LONG_MAX_MODEL_LEN, which the
# runtime warns can produce NaNs with relative position encoding.
MAX_MODEL_LEN = {"27b": 131072, "8b": 40960}
ARMS = ("llm-rl", "rl")


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path: Path, value) -> None:
    path = Path(path)
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + chr(10),
                         encoding="utf-8")
    os.replace(temporary, path)


def case_id(model: str, condition: str, seed: int) -> str:
    return f"{model}-{condition}-s{seed}"


def load_runner(snapshot: Path):
    snapshot = Path(snapshot)
    sys.path.insert(0, str(snapshot / "role_c_toolkit"))
    sys.path.insert(0, str(snapshot / "openmd/code"))
    spec = importlib.util.spec_from_file_location(
        "frozen_E6_grid_runner", snapshot / "role_c_toolkit/grid_rolec6.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- plan handling

def verify_plan(plan: dict, plan_path: Path) -> str:
    if plan.get("schema") != SCHEMA_PLAN:
        raise ValueError("Unexpected plan schema")
    seeds = plan.get("seeds") or []
    # The preregistered set may be extended with fresh, never-mined seeds; shrinking a
    # frozen set after seeing results is what would invalidate the experiment.
    if len(seeds) < 10 or len(set(seeds)) != len(seeds):
        raise ValueError("E6 requires at least 10 distinct strong/hold seeds")
    if plan.get("seed_set_extended_after_first_batch") and len(seeds) <= 10:
        raise ValueError("Plan declares an extension but carries no extra seeds")
    if list(plan.get("conditions") or []) != list(CONDITIONS):
        raise ValueError("E6 conditions must be exactly strong and hold")
    if plan.get("difficulty") != "medium" or plan.get("task_mode") != "continuous":
        raise ValueError("E6 runs grid medium/continuous only")
    if plan.get("plan_interval") != 10 or plan.get("stack") != "llm-rl":
        raise ValueError("E6 uses the frozen llm-rl stack at plan_interval 10")
    smoke = list(plan.get("smoke_seeds") or [])
    if len(set(smoke)) != len(smoke) or (set(smoke) & set(seeds)) or \
            (set(smoke) & set(plan.get("reference_seeds") or [])):
        raise ValueError("Smoke seeds must be distinct from every analysed seed")
    if plan.get("max_tokens") != 1024 or plan.get("temperature") != .1:
        raise ValueError("Frozen sampling settings differ")
    if plan.get("enable_thinking") is not False or plan.get("llm_retries") != 0:
        raise ValueError("Thinking must be off and retries pinned to zero")
    models = plan.get("models") or {}
    if set(models) != set(SERVED):
        raise ValueError("E6 needs exactly the two preregistered models")
    seen_endpoints: set[str] = set()
    for name, entry in models.items():
        if entry.get("served_name") != SERVED[name]:
            raise ValueError("Served model name differs from the plan: " + name)
        if entry.get("directory") != MODEL_DIRS[name]:
            raise ValueError("Model directory differs from the plan: " + name)
        if not re.fullmatch("[0-9a-f]{64}", str(entry.get("manifest_sha256"))):
            raise ValueError("Model manifest hash is missing: " + name)
        if entry.get("max_model_len") != MAX_MODEL_LEN[name]:
            raise ValueError("Serving context length differs from the planned value: " + name)
        endpoints = entry.get("endpoints") or []
        if not endpoints or len(set(endpoints)) != len(endpoints):
            raise ValueError("Every model needs distinct endpoints: " + name)
        if set(endpoints) & seen_endpoints:
            raise ValueError("Two models cannot share one endpoint")
        seen_endpoints.update(endpoints)
        if [str(port) for port in entry.get("ports") or []] != \
                [url.split("//")[1].split("/")[0].rsplit(":", 1)[1] for url in endpoints]:
            raise ValueError("Recorded ports disagree with the endpoint URLs: " + name)
    if len(models["27b"].get("endpoints") or []) != 1:
        raise ValueError("The 27B reference runs on exactly one preregistered replica "
                         "(replica b is reserved for the second model)")
    if sha(Path(__file__)) != plan.get("runner_sha256"):
        raise ValueError("Runner changed after the plan was frozen")
    for path, digest in (plan.get("frozen_files") or {}).items():
        if sha(Path(path)) != digest:
            raise ValueError("Frozen source or weight changed: " + path)
    return sha(plan_path)


# ------------------------------------------------------------------- endpoints

def get_json(url: str, timeout: float = 30.0):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, body: dict, timeout: float = 120.0):
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def endpoint_identity(base_url: str, served_name: str, model_directory: str,
                      expected_len: int | None = None) -> dict:
    listing = get_json(base_url.rstrip("/") + "/models")
    rows = listing.get("data") or []
    match = [row for row in rows if row.get("id") == served_name]
    if not match:
        raise ValueError("Endpoint does not serve " + served_name + ": " +
                         str([row.get("id") for row in rows]))
    row = match[0]
    root = str(row.get("root") or "")
    if not root.endswith(model_directory):
        raise ValueError("Endpoint weight root does not match the plan: " + root)
    if expected_len is not None and int(row.get("max_model_len") or 0) != expected_len:
        raise ValueError("Endpoint context length differs from the plan: " +
                         str(row.get("max_model_len")) + " != " + str(expected_len))
    return {"served_name": served_name, "root": root,
            "max_model_len": row.get("max_model_len")}


def cache_metrics(base_url: str) -> dict:
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/metrics", timeout=30) as response:
            text = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError):
        return {}
    rows = [line for line in text.splitlines() if line.startswith("vllm:cache_config_info{")]
    if len(rows) != 1:
        return {}
    quote = chr(34)
    return dict(re.findall("([a-z_]+)=" + quote + "([^" + quote + "]*)" + quote, rows[0]))


def process_start_ticks(pid: int) -> str | None:
    try:
        text = Path('/proc', str(pid), 'stat').read_text()
    except (FileNotFoundError, ProcessLookupError):
        return None
    return text[text.rfind(')') + 2:].split()[19]


def replica_state(service_dir: Path, replica: str) -> dict:
    """Read the launcher's own record so continuity is checked on its process."""
    path = Path(service_dir) / f"replica-{replica}.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def probe(plan: dict, model: str, base_url: str, replica: int, service_dir: Path | None = None) -> dict:
    entry = plan["models"][model]
    record = {"model": model, "base_url": base_url, "replica": replica}
    record.update(endpoint_identity(base_url, entry["served_name"], entry["directory"],
                                    entry.get("max_model_len")))
    record["cache"] = cache_metrics(base_url)
    body = {"model": entry["served_name"],
            "messages": [{"role": "user", "content": "Reply with the single word: ready"}],
            "max_tokens": 16, "temperature": 0.0,
            "chat_template_kwargs": {"enable_thinking": False}}
    answer = post_json(base_url.rstrip("/") + "/chat/completions", body)
    content = ((answer.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    record["non_thinking_reply"] = content.strip()
    record["reply_non_empty"] = bool(content.strip())
    record["usage"] = answer.get("usage")
    if service_dir:
        replica_name = entry.get("replica_names", {}).get(str(replica))
        state = replica_state(service_dir, replica_name) if replica_name else {}
        record["launcher_state"] = {key: state.get(key) for key in
                                    ("replica", "pid", "port", "model_dir", "max_model_len",
                                     "kv_blocks", "started_utc")
                                    if key in state}
        if state.get("pid"):
            record["metrics_pids"] = [{"pid": state["pid"],
                                       "start_ticks": process_start_ticks(int(state["pid"]))}]
    return record


# ------------------------------------------------------------------ case runner

def observe_controller(factory, counters):
    def wrapped_factory(*args, **kwargs):
        original = factory(*args, **kwargs)

        def controller(env, unit_id, goal_state):
            result = original(env, unit_id, goal_state)
            counters["calls"] += 1
            if result is None:
                entity = env.entities.get(unit_id)
                active = entity is not None and entity.alive
                counters["none_on_active_unit" if active else "none_on_inactive_unit"] += 1
            return result
        return controller
    return wrapped_factory


def run_case(plan_path: Path, output: Path, model: str, condition: str, seed: int,
             replica: int, arm: str = "llm-rl") -> int:
    plan_path, output = Path(plan_path), Path(output)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    digest = verify_plan(plan, plan_path)
    if seed not in plan.get("seeds", []) + plan.get("reference_seeds", []) + \
            plan.get("smoke_seeds", []) or condition not in CONDITIONS or arm not in ARMS:
        raise ValueError("Case is not preregistered")
    if arm == "rl" and condition != "strong":
        raise ValueError("The pure-RL reference has no goal-mode condition")
    if output.exists():
        raise FileExistsError("Never overwrite an episode")
    entry = plan["models"][model]
    endpoint = entry["endpoints"][replica] if arm == "llm-rl" else None
    if arm == "llm-rl" and replica >= len(entry["endpoints"]):
        raise ValueError("Replica index is outside the preregistered endpoint list")
    base = load_runner(Path(plan["snapshot"]))
    args = SimpleNamespace(source=Path(plan["snapshot"]) / "openmd", output=output, seed=seed,
                           arm=arm, difficulty=plan["difficulty"], task_mode=plan["task_mode"],
                           checkpoint=Path(plan["checkpoint"]), base_url=endpoint,
                           model=entry["served_name"] if arm == "llm-rl" else None,
                           plan_interval=plan["plan_interval"], pure_call_interval=1,
                           goal_mode=condition, max_steps=None,
                           llm_timeout=plan["llm_timeout_seconds"], llm_retries=plan["llm_retries"])
    counters = {"calls": 0, "none_on_active_unit": 0, "none_on_inactive_unit": 0}
    agents = []
    with ExitStack() as stack:
        if arm == "llm-rl":
            from grid_env.agents import hybrid_agent, mappo_agent

            def locked_call(agent, prompt):
                if not agents:
                    agents.append(agent)
                agent.plan_calls += 1
                return agent.llm.chat(hybrid_agent.PLANNER_SYSTEM_PROMPT, prompt,
                                      max_tokens=plan["max_tokens"],
                                      temperature=plan["temperature"])

            stack.enter_context(patch.object(hybrid_agent.HybridAgent, "_call_planner_llm", locked_call))
            stack.enter_context(patch.object(
                mappo_agent, "make_goai_controller",
                observe_controller(mappo_agent.make_goai_controller, counters)))
        code = base.run_one(args)
    native_path = output / "episode.json"
    native = json.loads(native_path.read_text(encoding="utf-8"))
    requests_path = output / "requests.jsonl"
    rows = ([json.loads(line) for line in requests_path.read_text(encoding="utf-8").splitlines()
             if line.strip()] if requests_path.exists() else [])
    requests = [row for row in rows if row.get("kind") == "request"]
    responses = [row for row in rows if row.get("kind") == "response"]
    leaks = (native.get("d1") or {}).get("input_role_truth_leaks") or []
    prompt_leaks = (native.get("d1") or {}).get("prompt_role_truth_leaks") or []
    reasons = []
    if not native.get("complete") or code:
        reasons.append("native_episode_failed")
    if leaks:
        reasons.append("input_role_truth_leak")
    if prompt_leaks:
        reasons.append("prompt_role_truth_leak")
    if arm == "llm-rl":
        served = {row.get("model") for row in requests}
        if not agents or not requests or not counters["calls"]:
            reasons.append("LLM_RL_path_not_exercised")
        if served != {entry["served_name"]}:
            reasons.append("served_model_mismatch")
        if any(row.get("max_tokens") != plan["max_tokens"]
               or row.get("temperature") != plan["temperature"]
               or row.get("enable_thinking") is not False for row in requests):
            reasons.append("request_lock_mismatch")
        if (native.get("agent_stats") or {}).get("fallback_count", 0):
            reasons.append("planner_rule_fallback")
        if counters["none_on_active_unit"]:
            reasons.append("RL_controller_fallback")
        if agents and agents[0].llm.errors:
            reasons.append("LLM_request_error")
        if len(requests) != len(responses) or any(row.get("empty") for row in responses):
            reasons.append("missing_or_empty_response")
    verify_plan(plan, plan_path)
    if sha(plan_path) != digest:
        raise ValueError("Frozen plan changed during the episode")
    stats = native.get("agent_stats") or {}
    result = {"schema": SCHEMA_CASE, "model": model, "condition": condition, "seed": seed,
              "arm": arm, "replica": replica if arm == "llm-rl" else None,
              "served_name": entry["served_name"] if arm == "llm-rl" else None,
              "endpoint": endpoint, "native_report": str(native_path),
              "native_report_sha256": sha(native_path), "V": native.get("V"),
              "complete": native.get("complete"), "steps": native.get("steps"),
              "analysis_valid": not reasons, "invalid_reasons": sorted(set(reasons)),
              "plan_sha256": digest,
              "costs": {"llm_calls": len(requests),
                        "actual_API_total_tokens": agents[0].llm.total_tokens if agents else 0,
                        "request_seconds": sum(row["elapsed_seconds"] for row in responses),
                        "prompt_text_utf8_bytes": sum(len((row["system"] + row["user"]).encode("utf-8"))
                                                      for row in requests),
                        "response_text_utf8_bytes": sum(len(row["text"].encode("utf-8"))
                                                        for row in responses),
                        "episode_wall_seconds": native.get("elapsed_seconds")},
              "RL_controller_observation": counters, "agent_stats": stats,
              "planner_call_settings": {"max_tokens": plan["max_tokens"],
                                        "temperature": plan["temperature"],
                                        "enable_thinking": False},
              "engine_files_unchanged": True, "new_training": False}
    save(output / "E6-case.json", result)
    return 0 if result["analysis_valid"] else 2


# -------------------------------------------------------------------- schedule

def _tasks_for_model(plan: dict) -> list[tuple[str, int, str]]:
    """The one canonical task list; scheduling and extension reporting both read it."""
    tasks = [(condition, seed, "llm-rl") for condition in CONDITIONS for seed in plan["seeds"]]
    tasks += [("strong", seed, "rl") for seed in plan["reference_seeds"]]
    return tasks


def schedule(plan_path: Path, run_dir: Path, models, jobs_per_model: int,
             extend: bool = False) -> int:
    plan_path, run_dir = Path(plan_path).resolve(), Path(run_dir).resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    verify_plan(plan, plan_path)
    status_path = run_dir / "status.json"
    prior = None
    if status_path.exists():
        if not extend:
            raise RuntimeError("Existing campaign state; pass --extend to add the new cases")
        prior = json.loads(status_path.read_text(encoding="utf-8"))
    probe_path = plan_path.parent / "endpoints.json"
    if not probe_path.exists():
        raise RuntimeError("Run `probe` first so the endpoints are verified before any episode")
    probes = json.loads(probe_path.read_text(encoding="utf-8"))
    if probes.get("plan_sha256") != sha(plan_path):
        raise RuntimeError("Endpoint probe belongs to a different plan; re-run `probe`")
    for row in probes["records"]:
        if not row.get("reply_non_empty"):
            raise RuntimeError("Endpoint failed its pre-flight reply: " + row["base_url"])
    (run_dir / "episodes").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(exist_ok=True)
    state = prior or {"schema": SCHEMA_STATUS, "status": "running", "pid": os.getpid(),
                      "started_utc": datetime.now(timezone.utc).isoformat(),
                      "plan_sha256": sha(plan_path), "completed": [], "active": {},
                      "failures": []}
    if prior:
        # Extension: keep every finished case, add the newly preregistered ones.
        state.setdefault("extensions", []).append(
            {"extended_utc": datetime.now(timezone.utc).isoformat(),
             "previous_plan_sha256": prior.get("plan_sha256"),
             "plan_sha256": sha(plan_path), "seeds": list(plan["seeds"]),
             "note": "fresh seeds appended; no seed dropped and no case re-run"})
        state["plan_sha256"] = sha(plan_path)
        state["status"] = "running"
        state["pid"] = os.getpid()
    finished_before = {row["case_id"] for row in state["completed"]}
    missing = []
    for model in models:
        for condition, seed, arm in _tasks_for_model(plan):
            identifier = case_id(model, condition, seed) if arm == "llm-rl" \
                else f"{model}-rl-s{seed}"
            if identifier not in finished_before:
                missing.append((model, condition, seed, arm))
    if prior and not missing:
        print("nothing to extend: every preregistered case is already recorded", flush=True)
        return 0
    if prior:
        print(f"extending with {len(missing)} new cases: "
              f"{[f'{m}/{c}/s{s}' for m, c, s, _a in missing]}", flush=True)
    lock = threading.Lock()
    slots = queue.Queue()
    for model in models:
        for replica in range(len(plan["models"][model]["endpoints"])):
            for _ in range(jobs_per_model):
                slots.put((model, replica))

    def persist():
        save(run_dir / "status.json", state)

    persist()

    def launch(model, condition, seed, replica, arm):
        identifier = case_id(model, condition, seed) if arm == "llm-rl" else f"{model}-rl-s{seed}"
        if identifier in finished_before:
            return True
        output = run_dir / "episodes" / identifier
        log_path = run_dir / "logs" / (identifier + ".log")
        if log_path.exists():
            # A previous attempt left a log without a result; keep both, never overwrite.
            log_path = run_dir / "logs" / (identifier + f"-ext{len(state['extensions'])}.log")
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "case",
                   "--plan", str(plan_path), "--output", str(output), "--model", model,
                   "--condition", condition, "--seed", str(seed), "--replica", str(replica)]
        if arm == "rl":
            command += ["--arm", "rl"]
        env = os.environ.copy()
        env.update(MPLBACKEND="Agg", CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="2",
                   OPENBLAS_NUM_THREADS="2", MKL_NUM_THREADS="2")
        with log_path.open("x", encoding="utf-8") as log:
            child = subprocess.Popen(command, cwd=plan["snapshot"], env=env,
                                     stdin=subprocess.DEVNULL, stdout=log,
                                     stderr=subprocess.STDOUT)
            with lock:
                state["active"][identifier] = {"pid": child.pid, "replica": replica,
                                               "model": model, "condition": condition}
                persist()
            try:
                code = child.wait(timeout=plan["case_wall_budget_seconds"])
            except BaseException:
                child.terminate()
                child.wait(timeout=30)
                raise
        result_path = output / "E6-case.json"
        result = (json.loads(result_path.read_text(encoding="utf-8"))
                  if result_path.exists() else None)
        valid = code == 0 and result is not None and result["analysis_valid"]
        with lock:
            state["active"].pop(identifier, None)
            row = {"case_id": identifier, "exit_code": code, "result": str(result_path),
                   "analysis_valid": valid, "model": model, "condition": condition,
                   "seed": seed, "replica": replica if arm == "llm-rl" else None}
            if result_path.exists():
                row["sha256"] = sha(result_path)
            state["completed"].append(row)
            if not valid:
                state["failures"].append(row)
            persist()
        return valid

    try:
        # One worker per (model, replica) slot; each worker owns its queue and never
        # waits on another slot, so a slow model cannot starve the other one.
        workers = []
        for model in models:
            pending = queue.Queue()
            for condition, seed, arm in _tasks_for_model(plan):
                pending.put((condition, seed, arm))
            for replica in range(len(plan["models"][model]["endpoints"])):
                for index in range(jobs_per_model):
                    workers.append(threading.Thread(
                        target=_slot_worker,
                        args=(model, replica, index, pending, launch),
                        daemon=False, name=f"{model}-{replica}-{index}"))
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        state["status"] = "complete" if not state["failures"] else "complete_with_failures"
    except BaseException as exc:  # noqa: BLE001
        state["status"] = "aborted"
        state["abort_reason"] = f"{type(exc).__name__}: {exc}"
        persist()
        raise
    state["finished_utc"] = datetime.now(timezone.utc).isoformat()
    persist()
    return 0 if not state["failures"] else 1


def _slot_worker(model: str, replica: int, index: int, pending: queue.Queue, launch) -> None:
    """Drain this model's queue on one replica slot."""
    while True:
        try:
            condition, seed, arm = pending.get_nowait()
        except queue.Empty:
            return
        try:
            launch(model, condition, seed, replica, arm)
        except BaseException as exc:  # noqa: BLE001
            print(f"slot {model}/{replica}#{index} failed on "
                  f"{condition} s{seed}: {type(exc).__name__}: {exc}", flush=True)


def probe_command(plan_path: Path, output: Path, only, service_dir: Path | None = None):
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    verify_plan(plan, Path(plan_path))
    records = []
    for model, entry in plan["models"].items():
        if only and model not in only:
            continue
        for replica, base_url in enumerate(entry["endpoints"]):
            record = probe(plan, model, base_url, replica, service_dir)
            records.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
    save(Path(output), {"schema": SCHEMA_PROBE, "plan_sha256": sha(Path(plan_path)),
                        "probed_utc": datetime.now(timezone.utc).isoformat(),
                        "records": records})
    return 0 if all(row.get("reply_non_empty") for row in records) else 3


def plan_command(args) -> int:
    if args.output.exists():
        raise FileExistsError("Plan already exists: " + str(args.output))
    models = {}
    for name, spec in (("27b", args.model_27b), ("8b", args.model_8b)):
        directory = Path(spec)
        ports = spec_ports(name, args)
        if name == "27b" and len(ports) != 1:
            raise ValueError("The 27B reference runs on exactly one replica; replica b is "
                             "the second model's GPU pair")
        if len(set(ports)) != len(ports):
            raise ValueError("Replica ports must be distinct: " + name)
        manifest = directory / "source-manifest.json"
        receipt = directory / "download-complete.json"
        if not manifest.is_file() or not receipt.is_file():
            raise FileNotFoundError("Weights are not verified yet: " + str(directory))
        if json.loads(receipt.read_text(encoding="utf-8")).get("status") != "all_files_sha256_verified":
            raise RuntimeError("Download receipt is not verified: " + str(receipt))
        manifest_sha = sha(manifest)
        if json.loads(receipt.read_text(encoding="utf-8")).get("manifest_sha256") != manifest_sha:
            raise RuntimeError("Manifest hash differs from its receipt: " + str(manifest))
        models[name] = {"served_name": SERVED[name], "directory": MODEL_DIRS[name],
                        "max_model_len": MAX_MODEL_LEN[name],
                        "manifest_sha256": manifest_sha,
                        "repository": json.loads(manifest.read_text(encoding="utf-8"))["repository"],
                        "replica_names": spec_replicas(name, args),
                        "ports": [int(port) for port in spec_ports(name, args)],
                        "endpoints": [f"http://127.0.0.1:{port}/v1"
                                      for port in spec_ports(name, args)]}
    seeds = list(args.seeds)
    snapshot = Path(args.snapshot).resolve()
    plan = {
        "schema": SCHEMA_PLAN,
        "scope": "E6 model-invariance: grid medium/continuous llm-rl, strong vs hold",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "seed_set_extended_after_first_batch": bool(args.extended_from),
        "extended_from": args.extended_from or None,
        "snapshot": str(snapshot),
        "checkpoint": str(Path(args.checkpoint).resolve()),
        "difficulty": "medium", "task_mode": "continuous", "stack": "llm-rl",
        "plan_interval": 10, "conditions": list(CONDITIONS), "seeds": seeds,
        "reference_seeds": list(args.reference_seeds),
        "smoke_seeds": list(args.smoke_seeds),
        "max_tokens": args.max_tokens, "temperature": args.temperature,
        "enable_thinking": False, "llm_retries": 0, "llm_timeout_seconds": 120,
        "case_wall_budget_seconds": args.case_wall_budget_seconds,
        "jobs_per_replica": args.jobs_per_replica,
        "models": models,
        "runner_sha256": sha(Path(__file__)),
        "frozen_files": {str((snapshot / "role_c_toolkit/grid_rolec6.py").resolve()):
                         sha(snapshot / "role_c_toolkit/grid_rolec6.py"),
                         str(Path(args.checkpoint).resolve()): sha(Path(args.checkpoint))},
        "success_criteria": {
            "interface_causal_necessity": "per model: mean(V_strong - V_hold) > 0 with the seed-bootstrap 95% CI lower bound > 0",
            "deployment_behind_baseline": "per model: mean(V_strong - V_pure_rl_same_seed) < 0",
            "honest_failure": "any model failing either criterion is reported as a law boundary, never re-labelled",
        },
        "no_cross_batch_merge": True,
        "note": "masked/goal-dose conditions do not exist in this pipeline; only strong and hold are run",
    }
    save(Path(args.output), plan)
    verify_plan(json.loads(Path(args.output).read_text(encoding="utf-8")),
                Path(args.output).resolve())
    print(json.dumps({"plan": str(args.output), "sha256": sha(Path(args.output))}, indent=2))
    return 0


def spec_ports(name: str, args) -> list[str]:
    return [str(port) for port in (args.ports_27b if name == "27b" else args.ports_8b)]


def spec_replicas(name: str, args) -> dict:
    """Map each endpoint index to the replica name the launcher records."""
    return {str(index): replica for index, replica in
            enumerate(args.replicas_27b if name == "27b" else args.replicas_8b)}


def status_command(run_dir: Path) -> int:
    state = json.loads((Path(run_dir) / "status.json").read_text(encoding="utf-8"))
    done = state["completed"]
    valid = sum(1 for row in done if row.get("analysis_valid"))
    print(f"E6 {state['status']} valid={valid}/{len(done)} active={len(state['active'])} "
          f"failures={len(state['failures'])}")
    for row in state["failures"]:
        print("  FAIL", row["case_id"], row.get("exit_code"))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    make = sub.add_parser("plan", help="write the frozen plan")
    make.add_argument("--output", type=Path, required=True)
    make.add_argument("--snapshot", type=Path, required=True)
    make.add_argument("--checkpoint", type=Path, required=True)
    make.add_argument("--model-27b", type=Path, required=True)
    make.add_argument("--model-8b", type=Path, required=True)
    make.add_argument("--ports-27b", type=int, nargs="+", default=[8001])
    make.add_argument("--ports-8b", type=int, nargs="+", default=[8003])
    make.add_argument("--replicas-27b", nargs="+", default=["a"])
    make.add_argument("--replicas-8b", nargs="+", default=["c"])
    make.add_argument("--service-dir", type=Path,
                      default=Path('/mnt/QTJC/chenyi-codex/services/qwen'))
    make.add_argument("--seeds", type=int, nargs="+", required=True)
    make.add_argument("--reference-seeds", type=int, nargs="+", required=True)
    make.add_argument("--extended-from", default="",
                      help="path or id of the earlier plan this seed set extends, for the record")
    make.add_argument("--smoke-seeds", type=int, nargs="+", default=[2026100391],
                      help="preregistered smoke seeds; never part of the analysis")
    make.add_argument("--max-tokens", type=int, default=1024)
    make.add_argument("--temperature", type=float, default=.1)
    make.add_argument("--case-wall-budget-seconds", type=int, default=5400)
    make.add_argument("--jobs-per-replica", type=int, default=1)

    check = sub.add_parser("probe", help="verify endpoint identity and a short reply")
    check.add_argument("--plan", type=Path, required=True)
    check.add_argument("--output", type=Path, required=True)
    check.add_argument("--model", action="append", choices=sorted(SERVED))
    check.add_argument("--service-dir", type=Path,
                       default=Path('/mnt/QTJC/chenyi-codex/services/qwen'))

    one = sub.add_parser("case", help="run exactly one preregistered case")
    one.add_argument("--plan", type=Path, required=True)
    one.add_argument("--output", type=Path, required=True)
    one.add_argument("--model", choices=sorted(SERVED), required=True)
    one.add_argument("--condition", choices=CONDITIONS, required=True)
    one.add_argument("--seed", type=int, required=True)
    one.add_argument("--replica", type=int, required=True)
    one.add_argument("--arm", choices=ARMS, default="llm-rl")

    run = sub.add_parser("schedule", help="run every preregistered case")
    run.add_argument("--plan", type=Path, required=True)
    run.add_argument("--run-dir", type=Path, required=True)
    run.add_argument("--model", action="append", choices=sorted(SERVED))
    run.add_argument("--jobs-per-model", type=int, default=1)
    run.add_argument("--extend", action="store_true",
                     help="add newly preregistered cases to an existing run directory")

    show = sub.add_parser("status", help="print progress")
    show.add_argument("--run-dir", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "plan":
        return plan_command(args)
    if args.command == "probe":
        return probe_command(args.plan, args.output, args.model, args.service_dir)
    if args.command == "case":
        return run_case(args.plan, args.output, args.model, args.condition, args.seed,
                        args.replica, args.arm)
    if args.command == "status":
        return status_command(args.run_dir)
    chosen = args.model or sorted(SERVED)
    return schedule(args.plan, args.run_dir, chosen, args.jobs_per_model, args.extend)


if __name__ == "__main__":
    raise SystemExit(main())
