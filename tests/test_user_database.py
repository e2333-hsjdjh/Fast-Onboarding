import tempfile
import unittest
from pathlib import Path

from fast_onboarding.core.user_database import UserDatabase
from fast_onboarding.resume_mvp import CandidateProfile, Experience


class UserDatabaseTest(unittest.TestCase):
    def test_records_user_profile_jd_and_generation_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = UserDatabase(Path(tmp) / "users.sqlite3")
            profile = CandidateProfile(
                name="张三",
                email="zhangsan@example.com",
                target_title="AI 产品经理",
                experiences=[Experience(title="AI 简历生成器", organization="个人项目")],
            )
            record = db.record_generation(
                profile=profile,
                jd_text="负责 AI 产品。",
                target_role="AI 产品经理",
                analysis={"target_role": "AI 产品经理", "ats_keywords": ["AI"]},
                resume_markdown="# 张三",
                ats_report={"score": 100},
                output_paths={"resume_path": "workspace/resume.md"},
            )

            self.assertEqual(record["user_id"], "zhangsan@example.com")
            user = db.get_user(record["user_id"])
            self.assertEqual(user["name"], "张三")
            generations = db.list_generations(record["user_id"])
            self.assertEqual(len(generations), 1)
            self.assertEqual(generations[0]["ats_report"]["score"], 100)
            self.assertIn("# 张三", generations[0]["resume_markdown"])


if __name__ == "__main__":
    unittest.main()
