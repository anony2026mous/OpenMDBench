"""Probe the DeepSeek backend: reachability, latency, and thinking behaviour.

Reads the key from an environment variable (default ``DEEPSEEK_API_KEY``) and
never prints it.  Reports, per probe:

  * HTTP status and wall-clock latency,
  * token usage,
  * whether the response carried ``reasoning_content`` (thinking) — the
    requirement is a NON-thinking fast model, so this must be empty,
  * whether the vLLM-specific ``chat_template_kwargs`` parameter is accepted.

Usage:
    python _w1_ds_probe.py [--model deepseek-flash] [--key-env DEEPSEEK_API_KEY]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "https://api.deepseek.com/v1"


def call(base_url: str, model: str, key: str, messages: list[dict],
         *, extra: dict | None = None, timeout: int = 60) -> tuple[bool, dict]:
    payload = {"model": model, "messages": messages, "max_tokens": 256,
               "temperature": 0.1}
    if extra:
        payload.update(extra)
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"},
        method="POST",
    )
    start = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            return True, {"latency": time.time() - start, "body": body}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:400]
        return False, {"latency": time.time() - start,
                       "error": f"HTTP {error.code}: {detail}"}
    except Exception as error:  # noqa: BLE001
        return False, {"latency": time.time() - start,
                       "error": f"{type(error).__name__}: {error}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--key-scope", default="User",
                        choices=("Process", "User", "Machine"))
    args = parser.parse_args()

    key = os.environ.get(args.key_env) or ""
    if not key and args.key_scope != "Process":
        # 会话环境里没有时，从 User/Machine 作用域补取（不打印内容）
        try:
            import subprocess
            key = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"[Environment]::GetEnvironmentVariable('{args.key_env}','{args.key_scope}')"],
                capture_output=True, text=True, timeout=30).stdout.strip()
        except Exception:  # noqa: BLE001
            key = ""
    print(f"key env {args.key_env}: {'present' if key else 'MISSING'} (len={len(key)})")
    print(f"base_url = {args.base_url}")
    print(f"model    = {args.model}\n")
    if not key:
        return 2

    plan = ("Output JSON only: {\"goal_commands\": [], \"reasoning\": \"probe\"}\n\n"
            "Tick 0. Situation report: two hostile UAVs inbound at 14 km and 16 km "
            "from the protected objective, both on straight courses. Interceptors "
            "are ready with 2 missiles each. Issue goal commands.")

    print("=== probe 1: plain chat (no vLLM-specific params) ===")
    ok, result = call(args.base_url, args.model, key, [
        {"role": "system", "content": "You are a strategic commander issuing GOAL COMMANDS."},
        {"role": "user", "content": plan},
    ])
    if not ok:
        print(f"  FAILED after {result['latency']:.1f}s: {result['error']}")
        return 1
    body = result["body"]
    choice = (body.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    usage = body.get("usage") or {}
    reasoning = message.get("reasoning_content") or ""
    print(f"  latency      = {result['latency']:.2f} s")
    print(f"  finish       = {choice.get('finish_reason')}")
    print(f"  usage        = prompt={usage.get('prompt_tokens')} "
          f"completion={usage.get('completion_tokens')} "
          f"total={usage.get('total_tokens')}")
    print(f"  reasoning    = {len(reasoning)} chars "
          f"({'THINKING ON' if reasoning.strip() else 'no thinking'})")
    content = (message.get("content") or "").strip()
    print(f"  content head = {content[:160]!r}")

    print("\n=== probe 2: with vLLM-specific chat_template_kwargs (expected to fail) ===")
    ok2, result2 = call(args.base_url, args.model, key, [
        {"role": "user", "content": "ping"}],
        extra={"chat_template_kwargs": {"enable_thinking": False}})
    print(f"  accepted = {ok2}" + ("" if ok2 else f"  ({result2['error'][:120]})"))

    print("\n=== probe 3: latency stability over 3 calls ===")
    latencies = []
    for index in range(3):
        ok3, result3 = call(args.base_url, args.model, key, [
            {"role": "user", "content": plan}])
        if ok3:
            latencies.append(result3["latency"])
            print(f"  call {index + 1}: {result3['latency']:.2f} s")
        else:
            print(f"  call {index + 1}: FAILED {result3['error'][:100]}")
    if latencies:
        print(f"  mean = {sum(latencies) / len(latencies):.2f} s "
              f"min = {min(latencies):.2f} s max = {max(latencies):.2f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
