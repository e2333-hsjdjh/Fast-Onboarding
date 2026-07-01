"""Daily JD and GitHub trend monitoring for resume strategy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from fast_onboarding.integrations.deepseek_client import DeepSeekClient
from fast_onboarding.intelligence.company_search import CompanyInfoSearch
from fast_onboarding.intelligence.github_project_archiver import GitHubProject, GitHubProjectArchiver
from fast_onboarding.resume_mvp import JDAnalyzer


@dataclass(frozen=True)
class IndustrySignal:
    industry: str
    source: str
    title: str
    url: str
    summary: str
    keywords: list[str]


class DailyIndustryMonitor:
    """Collect job-market pain points and GitHub project signals by industry."""

    def __init__(
        self,
        *,
        company_search: CompanyInfoSearch | None = None,
        github_archiver: GitHubProjectArchiver | None = None,
        jd_analyzer: JDAnalyzer | None = None,
        deepseek_client: DeepSeekClient | None = None,
        archive_root: str | Path = "data/industry_monitor",
    ) -> None:
        self.company_search = company_search or CompanyInfoSearch(deepseek_client=deepseek_client)
        self.github_archiver = github_archiver or GitHubProjectArchiver(deepseek_client=deepseek_client)
        self.jd_analyzer = jd_analyzer or JDAnalyzer(deepseek_client=deepseek_client)
        self.deepseek_client = deepseek_client
        self.archive_root = Path(archive_root)

    def collect(
        self,
        *,
        industries: list[str],
        companies: list[str],
        github_queries: list[str],
        limit_per_source: int = 5,
    ) -> dict[str, Any]:
        signals: list[IndustrySignal] = []
        for industry in industries:
            for company in companies:
                payload = self.company_search.search_company(
                    company,
                    focus_terms=[industry, "招聘", "JD", "岗位职责", "业务痛点"],
                    limit=limit_per_source,
                    summarize=False,
                )
                for item in payload["results"]:
                    analysis = self.jd_analyzer.analyze(str(item["snippet"]), target_role=industry)
                    signals.append(
                        IndustrySignal(
                            industry=industry,
                            source="jd_search",
                            title=str(item["title"]),
                            url=str(item["url"]),
                            summary=str(item["snippet"]),
                            keywords=analysis.ats_keywords,
                        )
                    )
            for query in github_queries:
                projects = self.github_archiver.collect(
                    f"{industry} {query}",
                    limit=limit_per_source,
                    min_stars=100,
                    summarize=False,
                )
                signals.extend(self._github_signals(industry, projects))
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "industries": industries,
            "signals": [asdict(signal) for signal in signals],
            "summary": self._summarize(signals),
        }
        return report

    def archive(self, report: dict[str, Any], *, label: str = "daily") -> Path:
        self.archive_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = self.archive_root / f"{stamp}-{self._slug(label)}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _github_signals(self, industry: str, projects: list[GitHubProject]) -> list[IndustrySignal]:
        signals = []
        for project in projects:
            keywords = [project.language or "", *project.topics]
            signals.append(
                IndustrySignal(
                    industry=industry,
                    source="github",
                    title=project.full_name,
                    url=project.html_url,
                    summary=project.summary or project.description,
                    keywords=[keyword for keyword in keywords if keyword],
                )
            )
        return signals

    def _summarize(self, signals: list[IndustrySignal]) -> str:
        if not signals:
            return "暂无可汇总信号。"
        if self.deepseek_client:
            evidence = "\n".join(
                f"- [{signal.industry}] {signal.source}: {signal.title} {signal.summary}"
                for signal in signals[:30]
            )
            return self.deepseek_client.complete_text(
                "你是行业研究员。请基于 JD 和 GitHub 信号总结行业痛点、技能趋势、可写入简历的项目方向。",
                evidence,
            )
        by_industry: dict[str, set[str]] = {}
        for signal in signals:
            by_industry.setdefault(signal.industry, set()).update(signal.keywords)
        lines = ["每日行业信号摘要："]
        for industry, keywords in by_industry.items():
            selected = "、".join(sorted(keyword for keyword in keywords if keyword)[:10])
            lines.append(f"- {industry}: 高频关键词 {selected or '待补充'}")
        lines.append("建议：优先把真实项目经历映射到高频关键词，避免编造经历。")
        return "\n".join(lines)

    def _slug(self, value: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-") or "daily"
