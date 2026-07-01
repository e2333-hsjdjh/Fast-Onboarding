"""MVP workflow for targeted resume generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
from typing import Any

from fast_onboarding.integrations.deepseek_client import DeepSeekClient


@dataclass(frozen=True)
class Experience:
    title: str
    organization: str
    start: str = ""
    end: str = ""
    bullets: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CandidateProfile:
    name: str
    target_title: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    skills: list[str] = field(default_factory=list)
    experiences: list[Experience] = field(default_factory=list)
    projects: list[Experience] = field(default_factory=list)
    education: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class JDAnalysis:
    target_role: str
    required_keywords: list[str]
    preferred_keywords: list[str]
    responsibilities: list[str]
    pain_points: list[str]
    ats_keywords: list[str]


class MaterialStore:
    """Load and save the user's structured career material."""

    def __init__(self, path: str | Path = "data/profile.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, profile: CandidateProfile) -> Path:
        self.path.write_text(json.dumps(asdict(profile), ensure_ascii=False, indent=2), encoding="utf-8")
        return self.path

    def load(self) -> CandidateProfile:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return self.from_dict(payload)

    def from_dict(self, payload: dict[str, Any]) -> CandidateProfile:
        return CandidateProfile(
            name=str(payload.get("name", "")),
            target_title=str(payload.get("target_title", "")),
            email=str(payload.get("email", "")),
            phone=str(payload.get("phone", "")),
            location=str(payload.get("location", "")),
            summary=str(payload.get("summary", "")),
            skills=list(payload.get("skills", [])),
            experiences=[Experience(**item) for item in payload.get("experiences", [])],
            projects=[Experience(**item) for item in payload.get("projects", [])],
            education=list(payload.get("education", [])),
        )


class JDAnalyzer:
    """Extract role requirements and ATS keywords from a job description."""

    DEFAULT_KEYWORDS = [
        "Python",
        "SQL",
        "数据分析",
        "产品",
        "增长",
        "A/B",
        "用户研究",
        "项目管理",
        "AI",
        "LLM",
        "自动化",
        "GitHub",
        "Word",
        "ATS",
        "DeepSeek",
    ]

    def __init__(self, deepseek_client: DeepSeekClient | None = None) -> None:
        self.deepseek_client = deepseek_client

    def analyze(self, jd_text: str, *, target_role: str = "") -> JDAnalysis:
        if self.deepseek_client:
            result = self.deepseek_client.complete_json(
                "你是招聘 JD 分析器。只输出 JSON，字段为 target_role, required_keywords, preferred_keywords, responsibilities, pain_points, ats_keywords。",
                jd_text,
            )
            return JDAnalysis(
                target_role=str(result.get("target_role") or target_role),
                required_keywords=list(result.get("required_keywords", [])),
                preferred_keywords=list(result.get("preferred_keywords", [])),
                responsibilities=list(result.get("responsibilities", [])),
                pain_points=list(result.get("pain_points", [])),
                ats_keywords=list(result.get("ats_keywords", [])),
            )
        return self._rule_based(jd_text, target_role=target_role)

    def _rule_based(self, jd_text: str, *, target_role: str) -> JDAnalysis:
        normalized = jd_text.lower()
        found = []
        for keyword in self.DEFAULT_KEYWORDS:
            if keyword.lower() in normalized:
                found.append(keyword)
        lines = [line.strip(" -•\t") for line in jd_text.splitlines() if line.strip()]
        responsibilities = [line for line in lines if self._looks_like_responsibility(line)][:6]
        pain_points = [line for line in lines if self._looks_like_pain_point(line)][:5]
        role = target_role or self._guess_role(lines)
        return JDAnalysis(
            target_role=role,
            required_keywords=found[:8],
            preferred_keywords=found[8:14],
            responsibilities=responsibilities,
            pain_points=pain_points,
            ats_keywords=sorted(set(found)),
        )

    def _looks_like_responsibility(self, line: str) -> bool:
        markers = ["负责", "推动", "建设", "分析", "设计", "优化", "协同", "deliver", "build", "analyze"]
        return any(marker.lower() in line.lower() for marker in markers)

    def _looks_like_pain_point(self, line: str) -> bool:
        markers = ["痛点", "问题", "效率", "转化", "成本", "风险", "增长", "体验", "quality", "scale"]
        return any(marker.lower() in line.lower() for marker in markers)

    def _guess_role(self, lines: list[str]) -> str:
        for line in lines[:5]:
            if len(line) <= 40 and any(word in line for word in ["经理", "工程师", "分析师", "运营", "Designer"]):
                return line
        return "目标岗位"


class ResumeGenerator:
    """Select relevant material and render a targeted Markdown resume."""

    def __init__(self, deepseek_client: DeepSeekClient | None = None) -> None:
        self.deepseek_client = deepseek_client

    def generate_markdown(self, profile: CandidateProfile, analysis: JDAnalysis) -> str:
        selected_experiences = self._select(profile.experiences, analysis, limit=3)
        selected_projects = self._select(profile.projects, analysis, limit=2)
        summary = self._summary(profile, analysis)
        sections = [
            f"# {profile.name}",
            self._contact(profile),
            "## 求职目标",
            analysis.target_role or profile.target_title or "目标岗位",
            "## 个人摘要",
            summary,
            "## 核心技能",
            "、".join(self._rank_skills(profile.skills, analysis)) or "待补充",
            "## 工作经历",
            self._render_items(selected_experiences),
            "## 项目经历",
            self._render_items(selected_projects),
            "## 教育背景",
            "\n".join(f"- {item}" for item in profile.education) or "- 待补充",
        ]
        draft = "\n\n".join(section for section in sections if section.strip()) + "\n"
        if self.deepseek_client:
            return self.deepseek_client.complete_text(
                "你是简历编辑。请保持 Markdown 结构，优化措辞，突出 JD 关键词和量化结果。",
                draft,
            )
        return draft

    def _select(self, items: list[Experience], analysis: JDAnalysis, *, limit: int) -> list[Experience]:
        scored = [(self._score(item, analysis), item) for item in items]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for score, item in scored[:limit] if score > 0] or items[:limit]

    def _score(self, item: Experience, analysis: JDAnalysis) -> int:
        text = " ".join([item.title, item.organization, *item.bullets, *item.skills]).lower()
        return sum(1 for keyword in analysis.ats_keywords + analysis.required_keywords if keyword.lower() in text)

    def _summary(self, profile: CandidateProfile, analysis: JDAnalysis) -> str:
        matched = self._rank_skills(profile.skills, analysis)[:5]
        base = profile.summary or f"{profile.target_title or analysis.target_role} 候选人"
        if matched:
            return f"{base}。重点匹配：{'、'.join(matched)}。"
        return base

    def _contact(self, profile: CandidateProfile) -> str:
        parts = [profile.email, profile.phone, profile.location]
        return " | ".join(part for part in parts if part)

    def _rank_skills(self, skills: list[str], analysis: JDAnalysis) -> list[str]:
        keywords = {keyword.lower() for keyword in analysis.ats_keywords + analysis.required_keywords}
        return sorted(skills, key=lambda skill: (skill.lower() not in keywords, skill.lower()))

    def _render_items(self, items: list[Experience]) -> str:
        if not items:
            return "- 待补充"
        blocks = []
        for item in items:
            dates = f"（{item.start}-{item.end}）" if item.start or item.end else ""
            bullets = item.bullets or ["待补充关键行动与结果"]
            metrics = [f"量化结果：{metric}" for metric in item.metrics]
            body = "\n".join(f"- {line}" for line in bullets + metrics)
            blocks.append(f"### {item.title} | {item.organization}{dates}\n{body}")
        return "\n\n".join(blocks)


class ATSChecker:
    """Score resume coverage against JD keywords and basic ATS constraints."""

    def check(self, resume_markdown: str, analysis: JDAnalysis) -> dict[str, Any]:
        text = resume_markdown.lower()
        keywords = sorted(set(analysis.ats_keywords + analysis.required_keywords))
        missing = [keyword for keyword in keywords if keyword.lower() not in text]
        coverage = 1.0 if not keywords else (len(keywords) - len(missing)) / len(keywords)
        warnings = []
        if len(resume_markdown) > 4500:
            warnings.append("内容可能过长，建议压缩到 1-2 页。")
        if "|" in resume_markdown:
            warnings.append("Markdown 中包含分隔符，导出 Word/PDF 前需确认 ATS 解析效果。")
        if not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", resume_markdown):
            warnings.append("缺少邮箱联系方式。")
        return {
            "score": round(coverage * 100),
            "keyword_coverage": round(coverage, 2),
            "missing_keywords": missing,
            "warnings": warnings,
        }


class ResumeMVPWorkflow:
    """End-to-end MVP: profile + JD -> tailored resume + ATS report."""

    def __init__(
        self,
        *,
        jd_analyzer: JDAnalyzer | None = None,
        resume_generator: ResumeGenerator | None = None,
        ats_checker: ATSChecker | None = None,
    ) -> None:
        self.jd_analyzer = jd_analyzer or JDAnalyzer()
        self.resume_generator = resume_generator or ResumeGenerator()
        self.ats_checker = ats_checker or ATSChecker()

    def run(
        self,
        *,
        profile: CandidateProfile,
        jd_text: str,
        output_dir: str | Path,
        target_role: str = "",
    ) -> dict[str, Any]:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        analysis = self.jd_analyzer.analyze(jd_text, target_role=target_role)
        resume = self.resume_generator.generate_markdown(profile, analysis)
        ats = self.ats_checker.check(resume, analysis)
        (output / "resume.md").write_text(resume, encoding="utf-8")
        (output / "jd_analysis.json").write_text(
            json.dumps(asdict(analysis), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (output / "ats_report.json").write_text(
            json.dumps(ats, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "resume_path": str(output / "resume.md"),
            "analysis_path": str(output / "jd_analysis.json"),
            "ats_report_path": str(output / "ats_report.json"),
            "ats": ats,
        }
