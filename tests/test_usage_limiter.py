import tempfile
import unittest
from pathlib import Path

from utils.usage_limiter import Quota, UsageLimitExceeded, UsageLimiter


class UsageLimiterTest(unittest.TestCase):
    def test_consumes_usage_and_rejects_over_quota(self):
        with tempfile.TemporaryDirectory() as tmp:
            limiter = UsageLimiter(
                Path(tmp) / "usage.sqlite3",
                quotas={"free": Quota(max_requests=2, max_tokens=10)},
            )
            usage = limiter.check_and_consume("u1", requests=1, tokens=4, day="2026-07-01")
            self.assertEqual(usage["requests"], 1)
            self.assertEqual(usage["tokens"], 4)
            limiter.check_and_consume("u1", requests=1, tokens=6, day="2026-07-01")
            with self.assertRaises(UsageLimitExceeded):
                limiter.check_and_consume("u1", requests=1, tokens=0, day="2026-07-01")


if __name__ == "__main__":
    unittest.main()
