"""SQLite persistence for users, profiles, JDs, and generated resumes."""

from __future__ import annotations

from dataclasses import asdict
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
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


MATERIAL_TEMPLATE_ROWS: list[dict[str, Any]] = [
    {
        "template_key": "basic",
        "module": "基础信息",
        "subsection": "基础信息",
        "required": ["姓名", "手机号", "邮箱", "求职意向", "所在城市"],
        "suggested": ["个人网站", "作品集链接", "GitHub", "LinkedIn", "公众号", "博客"],
        "details": ["手机号是否常用", "邮箱是否正式", "求职岗位名称是否清晰", "作品链接是否能正常打开"],
        "quantifiable": ["可到岗时间", "每周实习天数", "实习时长"],
        "focus": "简洁、准确、方便联系",
        "example": "姓名：张三｜电话：138xxxx8888｜邮箱：xxx@xxx.com｜求职意向：数据分析实习生｜可到岗：一周内",
        "fields": ["legal_name", "phone", "email", "target_role", "city", "portfolio", "github", "linkedin", "availability"],
    },
    {
        "template_key": "education",
        "module": "教育经历",
        "subsection": "教育经历",
        "required": ["学校", "专业", "学历", "入学与毕业时间"],
        "suggested": ["GPA", "排名", "主修课程", "辅修/双学位", "交换经历", "毕业论文"],
        "details": ["学校全称", "专业全称", "学历层次", "时间格式统一", "课程是否与目标岗位相关"],
        "quantifiable": ["GPA", "专业排名", "奖学金等级", "核心课程成绩"],
        "focus": "体现学习背景和专业匹配度",
        "example": "XX大学｜数据科学与大数据技术｜本科｜2022.09 - 2026.06｜GPA：3.7/4.0，专业前15%",
        "fields": ["school", "degree", "major", "start_date", "end_date", "gpa_rank", "core_courses", "thesis_research", "honors"],
    },
    {
        "template_key": "education_courses",
        "module": "教育经历",
        "subsection": "相关课程",
        "required": ["与岗位相关的课程"],
        "suggested": ["高分课程", "核心专业课", "实践类课程"],
        "details": ["根据岗位筛选课程，不要堆太多"],
        "quantifiable": ["课程成绩", "排名"],
        "focus": "应届生尤其适合写，弥补经历不足",
        "example": "相关课程：数据结构、数据库系统、机器学习、统计建模、Python程序设计",
        "fields": ["core_courses", "course_scores"],
    },
    {
        "template_key": "education_research",
        "module": "教育经历",
        "subsection": "论文/研究方向",
        "required": ["论文题目或研究方向"],
        "suggested": ["导师课题", "研究方法", "研究成果"],
        "details": ["研究对象", "使用方法", "数据来源", "结论"],
        "quantifiable": ["样本量", "实验次数", "准确率", "论文/报告成果"],
        "focus": "适合科研、技术、咨询、分析类岗位",
        "example": "毕业论文方向：基于用户评论数据的情感分析研究，使用 Python 完成数据清洗与模型训练",
        "fields": ["thesis_research", "research_method", "research_result"],
    },
    {
        "template_key": "work",
        "module": "工作经历",
        "subsection": "工作经历 / 实习经历",
        "required": ["公司名称", "部门", "岗位", "时间", "地点"],
        "suggested": ["汇报对象", "业务背景", "核心职责", "项目成果"],
        "details": ["公司做什么", "部门负责什么", "你负责哪部分", "和谁协作", "最终交付什么"],
        "quantifiable": ["用户数", "销售额", "转化率", "留存率", "效率提升", "成本下降", "数据量", "完成数量"],
        "focus": "重点写你做了什么和带来了什么结果",
        "example": "XX公司｜运营实习生｜2025.06 - 2025.09｜负责社群运营与活动数据复盘，推动社群周活跃率提升28%",
        "fields": ["company", "department", "role", "start_date", "end_date", "business_context", "responsibilities", "actions", "results", "tools_methods"],
    },
    {
        "template_key": "work_responsibility",
        "module": "工作经历",
        "subsection": "职责描述",
        "required": ["日常工作内容"],
        "suggested": ["负责的模块", "工具", "流程", "协作对象"],
        "details": ["每天/每周做什么", "是否独立负责", "是否对接其他部门"],
        "quantifiable": ["处理多少数据", "多少用户", "多少活动", "多少内容"],
        "focus": "避免只写参与、协助，要写具体动作",
        "example": "负责每周用户数据整理与分析，使用 Excel 建立活动效果追踪表，覆盖注册、转化、留存等指标",
        "fields": ["responsibilities", "actions", "team_collaboration"],
    },
    {
        "template_key": "work_result",
        "module": "工作经历",
        "subsection": "成果描述",
        "required": ["工作结果"],
        "suggested": ["对业务的影响", "优化前后对比"],
        "details": ["做之前的问题是什么", "做之后变好了什么"],
        "quantifiable": ["提升百分比", "节省时间", "增长数量", "降低成本"],
        "focus": "成果最好带数字，没有数字也要写清影响",
        "example": "优化活动报名流程后，用户填写时间从5分钟缩短至2分钟，报名转化率提升12%",
        "fields": ["results", "result_before_after"],
    },
    {
        "template_key": "work_tools",
        "module": "工作经历",
        "subsection": "工具方法",
        "required": ["使用的软件", "工具", "方法"],
        "suggested": ["数据分析方法", "项目管理方法", "内容运营方法", "设计工具"],
        "details": ["用了 SQL、Python、Excel、SPSS、Figma、剪映、飞书、Notion 等什么工具"],
        "quantifiable": ["自动化节省时间", "处理数据规模", "输出报告数量"],
        "focus": "让能力具体化，不要只写熟练办公软件",
        "example": "使用 SQL 提取用户行为数据，结合 Excel 透视表完成周度运营分析报告",
        "fields": ["tools_methods", "tool_outputs"],
    },
    {
        "template_key": "project",
        "module": "项目经历",
        "subsection": "项目经历",
        "required": ["项目名称", "角色", "时间"],
        "suggested": ["项目背景", "目标", "团队规模", "职责分工", "最终成果"],
        "details": ["为什么做这个项目", "你担任什么角色", "你负责哪一块", "项目怎么完成"],
        "quantifiable": ["数据规模", "模型准确率", "用户数", "作品浏览量", "项目周期", "排名"],
        "focus": "项目要写成解决问题，不是完成作业",
        "example": "用户评论情感分析系统｜项目负责人｜2025.03 - 2025.05",
        "fields": ["project_name", "project_role", "project_period", "project_context", "problem", "solution", "personal_contribution", "tech_stack", "result_metrics"],
    },
    {
        "template_key": "award",
        "module": "获奖经历",
        "subsection": "获奖经历",
        "required": ["奖项名称", "等级", "颁发单位", "获奖时间"],
        "suggested": ["比赛规模", "获奖比例", "团队角色"],
        "details": ["奖项全称", "国家级/省级/校级", "个人奖还是团队奖"],
        "quantifiable": ["排名前几", "获奖比例", "参赛人数", "团队数量"],
        "focus": "体现含金量，优先写高等级和相关奖项",
        "example": "全国大学生数学建模竞赛｜省级一等奖｜2024.09｜团队排名前5%",
        "fields": ["award_name", "issuer", "award_level", "award_date", "rank_percentile", "selection_criteria", "related_work"],
    },
    {
        "template_key": "skill",
        "module": "技能与特长",
        "subsection": "技能与特长",
        "required": ["专业技能", "办公技能", "语言能力"],
        "suggested": ["证书", "工具熟练度", "作品能力"],
        "details": ["哪些技能与岗位匹配", "熟练程度如何", "是否有作品证明"],
        "quantifiable": ["证书分数", "语言成绩", "作品数量", "代码量"],
        "focus": "按类别写，别一锅乱炖",
        "example": "数据分析：熟练使用 SQL、Excel、Python，能够完成数据清洗、指标分析与可视化",
        "fields": ["skill_group", "skill_items", "proficiency", "use_cases", "tools_platforms", "certifications", "representative_outputs"],
    },
    {
        "template_key": "other",
        "module": "其他",
        "subsection": "学生工作/社团/志愿/作品/兴趣",
        "required": ["组织名称或作品名称", "职务/角色", "时间"],
        "suggested": ["负责活动", "管理人数", "宣传成果", "服务对象", "代表作品"],
        "details": ["担任什么职位", "组织过什么活动", "负责什么模块", "是否有公开链接或认证证明"],
        "quantifiable": ["活动场次", "参与人数", "阅读量", "服务小时数", "作品数量"],
        "focus": "不要写成爱好介绍，要写成能力证明",
        "example": "学生会宣传部部长｜统筹10+场活动宣传，负责推文撰写、海报设计与现场执行",
        "fields": ["experience_type", "other_title", "role", "period", "context", "contribution", "outcome", "relevance"],
    },
]

UNIVERSAL_EXPERIENCE_QUESTIONS = [
    "这段经历发生在哪里？",
    "你是什么身份？",
    "时间是什么时候？",
    "背景是什么？",
    "你的任务是什么？",
    "你做了哪些动作？",
    "你用了什么工具或方法？",
    "最终产出了什么？",
    "结果怎么样？",
    "有没有数字证明？",
    "和目标岗位有什么关系？",
]

BULLET_FORMULAS = [
    "通过【方法/工具】完成【任务】，实现【结果】",
    "针对【问题】，设计/优化【方案】，使【指标】提升/降低【数字】",
    "使用【工具】分析【数据对象】，识别【问题/机会】，输出【报告/建议】",
    "策划并执行【活动/内容/社群】，覆盖【人数】，带来【增长结果】",
    "基于【技术/框架】开发【系统/功能】，实现【功能效果】",
    "协调【对象/部门】，推进【事项】，按期交付【成果】",
    "负责【内容类型】策划与制作，累计产出【数量】，获得【数据表现】",
]


class UserDatabase:
    """Small SQLite repository for user-owned resume generation data."""

    TEST_USER_ID = "test"
    TEST_USER_PASSWORD = "test123"
    MAX_RESUME_VERSIONS = 3
    RESUME_VERSION_RETENTION_DAYS = 30
    SESSION_RETENTION_DAYS = 30

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
        now = utc_now()
        with sqlite_connection(self.db_path) as conn:
            conn.execute(
                "update users set last_login_at = ?, last_active_at = ?, updated_at = ? where user_id = ?",
                (now, now, now, user_id),
            )
        return self.public_user(user_id) or {}

    def login_with_session(self, *, identifier: str, password: str) -> dict[str, Any]:
        user = self.login_user(email=identifier, password=password)
        return {"user": user, "session": self.create_session(user["user_id"])}

    def create_session(self, user_id: str, *, retention_days: int | None = None) -> dict[str, Any]:
        active_user_id = self._normalize_user_id(user_id)
        if not self.get_user(active_user_id):
            raise ValueError("user not found")
        token = secrets.token_urlsafe(32)
        session_id = f"ses-{uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=retention_days or self.SESSION_RETENTION_DAYS)
        with sqlite_connection(self.db_path) as conn:
            conn.execute(
                """
                insert into user_sessions(session_id, user_id, token_hash, expires_at, created_at, last_seen_at)
                values (?, ?, ?, ?, ?, ?)
                """,
                (session_id, active_user_id, hashlib.sha256(token.encode("utf-8")).hexdigest(),
                 expires_at.isoformat(timespec="seconds"), now.isoformat(timespec="seconds"), now.isoformat(timespec="seconds")),
            )
        return {"token": token, "expires_at": expires_at.isoformat(timespec="seconds")}

    def get_session_user(self, token: str) -> dict[str, Any] | None:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = utc_now()
        with sqlite_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                select u.* from user_sessions s join users u on u.user_id = s.user_id
                where s.token_hash = ? and s.expires_at > ? and s.revoked_at is null
                """,
                (token_hash, now),
            ).fetchone()
            if not row:
                return None
            conn.execute("update user_sessions set last_seen_at = ? where token_hash = ?", (now, token_hash))
            conn.execute("update users set last_active_at = ? where user_id = ?", (now, row["user_id"]))
        return self._public_user_from_row(dict(row))

    def create_test_session(self) -> dict[str, Any]:
        self.ensure_test_account()
        return {"user": self.public_user(self.TEST_USER_ID), "session": self.create_session(self.TEST_USER_ID)}

    def public_user(self, user_id: str) -> dict[str, Any] | None:
        user = self.get_user(user_id)
        return self._public_user_from_row(user) if user else None

    def save_experience(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        active_user_id = self.upsert_user_record(user_id=user_id, name=str(payload.get("user_name", "")))
        material_id = str(payload.get("experience_id") or payload.get("material_id") or f"mat-{uuid4().hex[:12]}")
        now = utc_now()
        category = str(payload.get("category") or "experience")
        template_key = self._template_key_for_category(str(payload.get("template_key") or category))
        template = self._template_for_key(template_key)
        template_data = dict(payload.get("template_data") or {})
        bullets = list(payload.get("bullets") or [])
        metrics = list(payload.get("metrics") or [])
        skills = list(payload.get("skills") or [])
        title = str(payload.get("title") or self._first_present(template_data, template.get("fields", [])) or template["subsection"])
        organization = str(payload.get("organization") or self._derive_organization(template_key, template_data))
        record = {
            "experience_id": material_id,
            "material_id": material_id,
            "user_id": active_user_id,
            "category": category,
            "template_key": template_key,
            "module": template["module"],
            "subsection": template["subsection"],
            "title": title,
            "organization": organization,
            "start": str(payload.get("start") or template_data.get("start_date") or ""),
            "end": str(payload.get("end") or template_data.get("end_date") or ""),
            "identity": self._first_present(template_data, ["role", "project_role", "employment_type", "experience_type"]),
            "period": self._first_present(template_data, ["period", "project_period"]) or self._join_period(template_data),
            "background": self._first_present(template_data, ["business_context", "project_context", "context", "problem"]),
            "task": self._first_present(template_data, ["responsibilities", "personal_contribution", "contribution", "selection_criteria"]),
            "actions": self._material_lines(template_data, ["actions", "responsibilities", "personal_contribution", "contribution"], bullets),
            "tools_methods": self._material_lines(template_data, ["tools_methods", "tech_stack", "tools_platforms", "research_method"]),
            "outputs": self._material_lines(template_data, ["outputs", "representative_outputs", "solution", "related_work"]),
            "results": self._material_lines(template_data, ["results", "result_metrics", "outcome", "research_result"], metrics),
            "quantification": self._material_lines(template_data, ["rank_percentile", "gpa_rank", "course_scores", "result_before_after"], metrics),
            "relevance": self._first_present(template_data, ["relevance", "award_relevance", "transferable_skills", "skills_reflected"]),
            "bullets": bullets,
            "skills": skills,
            "metrics": metrics,
            "template_data": template_data,
            "evidence": list(payload.get("evidence") or []),
            "updated_at": now,
        }
        with sqlite_connection(self.db_path) as conn:
            conn.execute(
                """
                insert into resume_materials(
                    material_id, user_id, template_key, module, subsection, title, organization,
                    identity, period, background, task, actions_json, tools_methods_json,
                    outputs_json, results_json, quantification_json, relevance,
                    template_data_json, evidence_json, legacy_bullets_json, legacy_skills_json,
                    legacy_metrics_json, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(material_id) do update set
                    template_key = excluded.template_key,
                    module = excluded.module,
                    subsection = excluded.subsection,
                    title = excluded.title,
                    organization = excluded.organization,
                    identity = excluded.identity,
                    period = excluded.period,
                    background = excluded.background,
                    task = excluded.task,
                    actions_json = excluded.actions_json,
                    tools_methods_json = excluded.tools_methods_json,
                    outputs_json = excluded.outputs_json,
                    results_json = excluded.results_json,
                    quantification_json = excluded.quantification_json,
                    relevance = excluded.relevance,
                    template_data_json = excluded.template_data_json,
                    evidence_json = excluded.evidence_json,
                    legacy_bullets_json = excluded.legacy_bullets_json,
                    legacy_skills_json = excluded.legacy_skills_json,
                    legacy_metrics_json = excluded.legacy_metrics_json,
                    updated_at = excluded.updated_at
                """,
                (
                    material_id,
                    active_user_id,
                    record["template_key"],
                    record["module"],
                    record["subsection"],
                    record["title"],
                    record["organization"],
                    record["identity"],
                    record["period"],
                    record["background"],
                    record["task"],
                    json.dumps(record["actions"], ensure_ascii=False),
                    json.dumps(record["tools_methods"], ensure_ascii=False),
                    json.dumps(record["outputs"], ensure_ascii=False),
                    json.dumps(record["results"], ensure_ascii=False),
                    json.dumps(record["quantification"], ensure_ascii=False),
                    record["relevance"],
                    json.dumps(record["template_data"], ensure_ascii=False),
                    json.dumps(record["evidence"], ensure_ascii=False),
                    json.dumps(record["bullets"], ensure_ascii=False),
                    json.dumps(record["skills"], ensure_ascii=False),
                    json.dumps(record["metrics"], ensure_ascii=False),
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
                select * from resume_materials
                where user_id = ?
                order by updated_at desc, created_at desc
                limit ?
                """,
                (user_id, limit),
            ).fetchall()
        return [self._material_from_row(dict(row)) for row in rows]

    def list_material_templates(self) -> list[dict[str, Any]]:
        with sqlite_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                select * from resume_material_templates
                order by sort_order asc
                """
            ).fetchall()
        return [self._material_template_from_row(dict(row)) for row in rows]

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
            "document_title": str(payload.get("document_title") or ""),
            "template_id": str(payload.get("template_id") or "zsc_table_resume"),
            "language": str(payload.get("language") or "zh-CN"),
            "visibility": str(payload.get("visibility") or "private"),
            "selected_material_ids": list(payload.get("selected_material_ids") or []),
            "resume_content": dict(payload.get("resume_content") or {}),
            "editor_preferences": dict(payload.get("editor_preferences") or {}),
            "export_settings": dict(payload.get("export_settings") or {}),
            "version_retention_days": int(payload.get("version_retention_days") or self.RESUME_VERSION_RETENTION_DAYS),
            "updated_at": now,
        }
        if not record["document_title"]:
            record["document_title"] = f"{record['company_name']}-{record['role_title']}"
        with sqlite_connection(self.db_path) as conn:
            conn.execute(
                """
                insert into application_projects(
                    project_id, user_id, company_name, role_title, jd_text,
                    status, notes, document_title, template_id, language, visibility,
                    selected_material_ids_json, resume_content_json, editor_preferences_json,
                    export_settings_json, version_retention_days, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(project_id) do update set
                    company_name = excluded.company_name,
                    role_title = excluded.role_title,
                    jd_text = excluded.jd_text,
                    status = excluded.status,
                    notes = excluded.notes,
                    document_title = excluded.document_title,
                    template_id = excluded.template_id,
                    language = excluded.language,
                    visibility = excluded.visibility,
                    selected_material_ids_json = excluded.selected_material_ids_json,
                    resume_content_json = excluded.resume_content_json,
                    editor_preferences_json = excluded.editor_preferences_json,
                    export_settings_json = excluded.export_settings_json,
                    version_retention_days = excluded.version_retention_days,
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
                    record["document_title"],
                    record["template_id"],
                    record["language"],
                    record["visibility"],
                    json.dumps(record["selected_material_ids"], ensure_ascii=False),
                    json.dumps(record["resume_content"], ensure_ascii=False),
                    json.dumps(record["editor_preferences"], ensure_ascii=False),
                    json.dumps(record["export_settings"], ensure_ascii=False),
                    record["version_retention_days"],
                    now,
                    now,
                ),
            )
        self._save_project_version(record, change_summary=str(payload.get("change_summary") or "保存简历"))
        return self.get_project(active_user_id, project_id) or record

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
        return [self._project_from_row(dict(row)) for row in rows]

    def get_project(self, user_id: str, project_id: str) -> dict[str, Any] | None:
        with sqlite_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "select * from application_projects where user_id = ? and project_id = ?",
                (self._normalize_user_id(user_id), project_id),
            ).fetchone()
        return self._project_from_row(dict(row)) if row else None

    def list_project_versions(self, user_id: str, project_id: str) -> list[dict[str, Any]]:
        self._cleanup_project_versions(project_id)
        with sqlite_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                select * from resume_versions where user_id = ? and project_id = ?
                order by version_number desc, created_at desc limit ?
                """,
                (self._normalize_user_id(user_id), project_id, self.MAX_RESUME_VERSIONS),
            ).fetchall()
        return [self._project_version_from_row(dict(row)) for row in rows]

    def restore_project_version(self, user_id: str, project_id: str, version_id: str) -> dict[str, Any]:
        with sqlite_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                select snapshot_json from resume_versions
                where version_id = ? and project_id = ? and user_id = ? and expires_at > ?
                """,
                (version_id, project_id, self._normalize_user_id(user_id), utc_now()),
            ).fetchone()
        if not row:
            raise ValueError("resume version not found")
        snapshot = json.loads(row["snapshot_json"])
        snapshot["project_id"] = project_id
        snapshot["change_summary"] = "恢复历史版本"
        return self.save_project(user_id, snapshot)

    def reset_test_account(self) -> dict[str, Any]:
        user_id = self.TEST_USER_ID
        with sqlite_connection(self.db_path) as conn:
            for table in ("user_sessions", "resume_versions", "ai_interactions", "export_jobs", "resume_generations", "job_descriptions", "profile_snapshots", "resume_materials", "user_experiences", "application_projects"):
                conn.execute(f"delete from {table} where user_id = ?", (user_id,))
            conn.execute("delete from users where user_id = ?", (user_id,))
        self.ensure_test_account(seed_demo=True)
        return {"user": self.public_user(user_id), "projects": self.list_projects(user_id)}

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

                create table if not exists resume_material_templates (
                    template_key text primary key,
                    module text not null,
                    subsection text not null,
                    required_content_json text not null,
                    suggested_content_json text not null,
                    detail_prompts_json text not null,
                    quantifiable_info_json text not null,
                    writing_focus text not null,
                    example text not null,
                    fields_json text not null,
                    universal_questions_json text not null,
                    bullet_formulas_json text not null,
                    sort_order integer not null
                );

                create table if not exists resume_materials (
                    material_id text primary key,
                    user_id text not null,
                    template_key text not null,
                    module text not null,
                    subsection text not null,
                    title text not null,
                    organization text,
                    identity text,
                    period text,
                    background text,
                    task text,
                    actions_json text not null,
                    tools_methods_json text not null,
                    outputs_json text not null,
                    results_json text not null,
                    quantification_json text not null,
                    relevance text,
                    template_data_json text not null,
                    evidence_json text not null,
                    legacy_bullets_json text not null,
                    legacy_skills_json text not null,
                    legacy_metrics_json text not null,
                    created_at text not null,
                    updated_at text not null,
                    foreign key(user_id) references users(user_id),
                    foreign key(template_key) references resume_material_templates(template_key)
                );

                create index if not exists idx_resume_materials_user_updated
                    on resume_materials(user_id, updated_at);

                create index if not exists idx_resume_materials_user_template
                    on resume_materials(user_id, template_key);

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

                create table if not exists user_sessions (
                    session_id text primary key,
                    user_id text not null,
                    token_hash text not null unique,
                    expires_at text not null,
                    created_at text not null,
                    last_seen_at text not null,
                    revoked_at text,
                    foreign key(user_id) references users(user_id)
                );

                create index if not exists idx_user_sessions_token on user_sessions(token_hash);

                create table if not exists resume_versions (
                    version_id text primary key,
                    project_id text not null,
                    user_id text not null,
                    version_number integer not null,
                    snapshot_json text not null,
                    change_summary text,
                    created_at text not null,
                    expires_at text not null,
                    foreign key(project_id) references application_projects(project_id),
                    foreign key(user_id) references users(user_id)
                );

                create index if not exists idx_resume_versions_project_created
                    on resume_versions(project_id, created_at);

                create table if not exists ai_interactions (
                    interaction_id text primary key,
                    user_id text not null,
                    project_id text,
                    material_id text,
                    action_type text not null,
                    model text,
                    prompt_json text not null,
                    response_json text not null,
                    accepted_at text,
                    created_at text not null,
                    foreign key(user_id) references users(user_id)
                );

                create table if not exists export_jobs (
                    export_id text primary key,
                    user_id text not null,
                    project_id text not null,
                    version_id text,
                    format text not null,
                    status text not null,
                    file_path text,
                    options_json text not null,
                    created_at text not null,
                    completed_at text,
                    foreign key(user_id) references users(user_id),
                    foreign key(project_id) references application_projects(project_id)
                );
                """
            )
            self._ensure_user_column(conn, "password_hash", "text")
            self._ensure_user_column(conn, "password_salt", "text")
            self._ensure_user_column(conn, "avatar_initials", "text")
            self._ensure_user_column(conn, "is_test", "integer not null default 0")
            self._ensure_user_column(conn, "account_status", "text not null default 'active'")
            self._ensure_user_column(conn, "timezone", "text not null default 'Asia/Shanghai'")
            self._ensure_user_column(conn, "locale", "text not null default 'zh-CN'")
            self._ensure_user_column(conn, "profile_json", "text not null default '{}'")
            self._ensure_user_column(conn, "preferences_json", "text not null default '{}'")
            self._ensure_user_column(conn, "last_login_at", "text")
            self._ensure_user_column(conn, "last_active_at", "text")
            self._ensure_table_column(conn, "user_experiences", "template_key", "text")
            self._ensure_table_column(conn, "user_experiences", "template_data_json", "text not null default '{}'")
            self._ensure_table_column(conn, "user_experiences", "evidence_json", "text not null default '[]'")
            self._ensure_table_column(conn, "application_projects", "document_title", "text not null default ''")
            self._ensure_table_column(conn, "application_projects", "template_id", "text not null default 'zsc_table_resume'")
            self._ensure_table_column(conn, "application_projects", "language", "text not null default 'zh-CN'")
            self._ensure_table_column(conn, "application_projects", "visibility", "text not null default 'private'")
            self._ensure_table_column(conn, "application_projects", "selected_material_ids_json", "text not null default '[]'")
            self._ensure_table_column(conn, "application_projects", "resume_content_json", "text not null default '{}'")
            self._ensure_table_column(conn, "application_projects", "editor_preferences_json", "text not null default '{}'")
            self._ensure_table_column(conn, "application_projects", "export_settings_json", "text not null default '{}'")
            self._ensure_table_column(conn, "application_projects", "version_retention_days", "integer not null default 30")
            self._seed_material_templates(conn)
        self.ensure_test_account()

    def ensure_test_account(self, *, seed_demo: bool = False) -> None:
        if not self.get_user(self.TEST_USER_ID):
            salt = secrets.token_hex(16)
            now = utc_now()
            with sqlite_connection(self.db_path) as conn:
                conn.execute(
                    """
                    insert into users(
                        user_id, name, email, target_title, password_hash, password_salt,
                        avatar_initials, is_test, account_status, created_at, updated_at, last_login_at, last_active_at
                    ) values (?, ?, ?, ?, ?, ?, ?, 1, 'active', ?, ?, ?, ?)
                    """,
                    (self.TEST_USER_ID, "test", "", "AI 产品经理", self._hash_password(self.TEST_USER_PASSWORD, salt),
                     salt, "TE", now, now, now, now),
                )
                seed_demo = True
        if seed_demo and not self.list_projects(self.TEST_USER_ID):
            self.save_project(
                self.TEST_USER_ID,
                {
                    "company_name": "示例科技",
                    "role_title": "AI 产品经理",
                    "document_title": "示例科技-AI 产品经理",
                    "jd_text": "负责 AI 产品需求分析、用户研究与自动化工作流落地。",
                    "status": "draft",
                    "notes": "test 账号演示简历，可随时重置。",
                    "resume_content": {"summary": "请从真实经历开始填写。", "sections": {}},
                    "change_summary": "创建演示简历",
                },
            )

    def _save_project_version(self, project: dict[str, Any], *, change_summary: str) -> None:
        project_id = str(project["project_id"])
        self._cleanup_project_versions(project_id)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=max(1, int(project.get("version_retention_days") or self.RESUME_VERSION_RETENTION_DAYS)))
        snapshot = {key: value for key, value in project.items() if key not in {"user_id", "created_at", "updated_at", "project_id"}}
        with sqlite_connection(self.db_path) as conn:
            next_number = int(conn.execute(
                "select coalesce(max(version_number), 0) + 1 from resume_versions where project_id = ?",
                (project_id,),
            ).fetchone()[0])
            conn.execute(
                """
                insert into resume_versions(version_id, project_id, user_id, version_number, snapshot_json, change_summary, created_at, expires_at)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (f"ver-{uuid4().hex[:12]}", project_id, project["user_id"], next_number,
                 json.dumps(snapshot, ensure_ascii=False), change_summary, now.isoformat(timespec="seconds"),
                 expires_at.isoformat(timespec="seconds")),
            )
            conn.execute(
                """
                delete from resume_versions where version_id in (
                    select version_id from resume_versions where project_id = ?
                    order by version_number desc, created_at desc limit -1 offset ?
                )
                """,
                (project_id, self.MAX_RESUME_VERSIONS),
            )

    def _cleanup_project_versions(self, project_id: str) -> None:
        with sqlite_connection(self.db_path) as conn:
            conn.execute("delete from resume_versions where project_id = ? and expires_at <= ?", (project_id, utc_now()))
            conn.execute(
                """
                delete from resume_versions where version_id in (
                    select version_id from resume_versions where project_id = ?
                    order by version_number desc, created_at desc limit -1 offset ?
                )
                """,
                (project_id, self.MAX_RESUME_VERSIONS),
            )

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

    def _seed_material_templates(self, conn: sqlite3.Connection) -> None:
        for index, template in enumerate(MATERIAL_TEMPLATE_ROWS):
            conn.execute(
                """
                insert into resume_material_templates(
                    template_key, module, subsection, required_content_json, suggested_content_json,
                    detail_prompts_json, quantifiable_info_json, writing_focus, example,
                    fields_json, universal_questions_json, bullet_formulas_json, sort_order
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(template_key) do update set
                    module = excluded.module,
                    subsection = excluded.subsection,
                    required_content_json = excluded.required_content_json,
                    suggested_content_json = excluded.suggested_content_json,
                    detail_prompts_json = excluded.detail_prompts_json,
                    quantifiable_info_json = excluded.quantifiable_info_json,
                    writing_focus = excluded.writing_focus,
                    example = excluded.example,
                    fields_json = excluded.fields_json,
                    universal_questions_json = excluded.universal_questions_json,
                    bullet_formulas_json = excluded.bullet_formulas_json,
                    sort_order = excluded.sort_order
                """,
                (
                    template["template_key"],
                    template["module"],
                    template["subsection"],
                    json.dumps(template["required"], ensure_ascii=False),
                    json.dumps(template["suggested"], ensure_ascii=False),
                    json.dumps(template["details"], ensure_ascii=False),
                    json.dumps(template["quantifiable"], ensure_ascii=False),
                    template["focus"],
                    template["example"],
                    json.dumps(template["fields"], ensure_ascii=False),
                    json.dumps(UNIVERSAL_EXPERIENCE_QUESTIONS, ensure_ascii=False),
                    json.dumps(BULLET_FORMULAS, ensure_ascii=False),
                    index,
                ),
            )

    def _template_key_for_category(self, value: str) -> str:
        mapping = {
            "basic": "basic",
            "education": "education",
            "experience": "work",
            "work": "work",
            "project": "project",
            "award": "award",
            "skill": "skill",
            "other": "other",
        }
        return mapping.get(value, value if self._has_material_template(value) else "work")

    def _template_for_key(self, key: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
        for template in MATERIAL_TEMPLATE_ROWS:
            if template["template_key"] == key:
                return template
        if default is not None:
            return default
        return MATERIAL_TEMPLATE_ROWS[0]

    def _has_material_template(self, key: str) -> bool:
        return any(template["template_key"] == key for template in MATERIAL_TEMPLATE_ROWS)

    def _first_present(self, data: dict[str, Any], keys: list[str]) -> str:
        for key in keys:
            value = str(data.get(key) or "").strip()
            if value:
                return value
        return ""

    def _derive_organization(self, template_key: str, data: dict[str, Any]) -> str:
        key_groups = {
            "basic": ["city", "target_industry"],
            "education": ["school"],
            "education_courses": ["school"],
            "education_research": ["school"],
            "work": ["company", "department"],
            "work_responsibility": ["company", "department"],
            "work_result": ["company", "department"],
            "work_tools": ["company", "department"],
            "project": ["project_role", "team_name"],
            "award": ["issuer"],
            "skill": ["skill_group"],
            "other": ["experience_type"],
        }
        return self._first_present(data, key_groups.get(template_key, []))

    def _join_period(self, data: dict[str, Any]) -> str:
        start = str(data.get("start_date") or "").strip()
        end = str(data.get("end_date") or "").strip()
        return " - ".join(part for part in [start, end] if part)

    def _material_lines(self, data: dict[str, Any], keys: list[str], extra: list[Any] | None = None) -> list[str]:
        lines: list[str] = []
        for key in keys:
            value = str(data.get(key) or "").strip()
            if value:
                lines.extend(part.strip() for part in value.splitlines() if part.strip())
        for item in extra or []:
            value = str(item).strip()
            if value:
                lines.append(value)
        deduped: list[str] = []
        for line in lines:
            if line not in deduped:
                deduped.append(line)
        return deduped

    def _public_user_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_id": row.get("user_id", ""),
            "name": row.get("name", ""),
            "email": row.get("email", ""),
            "phone": row.get("phone", ""),
            "location": row.get("location", ""),
            "target_title": row.get("target_title", ""),
            "avatar_initials": row.get("avatar_initials") or self._avatar_initials(str(row.get("name") or "")),
            "is_test": bool(row.get("is_test", False)),
            "account_status": row.get("account_status") or "active",
            "timezone": row.get("timezone") or "Asia/Shanghai",
            "locale": row.get("locale") or "zh-CN",
            "profile": json.loads(row.get("profile_json") or "{}"),
            "preferences": json.loads(row.get("preferences_json") or "{}"),
            "last_login_at": row.get("last_login_at") or "",
            "last_active_at": row.get("last_active_at") or "",
            "created_at": row.get("created_at", ""),
            "updated_at": row.get("updated_at", ""),
        }

    def _project_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        for key, default in (
            ("selected_material_ids_json", []),
            ("resume_content_json", {}),
            ("editor_preferences_json", {}),
            ("export_settings_json", {}),
        ):
            raw = row.pop(key, None)
            output_key = key.removesuffix("_json")
            try:
                row[output_key] = json.loads(raw) if raw else default
            except json.JSONDecodeError:
                row[output_key] = default
        row["document_title"] = row.get("document_title") or f"{row.get('company_name', '')}-{row.get('role_title', '')}"
        row["template_id"] = row.get("template_id") or "zsc_table_resume"
        row["language"] = row.get("language") or "zh-CN"
        row["visibility"] = row.get("visibility") or "private"
        row["version_retention_days"] = int(row.get("version_retention_days") or self.RESUME_VERSION_RETENTION_DAYS)
        return row

    def _project_version_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        row["snapshot"] = json.loads(row.pop("snapshot_json"))
        return row

    def _generation_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        row["analysis"] = json.loads(row.pop("analysis_json"))
        row["ats_report"] = json.loads(row.pop("ats_report_json"))
        row["output_paths"] = json.loads(row.pop("output_paths_json"))
        return row

    def _material_template_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        row["required_content"] = json.loads(row.pop("required_content_json"))
        row["suggested_content"] = json.loads(row.pop("suggested_content_json"))
        row["detail_prompts"] = json.loads(row.pop("detail_prompts_json"))
        row["quantifiable_info"] = json.loads(row.pop("quantifiable_info_json"))
        row["fields"] = json.loads(row.pop("fields_json"))
        row["universal_questions"] = json.loads(row.pop("universal_questions_json"))
        row["bullet_formulas"] = json.loads(row.pop("bullet_formulas_json"))
        return row

    def _material_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        bullets = json.loads(row.pop("legacy_bullets_json"))
        metrics = json.loads(row.pop("legacy_metrics_json"))
        skills = json.loads(row.pop("legacy_skills_json"))
        actions = json.loads(row.pop("actions_json"))
        tools_methods = json.loads(row.pop("tools_methods_json"))
        outputs = json.loads(row.pop("outputs_json"))
        results = json.loads(row.pop("results_json"))
        quantification = json.loads(row.pop("quantification_json"))
        template_data = json.loads(row.pop("template_data_json"))
        evidence = json.loads(row.pop("evidence_json"))
        row["experience_id"] = row["material_id"]
        row["category"] = self._category_from_template_key(str(row["template_key"]))
        row["start"] = template_data.get("start_date", "")
        row["end"] = template_data.get("end_date", "")
        row["bullets"] = bullets or actions + tools_methods + outputs + results
        row["skills"] = skills
        row["metrics"] = metrics or quantification
        row["template_data"] = template_data
        row["evidence"] = evidence
        row["material_sections"] = {
            "identity": row.get("identity", ""),
            "period": row.get("period", ""),
            "background": row.get("background", ""),
            "task": row.get("task", ""),
            "actions": actions,
            "tools_methods": tools_methods,
            "outputs": outputs,
            "results": results,
            "quantification": quantification,
            "relevance": row.get("relevance", ""),
        }
        return row

    def _category_from_template_key(self, template_key: str) -> str:
        if template_key.startswith("education"):
            return "education"
        if template_key.startswith("work"):
            return "work"
        if template_key in {"basic", "project", "award", "skill", "other"}:
            return template_key
        return "work"

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
