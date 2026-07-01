"""Company, job-market, and GitHub intelligence tools."""

from .company_search import CompanyInfoSearch, DuckDuckGoHtmlProvider, SearchResult
from .github_project_archiver import GitHubProject, GitHubProjectArchiver
from .industry_monitor import DailyIndustryMonitor, IndustrySignal

__all__ = [
    "CompanyInfoSearch",
    "DailyIndustryMonitor",
    "DuckDuckGoHtmlProvider",
    "GitHubProject",
    "GitHubProjectArchiver",
    "IndustrySignal",
    "SearchResult",
]
