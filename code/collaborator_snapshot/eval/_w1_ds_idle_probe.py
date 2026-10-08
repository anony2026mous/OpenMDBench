"""Does an idle gap break the pooled connection, and do retries recover it?

Run 1 showed the failure appears only after ~20 minutes of traffic, and the
transport probe showed pooled keep-alive connections are reliable while fresh
TLS handshakes are not.  This test reproduces the real pattern: one call, then an
idle gap, then a call with bounded retries, reporting which attempt succeeds.

Usage:
    python _w1_ds_idle_probe.py [--idle 75] [--attempts 4]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import time

import requests

BASE = "https://api.deepseek.com/v1"
BODY = {"model": "deepseek-flash", "max_tokens": 32, "temperature": 0.0,
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}]}


def key() -> str:
    value = os.environ.get("DEEPSEEK_API_KEY")
    if value:
        return value
    return subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "[Environment]::GetEnvironmentVariable('DEEPSEEK_API_KEY','User')"],
        capture_output=True, text=True, timeout=30).stdout.strip()


def call(k: str) -> tuple[bool, float, str]:
    start = time.time()
    try:
        response = requests.post(
            f"{BASE}/chat/completions",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {k}"},
            json=BODY, timeout=60)
        response.raise_for_status()
        return True, time.time() - start, ""
    except Exception as error:  # noqa: BLE001
        return False, time.time() - start, type(error).__name__


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--idle", type=float, default=75.0)
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--spacing", type=float, default=4.0)
    args = parser.parse_args()
    k = key()
    if not k:
        print("no API key")
        return 2

    ok, latency, err = call(k)
    print(f"warm-up call: {'ok' if ok else 'FAIL ' + err}  {latency:.2f}s")
    if not ok:
        return 1

    print(f"\n闲置 {args.idle:.0f}s（模拟两次规划之间的空档）…")
    time.sleep(args.idle)
    print(f"空闲后带重试的调用（最多 {args.attempts} 次、间隔 {args.spacing:.0f}s）：")
    for attempt in range(1, args.attempts + 1):
        ok, latency, err = call(k)
        print(f"  attempt {attempt}: {'ok' if ok else 'FAIL ' + err}  {latency:.2f}s")
        if ok:
            print(f"\n结论：空闲 {args.idle:.0f}s 后第 {attempt} 次尝试成功"
                  f"（{'无需重试' if attempt == 1 else '重试可恢复'}）")
            return 0
        time.sleep(args.spacing)
    print(f"\n结论：空闲后 {args.attempts} 次尝试全部失败 —— 单纯重试不足以恢复")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
