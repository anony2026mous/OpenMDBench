"""Read-only installation check for a copied 6.0 Role-C toolkit."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from toolkit_paths import PROJECT as ROOT, OPENMD, ENGINE, EVAL


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--probe-vllm", action="store_true")
    p.add_argument("--base-url", default="http://172.18.116.170:8000/v1")
    p.add_argument("--model", default="Qwen3.8-27B")
    args = p.parse_args()
    paths = {
        "hifi_engine": ENGINE / "openmdbench",
        "hifi_runner": EVAL / "run_episode.py",
        "hifi_weights_rl": EVAL / "_w1_runs/rl/theta_rl_legacy2.npz",
        "hifi_weights_rule_rl": EVAL / "_w1_runs/rl/theta_arm5_v12.npz",
        "hifi_weights_llm_rl": EVAL / "_w1_runs/rl/theta_arm5_llm_reward_v9.npz",
        "grid_engine": OPENMD / "code/grid_env/grid_env.py",
        "grid_checkpoint": Path(__file__).with_name("assets") / "mappo_medium_s42_best.pt",
    }
    files = {name: {"exists": path.exists(), "path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()
                    if path.is_file() else None}
             for name, path in paths.items()}
    modules = {name: importlib.util.find_spec(name) is not None
               for name in ("numpy", "scipy", "requests", "torch", "pydantic", "yaml")}
    result = {"python": sys.version.split()[0], "project_root": str(ROOT),
              "files": files, "modules": modules}
    if args.probe_vllm:
        import requests
        try:
            models = requests.get(args.base_url.rstrip("/") + "/models", timeout=10)
            models.raise_for_status()
            result["vllm_models"] = [item["id"] for item in models.json().get("data", [])]
            payload = {"model": args.model, "messages": [{"role": "user", "content": "Reply OK."}],
                       "max_tokens": 32, "temperature": 0.1,
                       "chat_template_kwargs": {"enable_thinking": False}}
            reply = requests.post(args.base_url.rstrip("/") + "/chat/completions",
                                  json=payload, timeout=30)
            reply.raise_for_status()
            body = reply.json()
            result["vllm_reply"] = {
                "content": (body["choices"][0]["message"].get("content") or "")[:120],
                "finish_reason": body["choices"][0].get("finish_reason")}
        except Exception as exc:
            result["vllm_error"] = f"{type(exc).__name__}: {exc}"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(item["exists"] for item in files.values()) and all(modules.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
