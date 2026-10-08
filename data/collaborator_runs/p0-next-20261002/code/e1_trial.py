"""Isolated episode with observational recorder and fixed no-thinking LLM config."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from common import write, digest


def plain(value):
    """Read-only conversion, avoiding dataclasses.asdict's tuple reconstruction."""
    import dataclasses
    import enum
    from collections.abc import Mapping
    if dataclasses.is_dataclass(value):
        return {f.name: plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, enum.Enum):
        return plain(value.value)
    if isinstance(value, Mapping):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f'Unrecordable state type: {type(value)}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--engine", type=Path, required=True)
    p.add_argument("--scenario", required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--arm", choices=["rule", "rule-rl", "rl", "pure-llm", "llm", "llm-rl"], required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--endpoint", default="http://127.0.0.1:8101/v1")
    p.add_argument("--trace-state", action="store_true")
    a = p.parse_args()
    import os
    os.environ["OPENMDBENCH_ROOT"] = str(a.engine.resolve())
    sys.path[:0] = [str(a.engine.resolve()), str(a.repo / "openmd/code/eval")]
    import run_episode
    import llm_client_hifi
    a.output.mkdir(parents=True, exist_ok=True)
    original_chat = llm_client_hifi.LLMClient._chat_once

    def chat(client, system_prompt, user_message, max_tokens=None, temperature=.1):
        if client.backend != "vllm" or client.enable_thinking is not False:
            raise ValueError("Frozen LLM no-thinking/backend guard failed")
        request = {"kind": "request", "model": client.model, "endpoint": client.base_url,
                   "system": system_prompt, "user": user_message, "temperature": 0,
                   "max_tokens": max_tokens or client.max_tokens, "enable_thinking": False}
        if "[declared briefing]" in system_prompt + user_message:
            raise ValueError("Future intelligence leakage")
        with (a.output / "llm_calls.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(request, ensure_ascii=False) + "\n")
        try:
            reply = original_chat(client, system_prompt, user_message, max_tokens=max_tokens, temperature=0)
        except Exception as error:
            with (a.output / "llm_calls.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps({"kind": "error", "error": str(error)}) + "\n")
            raise
        with (a.output / "llm_calls.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"kind": "response", "content": reply, "usage": client._last_usage}, ensure_ascii=False) + "\n")
        return reply

    llm_client_hifi.LLMClient._chat_once = chat
    # Optional per-tick physical/lifecycle recorder for clone equivalence.
    from openmdbench.sessions.lifecycle_v2 import SessionLifecycleV2
    original_step = SessionLifecycleV2.step
    original_submit = SessionLifecycleV2.submit_actions
    def submit(session, **kwargs):
        result=original_submit(session, **kwargs)
        batch=kwargs['batch'].model_dump(mode='json')
        # Never serialize authority_token or opaque session credentials.
        item={'tick':batch['based_on_tick'],'faction':batch['faction_id'],
              'persistent_commands':batch['persistent_commands'],'discrete_actions':batch['discrete_actions']}
        with (a.output/'action_batches.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(item,sort_keys=True)+'\n')
        return result
    SessionLifecycleV2.submit_actions=submit
    def step(session, *args, **kwargs):
        receipt = original_step(session, *args, **kwargs)
        entities = [{"id": e.id, "faction": e.faction_id, "domain": e.domain,
                         "state": e.state.model_dump(mode="json") if hasattr(e.state, "model_dump")
                         else plain(e.state)} for e in session.world_view.entities_stable()]
        own=[e for e in entities if e['faction']=='coalition.defender']
        value=json.dumps(own,sort_keys=True,separators=(',',':'))
        with (a.output/'defender_states.jsonl').open('a',encoding='utf8') as f:
            f.write(json.dumps({'tick':session.world_view.tick,'sha256':hashlib.sha256(value.encode()).hexdigest()})+'\n')
        if a.trace_state:
            payload = json.dumps(entities, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            with (a.output / "state_fingerprints.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps({"tick": session.world_view.tick, "sha256": hashlib.sha256(payload.encode()).hexdigest()}) + "\n")
        return receipt
    SessionLifecycleV2.step = step
    cli = ["--scenario", a.scenario, "--seed", str(a.seed), "--planner", a.arm,
           "--max-ticks", "1800", "--plan-interval", "10", "--decision-interval", "5",
           "--llm-briefing", "withheld", "--llm-backend", "vllm", "--llm-base-url", a.endpoint,
           "--llm-model", "Qwen3.8-27B", "--llm-max-tokens", "1024",
           "--checkpoint-tick", "1000000", "--checkpoint-dir", str(a.output / "checkpoints"),
           "--log", str(a.output / "episode.jsonl")]
    if a.arm in ["rl", "rule-rl", "llm-rl"]:
        checkpoint = a.repo / "openmd/code/eval/_w1_runs/rl" / (
            "theta_rl_legacy2.npz" if a.arm == "rl" else "theta_arm5_v12.npz")
        cli += ["--rl-theta", str(checkpoint), "--rl-speed-source", "legacy_tags"]
    args = run_episode.build_parser().parse_args(cli)
    log = run_episode._RunLog(args.log)
    try:
        report = run_episode.run_episode(args, log)
    finally:
        llm_client_hifi.LLMClient._chat_once = original_chat
        SessionLifecycleV2.step = original_step
        SessionLifecycleV2.submit_actions = original_submit
    report["e1_recording"] = {"frozen_cli": cli, "experiment_engine": str(a.engine),
                              "trial_script_sha256": digest(Path(__file__)),
                              "checkpoint_recording_disabled_only": True,
                              "runtime_threads":{k:os.environ.get(k) for k in ['TI_CPU_MAX_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']},
                              "LLM_temperature": 0, "thinking": False}
    write(a.output / "report.json", report)
    if report.get("aborted"):
        raise RuntimeError(report["aborted"])


if __name__ == "__main__":
    main()
