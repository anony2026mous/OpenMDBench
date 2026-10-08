"""
OpenMDBench — Phase 0 Tournament Runner

Runs a round-robin tournament through the CSS + ULHA evaluation pipeline.
Each agent system plays as BLUE against a scripted red attacker.
The tournament tests the full evaluation architecture:
  - CSS (environment management + trajectory recording)
  - ULHA protocol (polling-based agent interaction)
  - Metric engine (10 layered metrics)
  - Elo rating system (dual-role)
  - Round-robin scheduling

Usage:
    python run_tournament.py --episodes 5 --output_dir tournament_output
"""

import sys
import os
import json
import time
import argparse
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
    TimeoutError as FuturesTimeout,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation.css_server import CentralSimulationServer
from evaluation.ulha_client import ULHAClient
from evaluation.elo import EloSystem
from evaluation.metrics import MetricEngine

from grid_env.agents.rule_agent import RuleAgent
from grid_env.agents.hybrid_agent import HybridAgent
from grid_env.agents.ppo_agent import PPOAgent
from grid_env.agents.random_agent import RandomAgent
from grid_env.grid_env import GRID_SIZE, MAX_STEPS


# ---------------------------------------------------------------------------
# Scripted Red Attacker
# ---------------------------------------------------------------------------

class ScriptedRedAttacker:
    """
    Scripted red attacker for tournament play.

    Strategy:
    - Move all units toward the port (northwest corner at (1,18))
    - Avoid obstacles (simple reactive avoidance)
    - Spread approach from multiple angles

    This is a fixed opponent — not evaluated, just provides opposition.
    """

    PORT_X, PORT_Y = 1, 18

    def __init__(self, seed=42):
        self.rng = __import__('numpy').random.RandomState(seed)

    def act(self, observation, env=None):
        """Decide on RED's OWN observation (role="red" view, where
        friendly_assets lists red units)."""
        actions = {}
        red_assets = observation.get("situational_data", {}).get("friendly_assets", [])

        for asset in red_assets:
            uid = asset["id"]
            x, y = asset["position"]
            dx = self.PORT_X - x
            dy = self.PORT_Y - y

            # Add slight randomness for diversity
            if self.rng.random() < 0.1:
                actions[uid] = self.rng.randint(0, 5)
                continue

            # Greedy approach to port (Direction: UP=0 DOWN=1 LEFT=2 RIGHT=3 STAY=4)
            if abs(dx) >= abs(dy):
                if dx > 0:
                    actions[uid] = 3   # RIGHT (+x)
                elif dx < 0:
                    actions[uid] = 2   # LEFT (-x)
                else:
                    actions[uid] = 4   # STAY
            else:
                if dy > 0:
                    actions[uid] = 0   # UP (+y)
                elif dy < 0:
                    actions[uid] = 1   # DOWN (-y)
                else:
                    actions[uid] = 4   # STAY

        return actions


# ---------------------------------------------------------------------------
# Agent Factory
# ---------------------------------------------------------------------------

def _get_checkpoint(difficulty: str, ckpt_seed: int = 42) -> str:
    """Get the best checkpoint path for a given difficulty.

    v2: prefers the per-seed MAPPO checkpoints (train_mappo.py);
    falls back to legacy v1 PPO names (archived saturation evidence).
    ckpt_seed selects the TRAINING seed — H.10 criterion 5 ("reproducible
    across 3 seeds") is checked both over evaluation-seed blocks and,
    strictly, across training seeds 42/43/44.
    """
    candidates = [
        f"checkpoints/mappo_{difficulty}_s{ckpt_seed}_best.pt",
        f"checkpoints/mappo_{difficulty}_s{ckpt_seed}_final.pt",
        f"checkpoints/mappo_{difficulty}_best.pt",
        f"checkpoints/mappo_{difficulty}_final.pt",
        f"checkpoints/ppo_{difficulty}_best.pt",
        f"checkpoints/ppo_{difficulty}_final.pt",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def make_agent_factories(difficulty: str = "simple",
                         ckpt_seed: int = 42, llm_base_urls=()):
    """Create agent factories with trained checkpoints for the given difficulty."""
    from grid_env.agents.pure_llm_agent import PureLLMAgent
    from grid_env.agents.llm_client import LLMClient

    urls = tuple(llm_base_urls or ())

    def llm_client_for_seed(seed):
        # Stable assignment keeps reruns on the same replica regardless of
        # thread completion order. An empty list preserves the existing env.
        return LLMClient(base_url=urls[seed % len(urls)]) if urls else LLMClient()

    ckpt = _get_checkpoint(difficulty, ckpt_seed)
    print(f"  Using checkpoint: {ckpt}")

    factories = {
        "random": lambda role, seed: RandomAgent(role=role, seed=seed),
        # System B: LLM directly controls every unit each step
        "pure_llm": lambda role, seed: PureLLMAgent(
            role=role, seed=seed, llm_client=llm_client_for_seed(seed)
        ),
    }

    if ckpt:
        factories["pure_rl"] = lambda role, seed: PPOAgent(
            role=role, seed=seed, trained=True, checkpoint_path=ckpt
        )
        factories["rule"] = lambda role, seed: RuleAgent(
            role=role, seed=seed, executor_checkpoint=ckpt
        )
        factories["hybrid"] = lambda role, seed: HybridAgent(
            role=role, seed=seed, executor_checkpoint=ckpt,
            llm_client=llm_client_for_seed(seed),
        )
    else:
        # Fallback: untrained agents
        print("  WARNING: No trained checkpoint found. Using untrained agents.")
        factories["pure_rl"] = lambda role, seed: PPOAgent(
            role=role, seed=seed, trained=False
        )
        factories["rule"] = lambda role, seed: RuleAgent(role=role, seed=seed)
        factories["hybrid"] = lambda role, seed: HybridAgent(
            role=role, seed=seed, llm_client=llm_client_for_seed(seed)
        )

    return factories


# ---------------------------------------------------------------------------
# Match Runner
# ---------------------------------------------------------------------------

def run_match(css, blue_agent_name, difficulty, seed, agent_factory,
              red_agent=None, step_timeout: float = 5.0):
    """
    Run a single match: blue_agent (via ULHA) vs red (scripted).

    Robustness contract (competition-grade):
      - Each side decides on its OWN observation (symmetric partial
        observability).  Blue polls through the ULHA; an explicit
        red_agent receives env._get_observation(role="red").
      - A missing red_agent keeps the ENVIRONMENT-BUILTIN scripted red
        (it is part of the env and reads internal state — this also
        matches the distribution PPO was trained against).
      - Every act() call runs under a hard deadline plus an exception
        guard: on timeout or crash the side falls back to random
        actions for that step, counted in act_timeouts/act_errors.

    Returns:
        dict with match results
    """
    # Create ULHA client for blue agent
    client = ULHAClient(
        css=css,
        agent_name=blue_agent_name,
        scenario_id=f"grid_{difficulty}",
        difficulty=difficulty,
        role="blue",
        seed=seed,
    )

    # Create agents
    blue_agent = agent_factory(role="blue", seed=seed)
    if red_agent is None:
        red_agent = None  # builtin env script drives red

    # Last-resort fallback agents (fast, dependency-free)
    blue_fallback = RandomAgent(role="blue", seed=seed + 101)
    red_fallback = RandomAgent(role="red", seed=seed + 202)
    act_stats = {"errors": 0, "timeouts": 0}

    # Reset → get initial observation via polling
    obs = client.reset()
    env = client.get_env()  # Phase 0: local access for RL obs

    # Decision deadlines: agents may declare a larger budget (e.g. the
    # hybrid agent's LLM planning calls); others get the runner default.
    blue_deadline = getattr(blue_agent, "decision_timeout", step_timeout)
    red_deadline = (getattr(red_agent, "decision_timeout", step_timeout)
                    if red_agent is not None else step_timeout)

    # Give planning agents a handle to record upper-layer decisions
    # into the trajectory (needed for attribution / counterfactual replay)
    if hasattr(blue_agent, "ulha_client"):
        blue_agent.ulha_client = client

    if hasattr(blue_agent, 'reset'):
        blue_agent.reset()

    # act() executes in a helper thread so the deadline is enforceable;
    # the fallback path runs inline (random act is fast and safe).
    act_pool = ThreadPoolExecutor(max_workers=1)

    def guarded_act(agent, obs_view, deadline, fallback):
        fut = act_pool.submit(agent.act, obs_view, env=env)
        try:
            return fut.result(timeout=deadline)
        except FuturesTimeout:
            act_stats["timeouts"] += 1
            return fallback.act(obs_view)
        except Exception:
            act_stats["errors"] += 1
            return fallback.act(obs_view)

    # Run episode through the CSS + ULHA pipeline
    try:
        for step in range(MAX_STEPS):
            # Blue agent acts (via ULHA observation)
            blue_actions = guarded_act(blue_agent, obs, blue_deadline, blue_fallback)

            if red_agent is not None:
                # Red decides on its OWN view, never on blue's observation
                red_obs = env._get_observation(role="red")
                red_actions = guarded_act(red_agent, red_obs, red_deadline,
                                          red_fallback)
            else:
                # Builtin scripted opponent (part of the environment)
                red_actions = {}

            # Merge all actions and submit through CSS
            all_actions = {}
            all_actions.update(blue_actions)
            all_actions.update(red_actions)

            result = client.submit_actions(all_actions)
            obs = result["observation"]

            if result["done"]:
                break
    except Exception:
        # Best-effort session cleanup so a forfeited match does not
        # leak its session in the CSS table (competition invariant)
        try:
            client.close()
        except Exception:
            pass
        raise
    finally:
        act_pool.shutdown(wait=False)

    # End session → get final metrics
    final = client.close()

    return {
        "agent": blue_agent_name,
        "difficulty": difficulty,
        "seed": seed,
        "winner": final.get("winner", "unknown"),
        "steps": final.get("steps", 0),
        "composite": final.get("composite_score", 0),
        "planning": final.get("planning_score", 0),
        "execution": final.get("execution_score", 0),
        "mission_success": final.get("env_metrics", {}).get("mission_success", False),
        "metric_details": final.get("metric_details", {}),
        # v2 coupling/efficiency telemetry straight from the environment
        # (H.8 metrics 6-9: lock, handover, fuel — needed by validate.py
        # and the Phase-7 attribution framework)
        "env_metrics": final.get("env_metrics", {}),
        "act_errors": act_stats["errors"],
        "act_timeouts": act_stats["timeouts"],
        "llm_base_url": getattr(getattr(blue_agent, "llm", None), "base_url", None),
    }


def run_match_safe(css, blue_agent_name, difficulty, seed, agent_factory,
                   red_agent=None, step_timeout: float = 5.0) -> dict:
    """
    Match-level fault tolerance (competition invariant): a single
    crashing match must NEVER take down the whole tournament.

    On any non-act-level failure (agent construction, session errors,
    corrupted state...) the match is recorded as a FORFEIT: blue loses,
    the error message is stored for post-hoc audit.  This mirrors the
    distributed design where a dead worker means a lost match, not a
    dead benchmark.
    """
    try:
        return run_match(css, blue_agent_name, difficulty, seed,
                         agent_factory, red_agent=red_agent,
                         step_timeout=step_timeout)
    except Exception as e:  # noqa: BLE001 — deliberate catch-all
        import traceback
        print(f"  !! MATCH FAILURE {blue_agent_name}@{difficulty} seed={seed}: "
              f"{type(e).__name__}: {e}")
        traceback.print_exc()
        return {
            "agent": blue_agent_name,
            "difficulty": difficulty,
            "seed": seed,
            "winner": "red",
            "steps": 0,
            "composite": 0.0,
            "planning": 0.0,
            "execution": 0.0,
            "mission_success": False,
            "metric_details": {},
            "env_metrics": {},
            "act_errors": 0,
            "act_timeouts": 0,
            "forfeit": True,
            "forfeit_reason": f"{type(e).__name__}: {e}",
        }


def environment_fingerprint() -> dict:
    """
    Seed-locking support: hash the environment + protocol source so
    every result file records exactly which code produced it.  A
    result can be disputed/replicated by checking this fingerprint.
    """
    import hashlib

    code_dir = os.path.dirname(os.path.abspath(__file__))
    files = [
        "grid_env/grid_env.py",
        "evaluation/css_server.py",
        "evaluation/trajectory.py",
        "evaluation/metrics.py",
        "evaluation/elo.py",
        "run_tournament.py",
    ]
    digest = hashlib.sha256()
    per_file = {}
    for rel in files:
        path = os.path.join(code_dir, rel)
        try:
            with open(path, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()[:12]
        except OSError:
            h = "missing"
        per_file[rel] = h
        digest.update(f"{rel}:{h};".encode())

    from grid_env.grid_env import GRID_SIZE, MAX_STEPS
    return {
        "composite_sha256": digest.hexdigest()[:16],
        "files": per_file,
        "grid_size": GRID_SIZE,
        "max_steps": MAX_STEPS,
    }


# ---------------------------------------------------------------------------
# Tournament
# ---------------------------------------------------------------------------

def run_tournament(args):
    """Run the complete round-robin tournament."""
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # Get agent list from first difficulty (all share the same agent names)
    llm_base_urls = tuple(getattr(args, "llm_base_urls", None) or ())
    sample_factories = make_agent_factories(args.difficulties[0],
                                             args.ckpt_seed, llm_base_urls)
    agent_names = list(sample_factories.keys())
    if args.agents:
        agent_names = [n for n in agent_names if n in args.agents]

    print("=" * 70)
    print("OpenMDBench Phase 0 — Evaluation Tournament")
    print("=" * 70)
    print(f"Agents:       {agent_names}")
    print(f"Difficulties: {args.difficulties}")
    print(f"Seeds:        {args.seeds}")
    print(f"Episodes:     {args.episodes}")
    print(f"Output:       {output_dir}")
    print()

    # Initialize evaluation infrastructure
    css = CentralSimulationServer(output_dir=output_dir)
    elo = EloSystem(k=32, initial=1500.0)
    for name in agent_names:
        elo.register(name)

    all_results = []
    match_count = 0
    t_start = time.time()

    for difficulty in args.difficulties:
        seeds = list(args.seeds) if args.seeds is not None else list(range(args.episodes))
        factories = make_agent_factories(difficulty, args.ckpt_seed,
                                         llm_base_urls)

        for agent_name in factories:
            if agent_name not in agent_names:
                continue
            print(f"\n--- {agent_name.upper()} @ {difficulty} "
                  f"(parallel={args.parallel}) ---")

            if args.parallel <= 1:
                # Sequential path (original behavior)
                for seed in seeds:
                    match_count += 1
                    result = run_match_safe(css, agent_name, difficulty, seed,
                                            factories[agent_name],
                                            step_timeout=args.step_timeout)
                    all_results.append(result)

                    # Update Elo (use blue_score from env metrics)
                    blue_score = result.get("metric_details", {}).get("TSR", 0.5)
                    elo.update(agent_name, "scripted_red", blue_score)

                    status = "WIN" if result["mission_success"] else "LOSS"
                    print(f"  [{match_count}] seed={seed} | {status} | "
                          f"comp={result['composite']:.3f} "
                          f"plan={result['planning']:.3f} "
                          f"exec={result['execution']:.3f} | "
                          f"steps={result['steps']}")
            else:
                # Parallel path: matches run in a thread pool.
                # Safe because each match owns its own session/env/agents;
                # the CSS session table and trajectory recorder are
                # session-keyed and lock-guarded.  Results are collected
                # first and Elo is updated afterwards in deterministic
                # (agent, seed) order — completion order varies with
                # thread scheduling and would make Elo non-reproducible.
                with ThreadPoolExecutor(max_workers=args.parallel) as pool:
                    futures = {
                        pool.submit(run_match_safe, css, agent_name, difficulty,
                                    seed, factories[agent_name],
                                    step_timeout=args.step_timeout): seed
                        for seed in seeds
                    }
                    for fut in as_completed(futures):
                        seed = futures[fut]
                        result = fut.result()  # fail fast on match errors
                        match_count += 1
                        all_results.append(result)

                        status = "WIN" if result["mission_success"] else "LOSS"
                        print(f"  [{match_count}] seed={seed} | {status} | "
                              f"comp={result['composite']:.3f} "
                              f"plan={result['planning']:.3f} "
                              f"exec={result['execution']:.3f} | "
                              f"steps={result['steps']}")

                # Deterministic Elo updates AFTER all matches complete
                for result in sorted(
                    (r for r in all_results
                     if r["agent"] == agent_name and r["difficulty"] == difficulty),
                    key=lambda r: r["seed"],
                ):
                    blue_score = result.get("metric_details", {}).get("TSR", 0.5)
                    elo.update(agent_name, "scripted_red", blue_score)

    elapsed = time.time() - t_start
    print(f"\nAll matches finished in {elapsed/60:.1f} min "
          f"({len(all_results)} matches, {len([r for r in all_results if r.get('forfeit')])} forfeits).")

    # Save results
    forfeits = [r for r in all_results if r.get("forfeit")]
    output = {
        "num_matches": len(all_results),
        "agents": agent_names,
        "difficulties": args.difficulties,
        "episodes": args.episodes,
        "ckpt_seed": args.ckpt_seed,
        "environment_fingerprint": environment_fingerprint(),
        "forfeit_count": len(forfeits),
        "elo_rankings": {
            role: elo.get_rankings(role)
            for role in ["blue", "red", "average"]
        },
        "matches": all_results,
    }

    results_path = os.path.join(output_dir, "tournament_results.json")
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    # Save Elo details
    elo.save(os.path.join(output_dir, "elo_ratings.json"))

    # Save trajectories
    traj_path = css.save_trajectories("all_trajectories.json")

    # Print summary
    print("\n" + "=" * 70)
    print("TOURNAMENT SUMMARY")
    print("=" * 70)

    # Per-agent summary
    for agent_name in agent_names:
        agent_results = [r for r in all_results if r["agent"] == agent_name]
        if not agent_results:
            continue
        avg_comp = sum(r["composite"] for r in agent_results) / len(agent_results)
        avg_plan = sum(r["planning"] for r in agent_results) / len(agent_results)
        avg_exec = sum(r["execution"] for r in agent_results) / len(agent_results)
        wins = sum(1 for r in agent_results if r["mission_success"])
        win_rate = wins / len(agent_results) * 100

        rating = elo.get_rating(agent_name)
        print(f"\n  {agent_name.upper():>10}:")
        print(f"    Win Rate:   {win_rate:.0f}% ({wins}/{len(agent_results)})")
        print(f"    Composite:  {avg_comp:.4f}")
        print(f"    Planning:   {avg_plan:.4f}")
        print(f"    Execution:  {avg_exec:.4f}")
        print(f"    Elo (blue): {rating['blue']:.1f}")
        print(f"    Elo (avg):  {rating['average']:.1f}")

    # Elo rankings
    print("\n" + "-" * 40)
    print("ELO RANKINGS (Blue Role):")
    for rank, (name, score) in enumerate(elo.get_rankings("blue"), 1):
        if name == "scripted_red":
            continue
        print(f"  {rank}. {name:<15} {score:.1f}")

    print(f"\nResults saved to: {results_path}")
    print(f"Trajectories saved to: {traj_path}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenMDBench Phase 0 Tournament")
    parser.add_argument("--episodes", type=int, default=5,
                        help="Number of episodes per agent per difficulty")
    parser.add_argument("--difficulties", nargs="+",
                        default=["simple", "medium", "complex"],
                        help="Difficulty levels to test")
    parser.add_argument("--seeds", nargs="+", type=int, default=None,
                        help="Specific seeds (default: 0..episodes-1)")
    parser.add_argument("--output_dir", type=str, default="tournament_output",
                        help="Output directory")
    parser.add_argument("--agents", nargs="+", default=None,
                        help="Subset of agents to run (default: all)")
    parser.add_argument("--parallel", type=int, default=1,
                        help="Number of matches to run concurrently "
                             "(thread pool; size this to model endpoint "
                             "capacity, 1 = sequential)")
    parser.add_argument("--llm-base-urls", "--llm_base_urls", nargs="+",
                        dest="llm_base_urls", default=None,
                        help="OpenAI-compatible model endpoints; assign LLM "
                             "matches by seed, cycling through this list")
    parser.add_argument("--step_timeout", type=float, default=5.0,
                        help="Hard deadline (seconds) per act() call; "
                             "agents may declare a larger decision_timeout "
                             "(e.g. hybrid LLM planning). Exceeding it "
                             "falls back to random actions")
    parser.add_argument("--ckpt_seed", type=int, default=42,
                        help="Training seed of the MAPPO checkpoint to load "
                             "(H.10 criterion 5 strict reading: run 42/43/44)")
    args = parser.parse_args()

    if args.seeds:
        args.episodes = len(args.seeds)

    run_tournament(args)
