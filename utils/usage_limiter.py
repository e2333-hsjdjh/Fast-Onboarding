"""Compatibility wrapper for fast_onboarding.core.usage_limiter."""

from fast_onboarding.core.usage_limiter import Quota, UsageLimitExceeded, UsageLimiter

__all__ = ["Quota", "UsageLimitExceeded", "UsageLimiter"]
