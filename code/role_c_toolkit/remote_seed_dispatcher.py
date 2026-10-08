"""Scheduling-only overlay for an immutable Role-C inference campaign.

Preserves original plan/recorder/engine, adopts live detached episodes, uses
seed-major dynamic dispatch, and serializes HTTP calls before client timeout
starts. Extra episode processes overlap CPU work with another episode's model
call. No model, policy, score, sampling, timeout, or engine parameter changes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import time
import traceback

VERSION = "seed-major-prefetch-dispatch@1"
BASE = Path("/mnt/<lab>/<user>-codex/experiments")


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def same_process(left, right):
    return bool(left and right and type(left.get("pid")) is int and left["pid"] > 0
                and isinstance(left.get("start_ticks"), str) and left["start_ticks"]
                and left.get("pid") == right.get("pid")
                and left.get("start_ticks") == right.get("start_ticks"))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()


def save(path, value):
    path = Path(path); temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, path)


def frozen_runner(snapshot):
    path = Path(snapshot) / "role_c_toolkit/remote_seed_campaign.py"
    spec = importlib.util.spec_from_file_location("rolec_frozen_campaign", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def derived_plan(original, case_id, replica, origin_sha):
    if replica not in (0, 1): raise ValueError("unknown replica")
    result = deepcopy(original)
    case = next(c for c in result["cases"] if c["id"] == case_id)
    old_slot = case["slot"]; case["slot"] = replica
    result["scheduling_dispatch"] = {"version": VERSION, "original_plan_sha256": origin_sha,
        "case_id": case_id, "original_slot": old_slot, "assigned_slot": replica,
        "only_existing_identical_model_replica_routing_changed": True}
    restored = deepcopy(result); restored.pop("scheduling_dispatch")
    next(c for c in restored["cases"] if c["id"] == case_id)["slot"] = old_slot
    if restored != original: raise AssertionError("dispatch changed a non-routing input")
    return result


def choices(cases, completed, active, costs, *, cpu_limit=4, llm_prefetch=2):
    """Longest known cases first within exactly the earliest unfinished seed."""
    remaining = [c for c in cases if c["id"] not in completed]
    if not remaining: return []
    phase_seed = (remaining[0]["phase"], remaining[0]["seed"])
    pending = [c for c in remaining if (c["phase"], c["seed"]) == phase_seed and c["id"] not in active]
    def cost(c): return costs.get((c["scenario"], c["arm"]), 1800.)
    pending.sort(key=lambda c: (-cost(c), c["id"]))
    cpu_used = sum(x["case"]["planner"] == "rl" for x in active.values())
    counts = Counter(); loads = Counter(); blocked = set()
    for item in active.values():
        c = item["case"]
        if c["planner"] == "rl": continue
        replica = item.get("replica", c["slot"])
        counts[replica] += 1; loads[replica] += cost(c)
        if not item.get("gated", False): blocked.add(replica)
    selected = []
    for c in pending:
        if c["planner"] == "rl":
            if cpu_used < cpu_limit:
                selected.append((c, c["slot"])); cpu_used += 1
        else:
            free = [r for r in (0, 1) if r not in blocked and counts[r] < llm_prefetch]
            if free:
                replica = min(free, key=lambda r: (loads[r], counts[r], r))
                selected.append((c, replica)); counts[replica] += 1; loads[replica] += cost(c)
    return selected


def admitted_call(original, client, system_prompt, user_message, *, max_tokens, temperature, lock_path, log_path, case_id, replica):
    """Admission wait is outside the original HTTP client's unchanged timeout."""
    import fcntl
    queued = time.monotonic(); began_utc = now(); began = None; outcome = "exception"
    with Path(lock_path).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            began = time.monotonic()
            result = original(client, system_prompt, user_message, max_tokens=max_tokens, temperature=temperature)
            outcome = "returned"
            return result
        finally:
            ended = time.monotonic(); fcntl.flock(lock, fcntl.LOCK_UN)
            row = {"schema": "model-request-admission@1", "case_id": case_id, "replica": replica,
                "pid": os.getpid(), "queued_utc": began_utc, "finished_utc": now(),
                "queue_wait_seconds": began - queued, "service_call_seconds": ended - began,
                "client_timeout_seconds_unchanged": client.timeout, "outcome": outcome}
            with Path(log_path).open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row) + "\n"); stream.flush()


def worker(config_path, dispatch_path, case_id):
    config = load(config_path); campaign = Path(config["campaign_dir"]); revision = Path(config["revision_dir"])
    if sha(Path(__file__)) != config["scheduler_sha256"]: raise RuntimeError("scheduler code changed")
    if sha(campaign / "plan.json") != config["original_plan_sha256"]: raise RuntimeError("original plan changed")
    runner = frozen_runner(config["snapshot"]); original_plan = load(campaign / "plan.json")
    plan = load(dispatch_path); assigned = next(c for c in plan["cases"] if c["id"] == case_id)
    if plan != derived_plan(original_plan, case_id, assigned["slot"], config["original_plan_sha256"]):
        raise RuntimeError("derived plan changes more than routing")
    sys.path.insert(0, str(Path(config["snapshot"]) / "openmd/code/eval"))
    from llm_client_hifi import LLMClient
    original = LLMClient.chat; folder = campaign / "episodes" / case_id
    def gated(client, system_prompt, user_message, max_tokens=None, temperature=.1):
        return admitted_call(original, client, system_prompt, user_message, max_tokens=max_tokens,
            temperature=temperature, lock_path=revision / f"replica-{assigned['slot']}.http.lock",
            log_path=folder / "request-admission.jsonl", case_id=case_id, replica=assigned["slot"])
    LLMClient.chat = gated
    try:
        result = runner.run_episode_case(plan, assigned, folder)
        extra = folder / "request-admission.jsonl"
        save(folder / "scheduling-provenance.json", {"version": VERSION, "finished_utc": now(),
            "config_sha256": sha(config_path), "scheduler_sha256": config["scheduler_sha256"],
            "original_plan_sha256": config["original_plan_sha256"], "dispatch_plan": str(dispatch_path),
            "dispatch_plan_sha256": sha(dispatch_path), "assigned_replica": assigned["slot"],
            "request_admission_sha256": sha(extra) if extra.exists() else None,
            "request_arguments_return_values_and_timeout_unchanged": True,
            "engine_policy_score_or_model_settings_changed": False,
            "bitwise_llm_equivalence_to_previous_request_order_claimed": False})
        return result
    finally:
        LLMClient.chat = original


def history_costs(campaign, completed, case_map):
    values = defaultdict(list)
    for cid in completed:
        r = load(campaign / "episodes" / cid / "report.json"); c = case_map[cid]
        values[c["scenario"], c["arm"]].append(float(r["elapsed_seconds"]))
    return {k: statistics.median(v) for k, v in values.items()}


def controller(config_path):
    import fcntl
    config = load(config_path); campaign = Path(config["campaign_dir"]); revision = Path(config["revision_dir"])
    runner = frozen_runner(config["snapshot"]); plan = load(campaign / "plan.json"); case_map = {c["id"]: c for c in plan["cases"]}
    lock = (campaign / ".run.lock").open("a"); ownership = False; children = {}
    old_controller_signaled = False; marker = campaign / "STOP_AFTER_CURRENT_EPISODES"; token = None
    state = {"schema": "remote-seed-status@2", "status": "preparing_handoff", "started_utc": now(),
        "controller": runner.process_identity(os.getpid()), "snapshot": config["snapshot"],
        "total_cases": len(plan["cases"]), "completed": [], "active": {}, "failures": [],
        "queue_policy": "strict seed barrier; dynamic LLM replicas; 2 prefetched episodes/replica with 1 HTTP call/replica; separate 4-worker RL pool",
        "scheduler_revision": VERSION, "scheduler_dir": str(revision)}
    completed = set()
    def persist():
        state["updated_utc"] = now(); state["completed"] = sorted(completed)
        state["completed_by_seed"] = dict(Counter(str(case_map[x]["seed"]) for x in completed))
        save(revision / "status.json", state)
        if ownership: save(campaign / "status.json", state)
    persist()
    try:
        if sha(Path(__file__)) != config["scheduler_sha256"] or sha(campaign / "plan.json") != config["original_plan_sha256"]:
            raise RuntimeError("frozen scheduling inputs differ")
        runner.verify_plan(plan); runner.service_health(plan)
        old_launch = load(campaign / "launch.json"); old_state = load(campaign / "status.json")
        if old_state.get("failures"): raise RuntimeError("existing failures require review, not automatic retry")
        if not same_process(old_launch["controller"], old_state["controller"]):
            raise RuntimeError("old controller identities disagree")
        marker = campaign / "STOP_AFTER_CURRENT_EPISODES"
        token = {"purpose": "scheduler-only handoff", "revision": str(revision), "created_utc": now()}
        with marker.open("x", encoding="utf-8") as stream: json.dump(token, stream)
        time.sleep(4.5)  # Let the old two-second loop stop admitting new work.
        old_state = load(campaign / "status.json")
        if old_state.get("failures"): raise RuntimeError("old controller recorded a failure during handoff")
        save(revision / "handoff-old-status.json", old_state); save(revision / "handoff-old-launch.json", old_launch)
        active = deepcopy(old_state.get("active", {}))
        for cid, item in list(active.items()):
            if cid not in case_map: raise RuntimeError("unknown running episode")
            if runner.alive(item["process"]):
                actual = runner.process_identity(item["process"]["pid"])
                if actual["session_id"] == old_launch["controller"]["session_id"]:
                    raise RuntimeError("episode is not in its own detached session")
                item.update(replica=item["case"]["slot"], gated=False, adopted=True)
            elif runner.certified(campaign / "episodes" / cid): del active[cid]
            else: raise RuntimeError("old episode ended without complete evidence: " + cid)
        old = old_launch["controller"]
        state["active"] = active; persist()
        if runner.alive(old):
            command = Path("/proc", str(old["pid"]), "cmdline").read_bytes().decode().split("\0")
            if str(Path(config["snapshot"]) / "role_c_toolkit/remote_seed_campaign.py") not in command or "run" not in command:
                raise RuntimeError("refusing to signal an unrecognized controller")
            if not runner.alive(old): raise RuntimeError("controller changed during handoff")
            os.kill(old["pid"], signal.SIGTERM)  # PID only: never its group or episode children.
            old_controller_signaled = True
            for _ in range(50):
                if not runner.alive(old): break
                time.sleep(.1)
            if runner.alive(old): raise RuntimeError("old controller did not yield; no escalation")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB); ownership = True
        state["active"] = active
        for c in plan["cases"]:
            folder = campaign / "episodes" / c["id"]
            if c["id"] in active: continue
            if folder.exists():
                if not runner.certified(folder): raise RuntimeError("uncertified existing folder preserved: " + c["id"])
                completed.add(c["id"])
        for cid, item in active.items():
            if not runner.alive(item["process"]) and not runner.certified(campaign / "episodes" / cid):
                raise RuntimeError("adopted episode disappeared without evidence")
        save(revision / "handoff.json", {"finished_utc": now(), "old_controller": old,
            "new_controller": state["controller"], "adopted_processes": active, "completed_preserved": len(completed),
            "only_old_scheduler_pid_signaled": True, "episode_processes_restarted_or_signaled": False})
        new_launch = deepcopy(old_launch); new_launch.update(created_utc=now(), controller=state["controller"],
            controller_log=str(revision / "controller.log"), command=config["controller_command"],
            scheduler_revision=VERSION, scheduler_dir=str(revision), previous_launch=str(revision / "handoff-old-launch.json"))
        save(campaign / "launch.json", new_launch)
        if load(marker) != token: raise RuntimeError("control marker was changed by another actor")
        marker.rename(revision / "handoff-stop-marker.json")
        state["status"] = "running"; persist(); print(json.dumps({"event": "handoff_complete", "adopted": list(active), "completed": len(completed)}), flush=True)
        costs = history_costs(campaign, completed, case_map)
        while len(completed) < len(plan["cases"]):
            for cid, item in list(state["active"].items()):
                process = children.get(cid)
                code = process.poll() if process else None
                alive = runner.alive(item["process"])
                age = time.time() - datetime.fromisoformat(item["started_utc"]).timestamp()
                if alive and age > plan["episode_wall_watchdog_seconds"] and not item.get("watchdog_signaled"):
                    # Preserve the original wall watchdog, never a shorter optimization timeout.
                    identity = runner.process_identity(item["process"]["pid"])
                    if identity and identity["start_ticks"] == item["process"]["start_ticks"]:
                        os.kill(identity["pid"], signal.SIGTERM)
                    state["failures"].append({"case_id": cid, "reason": "original external wall watchdog; partial traces preserved"})
                    item["watchdog_signaled"] = True
                    continue
                if alive: continue
                if (code in (None, 0)) and runner.certified(Path(item["folder"])):
                    completed.add(cid); costs.update(history_costs(campaign, [cid], case_map))
                    print(json.dumps({"event": "case_finished", "case_id": cid, "completed": len(completed), "utc": now()}), flush=True)
                else:
                    state["failures"].append({"case_id": cid, "returncode": code, "reason": "native failure or incomplete artifact; no automatic retry"})
                del state["active"][cid]; children.pop(cid, None); persist()
            stop = marker.exists() or bool(state["failures"])
            if stop and not state["active"]: break
            if not stop:
                if sha(campaign / "plan.json") != config["original_plan_sha256"]: raise RuntimeError("original plan changed")
                selected = choices(plan["cases"], completed, state["active"], costs,
                    cpu_limit=config["cpu_workers"], llm_prefetch=config["llm_prefetch_per_replica"])
                if selected: runner.verify_plan(plan)
                for case, replica in selected:
                    cid = case["id"]; folder = campaign / "episodes" / cid
                    if folder.exists(): raise RuntimeError("refusing to overwrite episode: " + cid)
                    if case["planner"] != "rl": runner.service_health(plan)
                    dispatch = derived_plan(plan, cid, replica, config["original_plan_sha256"])
                    dispatch_path = revision / "dispatch-plans" / (cid + ".json")
                    if dispatch_path.exists(): raise RuntimeError("prior dispatch requires inspection: " + cid)
                    save(dispatch_path, dispatch)
                    command = [sys.executable, "-u", "-B", str(Path(__file__).resolve()), "worker",
                               "--config", str(config_path), "--dispatch-plan", str(dispatch_path), "--case-id", cid]
                    env = os.environ.copy(); env.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
                        MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1", MPLBACKEND="Agg", PYTHONDONTWRITEBYTECODE="1")
                    console = campaign / "logs" / (cid + ".log")
                    with console.open("xb", buffering=0) as stream:
                        process = subprocess.Popen(command, cwd=str(Path(config["snapshot"]) / "openmd/code/eval"),
                            env=env, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                    assigned = next(c for c in dispatch["cases"] if c["id"] == cid)
                    item = {"case": assigned, "process": runner.process_identity(process.pid), "started_utc": now(),
                        "folder": str(folder), "console": str(console), "replica": replica, "gated": True,
                        "dispatch_plan": str(dispatch_path), "dispatch_plan_sha256": sha(dispatch_path), "adopted": False}
                    state["active"][cid] = item; children[cid] = process; persist()
                    print(json.dumps({"event": "case_started", "case_id": cid, "replica": replica, "planner": case["planner"], "utc": now()}), flush=True)
            time.sleep(2); persist()
        state["status"] = "complete" if len(completed) == len(plan["cases"]) else "blocked_failed_case" if state["failures"] else "stopped_by_control_file"
    except Exception as error:
        state["status"] = "controller_error"; state["controller_error"] = type(error).__name__ + ": " + str(error)
        state["traceback"] = traceback.format_exc(); print(state["traceback"], flush=True)
        if not ownership and not old_controller_signaled and token is not None and marker.exists():
            if load(marker) == token:
                marker.rename(revision / "aborted-handoff-stop-marker.json")
    finally:
        state["finished_utc"] = now(); persist(); lock.close()
    return 0 if state["status"] == "complete" else 2


def start(campaign, revision, cpu_workers=4, llm_prefetch=2):
    import fcntl
    campaign, revision = campaign.resolve(), revision.resolve()
    if campaign == BASE or not campaign.is_relative_to(BASE) or not revision.is_relative_to(campaign):
        raise ValueError("outside the explicitly owned campaign")
    if not 1 <= cpu_workers <= 4 or not 1 <= llm_prefetch <= 2: raise ValueError("unvalidated concurrency")
    preservation = load(revision / "preservation.json"); runner = frozen_runner(preservation["snapshot"])
    with (revision / ".launch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (revision / "launch.json").exists():
            old = load(revision / "launch.json")
            if runner.alive(old["controller"]): return {"status": "already_running", **old}
            raise RuntimeError("prior launch stopped: inspect preserved state; do not duplicate")
        if sha(campaign / "plan.json") != preservation["plan_sha256"]: raise RuntimeError("plan differs from preservation baseline")
        for row in preservation["completed_artifacts"]:
            folder = campaign / "episodes" / row["case_id"]
            if sha(folder / "manifest.json") != row["manifest_sha256"] or not runner.certified(folder):
                raise RuntimeError("preserved completed data changed: " + row["case_id"])
        (revision / "dispatch-plans").mkdir(exist_ok=True)
        config_path = revision / "config.json"
        command = [sys.executable, "-u", "-B", str(Path(__file__).resolve()), "controller", "--config", str(config_path)]
        config = {"version": VERSION, "created_utc": now(), "campaign_dir": str(campaign), "revision_dir": str(revision),
            "snapshot": preservation["snapshot"], "original_plan_sha256": preservation["plan_sha256"],
            "scheduler_sha256": sha(Path(__file__)), "cpu_workers": cpu_workers, "llm_prefetch_per_replica": llm_prefetch,
            "maximum_inflight_http_per_replica": 1, "controller_command": command}
        save(config_path, config)
        with (revision / "controller.log").open("xb", buffering=0) as stream:
            process = subprocess.Popen(command, cwd=str(revision), stdin=subprocess.DEVNULL,
                                       stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        record = {"created_utc": now(), "controller": runner.process_identity(process.pid), "command": command,
                  "config": str(config_path), "scheduler_sha256": config["scheduler_sha256"]}
        save(revision / "launch.json", record); return {"status": "started", **record}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["start", "controller", "worker"])
    p.add_argument("--campaign-dir", type=Path); p.add_argument("--revision-dir", type=Path)
    p.add_argument("--config", type=Path); p.add_argument("--dispatch-plan", type=Path); p.add_argument("--case-id")
    a = p.parse_args()
    if a.action == "start": print(json.dumps(start(a.campaign_dir, a.revision_dir)), flush=True); return 0
    if a.action == "controller": return controller(a.config)
    return worker(a.config, a.dispatch_plan, a.case_id)


if __name__ == "__main__":
    raise SystemExit(main())
