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

                conn.request("HEAD", "/resume/")
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                self.assertIn("text/html", response.getheader("Content-Type"))
                response.read()

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
