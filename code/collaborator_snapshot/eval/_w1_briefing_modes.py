"""Compare the three briefing modes exactly as the LLM would receive them."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, r"C:\Code\source-code\openmd\code\eval")

import run_episode  # noqa: E402

PUB = os.environ.get("PROBE_SCENARIO", "IE-11-DECOY-SCREEN")
payload = run_episode.load_attack_profile_data(PUB)

for mode in ("withheld", "aggregate", "declared"):
    print("=" * 78)
    print(f"{PUB}   briefing = {mode}")
    print("=" * 78)
    print(run_episode._build_roe_notes(payload, briefing=mode))
    print()
