"""Read-only observer on exact self-replays of released P3a trajectories.

Gold roles are written only to the offline dataset. No extra observation calls
are made; class hooks observe the existing calls without changing instance state.
"""
import argparse
import copy
import sys
from pathlib import Path
from common import read, write, digest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--toolkit", type=Path, required=True)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--campaign", type=Path, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--variant", choices=["llm_original", "rule_planner", "rule-rule", "rule-rl", "rl"], required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    sys.path.insert(0, str(a.toolkit.resolve()))
    import grid_replay
    is_p1 = a.variant in ["rule-rule", "rule-rl", "rl"]
    if is_p1:
        matches = sorted(a.campaign.glob(f"medium_continuous_{a.variant}_s{a.seed}_strong_a*/episode.json"),
                         key=lambda x: int(x.parent.name.rsplit("_a", 1)[1]))
        original = matches[-1]
    else:
        original = a.campaign / f"seed-{a.seed}" / a.variant / "episode.json"
    baseline = read(original)
    expected = {k.replace("\\", "/"): v for k, v in baseline["source_hashes"].items()}
    actual = {k.replace("\\", "/"): v for k, v in grid_replay.component_hashes(a.source).items()}
    ckpt_hash = baseline["config"].get("mappo_checkpoint_sha256", baseline["config"].get("checkpoint_sha256"))
    if actual != expected or (ckpt_hash and digest(a.checkpoint) != ckpt_hash):
        raise ValueError("Source/checkpoint does not match released trajectory")
    _, Env, _, _, _, _ = grid_replay.load_components(a.source)
    get = Env._get_observation
    frames = {}

    def observe(env, role="blue"):
        obs = get(env, role)
        if role != "blue":
            return obs
        tick = env.step_count
        sit = obs.get("situational_data", {})
        for c in [*sit.get("detected_contacts", []), *sit.get("unknown_contacts", [])]:
            ent = env.entities.get(c["id"])
            if ent is None or ent.entity_type.name != "RED_TRANSPORT":
                continue
            key = (c["id"], tick)
            if key in frames:
                continue
            local = {uid: env.get_local_observation(uid)["grid"].tolist()
                     for uid in env.blue_units if env.entities[uid].alive}
            frames[key] = {"contact": c["id"], "tick": tick,
                           "position": copy.deepcopy(c["position"]),
                           "heading": copy.deepcopy(c.get("heading")),
                           "local_grid": local,
                           "gold_real": bool(ent.is_real_threat)}
        return obs

    Env._get_observation = observe
    try:
        if is_p1:
            from grid_env.agents.rule_agent import RuleAgent
            from grid_env.agents.mappo_agent import MAPPOAgent
            config = baseline["config"]
            env = Env(difficulty=config["difficulty"], seed=a.seed, task_mode=config["task_mode"])
            if a.variant == "rl":
                agent = MAPPOAgent(role="blue", seed=a.seed, trained=True,
                                   checkpoint_path=str(a.checkpoint.resolve()))
            else:
                agent = RuleAgent(role="blue", seed=a.seed,
                                  executor_checkpoint=str(a.checkpoint.resolve()) if a.variant == "rule-rl" else None)
                agent.plan_interval = config["plan_interval"]
            import json
            events = [json.loads(line) for line in original.with_name("events.jsonl").read_text().splitlines()]
            if digest(original.with_name("events.jsonl")) != baseline["events_sha256"]:
                raise ValueError("P1 trace hash mismatch")
            for row in events:
                obs = env._get_observation("blue")
                actions = {k: int(v) for k, v in agent.act(obs, env=env).items()}
                if actions != row["actions"]:
                    raise ValueError(f"P1 action replay diverged at step {row['step']}")
                env.step(actions, None)
                env.compute_reward("blue")
                if bool(env.done) != row["done"]:
                    raise ValueError("P1 termination replay mismatch")
            if grid_replay.canonical(env.get_episode_metrics()) != grid_replay.canonical(baseline["metrics"]):
                raise ValueError("P1 full metrics replay mismatch")
            result = {"replay_check": {"exact_match": True},
                      "validation_level": "Exact actions, termination and full metrics; P1 has no full-state fingerprints"}
        else:
        # Only portable path-key separators change. Decisions, values and state
        # fingerprints remain byte-equivalent data; the archived file is untouched.
            portable = copy.deepcopy(baseline)
            portable["source_hashes"] = grid_replay.component_hashes(a.source)
            write(a.output / "portable_replay_source.json", portable)
            result = grid_replay.run_episode(
                a.source, a.output / "replay", seed=a.seed, difficulty=baseline["config"]["difficulty"],
                task_mode=baseline["config"]["task_mode"],
                planner_kind="llm" if a.variant == "llm_original" else "rule",
                executor_kind="mappo", interval=baseline["config"]["interval"],
                executor_contract=baseline["config"]["executor_contract"],
                mappo_checkpoint=a.checkpoint, replay_from=a.output / "portable_replay_source.json")
            result["validation_level"] = "Exact full environment state, actions, broker and metrics fingerprints"
    finally:
        Env._get_observation = get
    if result.get("replay_check", {}).get("exact_match") is not True:
        write(a.output / "audit.json", {"eligible": False, "replay_check": result.get("replay_check")})
        raise ValueError("Cross-platform exact replay failed; exclude reconstructed views")
    records = grid_replay.plain(sorted(frames.values(), key=lambda r: (r["contact"], r["tick"])))
    write(a.output / "frames.json", {"seed": a.seed, "variant": a.variant,
                                    "source_episode_sha256": digest(original), "frames": records,
                                    "source_batch": "P1" if is_p1 else "P3a"})
    write(a.output / "audit.json", {"eligible": True, "exact_replay": True,
                                   "frames": len(records), "source_episode_sha256": digest(original),
                                   "frame_file_sha256": digest(a.output / "frames.json"),
                                   "validation_level": result["validation_level"]})
    print({"seed": a.seed, "variant": a.variant, "frames": len(records), "exact_replay": True})


if __name__ == "__main__":
    main()
