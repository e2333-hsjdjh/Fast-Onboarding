"""SQLite persistence for users, profiles, JDs, and generated resumes."""

from __future__ import annotations

from dataclasses import asdict
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
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
        self.upsert_user_record(
            user_id=active_user_id,
            name=profile.name,
            email=profile.email,
            phone=profile.phone,
            location=profile.location,
            target_title=profile.target_title,
        )
        return active_user_id

    def upsert_user_record(
        self,
        *,
        user_id: str,
        name: str = "",
        email: str = "",
        phone: str = "",
        location: str = "",
        target_title: str = "",
    ) -> str:
        active_user_id = user_id.strip().lower().replace(" ", "-")
        now = utc_now()
        with sqlite_connection(self.db_path) as conn:
            conn.execute(
                """
                insert into users(user_id, name, email, phone, location, target_title, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(user_id) do update set
                    name = coalesce(nullif(excluded.name, ''), users.name),
                    email = coalesce(nullif(excluded.email, ''), users.email),
                    phone = coalesce(nullif(excluded.phone, ''), users.phone),
                    location = coalesce(nullif(excluded.location, ''), users.location),
                    target_title = coalesce(nullif(excluded.target_title, ''), users.target_title),
                    updated_at = excluded.updated_at
                """,
                (active_user_id, name or active_user_id, email, phone, location, target_title, now, now),
            )
        return active_user_id

    def register_user(
        self,
        *,
        name: str,
        email: str,
        password: str,
        phone: str = "",
        location: str = "",
        target_title: str = "",
    ) -> dict[str, Any]:
        clean_email = email.strip().lower()
        if not clean_email:
            raise ValueError("email is required")
        if len(password) < 6:
            raise ValueError("password must be at least 6 characters")
        active_user_id = self._normalize_user_id(clean_email)
        if self.get_user(active_user_id):
            raise ValueError("user already exists")
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        now = utc_now()
        display_name = name.strip() or clean_email.split("@")[0]
        avatar_initials = self._avatar_initials(display_name)
        with sqlite_connection(self.db_path) as conn:
            conn.execute(
                """
                insert into users(
                    user_id, name, email, phone, location, target_title,
                    password_hash, password_salt, avatar_initials, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    active_user_id,
                    display_name,
                    clean_email,
                    phone,
                    location,
                    target_title,
                    password_hash,
                    salt,
                    avatar_initials,
                    now,
                    now,
                ),
            )
        return self.public_user(active_user_id) or {}

    def login_user(self, *, email: str, password: str) -> dict[str, Any]:
        user_id = self._normalize_user_id(email)
        with sqlite_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("select * from users where user_id = ?", (user_id,)).fetchone()
        if not row:
            raise ValueError("invalid email or password")
        user = dict(row)
        salt = str(user.get("password_salt") or "")
        expected_hash = str(user.get("password_hash") or "")
        if not salt or not expected_hash:
            raise ValueError("password login is not enabled for this user")
        if not secrets.compare_digest(self._hash_password(password, salt), expected_hash):
            raise ValueError("invalid email or password")
        return self._public_user_from_row(user)

    def public_user(self, user_id: str) -> dict[str, Any] | None:
        user = self.get_user(user_id)
        return self._public_user_from_row(user) if user else None

    def save_experience(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        active_user_id = self.upsert_user_record(user_id=user_id, name=str(payload.get("user_name", "")))
        experience_id = str(payload.get("experience_id") or f"exp-{uuid4().hex[:12]}")
        now = utc_now()
        record = {
            "experience_id": experience_id,
            "user_id": active_user_id,
            "category": str(payload.get("category") or "experience"),
            "template_key": str(payload.get("template_key") or payload.get("category") or "experience"),
            "title": str(payload.get("title") or ""),
            "organization": str(payload.get("organization") or ""),
            "start": str(payload.get("start") or ""),
            "end": str(payload.get("end") or ""),
            "bullets": list(payload.get("bullets") or []),
            "skills": list(payload.get("skills") or []),
            "metrics": list(payload.get("metrics") or []),
            "template_data": dict(payload.get("template_data") or {}),
            "evidence": list(payload.get("evidence") or []),
            "updated_at": now,
        }
        with sqlite_connection(self.db_path) as conn:
            conn.execute(
                """
                insert into user_experiences(
                    experience_id, user_id, category, title, organization, start_date, end_date,
                    bullets_json, skills_json, metrics_json, template_key, template_data_json,
                    evidence_json, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(experience_id) do update set
                    category = excluded.category,
                    title = excluded.title,
                    organization = excluded.organization,
                    start_date = excluded.start_date,
                    end_date = excluded.end_date,
                    bullets_json = excluded.bullets_json,
                    skills_json = excluded.skills_json,
                    metrics_json = excluded.metrics_json,
                    template_key = excluded.template_key,
                    template_data_json = excluded.template_data_json,
                    evidence_json = excluded.evidence_json,
                    updated_at = excluded.updated_at
                """,
                (
                    experience_id,
                    active_user_id,
                    record["category"],
                    record["title"],
                    record["organization"],
                    record["start"],
                    record["end"],
                    json.dumps(record["bullets"], ensure_ascii=False),
                    json.dumps(record["skills"], ensure_ascii=False),
                    json.dumps(record["metrics"], ensure_ascii=False),
                    record["template_key"],
                    json.dumps(record["template_data"], ensure_ascii=False),
                    json.dumps(record["evidence"], ensure_ascii=False),
                    now,
                    now,
                ),
            )
        return record

    def list_experiences(self, user_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        with sqlite_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                select * from user_experiences
                where user_id = ?
                order by updated_at desc, created_at desc
                limit ?
                """,
                (user_id, limit),
            ).fetchall()
        return [self._experience_from_row(dict(row)) for row in rows]

    def save_project(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        active_user_id = self.upsert_user_record(user_id=user_id, name=str(payload.get("user_name", "")))
        project_id = str(payload.get("project_id") or f"proj-{uuid4().hex[:12]}")
        now = utc_now()
        record = {
            "project_id": project_id,
            "user_id": active_user_id,
            "company_name": str(payload.get("company_name") or ""),
            "role_title": str(payload.get("role_title") or ""),
            "jd_text": str(payload.get("jd_text") or ""),
            "status": str(payload.get("status") or "draft"),
            "notes": str(payload.get("notes") or ""),
            "updated_at": now,
        }
        with sqlite_connection(self.db_path) as conn:
            conn.execute(
                """
                insert into application_projects(
                    project_id, user_id, company_name, role_title, jd_text,
                    status, notes, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(project_id) do update set
                    company_name = excluded.company_name,
                    role_title = excluded.role_title,
                    jd_text = excluded.jd_text,
                    status = excluded.status,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                (
                    project_id,
                    active_user_id,
                    record["company_name"],
                    record["role_title"],
                    record["jd_text"],
                    record["status"],
                    record["notes"],
                    now,
                    now,
                ),
            )
        return record

    def list_projects(self, user_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        with sqlite_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                select * from application_projects
                where user_id = ?
                order by updated_at desc, created_at desc
                limit ?
                """,
                (user_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

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
                    password_hash text,
                    password_salt text,
                    avatar_initials text,
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

                create table if not exists user_experiences (
                    experience_id text primary key,
                    user_id text not null,
                    category text not null,
                    title text not null,
                    organization text,
                    start_date text,
                    end_date text,
                    bullets_json text not null,
                    skills_json text not null,
                    metrics_json text not null,
                    template_key text,
                    template_data_json text not null default '{}',
                    evidence_json text not null default '[]',
                    created_at text not null,
                    updated_at text not null,
                    foreign key(user_id) references users(user_id)
                );

                create index if not exists idx_user_experiences_user_updated
                    on user_experiences(user_id, updated_at);

                create table if not exists application_projects (
                    project_id text primary key,
                    user_id text not null,
                    company_name text not null,
                    role_title text not null,
                    jd_text text not null,
                    status text not null,
                    notes text,
                    created_at text not null,
                    updated_at text not null,
                    foreign key(user_id) references users(user_id)
                );

                create index if not exists idx_application_projects_user_updated
                    on application_projects(user_id, updated_at);
                """
            )
            self._ensure_user_column(conn, "password_hash", "text")
            self._ensure_user_column(conn, "password_salt", "text")
            self._ensure_user_column(conn, "avatar_initials", "text")
            self._ensure_table_column(conn, "user_experiences", "template_key", "text")
            self._ensure_table_column(conn, "user_experiences", "template_data_json", "text not null default '{}'")
            self._ensure_table_column(conn, "user_experiences", "evidence_json", "text not null default '[]'")

    def _stable_user_id(self, profile: "CandidateProfile") -> str:
        key = (profile.email or profile.phone or profile.name).strip()
        if key:
            return self._normalize_user_id(key)
        return f"user-{uuid4().hex[:12]}"

    def _normalize_user_id(self, value: str) -> str:
        return value.strip().lower().replace(" ", "-")

    def _hash_password(self, password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()

    def _avatar_initials(self, name: str) -> str:
        clean = name.strip()
        if not clean:
            return "U"
        if any("\u4e00" <= char <= "\u9fff" for char in clean):
            return clean[:2].upper()
        parts = [part for part in clean.replace("_", " ").replace("-", " ").split(" ") if part]
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return clean[:2].upper()

    def _ensure_user_column(self, conn: sqlite3.Connection, column: str, column_type: str) -> None:
        existing = {row[1] for row in conn.execute("pragma table_info(users)").fetchall()}
        if column not in existing:
            conn.execute(f"alter table users add column {column} {column_type}")

    def _ensure_table_column(self, conn: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
        existing = {row[1] for row in conn.execute(f"pragma table_info({table})").fetchall()}
        if column not in existing:
            conn.execute(f"alter table {table} add column {column} {column_type}")

    def _public_user_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_id": row.get("user_id", ""),
            "name": row.get("name", ""),
            "email": row.get("email", ""),
            "phone": row.get("phone", ""),
            "location": row.get("location", ""),
            "target_title": row.get("target_title", ""),
            "avatar_initials": row.get("avatar_initials") or self._avatar_initials(str(row.get("name") or "")),
            "created_at": row.get("created_at", ""),
            "updated_at": row.get("updated_at", ""),
        }

    def _generation_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        row["analysis"] = json.loads(row.pop("analysis_json"))
        row["ats_report"] = json.loads(row.pop("ats_report_json"))
        row["output_paths"] = json.loads(row.pop("output_paths_json"))
        return row

    def _experience_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        row["start"] = row.pop("start_date")
        row["end"] = row.pop("end_date")
        row["bullets"] = json.loads(row.pop("bullets_json"))
        row["skills"] = json.loads(row.pop("skills_json"))
        row["metrics"] = json.loads(row.pop("metrics_json"))
        row["template_key"] = row.get("template_key") or row.get("category") or "experience"
        row["template_data"] = json.loads(row.pop("template_data_json", "{}") or "{}")
        row["evidence"] = json.loads(row.pop("evidence_json", "[]") or "[]")
        return row
