"""Small OpenAI-compatible DeepSeek API client built on the standard library."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable
from urllib import request

from fast_onboarding.core.config import DeepSeekConfig

HttpPost = Callable[[str, dict[str, str], bytes, int], dict[str, Any]]


def _urllib_post(url: str, headers: dict[str, str], body: bytes, timeout: int) -> dict[str, Any]:
    req = request.Request(url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


@dataclass
class DeepSeekClient:
    """Thin client for chat completions, injectable for offline tests."""

    config: DeepSeekConfig
    http_post: HttpPost = _urllib_post

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        return self.http_post(url, headers, body, self.config.timeout_seconds)

    def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        result = self.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        return result["choices"][0]["message"]["content"]

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        text = self.complete_text(system_prompt, user_prompt)
        return json.loads(text)
