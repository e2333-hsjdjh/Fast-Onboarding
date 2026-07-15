import json
from http.client import HTTPConnection
from pathlib import Path
import socket
import tempfile
from threading import Thread
import unittest

from fast_onboarding.web.server import WebAppConfig, create_handler, normalize_base_path
from http.server import ThreadingHTTPServer


class WebServerTest(unittest.TestCase):
    def test_normalize_base_path(self):
        self.assertEqual(normalize_base_path(""), "")
        self.assertEqual(normalize_base_path("/"), "")
        self.assertEqual(normalize_base_path("resume"), "/resume")
        self.assertEqual(normalize_base_path("/resume/"), "/resume")

    def test_static_page_switching_does_not_use_hash_routing(self):
        app_js = Path("src/fast_onboarding/web/static/app.js").read_text(encoding="utf-8")

        self.assertNotIn("location.hash", app_js)
        self.assertNotIn("hashchange", app_js)

    def test_home_background_uses_visible_image_layer(self):
        styles = Path("src/fast_onboarding/web/static/styles.css").read_text(encoding="utf-8")

        self.assertIn(".home-page .portal::before", styles)
        self.assertIn("resume-hero-3d-v2.png", styles)
        self.assertIn("brightness(1.24)", styles)

    def test_user_avatar_opens_experience_editor(self):
        workspace_html = Path("src/fast_onboarding/web/static/workspace.html").read_text(encoding="utf-8")
        app_js = Path("src/fast_onboarding/web/static/app.js").read_text(encoding="utf-8")

        self.assertIn('aria-label="修改用户经历"', workspace_html)
        self.assertIn("openUserExperiences", app_js)
        self.assertIn("setSourceCategory('basic')", app_js)
        self.assertIn("showWorkspaceView('editor')", app_js)
        self.assertNotIn("function showPage", app_js)

    def test_workspace_uses_resume_library_and_three_pane_editor(self):
        workspace_html = Path("src/fast_onboarding/web/static/workspace.html").read_text(encoding="utf-8")
        styles = Path("src/fast_onboarding/web/static/styles.css").read_text(encoding="utf-8")

        self.assertIn('id="resumeLibrary"', workspace_html)
        self.assertIn('id="resumeEditor"', workspace_html)
        self.assertIn('id="resumeCardGrid"', workspace_html)
        self.assertIn('id="experienceDialog"', workspace_html)
        self.assertNotIn('value="AI 简历生成器产品负责人"', workspace_html)
        self.assertNotIn('将简历初稿生成时间从 60 分钟压缩到 5 分钟', workspace_html)
        self.assertIn("source-pane", workspace_html)
        self.assertIn("resume-pane", workspace_html)
        self.assertIn("ai-pane", workspace_html)
        self.assertIn(".resume-card-grid", styles)
        self.assertIn("grid-template-columns: 300px minmax(460px, 1fr) 340px", styles)
        self.assertIn(".experience-dialog", styles)

    def test_health_and_generate_work_behind_base_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = WebAppConfig(
                host="127.0.0.1",
                port=0,
                base_path="/resume",
                output_dir=str(Path(tmp) / "out"),
                database_path=str(Path(tmp) / "users.sqlite3"),
            )
            try:
                server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(config))
            except (PermissionError, socket.error) as exc:
                self.skipTest(f"local socket binding is unavailable: {exc}")
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                port = server.server_address[1]
                conn = HTTPConnection("127.0.0.1", port, timeout=5)
                conn.request("GET", "/resume/api/health")
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                health = json.loads(response.read().decode("utf-8"))
                self.assertEqual(health["base_path"], "/resume")

                conn.request("GET", "/resume/api/material-templates")
                response = conn.getresponse()
                templates_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertIn("templates", templates_body)
                self.assertTrue(any(item["template_key"] == "work_result" for item in templates_body["templates"]))

                conn.request("HEAD", "/resume/")
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                self.assertIn("text/html", response.getheader("Content-Type"))
                response.read()

                conn.request("GET", "/resume/")
                response = conn.getresponse()
                html = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn('href="/resume/workspace"', html)
                self.assertNotIn('id="workspace"', html)
                self.assertNotIn('data-page="profile"', html)
                self.assertNotIn('href="#workspace"', html)

                conn.request("GET", "/resume/static/styles.css")
                response = conn.getresponse()
                css = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("/resume/static/assets/resume-hero-3d-v2.png", css)

                conn.request("HEAD", "/resume/static/assets/resume-hero-3d-v2.png")
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.getheader("Content-Type"), "image/png")
                response.read()

                conn.request("HEAD", "/resume/workspace")
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                self.assertIn("text/html", response.getheader("Content-Type"))
                response.read()

                conn.request("GET", "/resume/workspace")
                response = conn.getresponse()
                workspace_html = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn('id="workspace"', workspace_html)
                self.assertIn('id="resumeLibrary"', workspace_html)
                self.assertIn('id="resumeEditor"', workspace_html)
                self.assertIn('id="sourceCategoryNav"', workspace_html)
                self.assertIn('id="aiReply"', workspace_html)
                self.assertIn('href="/resume/"', workspace_html)
                self.assertIn('id="authGate"', workspace_html)
                self.assertIn('id="userBadge"', workspace_html)
                self.assertIn('id="newResumeDialog"', workspace_html)
                self.assertIn('id="testLoginBtn"', workspace_html)

                conn.request(
                    "POST",
                    "/resume/api/auth/test-session",
                    json.dumps({}).encode("utf-8"),
                    {"Content-Type": "application/json"},
                )
                response = conn.getresponse()
                test_session_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(test_session_body["user"]["user_id"], "test")
                self.assertTrue(test_session_body["session"]["token"])

                conn.request("GET", f"/resume/api/auth/session/{test_session_body['session']['token']}")
                response = conn.getresponse()
                session_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertTrue(session_body["user"]["is_test"])

                conn.request("GET", "/resume/api/users/test/projects")
                response = conn.getresponse()
                test_projects_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertTrue(test_projects_body["projects"])
                test_project = test_projects_body["projects"][0]
                conn.request("GET", f"/resume/api/users/test/projects/{test_project['project_id']}/versions")
                response = conn.getresponse()
                versions_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertTrue(versions_body["versions"])

                register_payload = {
                    "name": "李四",
                    "email": "lisi@example.com",
                    "password": "123456",
                    "target_title": "增长产品经理",
                }
                conn.request(
                    "POST",
                    "/resume/api/auth/register",
                    json.dumps(register_payload).encode("utf-8"),
                    {"Content-Type": "application/json"},
                )
                response = conn.getresponse()
                register_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(register_body["user"]["user_id"], "lisi@example.com")
                self.assertNotIn("password_hash", register_body["user"])

                conn.request(
                    "POST",
                    "/resume/api/auth/login",
                    json.dumps({"email": "lisi@example.com", "password": "123456"}).encode("utf-8"),
                    {"Content-Type": "application/json"},
                )
                response = conn.getresponse()
                login_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(login_body["user"]["name"], "李四")

                ai_payload = {
                    "target": "experience",
                    "context": {
                        "experience": {
                            "title": "AI 简历生成器",
                            "bullets": ["负责 DeepSeek 驱动的简历改写 agent"],
                        }
                    },
                }
                conn.request(
                    "POST",
                    "/resume/api/ai/autofill",
                    json.dumps(ai_payload).encode("utf-8"),
                    {"Content-Type": "application/json"},
                )
                response = conn.getresponse()
                ai_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertIn("authenticity_notice", ai_body["ai"])

                conn.request(
                    "POST",
                    "/resume/api/ai/polish-experience",
                    json.dumps({"context": ai_payload["context"]}).encode("utf-8"),
                    {"Content-Type": "application/json"},
                )
                response = conn.getresponse()
                polish_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertTrue(polish_body["ai"]["requires_confirmation"])
                self.assertIn("负责 DeepSeek 驱动的简历改写 agent", polish_body["ai"]["polished_bullets"])

                conn.request(
                    "POST",
                    "/resume/api/ai/chat",
                    json.dumps({"message": "怎么补充真实性？", "context": ai_payload["context"]}).encode("utf-8"),
                    {"Content-Type": "application/json"},
                )
                response = conn.getresponse()
                chat_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertTrue(chat_body["ai"]["suggestions"])

                conn.request(
                    "POST",
                    "/resume/api/ai/chat/stream",
                    json.dumps({"message": "怎么补充真实性？", "context": ai_payload["context"]}).encode("utf-8"),
                    {"Content-Type": "application/json"},
                )
                response = conn.getresponse()
                stream_lines = [
                    json.loads(line)
                    for line in response.read().decode("utf-8").splitlines()
                    if line.strip()
                ]
                self.assertEqual(response.status, 200)
                self.assertEqual(stream_lines[0]["type"], "start")
                self.assertEqual(stream_lines[-1]["type"], "final")
                self.assertTrue(any(event["type"] == "delta" for event in stream_lines))

                experience_payload = {
                    "user_name": "张三",
                    "category": "project",
                    "title": "增长实验平台",
                    "organization": "实习项目",
                    "bullets": ["分析转化漏斗并定位留存问题"],
                    "skills": ["SQL", "增长"],
                    "metrics": ["转化率提升 18%"],
                }
                conn.request(
                    "POST",
                    "/resume/api/users/zhangsan@example.com/experiences",
                    json.dumps(experience_payload).encode("utf-8"),
                    {"Content-Type": "application/json"},
                )
                response = conn.getresponse()
                experience_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(experience_body["experience"]["title"], "增长实验平台")

                project_payload = {
                    "user_name": "张三",
                    "company_name": "示例科技",
                    "role_title": "增长产品经理",
                    "jd_text": "负责增长分析和用户研究。",
                    "status": "draft",
                    "notes": "第一版",
                }
                conn.request(
                    "POST",
                    "/resume/api/users/zhangsan@example.com/projects",
                    json.dumps(project_payload).encode("utf-8"),
                    {"Content-Type": "application/json"},
                )
                response = conn.getresponse()
                project_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(project_body["project"]["company_name"], "示例科技")

                conn.request("GET", "/resume/api/users/zhangsan@example.com/experiences")
                response = conn.getresponse()
                experiences_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(len(experiences_body["experiences"]), 1)

                conn.request("GET", "/resume/api/users/zhangsan@example.com/projects")
                response = conn.getresponse()
                projects_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(len(projects_body["projects"]), 1)

                payload = {
                    "profile": {
                        "name": "张三",
                        "target_title": "AI 产品经理",
                        "email": "zhangsan@example.com",
                        "skills": ["AI", "LLM", "SQL"],
                        "experiences": [
                            {
                                "title": "AI 简历生成器",
                                "organization": "个人项目",
                                "bullets": ["负责 AI 和 LLM 简历生成"],
                                "skills": ["AI", "LLM"],
                                "metrics": ["效率提升 80%"],
                            }
                        ],
                        "projects": [],
                        "education": [],
                    },
                    "jd_text": "负责 AI 产品、LLM 工作流和 SQL 数据分析。",
                    "target_role": "AI 产品经理",
                }
                headers = {
                    "Content-Type": "application/json",
                    "X-Forwarded-Proto": "https",
                    "X-Forwarded-Host": "example.com",
                    "X-Forwarded-Prefix": "/resume",
                }
                conn.request("POST", "/resume/api/generate", json.dumps(payload).encode("utf-8"), headers)
                response = conn.getresponse()
                body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertIn("resume_markdown", body)
                self.assertEqual(body["content"]["priority"], "content_first")
                self.assertTrue(Path(body["content_report_path"]).exists())
                self.assertEqual(body["proxy"]["proto"], "https")
                self.assertEqual(body["persistence"]["user_id"], "zhangsan@example.com")
                self.assertTrue(Path(body["resume_path"]).exists())

                conn.request("GET", "/resume/api/users/zhangsan@example.com")
                response = conn.getresponse()
                user_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(user_body["user"]["name"], "张三")

                conn.request("GET", "/resume/api/users/zhangsan@example.com/generations")
                response = conn.getresponse()
                history_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(len(history_body["generations"]), 1)
                self.assertIn("resume_markdown", history_body["generations"][0])
            finally:
                server.shutdown()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
