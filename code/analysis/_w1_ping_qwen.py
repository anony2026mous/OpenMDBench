"""Qwen 端点连通性测试（只测通不通，不做实验）。

检查三件事：
1. 端点可达 + /v1/models 列表（确认模型名与 revision 线索）
2. 一次最小 chat 调用能否返回（关思考，max_tokens 很小）
3. 延迟量级（与历史 19 s 基线对照）

用法：python _w1_ping_qwen.py [--base URL] [--model NAME]
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request


def get(url: str, timeout: float = 15.0):
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def post(url: str, body: dict, timeout: float = 120.0):
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://172.18.116.170:8000/v1")
    parser.add_argument("--model", default="Qwen3.8-27B")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    print(f"[1/3] GET {base}/models")
    try:
        status, payload = get(f"{base}/models")
    except urllib.error.HTTPError as error:
        print(f"      HTTP {error.code}: {error.reason}")
        return 1
    except Exception as error:                                   # noqa: BLE001
        print(f"      连不上：{type(error).__name__}: {error}")
        return 1
    ids = [item.get("id") for item in payload.get("data", [])]
    print(f"      HTTP {status}  模型数={len(ids)}")
    for name in ids:
        print(f"        - {name}")
    if args.model not in ids:
        print(f"      注意：{args.model!r} 不在列表里，将按名字直接尝试。")

    print(f"[2/3] POST {base}/chat/completions（最小请求，关思考）")
    body = {
        "model": args.model,
        "messages": [{"role": "user", "content": "reply with the single word: ok"}],
        "max_tokens": 16,
        "temperature": 0.0,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    started = time.time()
    try:
        status, payload = post(f"{base}/chat/completions", body)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:300]
        print(f"      HTTP {error.code}: {error.reason}\n      {detail}")
        return 1
    except Exception as error:                                   # noqa: BLE001
        print(f"      调用失败：{type(error).__name__}: {error}")
        return 1
    elapsed = time.time() - started
    choice = (payload.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = (message.get("content") or "").strip()
    reasoning = (message.get("reasoning_content") or "").strip()
    usage = payload.get("usage") or {}
    print(f"      HTTP {status}  延迟 {elapsed:.2f}s  finish={choice.get('finish_reason')}")
    print(f"      content={content!r}")
    if reasoning:
        print(f"      reasoning_content 非空（{len(reasoning)} 字符）⇒ 关思考开关可能未生效")
    print(f"      usage={usage}")

    print("[3/3] 结论")
    print(f"      端点可达、模型可推理；单次最小调用 {elapsed:.2f}s")
    print(f"      （历史基线：真实规划 prompt 下 mean 19.0 s / 5.4k token/次）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
