"""
高保真实验 LLM 客户端 —— 基于 grid 的 llm_client.py 重写，默认调用 Qwen3.8-27B。

与 grid 版差异：
1. 默认后端改为 Qwen3.8-27B（端点由 `OPENAI_BASE_URL` 指定，见 `code/.env.example`，秒级响应，适合批量评估）
2. 保留 OpenAI 兼容协议、超时重试、token 统计
3. 新增并发闸门（grid 教训：complex 层 3 并发会引发 120s 读超时连环重试）
4. 保留 max_tokens 可配置（grid 默认 512，高保真 goal 更复杂可放宽）
5. 流式调用（stream=True）：进程被 kill = 连接断开，服务器立即中止生成、
   释放 GPU 槽位，不留"僵尸请求"（非流式下 kill 进程会遗留服务端生成）

用法：
    client = LLMClient()  # 默认读环境变量，指向 Qwen3.8-27B
    reply = client.chat(system_prompt, user_message)
"""

from __future__ import annotations

import json
import os
import time
import threading
from typing import Optional

import requests


def _load_env_file():
    """Load .env from the project code directory (does not override existing vars)."""
    env_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"
    )
    env_path = os.path.normpath(env_path)
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_env_file()


class LLMClient:
    """OpenAI-compatible LLM client for planner calls (Qwen3.8-27B default)."""

    # 并发闸门：complex 层长 reasoning 下并发超过 3 会连环超时（grid 实测教训）
    _concurrency_limit = 2
    _active_calls = 0
    _lock = threading.Lock()

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 50,
        max_retries: int = 2,
        max_tokens: int = 512,
        enable_thinking: Optional[bool] = False,
    ):
        self.base_url = (
            base_url or os.environ.get("OPENAI_BASE_URL", "http://172.18.116.170:8000/v1")
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model or os.environ.get("LLM_DEFAULT_MODEL", "Qwen3.8-27B")
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        # Qwen3.8 是思考模型：不关思考时 max_tokens 会被 reasoning 吃光，
        # content 返回空（finish_reason=length）。默认关掉，直接输出干净 content。
        self.enable_thinking = enable_thinking

        # Statistics
        self.total_calls = 0
        self.total_tokens = 0
        self.total_latency = 0.0
        self.errors = 0
        self._last_usage: dict = {}  # 最近一次成功调用的 usage（供测量子类读取）
        # 调用策略：单次 50s 超时、无重试、失败直接抛错（不回退）——
        # run_episode 捕获后优雅中止并保存现场。保留连续失败计数供诊断。
        self.consecutive_failures = 0
        self.circuit_open = False

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.1,
    ) -> str:
        """
        Send a chat request to the LLM.

        Args:
            system_prompt: System message (role definition)
            user_message: User message (current situation)
            max_tokens: Maximum response tokens (defaults to self.max_tokens)
            temperature: Sampling temperature

        Returns:
            The assistant's response text (empty string on failure)
        """
        max_tokens = max_tokens or self.max_tokens
        start = time.time()

        # 并发闸门：超过上限时等待
        with self._lock:
            while self._active_calls >= self._concurrency_limit:
                time.sleep(0.5)

        self.total_calls += 1
        with self._lock:
            self._active_calls += 1

        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,  # 流式：进程被杀=连接断开，服务器立即中止生成
                "stream_options": {"include_usage": True},
            }
            if self.enable_thinking is not None:
                payload["chat_template_kwargs"] = {
                    "enable_thinking": self.enable_thinking
                }

            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
                stream=True,
            )
            resp.raise_for_status()
            content, usage = self._read_sse(resp)
            if not content:
                raise RuntimeError("empty completion content")

            latency = time.time() - start
            self.total_latency += latency
            self.total_tokens += usage.get("total_tokens", 0)
            self._last_usage = dict(usage)
            self.consecutive_failures = 0
            return content

        except Exception as e:
            # 单次调用、无重试、无回退：失败直接弹出错误（run_episode 会优雅中止并保存现场）
            self.errors += 1
            self.consecutive_failures += 1
            print(f"[LLMClient] Error: {type(e).__name__}: {e}")
            raise
        finally:
            with self._lock:
                self._active_calls -= 1

    @staticmethod
    def _read_sse(resp) -> tuple:
        """解析 SSE 流：拼接 content 增量、捕获 usage（末块），兼容非 SSE 兜底。"""
        pieces: list = []
        raw_lines: list = []
        usage: dict = {}
        saw_sse = False
        with resp:
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data:"):
                    saw_sse = True
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        continue
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if choices:
                        delta = choices[0].get("delta") or {}
                        piece = delta.get("content")
                        if piece:
                            pieces.append(piece)
                    if chunk.get("usage"):
                        usage = chunk["usage"]
                else:
                    raw_lines.append(line)
        if not saw_sse and raw_lines:
            # 服务器忽略了 stream 参数，整包 JSON 兜底
            try:
                data = json.loads("".join(raw_lines))
            except json.JSONDecodeError:
                return "", {}
            usage = data.get("usage") or {}
            content = data["choices"][0]["message"].get("content")
            pieces = [content] if content else []
        return "".join(pieces), usage

    def get_stats(self) -> dict:
        """Return usage statistics."""
        return {
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "total_latency": round(self.total_latency, 2),
            "avg_latency": round(self.total_latency / max(self.total_calls, 1), 2),
            "avg_tokens_per_call": round(self.total_tokens / max(self.total_calls, 1), 1),
            "errors": self.errors,
            "circuit_open": self.circuit_open,
            "model": self.model,
            "base_url": self.base_url,
        }

    def reset_stats(self):
        """Reset usage statistics."""
        self.total_calls = 0
        self.total_tokens = 0
        self.total_latency = 0.0
        self.errors = 0
        self.consecutive_failures = 0
        self.circuit_open = False


if __name__ == "__main__":
    # 自测：直接运行此文件，验证能否输出回答
    client = LLMClient()
    print(f"后端: {client.base_url}  模型: {client.model}")
    print("--- 发送测试请求 ---")
    reply = client.chat(
        "你是一个战术指挥官助手。",
        "请用一句话回答：你是什么模型？",
    )
    print(f"回答: {reply}")
    print(f"统计: {client.get_stats()}")
