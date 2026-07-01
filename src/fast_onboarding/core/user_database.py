"""SQLite persistence for users, profiles, JDs, and generated resumes."""

from __future__ import annotations

from dataclasses import asdict
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from fast_onboarding.resume_mvp import CandidateProfile


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def sqlite_connection(db_path: Path):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


class UserDatabase:
    """Small SQLite repository for user-owned resume generation data."""

    def __init__(self, db_path: str | Path = "data/fast_onboarding.sqlite3") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def upsert_user(self, profile: "CandidateProfile", *, user_id: str | None = None) -> str:
        active_user_id = user_id or self._stable_user_id(profile)
        now = utc_now()
        with sqlite_connection(self.db_path) as conn:
            conn.execute(
                """
                insert into users(user_id, name, email, phone, location, target_title, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(user_id) do update set
                    name = excluded.name,
                    email = excluded.email,
                    phone = excluded.phone,
                    location = excluded.location,
                    target_title = excluded.target_title,
                    updated_at = excluded.updated_at
                """,
                (
                    active_user_id,
                    profile.name,
                    profile.email,
                    profile.phone,
                    profile.location,
                    profile.target_title,
                    now,
                    now,
                ),
            )
        return active_user_id

    def save_profile_snapshot(self, user_id: str, profile: "CandidateProfile") -> int:
        payload = json.dumps(asdict(profile), ensure_ascii=False)
        with sqlite_connection(self.db_path) as conn:
            cursor = conn.execute(
                """
                insert into profile_snapshots(user_id, profile_json, created_at)
                values (?, ?, ?)
                """,
                (user_id, payload, utc_now()),
            )
            return int(cursor.lastrowid)

    def save_job_description(self, user_id: str, *, target_role: str, jd_text: str, analysis: dict[str, Any]) -> int:
        with sqlite_connection(self.db_path) as conn:
            cursor = conn.execute(
                """
                insert into job_descriptions(user_id, target_role, jd_text, analysis_json, created_at)
                values (?, ?, ?, ?, ?)
                """,
                (user_id, target_role, jd_text, json.dumps(analysis, ensure_ascii=False), utc_now()),
            )
            return int(cursor.lastrowid)

    def save_generation(
        self,
        user_id: str,
        *,
        profile_snapshot_id: int,
        jd_id: int,
        resume_markdown: str,
        ats_report: dict[str, Any],
        output_paths: dict[str, str],
    ) -> int:
        with sqlite_connection(self.db_path) as conn:
            cursor = conn.execute(
                """
                insert into resume_generations(
                    user_id, profile_snapshot_id, jd_id, resume_markdown,
                    ats_report_json, output_paths_json, created_at
                )
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    profile_snapshot_id,
                    jd_id,
                    resume_markdown,
                    json.dumps(ats_report, ensure_ascii=False),
                    json.dumps(output_paths, ensure_ascii=False),
                    utc_now(),
                ),
            )
            return int(cursor.lastrowid)

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with sqlite_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("select * from users where user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def list_generations(self, user_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        with sqlite_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                select
                    g.generation_id,
                    g.user_id,
                    j.target_role,
                    j.jd_text,
                    j.analysis_json,
                    g.resume_markdown,
                    g.ats_report_json,
                    g.output_paths_json,
                    g.created_at
                from resume_generations g
                join job_descriptions j on j.jd_id = g.jd_id
                where g.user_id = ?
                order by g.created_at desc, g.generation_id desc
                limit ?
                """,
                (user_id, limit),
            ).fetchall()
        return [self._generation_from_row(dict(row)) for row in rows]

    def record_generation(
        self,
        *,
        profile: "CandidateProfile",
        jd_text: str,
        target_role: str,
        analysis: dict[str, Any],
        resume_markdown: str,
        ats_report: dict[str, Any],
        output_paths: dict[str, str],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        active_user_id = self.upsert_user(profile, user_id=user_id)
        snapshot_id = self.save_profile_snapshot(active_user_id, profile)
        jd_id = self.save_job_description(active_user_id, target_role=target_role, jd_text=jd_text, analysis=analysis)
        generation_id = self.save_generation(
            active_user_id,
            profile_snapshot_id=snapshot_id,
            jd_id=jd_id,
            resume_markdown=resume_markdown,
            ats_report=ats_report,
            output_paths=output_paths,
        )
        return {
            "user_id": active_user_id,
            "profile_snapshot_id": snapshot_id,
            "jd_id": jd_id,
            "generation_id": generation_id,
        }

    def _init_db(self) -> None:
        with sqlite_connection(self.db_path) as conn:
            conn.executescript(
                """
                create table if not exists users (
                    user_id text primary key,
                    name text not null,
                    email text,
                    phone text,
                    location text,
                    target_title text,
                    created_at text not null,
                    updated_at text not null
                );

                create table if not exists profile_snapshots (
                    snapshot_id integer primary key autoincrement,
                    user_id text not null,
                    profile_json text not null,
                    created_at text not null,
                    foreign key(user_id) references users(user_id)
                );

                create table if not exists job_descriptions (
                    jd_id integer primary key autoincrement,
                    user_id text not null,
                    target_role text,
                    jd_text text not null,
                    analysis_json text not null,
                    created_at text not null,
                    foreign key(user_id) references users(user_id)
                );

                create table if not exists resume_generations (
                    generation_id integer primary key autoincrement,
                    user_id text not null,
                    profile_snapshot_id integer not null,
                    jd_id integer not null,
                    resume_markdown text not null,
                    ats_report_json text not null,
                    output_paths_json text not null,
                    created_at text not null,
                    foreign key(user_id) references users(user_id),
                    foreign key(profile_snapshot_id) references profile_snapshots(snapshot_id),
                    foreign key(jd_id) references job_descriptions(jd_id)
                );

                create index if not exists idx_resume_generations_user_created
                    on resume_generations(user_id, created_at);
                """
            )

    def _stable_user_id(self, profile: "CandidateProfile") -> str:
        key = (profile.email or profile.phone or profile.name).strip()
        if key:
            return key.lower().replace(" ", "-")
        return f"user-{uuid4().hex[:12]}"

    def _generation_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        row["analysis"] = json.loads(row.pop("analysis_json"))
        row["ats_report"] = json.loads(row.pop("ats_report_json"))
        row["output_paths"] = json.loads(row.pop("output_paths_json"))
        return row
