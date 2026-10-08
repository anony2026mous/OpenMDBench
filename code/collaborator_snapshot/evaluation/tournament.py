"""
OpenMDBench — Two-Role Round-Robin Tournament Scheduler

Organizes and executes the round-robin tournament where every pair
of systems plays two matches (A-blue vs B-red, B-blue vs A-red)
across all scenarios and seeds.

The tournament scheduler:
  1. Generates all match pairings
  2. Runs each match through the CSS + ULHA pipeline
  3. Updates Elo ratings after each match
  4. Collects and aggregates results

Reference: Section 4.1, Appendix G.4 of OpenMDBench paper.
"""

from __future__ import annotations

import json
import os
import time
from itertools import combinations
from typing import Any, Callable, Dict, List, Optional, Tuple

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.css_server import CentralSimulationServer
from evaluation.ulha_client import ULHAClient
from evaluation.elo import EloSystem
from evaluation.metrics import MetricEngine
from evaluation.trajectory import TrajectoryRecorder


class MatchResult:
    """Result of a single match."""

    def __init__(
        self,
        blue_agent: str,
        red_agent: str,
        scenario_id: str,
        difficulty: str,
        seed: int,
        blue_result: dict,
        red_result: dict,
    ):
        self.blue_agent = blue_agent
        self.red_agent = red_agent
        self.scenario_id = scenario_id
        self.difficulty = difficulty
        self.seed = seed
        self.blue_result = blue_result
        self.red_result = red_result

    @property
    def blue_score(self) -> float:
        return self.blue_result.get("composite_score", 0.0)

    @property
    def red_score(self) -> float:
        return self.red_result.get("composite_score", 0.0)

    @property
    def blue_mission_success(self) -> bool:
        return self.blue_result.get("env_metrics", {}).get("mission_success", False)

    def to_dict(self) -> dict:
        return {
            "blue_agent": self.blue_agent,
            "red_agent": self.red_agent,
            "scenario_id": self.scenario_id,
            "difficulty": self.difficulty,
            "seed": self.seed,
            "blue_composite": self.blue_result.get("composite_score", 0),
            "red_composite": self.red_result.get("composite_score", 0),
            "blue_planning": self.blue_result.get("planning_score", 0),
            "red_planning": self.red_result.get("planning_score", 0),
            "blue_execution": self.blue_result.get("execution_score", 0),
            "red_execution": self.red_result.get("execution_score", 0),
            "blue_mission_success": self.blue_mission_success,
            "winner": self.blue_result.get("winner", "unknown"),
        }


class TournamentScheduler:
    """
    Two-role round-robin tournament.

    Usage:
        scheduler = TournamentScheduler(
            agent_factories={"hybrid": create_hybrid, "rule": create_rule},
            scenarios=["grid_simple"],
            difficulties=["simple", "medium", "complex"],
            seeds=[42, 43, 44, 45, 46],
        )
        results = scheduler.run_all()
        rankings = scheduler.elo.get_rankings()
    """

    def __init__(
        self,
        agent_factories: Dict[str, Callable],
        scenarios: List[str] = None,
        difficulties: List[str] = None,
        seeds: List[int] = None,
        output_dir: str = "tournament_output",
    ):
        """
        Args:
            agent_factories: {name: callable(role, seed) -> agent}
                Each factory creates an agent for the given role.
            scenarios: list of scenario IDs
            difficulties: list of difficulty levels
            seeds: list of random seeds
            output_dir: directory for results
        """
        self.agent_factories = agent_factories
        self.scenarios = scenarios or ["grid_simple"]
        self.difficulties = difficulties or ["simple"]
        self.seeds = seeds or [42]
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        self.css = CentralSimulationServer(output_dir=output_dir)
        self.elo = EloSystem(k=32, initial=1500.0)
        self.results: List[MatchResult] = []

        # Register all agents
        for name in self.agent_factories:
            self.elo.register(name)

    def generate_matchings(self) -> List[Tuple[str, str]]:
        """Generate all pairs for round-robin."""
        names = list(self.agent_factories.keys())
        pairs = list(combinations(names, 2))
        return pairs

    def run_single_match(
        self,
        blue_agent_name: str,
        red_agent_name: str,
        scenario_id: str,
        difficulty: str,
        seed: int,
    ) -> MatchResult:
        """
        Run a single match: blue_agent (blue) vs red_agent (red).

        Both agents interact in the same environment.
        The blue agent is the primary evaluated agent.
        """
        # Create blue ULHA client
        blue_client = ULHAClient(
            css=self.css,
            agent_name=blue_agent_name,
            scenario_id=scenario_id,
            difficulty=difficulty,
            role="blue",
            seed=seed,
        )

        # Create agents
        blue_agent = self.agent_factories[blue_agent_name](role="blue", seed=seed)
        red_agent = self.agent_factories[red_agent_name](role="red", seed=seed)

        # Reset and get initial observation
        obs = blue_client.reset()
        env = blue_client.get_env()

        blue_agent.reset() if hasattr(blue_agent, 'reset') else None
        red_agent.reset() if hasattr(red_agent, 'reset') else None

        # Run episode
        for step in range(150):
            # Blue agent acts
            blue_actions = blue_agent.act(obs, env=env)

            # Red agent acts (scripted or via its own logic)
            red_actions = red_agent.act(obs, env=env)

            # Merge actions (blue agent controls blue units, red controls red)
            all_actions = {}
            all_actions.update(blue_actions)
            all_actions.update(red_actions)

            # Submit to CSS
            result = blue_client.submit_actions(all_actions)
            obs = result["observation"]

            if result["done"]:
                break

        # End session and get metrics
        blue_result = blue_client.close()

        # For the red agent's metrics, we need a separate view
        # For now, use the complement of blue's metrics
        red_result = {
            "composite_score": 1.0 - blue_result.get("composite_score", 0.5),
            "planning_score": 1.0 - blue_result.get("planning_score", 0.5),
            "execution_score": 1.0 - blue_result.get("execution_score", 0.5),
            "env_metrics": {
                "mission_success": not blue_result.get("env_metrics", {}).get("mission_success", True),
            },
            "winner": "red" if blue_result.get("winner") == "red" else "blue",
        }

        match_result = MatchResult(
            blue_agent=blue_agent_name,
            red_agent=red_agent_name,
            scenario_id=scenario_id,
            difficulty=difficulty,
            seed=seed,
            blue_result=blue_result,
            red_result=red_result,
        )

        # Update Elo
        blue_score_for_elo = blue_result.get("env_metrics", {}).get("blue_score", 0.5)
        self.elo.update(blue_agent_name, red_agent_name, blue_score_for_elo)

        return match_result

    def run_all(self) -> List[MatchResult]:
        """
        Run the complete round-robin tournament.

        For each pair (A, B):
          - A as blue vs B as red (all scenarios × difficulties × seeds)
          - B as blue vs A as red (all scenarios × difficulties × seeds)
        """
        pairs = self.generate_matchings()
        total_matches = len(pairs) * 2 * len(self.scenarios) * len(self.difficulties) * len(self.seeds)
        match_count = 0

        print(f"Tournament: {len(self.agent_factories)} agents, "
              f"{len(pairs)} pairs, {total_matches} total matches")

        for agent_a, agent_b in pairs:
            for scenario in self.scenarios:
                for difficulty in self.difficulties:
                    for seed in self.seeds:
                        # Match 1: A as blue, B as red
                        match_count += 1
                        print(f"  [{match_count}/{total_matches}] "
                              f"{agent_a}(blue) vs {agent_b}(red) "
                              f"| {scenario} | {difficulty} | seed={seed}")
                        result = self.run_single_match(
                            agent_a, agent_b, scenario, difficulty, seed
                        )
                        self.results.append(result)

                        # Match 2: B as blue, A as red
                        match_count += 1
                        print(f"  [{match_count}/{total_matches}] "
                              f"{agent_b}(blue) vs {agent_a}(red) "
                              f"| {scenario} | {difficulty} | seed={seed}")
                        result = self.run_single_match(
                            agent_b, agent_a, scenario, difficulty, seed
                        )
                        self.results.append(result)

        return self.results

    def save_results(self, filename: str = "tournament_results.json"):
        """Save all results and Elo ratings."""
        path = os.path.join(self.output_dir, filename)
        data = {
            "num_matches": len(self.results),
            "elo_rankings": {
                role: self.elo.get_rankings(role)
                for role in ["blue", "red", "average"]
            },
            "matches": [r.to_dict() for r in self.results],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        # Also save Elo details
        self.elo.save(os.path.join(self.output_dir, "elo_ratings.json"))

        # Save trajectories
        self.css.save_trajectories()

        return path

    def print_rankings(self):
        """Print current Elo rankings."""
        print("\n" + "=" * 60)
        print("ELO RANKINGS")
        print("=" * 60)
        for role in ["blue", "red", "average"]:
            print(f"\n  {role.upper()} ROLE:")
            rankings = self.elo.get_rankings(role)
            for rank, (name, elo) in enumerate(rankings, 1):
                print(f"    {rank}. {name:<20} {elo:.1f}")
