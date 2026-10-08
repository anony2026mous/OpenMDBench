"""
OpenMDBench — Elo Rating System

Maintains separate Elo ratings for blue-role and red-role performance,
updated after each match.  K=32, initial Elo=1500.

Reference: Appendix G.4 of OpenMDBench paper.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


class EloSystem:
    """
    Two-role Elo rating system.

    Each system has a blue Elo and a red Elo, updated independently.
    After a match between A (blue) and B (red):
      - A's blue Elo and B's red Elo are updated based on the outcome.
    """

    def __init__(self, k: int = 32, initial: float = 1500.0):
        self.k = k
        self.initial = initial
        self.ratings: Dict[str, Dict[str, float]] = {}  # {agent: {"blue": elo, "red": elo}}
        self.match_history: List[dict] = []

    def register(self, agent_name: str):
        """Register a new agent with initial ratings."""
        if agent_name not in self.ratings:
            self.ratings[agent_name] = {
                "blue": self.initial,
                "red": self.initial,
            }

    def update(
        self,
        blue_agent: str,
        red_agent: str,
        blue_score: float,
    ) -> Tuple[float, float]:
        """
        Update Elo ratings after a match.

        Args:
            blue_agent: name of the agent playing blue
            red_agent: name of the agent playing red
            blue_score: score for blue (0.0 = loss, 0.5 = draw, 1.0 = win)

        Returns:
            (blue_elo_change, red_elo_change)
        """
        self.register(blue_agent)
        self.register(red_agent)

        blue_elo = self.ratings[blue_agent]["blue"]
        red_elo = self.ratings[red_agent]["red"]

        # Expected scores
        e_blue = 1.0 / (1.0 + 10 ** ((red_elo - blue_elo) / 400.0))
        e_red = 1.0 - e_blue

        # Actual scores
        s_blue = blue_score
        s_red = 1.0 - blue_score

        # Update
        delta_blue = self.k * (s_blue - e_blue)
        delta_red = self.k * (s_red - e_red)

        self.ratings[blue_agent]["blue"] += delta_blue
        self.ratings[red_agent]["red"] += delta_red

        self.match_history.append({
            "blue_agent": blue_agent,
            "red_agent": red_agent,
            "blue_score": blue_score,
            "blue_elo_before": blue_elo,
            "red_elo_before": red_elo,
            "blue_elo_after": self.ratings[blue_agent]["blue"],
            "red_elo_after": self.ratings[red_agent]["red"],
        })

        return delta_blue, delta_red

    def get_rating(self, agent_name: str) -> Dict[str, float]:
        """Get current ratings for an agent."""
        if agent_name not in self.ratings:
            self.register(agent_name)
        return {
            "blue": round(self.ratings[agent_name]["blue"], 1),
            "red": round(self.ratings[agent_name]["red"], 1),
            "average": round(
                (self.ratings[agent_name]["blue"] + self.ratings[agent_name]["red"]) / 2, 1
            ),
        }

    def get_rankings(self, role: str = "average") -> List[Tuple[str, float]]:
        """
        Get rankings by role.

        Args:
            role: "blue", "red", or "average"
        """
        if role == "average":
            items = [
                (name, (r["blue"] + r["red"]) / 2)
                for name, r in self.ratings.items()
            ]
        else:
            items = [(name, r[role]) for name, r in self.ratings.items()]

        return sorted(items, key=lambda x: x[1], reverse=True)

    def save(self, path: str):
        """Save ratings and history to disk."""
        data = {
            "ratings": self.ratings,
            "match_history": self.match_history,
            "k": self.k,
            "initial": self.initial,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str):
        """Load ratings from disk."""
        with open(path) as f:
            data = json.load(f)
        self.ratings = data["ratings"]
        self.match_history = data.get("match_history", [])
        self.k = data.get("k", 32)
        self.initial = data.get("initial", 1500.0)
