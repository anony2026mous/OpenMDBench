"""Anthropic-Messages adapter for third-party planners (MiniMax), for the E6b ablation.

The frozen grid client (``grid_env.agents.llm_client.LLMClient``) speaks
OpenAI ``/chat/completions``.  MiniMax's OpenAI-compatible path prepends the model's
reasoning to ``content`` and therefore contaminates the planner answer, while its
Anthropic-compatible path returns reasoning and answer as separate content blocks.
``AnthropicMessagesClient`` keeps that surface but talks to
``POST /anthropic/v1/messages`` and keeps only the ``text`` blocks.

Evidence produced for every request, mirrored into ``requests.jsonl`` by the runner:
    request:  model/base_url/api_path/thinking_policy/max_tokens/temperature/system/user
    response: text/elapsed_seconds/empty/blocks/output_tokens/stop_reason/thinking_blocks

Credentials come from the environment (``key_env``) and are never written to disk.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

DEFAULT_API_PATH = '/anthropic/v1/messages'
DEFAULT_ANTHROPIC_VERSION = '2023-06-01'
RETRY_STATUSES = (408, 409, 425, 429, 500, 502, 503, 504, 529)


def thinking_of(payload: dict) -> list:
    return [block for block in (payload.get('content') or [])
            if isinstance(block, dict) and block.get('type') == 'thinking']


class ProviderError(RuntimeError):
    """Raised when the provider keeps failing after the bounded retries."""


class AnthropicMessagesClient:
    """Drop-in replacement for the grid's ``LLMClient`` on the Anthropic path."""

    def __init__(self, base_url: str, model: str, key_env: str = 'MINIMAX_API_KEY',
                 api_path: str = DEFAULT_API_PATH, timeout: float = 300.0,
                 max_retries: int = 3, thinking_policy: str = 'disabled',
                 anthropic_version: str = DEFAULT_ANTHROPIC_VERSION,
                 response_marker: str | None = None, request_log: str | None = None,
                 min_interval_seconds: float = 0.0, extra_body: dict | None = None):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.key_env = key_env
        self.api_path = api_path
        self.timeout = timeout
        self.max_retries = max_retries
        self.thinking_policy = thinking_policy
        self.anthropic_version = anthropic_version
        self.response_marker = response_marker
        self.request_log = Path(request_log) if request_log else None
        self.min_interval_seconds = float(min_interval_seconds)
        self.extra_body = dict(extra_body or {})
        self.total_calls = 0
        self.total_tokens = 0
        self.total_output_tokens = 0
        self.errors = 0
        self.thinking_blocks_seen = 0
        self.truncated_responses = 0
        self.protocol_errors: list[str] = []
        self.last_blocks: list[str] = []
        self.last_stop_reason: str | None = None
        self.last_output_tokens: int | None = None
        self.last_usage: dict | None = None
        self._last_started = 0.0

    # ------------------------------------------------------------------ helpers

    @property
    def url(self) -> str:
        return self.base_url + self.api_path

    def _headers(self) -> dict:
        key = os.environ.get(self.key_env, '')
        if not key:
            raise ProviderError(f'{self.key_env} is not set in the environment')
        return {'x-api-key': key, 'anthropic-version': self.anthropic_version,
                'Content-Type': 'application/json', 'Accept': 'application/json'}

    def _body(self, system_prompt: str, user_message: str, max_tokens: int,
              temperature: float) -> dict:
        body = {'model': self.model, 'max_tokens': int(max_tokens),
                'temperature': float(temperature), 'messages': [
                    {'role': 'user', 'content': user_message}]}
        if system_prompt:
            body['system'] = system_prompt
        if self.thinking_policy == 'disabled':
            body['thinking'] = {'type': 'disabled'}
        body.update(self.extra_body)
        marker = self.response_marker
        if marker:
            # A per-call marker the harness can search for to prove post-processing:
            # appended as a user-visible instruction, so it also shows up in the log.
            body['messages'][0]['content'] = f'{user_message}\n\n{marker}'
        return body

    def _post(self, body: dict) -> dict:
        request = urllib.request.Request(self.url, data=json.dumps(body).encode('utf-8'),
                                         headers=self._headers(), method='POST')
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode('utf-8', 'replace'))

    # --------------------------------------------------------------------- chat

    def chat(self, system_prompt: str, user_message: str, max_tokens: int = 512,
             temperature: float = 0.1) -> str:
        """Return only the answer text; reasoning blocks are counted, never returned."""
        self._headers()  # fail before any request or log entry when the key is missing
        body = self._body(system_prompt, user_message, max_tokens, temperature)
        self._write_log({'kind': 'request', 'call_id': self.total_calls + 1,
                         'model': self.model, 'base_url': self.base_url,
                         'api_path': self.api_path, 'thinking_policy': self.thinking_policy,
                         'max_tokens': int(max_tokens), 'temperature': float(temperature),
                         'enable_thinking': False,
                         'system': str(system_prompt), 'user': str(user_message)})
        started = time.monotonic()
        if self.min_interval_seconds > 0:
            wait = self.min_interval_seconds - (started - self._last_started)
            if wait > 0:
                time.sleep(wait)
        self._last_started = time.monotonic()
        payload, last_error = None, None
        self.last_text = ''
        for attempt in range(self.max_retries + 1):
            try:
                payload = self._post(body)
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode('utf-8', 'replace')[:300]
                last_error = f'HTTP {exc.code}: {detail}'
                if exc.code not in RETRY_STATUSES or attempt == self.max_retries:
                    break
            except Exception as exc:  # noqa: BLE001 - network layer
                last_error = f'{type(exc).__name__}: {exc}'
                if attempt == self.max_retries:
                    break
            time.sleep(min(2 ** (attempt + 1), 20))
        elapsed = time.monotonic() - started
        self.total_calls += 1
        self.last_error = last_error
        if payload is None:
            self.errors += 1
            self.last_blocks, self.last_stop_reason = [], None
            self.last_output_tokens, self.last_usage = None, None
            self.last_elapsed = elapsed
            self.protocol_errors.append(last_error or 'unknown provider failure')
            self._write_log({'kind': 'response', 'call_id': self.total_calls, 'text': '',
                             'elapsed_seconds': elapsed, 'empty': True, 'blocks': [],
                             'thinking_blocks': 0, 'stop_reason': None, 'error': last_error})
            return ''
        self._absorb(payload, elapsed)
        self._write_log({'kind': 'response', 'call_id': self.total_calls, 'text': self.last_text,
                         'elapsed_seconds': elapsed, 'empty': not self.last_text.strip(),
                         'blocks': list(self.last_blocks), 'thinking_blocks': len(thinking_of(payload)),
                         'stop_reason': self.last_stop_reason,
                         'output_tokens': self.last_output_tokens})
        return self.last_text

    def _write_log(self, record: dict) -> None:
        if self.request_log is None:
            return
        safe = sanitize_record(record, self.key_env)
        with self.request_log.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(safe, ensure_ascii=False) + chr(10))

    def _absorb(self, payload: dict, elapsed: float) -> None:
        blocks = [block for block in (payload.get('content') or []) if isinstance(block, dict)]
        self.last_blocks = [str(block.get('type')) for block in blocks]
        thinking = thinking_of(payload)
        self.thinking_blocks_seen += len(thinking)
        if thinking:
            self.protocol_errors.append('thinking_block_returned')
        self.last_text = ''.join(str(block.get('text') or '') for block in blocks
                                 if block.get('type') == 'text')
        usage = payload.get('usage') or {}
        self.last_usage = usage
        self.last_output_tokens = usage.get('output_tokens')
        self.total_output_tokens += int(usage.get('output_tokens') or 0)
        self.total_tokens += int(usage.get('input_tokens') or 0) + int(usage.get('output_tokens') or 0)
        self.last_stop_reason = payload.get('stop_reason')
        if self.last_stop_reason == 'max_tokens':
            self.truncated_responses += 1
            self.protocol_errors.append('response_truncated_by_max_tokens')
        if not self.last_text.strip():
            self.protocol_errors.append('empty_text_block')
        self.last_elapsed = elapsed

    # The runner reads these after each call to build the request record.
    last_text = ''
    last_elapsed = 0.0
    last_error: str | None = None


def sanitize_record(record: dict, key_env: str) -> dict:
    """Refuse to persist anything that looks like the credential itself."""
    key = os.environ.get(key_env, '')
    if not key:
        return record
    blob = json.dumps(record, ensure_ascii=False, default=str)
    if key in blob:
        raise ProviderError('Refusing to write a request record containing the API key')
    return record
