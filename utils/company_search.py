"""Unified company intelligence search and DeepSeek summarization."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import html
import json
from pathlib import Path
import re
from typing import Callable
from urllib import parse, request

from .deepseek_client import DeepSeekClient

HttpTextGet = Callable[[str, dict[str, str], int], str]


def _urllib_text_get(url: str, headers: dict[str, str], timeout: int) -> str:
    req = request.Request(url, headers=headers, method="GET")
    with request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str


class DuckDuckGoHtmlProvider:
    """Low-dependency web search provider for public company research."""

    def __init__(self, http_get: HttpTextGet = _urllib_text_get, timeout_seconds: int = 20) -> None:
        self.http_get = http_get
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, *, limit: int = 8) -> list[SearchResult]:
        params = parse.urlencode({"q": query})
        text = self.http_get(
            f"https://html.duckduckgo.com/html/?{params}",
            {"User-Agent": "resume-generator-utils"},
            self.timeout_seconds,
        )
        return self._parse(text)[:limit]

    def _parse(self, text: str) -> list[SearchResult]:
        results: list[SearchResult] = []
        pattern = re.compile(
            r'<a rel="nofollow" class="result__a" href="(?P<url>[^"]+)".*?>(?P<title>.*?)</a>.*?'
            r'<a class="result__snippet".*?>(?P<snippet>.*?)</a>',
            re.S,
        )
        for match in pattern.finditer(text):
            url = html.unescape(re.sub("<.*?>", "", match.group("url")))
            title = html.unescape(re.sub("<.*?>", "", match.group("title"))).strip()
            snippet = html.unescape(re.sub("<.*?>", "", match.group("snippet"))).strip()
            results.append(SearchResult(title=title, url=url, snippet=snippet, source="duckduckgo"))
        return results


class CompanyInfoSearch:
    """Search the web for a company and ask DeepSeek to structure the findings."""

    def __init__(
        self,
        *,
        provider: DuckDuckGoHtmlProvider | None = None,
        deepseek_client: DeepSeekClient | None = None,
        archive_root: str | Path = "data/company_search",
    ) -> None:
        self.provider = provider or DuckDuckGoHtmlProvider()
        self.deepseek_client = deepseek_client
        self.archive_root = Path(archive_root)

    def search_company(
        self,
        company: str,
        *,
        focus_terms: list[str] | None = None,
        limit: int = 8,
        summarize: bool = True,
    ) -> dict[str, object]:
        terms = focus_terms or ["业务", "产品", "招聘", "文化", "新闻", "面试"]
        query = f"{company} " + " OR ".join(terms)
        results = self.provider.search(query, limit=limit)
        summary = ""
        if summarize and self.deepseek_client:
            summary = self._summarize(company, terms, results)
        return {
            "company": company,
            "query": query,
            "results": [asdict(result) for result in results],
            "summary": summary,
        }

    def archive(self, payload: dict[str, object]) -> Path:
        self.archive_root.mkdir(parents=True, exist_ok=True)
        company = str(payload.get("company") or "company")
        path = self.archive_root / f"{self._slug(company)}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _summarize(self, company: str, terms: list[str], results: list[SearchResult]) -> str:
        evidence = "\n".join(
            f"- {result.title}\n  {result.url}\n  {result.snippet}" for result in results
        )
        return self.deepseek_client.complete_text(
            "你是求职信息研究员，只基于给定搜索结果提炼信息。",
            (
                f"公司：{company}\n关注点：{', '.join(terms)}\n"
                "请输出：业务概览、近期动态、简历关键词、面试准备点、信息来源风险。\n\n"
                f"{evidence}"
            ),
        )

    def _slug(self, value: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-") or "company"
