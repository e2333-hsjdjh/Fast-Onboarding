"""Shared configuration for DeepSeek-backed tools."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class DeepSeekConfig:
    """Configuration shared by all DeepSeek calls."""

    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> "DeepSeekConfig":
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required")
        return cls(
            api_key=api_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", cls.base_url).rstrip("/"),
            model=os.getenv("DEEPSEEK_MODEL", cls.model),
            timeout_seconds=int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "30")),
        )
