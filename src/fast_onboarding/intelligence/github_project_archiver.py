"""Collect and archive high-signal GitHub projects for resume inspiration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable
from urllib import parse, request

from fast_onboarding.integrations.deepseek_client import DeepSeekClient

HttpGet = Callable[[str, dict[str, str], int], dict[str, Any]]


def _urllib_get(url: str, headers: dict[str, str], timeout: int) -> dict[str, Any]:
    req = request.Request(url, headers=headers, method="GET")
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


@dataclass(frozen=True)
class GitHubProject:
    full_name: str
    html_url: str
    description: str
    stars: int
    forks: int
    language: str | None
    topics: list[str]
    pushed_at: str
    score: float
    summary: str = ""


class GitHubProjectArchiver:
    """Search GitHub repositories, rank them, and store normalized archives."""

    def __init__(
        self,
        *,
        archive_root: str | Path = "data/github_projects",
        github_token: str | None = None,
        deepseek_client: DeepSeekClient | None = None,
        http_get: HttpGet = _urllib_get,
        timeout_seconds: int = 20,
    ) -> None:
        self.archive_root = Path(archive_root)
        self.github_token = github_token
        self.deepseek_client = deepseek_client
        self.http_get = http_get
        self.timeout_seconds = timeout_seconds

    def collect(
        self,
        query: str,
        *,
        limit: int = 20,
        min_stars: int = 200,
        language: str | None = None,
        summarize: bool = False,
    ) -> list[GitHubProject]:
        search_query = f"{query} stars:>={min_stars}"
        if language:
            search_query += f" language:{language}"
        params = parse.urlencode(
            {
                "q": search_query,
                "sort": "stars",
                "order": "desc",
                "per_page": min(max(limit, 1), 100),
            }
        )
        data = self.http_get(
            f"https://api.github.com/search/repositories?{params}",
            self._headers(),
            self.timeout_seconds,
        )
        projects = [self._from_item(item) for item in data.get("items", [])[:limit]]
        if summarize and self.deepseek_client:
            projects = [self._with_summary(project) for project in projects]
        return projects

    def archive(self, projects: list[GitHubProject], *, label: str) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        folder = self.archive_root / f"{timestamp}-{self._slug(label)}"
        folder.mkdir(parents=True, exist_ok=True)
        payload = [asdict(project) for project in projects]
        (folder / "projects.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        lines = [json.dumps(item, ensure_ascii=False) for item in payload]
        (folder / "projects.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (folder / "README.md").write_text(self._readme(label, projects), encoding="utf-8")
        return folder

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "resume-generator-utils",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    def _from_item(self, item: dict[str, Any]) -> GitHubProject:
        stars = int(item.get("stargazers_count") or 0)
        forks = int(item.get("forks_count") or 0)
        topics = list(item.get("topics") or [])
        score = stars + forks * 2 + len(topics) * 25
        return GitHubProject(
            full_name=item["full_name"],
            html_url=item["html_url"],
            description=item.get("description") or "",
            stars=stars,
            forks=forks,
            language=item.get("language"),
            topics=topics,
            pushed_at=item.get("pushed_at") or "",
            score=score,
        )

    def _with_summary(self, project: GitHubProject) -> GitHubProject:
        prompt = (
            "请判断这个 GitHub 项目对简历生成器有哪些可借鉴点，"
            "输出 3 条以内，聚焦架构、数据流、用户体验。"
        )
        summary = self.deepseek_client.complete_text(
            "你是软件架构研究助手。",
            f"{project.full_name}\n{project.description}\nTopics: {', '.join(project.topics)}\n{prompt}",
        )
        return GitHubProject(**{**asdict(project), "summary": summary})

    def _readme(self, label: str, projects: list[GitHubProject]) -> str:
        rows = [
            "# GitHub Project Archive",
            "",
            f"- Label: {label}",
            f"- Count: {len(projects)}",
            "",
            "| Project | Stars | Language | Notes |",
            "| --- | ---: | --- | --- |",
        ]
        for project in projects:
            notes = project.summary or project.description.replace("|", " ")
            rows.append(
                f"| [{project.full_name}]({project.html_url}) | {project.stars} | "
                f"{project.language or ''} | {notes} |"
            )
        return "\n".join(rows) + "\n"

    def _slug(self, value: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-") or "archive"
