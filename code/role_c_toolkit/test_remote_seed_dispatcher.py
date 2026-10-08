from copy import deepcopy
from pathlib import Path
import importlib.util
import json
import os
import threading
import time
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location("dispatcher", Path(__file__).with_name("remote_seed_dispatcher.py"))
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)


def case(name, seed=31, planner="llm", slot=0):
    return {"id": name, "seed": seed, "phase": "new", "planner": planner, "arm": planner, "slot": slot, "scenario": name}


def active(c, gated=True):
    return {"case": c, "replica": c["slot"], "gated": gated}


def test_seed_barrier_never_advances_while_previous_seed_is_active():
    a, b = case("a"), case("b", seed=37)
    assert d.choices([a,b], set(), {"a": active(a)}, {}) == []
    assert d.choices([a,b], {"a"}, {}, {})[0][0] == b


def test_idle_replica_can_take_pending_case_from_busy_original_slot():
    a, b = case("a"), case("b")
    assert d.choices([a,b], set(), {"a": active(a, gated=False)}, {}) == [(b,1)]


def test_rl_jobs_use_separate_cpu_capacity_not_model_slots():
    cases = [case("r"+str(i), planner="rl") for i in range(6)] + [case("l"+str(i)) for i in range(6)]
    selected = d.choices(cases, set(), {}, {})
    assert sum(c["planner"] == "rl" for c,_ in selected) == 4
    assert sum(c["planner"] != "rl" for c,_ in selected) == 4
    assert [sum(c["planner"] != "rl" and s == i for c,s in selected) for i in [0,1]] == [2,2]


def test_completed_and_running_cases_are_not_duplicated():
    cases = [case(x) for x in ["done","running","pending"]]
    selected = d.choices(cases, {"done"}, {"running": active(cases[1])}, {})
    assert [c["id"] for c,_ in selected] == ["pending"]


def test_long_known_jobs_start_first_and_spread_load():
    cases = [case(x) for x in ["short","long","middle"]]
    costs = {("short","llm"):10,("long","llm"):100,("middle","llm"):80}
    selected = d.choices(cases, set(), {}, costs)
    assert [c["id"] for c,_ in selected] == ["long","middle","short"]
    assert [s for _,s in selected] == [0,1,1]


def test_original_plan_and_all_nonrouting_conditions_are_preserved():
    original = {"cases":[case("a"),case("b")],"parameters":{"temperature":.1,"max_tokens":1024},
                "engine_pin":{"hash":"frozen"},"endpoints":["a","b"]}
    before = deepcopy(original); changed = d.derived_plan(original, "b", 1, "hash")
    assert original == before and changed["cases"][0] == original["cases"][0]
    restored = deepcopy(changed); restored.pop("scheduling_dispatch"); restored["cases"][1]["slot"] = 0
    assert restored == original


@pytest.mark.parametrize("replica", [-1,2,9])
def test_unknown_replica_is_rejected(replica):
    with pytest.raises(ValueError): d.derived_plan({"cases":[case("a")]},"a",replica,"hash")


def test_process_identity_ignores_transient_cpu_state_but_rejects_pid_reuse():
    assert d.same_process({"pid":1,"start_ticks":"a","state":"R"},{"pid":1,"start_ticks":"a","state":"S"})
    assert not d.same_process({"pid":1,"start_ticks":"a"},{"pid":1,"start_ticks":"b"})
    assert not d.same_process(None,{"pid":1,"start_ticks":"a"})
    assert not d.same_process({"state":"R"},{"state":"S"})


def test_cpu_active_jobs_do_not_block_idle_replica_and_caps_include_running_jobs():
    running = [case("cpu",planner="rl"),case("llm",slot=0)]
    pending = [case("r"+str(i),planner="rl") for i in range(5)] + [case("l"+str(i)) for i in range(5)]
    a = {c["id"]:active(c) for c in running}
    chosen = d.choices(running+pending,set(),a,{})
    assert sum(c["planner"]=="rl" for c,_ in chosen)==3
    assert sum(c["planner"]!="rl" for c,_ in chosen)==3
    assert sum(c["planner"]!="rl" and s==0 for c,s in chosen)==1


@pytest.mark.skipif(os.name != "posix", reason="Production request admission uses Linux flock")
def test_request_gate_serializes_and_preserves_args_returns_and_timeout(tmp_path):
    lock = tmp_path / "gate.lock"; client = SimpleNamespace(timeout=50); running = 0; peak = 0; answers = []; errors = []
    guard = threading.Lock(); returned = object()
    def original(c, system_prompt, user_message, max_tokens=None, temperature=.1):
        nonlocal running,peak
        assert c is client and (system_prompt,user_message,max_tokens,temperature) == ("s","u",1024,.1) and c.timeout == 50
        with guard: running += 1; peak = max(peak,running)
        time.sleep(.05)
        with guard: running -= 1
        return returned
    def call(index):
        try: answers.append(d.admitted_call(original,client,"s","u",max_tokens=1024,temperature=.1,lock_path=lock,log_path=tmp_path/f"{index}.jsonl",case_id=str(index),replica=0))
        except BaseException as e: errors.append(e)
    threads = [threading.Thread(target=call,args=(i,)) for i in range(4)]
    for t in threads:t.start()
    for t in threads:t.join(timeout=3);assert not t.is_alive()
    assert not errors and peak == 1 and len(answers) == 4 and all(x is returned for x in answers)
    rows = [json.loads((tmp_path/f"{i}.jsonl").read_text()) for i in range(4)]
    assert all(r["client_timeout_seconds_unchanged"] == 50 for r in rows)
    assert max(r["queue_wait_seconds"] for r in rows) > .05


@pytest.mark.skipif(os.name != "posix", reason="Production request admission uses Linux flock")
def test_request_gate_releases_after_exception(tmp_path):
    client = SimpleNamespace(timeout=50);args = dict(max_tokens=1024,temperature=.1,lock_path=tmp_path/"gate",log_path=tmp_path/"calls",case_id="a",replica=0)
    def failure(*a,**k):raise RuntimeError("original failure")
    with pytest.raises(RuntimeError,match="original failure"):d.admitted_call(failure,client,"s","u",**args)
    assert d.admitted_call(lambda *a,**k:"same",client,"s","u",**args) == "same"
    assert [json.loads(x)["outcome"] for x in (tmp_path/"calls").read_text().splitlines()] == ["exception","returned"]
