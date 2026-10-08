"""Transport probe: is the DeepSeek SSL EOF caused by connection reuse?

The planner talks to DeepSeek through ``requests``.  A first episode ran 1200
ticks and then every subsequent call failed with
``SSLEOFError(8, 'UNEXPECTED_EOF_WHILE_READING')``, while a plain ``urllib``
probe succeeded immediately before and after.  The usual cause is a stale pooled
keep-alive connection being reused after the peer closed it.

This probe sends N sequential requests in each mode and reports the failure rate:

  A. default (connection pooling / keep-alive)
  B. ``Connection: close`` header forced
  C. fresh ``requests.Session`` per call

Usage:
    python _w1_ds_transport_probe.py [--calls 6]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time

import requests

BASE = "https://api.deepseek.com/v1"
BODY = {"model": "deepseek-flash", "max_tokens": 32, "temperature": 0.0,
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}]}


def resolve_key() -> str:
    value = os.environ.get("DEEPSEEK_API_KEY")
    if value:
        return value
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[Environment]::GetEnvironmentVariable('DEEPSEEK_API_KEY','User')"],
            capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def run_mode(label: str, calls: int, key: str, *, mode: str) -> None:
    ok = 0
    failures = []
    latencies = []
    session = None
    for index in range(calls):
        headers = {"Content-Type": "application/json",
                   "Authorization": f"Bearer {key}"}
        if mode == "close":
            headers["Connection"] = "close"
        if mode == "fresh":
            session = requests.Session()
            headers["Connection"] = "close"
        start = time.time()
        try:
            poster = session.post if session is not None else requests.post
            response = poster(f"{BASE}/chat/completions", headers=headers,
                              json=BODY, timeout=60)
            response.raise_for_status()
            ok += 1
            latencies.append(time.time() - start)
        except Exception as error:  # noqa: BLE001
            failures.append(f"{type(error).__name__}")
        finally:
            if session is not None:
                session.close()
                session = None
    mean = f"{sum(latencies)/len(latencies):.2f}s" if latencies else "-"
    print(f"  {label:<34} ok={ok}/{calls}  mean={mean:<7} "
          f"failures={','.join(failures) if failures else 'none'}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calls", type=int, default=6)
    args = parser.parse_args()
    key = resolve_key()
    if not key:
        print("no API key")
        return 2
    print(f"sequential requests, {args.calls} per mode\n")
    run_mode("A default (pooling keep-alive)", args.calls, key, mode="default")
    run_mode("B Connection: close", args.calls, key, mode="close")
    run_mode("C fresh Session + close", args.calls, key, mode="fresh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
