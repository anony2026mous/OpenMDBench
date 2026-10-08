"""
OpenMDBench Evaluation Framework

Core modules for the distributed open evaluation architecture (C3):
  - css_server:      Central Simulation Server (environment wrapper)
  - ulha_client:     User-Local Hybrid Agent client (polling API)
  - trajectory:      Full trajectory recording for counterfactual replay
  - metrics:         Layered metric engine (10 metrics + composite)
  - elo:             Two-role Elo rating system
  - tournament:      Round-robin tournament scheduler
"""

from .css_server import CentralSimulationServer
from .ulha_client import ULHAClient, ULHAHTTPClient
from .trajectory import TrajectoryRecorder
from .metrics import MetricEngine, MetricResult
from .elo import EloSystem
from .tournament import TournamentScheduler, MatchResult

__all__ = [
    "CentralSimulationServer",
    "ULHAClient",
    "ULHAHTTPClient",
    "TrajectoryRecorder",
    "MetricEngine",
    "MetricResult",
    "EloSystem",
    "TournamentScheduler",
    "MatchResult",
]
