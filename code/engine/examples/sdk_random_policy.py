"""Minimal random-policy loop using only the public SDK."""

from __future__ import annotations

import random

from openmdbench.sdk import OpenMDBenchClient


def run(base_url: str, *, scenario_id: str = "MD-REC-001", seed: int = 7) -> None:
    policy_rng = random.Random(seed)
    with OpenMDBenchClient(base_url) as client:
        session = client.create_session(scenario_id, seed=seed)
        session_id = str(session["session_id"])
        for step_index in range(100):
            observation = client.observation(session_id)
            result = client.submit_action(
                session_id,
                timestamp=int(observation["timestamp"]),
                action=(policy_rng.uniform(0.0, 12.9), policy_rng.uniform(0.0, 360.0)),
                idempotency_key=f"random-policy-{step_index}",
            )
            if result["terminated"] or result["truncated"]:
                break
        print(client.results(session_id))
        client.close_session(session_id)


if __name__ == "__main__":
    run("http://127.0.0.1:8000")
