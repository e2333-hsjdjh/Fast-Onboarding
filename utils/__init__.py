"""Backward-compatible imports for the old flat utils package."""

from pathlib import Path
import sys

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fast_onboarding.core.config import DeepSeekConfig
from fast_onboarding.core.usage_limiter import UsageLimitExceeded, UsageLimiter
from fast_onboarding.integrations.deepseek_client import DeepSeekClient

__all__ = [
    "DeepSeekClient",
    "DeepSeekConfig",
    "UsageLimitExceeded",
    "UsageLimiter",
]
