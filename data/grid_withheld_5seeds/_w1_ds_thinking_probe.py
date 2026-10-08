"""Find the parameter that actually disables thinking on the DeepSeek backend.

``deepseek-flash`` reasons by default: with a small max_tokens the reasoning
content consumes the whole budget and ``content`` comes back empty.  The vLLM
parameter the Qwen path uses (``chat_template_kwargs.enable_thinking``) is
accepted with HTTP 200 but silently ignored here, so guessing is not enough —
this script tries every plausible switch and reports which one produced an empty
``reasoning_content`` together with non-empty ``content``.

Usage:
    python _w1_ds_thinking_probe.py [--model deepseek-flash]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

BASE = "https://api.deepseek.com/v1"
PROMPT = ('Reply with JSON only: {"goal_commands": [], "reasoning": "ok"}.')

VARIANTS: list[tuple[str, dict]] = [
    ("baseline (no switch)", {}),
    ("chat_template_kwargs.enable_thinking=False", {"chat_template_kwargs": {"enable_thinking": False}}),
    ("enable_thinking=False (top level)", {"enable_thinking": False}),
    ("thinking={'type':'disabled'}", {"thinking": {"type": "disabled"}}),
    ("thinking=False", {"thinking": False}),
    ("reasoning={'enabled':False}", {"reasoning": {"enabled": False}}),
    ("reasoning_effort='none'", {"reasoning_effort": "none"}),
    ("reasoning_effort='minimal'", {"reasoning_effort": "minimal"}),
    ("extra_body.thinking disabled", {"extra_body": {"thinking": {"type": "disabled"}}}),
]


def resolve_key(name: str, scope: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"[Environment]::GetEnvironmentVariable('{name}','{scope}')"],
            capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def call(model: str, key: str, extra: dict, timeout: int = 120) -> dict:
    payload = {"model": model, "messages": [{"role": "user", "content": PROMPT}],
               "max_tokens": 200, "temperature": 0.0}
    payload.update(extra)
    request = urllib.request.Request(
        f"{BASE}/chat/completions", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"}, method="POST")
    start = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"ok": True, "latency": time.time() - start,
                    "body": json.loads(response.read().decode())}
    except urllib.error.HTTPError as error:
        return {"ok": False, "latency": time.time() - start,
                "error": f"HTTP {error.code}: {error.read().decode('utf-8','replace')[:200]}"}
    except Exception as error:  # noqa: BLE001
        return {"ok": False, "latency": time.time() - start,
                "error": f"{type(error).__name__}: {error}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--key-env", default="DEEPSEEK_API_KEY")
    args = parser.parse_args()
    key = resolve_key(args.key_env, "User")
    if not key:
        print("no API key")
        return 2

    print(f"model = {args.model}\n")
    print(f"{'variant':<46}{'ok':<5}{'latency':>9}{'reason':>8}{'content':>9}  verdict")
    print("-" * 96)
    winners = []
    for label, extra in VARIANTS:
        result = call(args.model, key, extra)
        if not result["ok"]:
            print(f"{label:<46}{'no':<5}{result['latency']:>8.2f}s"
                  f"{'-':>8}{'-':>9}  {result['error'][:44]}")
            continue
        body = result["body"]
        choice = (body.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        reasoning = message.get("reasoning_content") or ""
        content = (message.get("content") or "").strip()
        good = (not reasoning.strip()) and bool(content)
        if good:
            winners.append(label)
        print(f"{label:<46}{'yes':<5}{result['latency']:>8.2f}s"
              f"{len(reasoning):>8}{len(content):>9}  "
              f"{'THINKING OFF ✓' if good else 'still thinking'}")

    print()
    if winners:
        print("可用的关思考写法：" + "; ".join(winners))
    else:
        print("没有找到能关闭思考的参数 —— 需要改用 max_tokens 足够大并丢弃 reasoning，"
              "或换非思考模型 id。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
