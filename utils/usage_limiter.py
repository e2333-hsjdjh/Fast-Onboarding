"""SQLite-backed usage control for API calls and resume actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


class UsageLimitExceeded(RuntimeError):
    """Raised when a user exceeds a configured quota."""


@dataclass(frozen=True)
class Quota:
    max_requests: int
    max_tokens: int


DEFAULT_QUOTAS = {
    "free": Quota(max_requests=30, max_tokens=50_000),
    "pro": Quota(max_requests=500, max_tokens=1_000_000),
    "admin": Quota(max_requests=100_000, max_tokens=100_000_000),
}


class UsageLimiter:
    """Track per-user daily usage and gate expensive DeepSeek/API actions."""

    def __init__(self, db_path: str | Path = "data/usage.sqlite3", quotas: dict[str, Quota] | None = None) -> None:
        self.db_path = Path(db_path)
        self.quotas = quotas or DEFAULT_QUOTAS
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def check_and_consume(
        self,
        user_id: str,
        *,
        plan: str = "free",
        requests: int = 1,
        tokens: int = 0,
        day: str | None = None,
    ) -> dict[str, int | str]:
        quota = self.quotas.get(plan)
        if not quota:
            raise ValueError(f"Unknown plan: {plan}")
        usage_day = day or datetime.now(timezone.utc).date().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            current = self._get_usage(conn, user_id, usage_day)
            next_requests = current["requests"] + requests
            next_tokens = current["tokens"] + tokens
            if next_requests > quota.max_requests or next_tokens > quota.max_tokens:
                raise UsageLimitExceeded(
                    f"{user_id} exceeds {plan} quota: "
                    f"{next_requests}/{quota.max_requests} requests, "
                    f"{next_tokens}/{quota.max_tokens} tokens"
                )
            conn.execute(
                """
                insert into usage(user_id, day, requests, tokens)
                values (?, ?, ?, ?)
                on conflict(user_id, day) do update set
                    requests = excluded.requests,
                    tokens = excluded.tokens
                """,
                (user_id, usage_day, next_requests, next_tokens),
            )
        return {
            "user_id": user_id,
            "day": usage_day,
            "requests": next_requests,
            "tokens": next_tokens,
            "request_limit": quota.max_requests,
            "token_limit": quota.max_tokens,
        }

    def get_usage(self, user_id: str, *, day: str | None = None) -> dict[str, int]:
        usage_day = day or datetime.now(timezone.utc).date().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            return self._get_usage(conn, user_id, usage_day)

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                create table if not exists usage (
                    user_id text not null,
                    day text not null,
                    requests integer not null default 0,
                    tokens integer not null default 0,
                    primary key(user_id, day)
                )
                """
            )

    def _get_usage(self, conn: sqlite3.Connection, user_id: str, day: str) -> dict[str, int]:
        row = conn.execute(
            "select requests, tokens from usage where user_id = ? and day = ?",
            (user_id, day),
        ).fetchone()
        if not row:
            return {"requests": 0, "tokens": 0}
        return {"requests": int(row[0]), "tokens": int(row[1])}
