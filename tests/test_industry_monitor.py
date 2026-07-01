import tempfile
import unittest

from utils.company_search import SearchResult
from utils.github_project_archiver import GitHubProject
from utils.industry_monitor import DailyIndustryMonitor


class FakeCompanySearch:
    def search_company(self, company, *, focus_terms, limit, summarize):
        return {
            "company": company,
            "results": [
                {
                    "title": f"{company} AI 产品经理 JD",
                    "url": "https://example.com/jd",
                    "snippet": "负责 AI 自动化产品，优化效率和用户体验。",
                }
            ],
        }


class FakeGitHubArchiver:
    def collect(self, query, *, limit, min_stars, summarize):
        return [
            GitHubProject(
                full_name="owner/ai-workflow",
                html_url="https://github.com/owner/ai-workflow",
                description="AI workflow automation",
                stars=1000,
                forks=80,
                language="Python",
                topics=["ai", "automation"],
                pushed_at="2026-01-01T00:00:00Z",
                score=1200,
            )
        ]


class IndustryMonitorTest(unittest.TestCase):
    def test_collects_jd_and_github_signals(self):
        with tempfile.TemporaryDirectory() as tmp:
            monitor = DailyIndustryMonitor(
                company_search=FakeCompanySearch(),
                github_archiver=FakeGitHubArchiver(),
                archive_root=tmp,
            )
            report = monitor.collect(
                industries=["AI 工具"],
                companies=["Example"],
                github_queries=["resume generator"],
                limit_per_source=1,
            )
            path = monitor.archive(report, label="test")
            self.assertTrue(path.exists())

        self.assertEqual(len(report["signals"]), 2)
        self.assertIn("每日行业信号摘要", report["summary"])


if __name__ == "__main__":
    unittest.main()
