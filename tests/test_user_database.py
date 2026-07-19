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
                    "template_key": "project",
                    "title": "增长实验平台",
                    "organization": "实习项目",
                    "bullets": ["分析转化漏斗并定位留存问题"],
                    "skills": ["SQL", "增长"],
                    "metrics": ["转化率提升 18%"],
                    "template_data": {
                        "project_name": "增长实验平台",
                        "problem": "注册后留存低",
                        "result_metrics": "转化率提升 18%",
                    },
                    "evidence": ["https://example.com/project"],
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
            self.assertEqual(experience["module"], "项目经历")
            self.assertEqual(experience["subsection"], "项目经历")
            self.assertEqual(experience["template_key"], "project")
            self.assertEqual(experience["template_data"]["problem"], "注册后留存低")
            self.assertEqual(experience["evidence"], ["https://example.com/project"])
            self.assertEqual(project["user_id"], "zhangsan@example.com")
            self.assertEqual(db.list_experiences("zhangsan@example.com")[0]["metrics"], ["转化率提升 18%"])
            self.assertEqual(db.list_experiences("zhangsan@example.com")[0]["material_sections"]["results"], ["转化率提升 18%"])
            self.assertEqual(
                db.list_experiences("zhangsan@example.com")[0]["template_data"]["result_metrics"],
                "转化率提升 18%",
            )
            self.assertEqual(db.list_projects("zhangsan@example.com")[0]["company_name"], "示例科技")

    def test_seeds_detailed_resume_material_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = UserDatabase(Path(tmp) / "users.sqlite3")

            templates = db.list_material_templates()
            keys = {template["template_key"] for template in templates}

            self.assertIn("basic", keys)
            self.assertIn("education_courses", keys)
            self.assertIn("work_result", keys)
            self.assertIn("project", keys)
            self.assertIn("other", keys)
            project = next(template for template in templates if template["template_key"] == "project")
            self.assertIn("项目名称", project["required_content"])
            self.assertIn("数据规模", project["quantifiable_info"])
            self.assertIn("这段经历发生在哪里？", project["universal_questions"])
            self.assertTrue(project["bullet_formulas"])

    def test_registers_and_logs_in_user_without_exposing_password_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = UserDatabase(Path(tmp) / "users.sqlite3")

            user = db.register_user(
                name="张三",
                email="ZhangSan@Example.com",
                password="CorrectHorseBattery7",
                target_title="AI 产品经理",
            )

            self.assertEqual(user["user_id"], "zhangsan@example.com")
            self.assertEqual(user["avatar_initials"], "张三")
            self.assertNotIn("password_hash", user)
            logged_in = db.login_user(email="zhangsan@example.com", password="CorrectHorseBattery7")
            self.assertEqual(logged_in["name"], "张三")
            with self.assertRaises(ValueError):
                db.login_user(email="zhangsan@example.com", password="wrong-password")
            with self.assertRaises(ValueError):
                db.register_user(name="弱密码", email="weak@example.com", password="123456789012")

    def test_test_account_sessions_and_resume_versions_are_persistent_and_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = UserDatabase(Path(tmp) / "users.sqlite3")

            test_user = db.login_user(email="test", password="test123")
            self.assertTrue(test_user["is_test"])
            self.assertEqual(test_user["email"], "")
            session = db.create_session("test")
            self.assertEqual(db.get_session_user(session["token"])["user_id"], "test")

            project = db.save_project(
                "test",
                {
                    "company_name": "示例公司",
                    "role_title": "产品经理",
                    "document_title": "示例公司-产品经理",
                    "jd_text": "负责产品规划。",
                    "resume_content": {"summary": "第一版"},
                },
            )
            for number in range(2, 6):
                project = db.save_project(
                    "test",
                    {
                        **project,
                        "resume_content": {"summary": f"第 {number} 版"},
                        "change_summary": f"保存第 {number} 版",
                    },
                )

            versions = db.list_project_versions("test", project["project_id"])
            self.assertEqual(len(versions), 3)
            restored = db.restore_project_version("test", project["project_id"], versions[-1]["version_id"])
            self.assertEqual(restored["resume_content"]["summary"], versions[-1]["snapshot"]["resume_content"]["summary"])

            reset = db.reset_test_account()
            self.assertTrue(reset["projects"])
            self.assertEqual(reset["projects"][0]["company_name"], "示例科技")


if __name__ == "__main__":
    unittest.main()
