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

    def test_saves_user_experiences_and_application_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = UserDatabase(Path(tmp) / "users.sqlite3")

            experience = db.save_experience(
                "zhangsan@example.com",
                {
                    "user_name": "张三",
                    "category": "project",
                    "title": "增长实验平台",
                    "organization": "实习项目",
                    "bullets": ["分析转化漏斗并定位留存问题"],
                    "skills": ["SQL", "增长"],
                    "metrics": ["转化率提升 18%"],
                },
            )
            project = db.save_project(
                "zhangsan@example.com",
                {
                    "company_name": "示例科技",
                    "role_title": "增长产品经理",
                    "jd_text": "负责增长分析和用户研究。",
                    "status": "draft",
                    "notes": "第一版",
                },
            )

            self.assertEqual(experience["user_id"], "zhangsan@example.com")
            self.assertEqual(project["user_id"], "zhangsan@example.com")
            self.assertEqual(db.list_experiences("zhangsan@example.com")[0]["metrics"], ["转化率提升 18%"])
            self.assertEqual(db.list_projects("zhangsan@example.com")[0]["company_name"], "示例科技")


if __name__ == "__main__":
    unittest.main()
