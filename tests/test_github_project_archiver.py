import json
import tempfile
import unittest
from pathlib import Path

from utils.github_project_archiver import GitHubProjectArchiver


class GitHubProjectArchiverTest(unittest.TestCase):
    def test_collect_ranks_and_archives_projects(self):
        def fake_get(url, headers, timeout):
            self.assertIn("search/repositories", url)
            self.assertEqual(headers["X-GitHub-Api-Version"], "2022-11-28")
            return {
                "items": [
                    {
                        "full_name": "owner/resume-ai",
                        "html_url": "https://github.com/owner/resume-ai",
                        "description": "Resume generator",
                        "stargazers_count": 1000,
                        "forks_count": 80,
                        "language": "Python",
                        "topics": ["resume", "agent"],
                        "pushed_at": "2026-01-01T00:00:00Z",
                    }
                ]
            }

        with tempfile.TemporaryDirectory() as tmp:
            archiver = GitHubProjectArchiver(archive_root=tmp, http_get=fake_get)
            projects = archiver.collect("resume generator", limit=1, min_stars=100)
            self.assertEqual(projects[0].full_name, "owner/resume-ai")
            self.assertGreater(projects[0].score, projects[0].stars)
            folder = archiver.archive(projects, label="resume generator")
            payload = json.loads((folder / "projects.json").read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["full_name"], "owner/resume-ai")
            self.assertTrue(Path(folder / "README.md").exists())


if __name__ == "__main__":
    unittest.main()
