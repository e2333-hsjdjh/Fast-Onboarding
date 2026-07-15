"""Stdlib web server for the resume generator UI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import mimetypes
import os
from pathlib import Path
from typing import Any
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from fast_onboarding.core.config import DeepSeekConfig
from fast_onboarding.core.user_database import UserDatabase
from fast_onboarding.integrations.deepseek_client import DeepSeekClient
from fast_onboarding.resume_mvp import MaterialStore, ResumeMVPWorkflow
from fast_onboarding.web.ai_assistant import WorkspaceAIAssistant


@dataclass(frozen=True)
class WebAppConfig:
    host: str = "127.0.0.1"
    port: int = 8787
    base_path: str = ""
    output_dir: str = "workspace/web-output"
    database_path: str = "data/fast_onboarding.sqlite3"
    static_dir: Path = Path(__file__).resolve().parent / "static"

    @classmethod
    def from_env(cls) -> "WebAppConfig":
        return cls(
            host=os.getenv("FAST_ONBOARDING_HOST", "127.0.0.1"),
            port=int(os.getenv("FAST_ONBOARDING_PORT", "8787")),
            base_path=normalize_base_path(os.getenv("FAST_ONBOARDING_BASE_PATH", "")),
            output_dir=os.getenv("FAST_ONBOARDING_OUTPUT_DIR", "workspace/web-output"),
            database_path=os.getenv("FAST_ONBOARDING_DATABASE", "data/fast_onboarding.sqlite3"),
        )


def normalize_base_path(value: str) -> str:
    clean = value.strip()
    if not clean or clean == "/":
        return ""
    return "/" + clean.strip("/")


def create_handler(config: WebAppConfig) -> type[BaseHTTPRequestHandler]:
    class ResumeWebHandler(BaseHTTPRequestHandler):
        server_version = "FastOnboardingWeb/0.1"

        def do_GET(self) -> None:
            route = self._route_path()
            if route == "/api/health":
                self._send_json({"status": "ok", "base_path": config.base_path})
                return
            if route == "/api/material-templates":
                self._send_json({"templates": UserDatabase(config.database_path).list_material_templates()})
                return
            if route.startswith("/api/auth/session/"):
                token = unquote(route.removeprefix("/api/auth/session/"))
                user = UserDatabase(config.database_path).get_session_user(token)
                if not user:
                    self._send_json({"error": "session_expired"}, status=401)
                    return
                self._send_json({"user": user})
                return
            if route.startswith("/api/users/"):
                self._handle_user_get(route)
                return
            if route in {"", "/"}:
                self._send_static("index.html")
                return
            if route in {"/workspace", "/workspace/"}:
                self._send_static("workspace.html")
                return
            if route.startswith("/static/"):
                self._send_static(route.removeprefix("/static/"))
                return
            self._send_json({"error": "not_found"}, status=404)

        def do_HEAD(self) -> None:
            route = self._route_path()
            if route == "/api/health":
                self._send_json({"status": "ok", "base_path": config.base_path}, include_body=False)
                return
            if route in {"", "/"}:
                self._send_static("index.html", include_body=False)
                return
            if route in {"/workspace", "/workspace/"}:
                self._send_static("workspace.html", include_body=False)
                return
            if route.startswith("/static/"):
                self._send_static(route.removeprefix("/static/"), include_body=False)
                return
            self._send_json({"error": "not_found"}, status=404, include_body=False)

        def do_POST(self) -> None:
            route = self._route_path()
            if route.startswith("/api/auth/"):
                self._handle_auth_post(route)
                return
            if route == "/api/generate":
                self._handle_generate()
                return
            if route.startswith("/api/ai/"):
                self._handle_ai_post(route)
                return
            if route.startswith("/api/users/"):
                self._handle_user_post(route)
                return
            self._send_json({"error": "not_found"}, status=404)

        def _handle_generate(self) -> None:
            try:
                payload = self._read_json()
                profile = MaterialStore("data/web-profile.json").from_dict(payload.get("profile", {}))
                jd_text = str(payload.get("jd_text", ""))
                target_role = str(payload.get("target_role", ""))
                requested_user_id = str(payload.get("user_id", "")).strip() or None
                if not profile.name.strip():
                    raise ValueError("profile.name is required")
                if not jd_text.strip():
                    raise ValueError("jd_text is required")
                result = ResumeMVPWorkflow().run(
                    profile=profile,
                    jd_text=jd_text,
                    output_dir=config.output_dir,
                    target_role=target_role,
                )
                resume_markdown = Path(result["resume_path"]).read_text(encoding="utf-8")
                jd_analysis = json.loads(Path(result["analysis_path"]).read_text(encoding="utf-8"))
                persistence = UserDatabase(config.database_path).record_generation(
                    profile=profile,
                    jd_text=jd_text,
                    target_role=target_role or profile.target_title,
                    analysis=jd_analysis,
                    resume_markdown=resume_markdown,
                    ats_report=result["ats"],
                    output_paths={
                        "resume_path": result["resume_path"],
                        "analysis_path": result["analysis_path"],
                        "content_report_path": result["content_report_path"],
                        "ats_report_path": result["ats_report_path"],
                    },
                    user_id=requested_user_id,
                )
                response = {
                    **result,
                    "resume_markdown": resume_markdown,
                    "jd_analysis": jd_analysis,
                    "persistence": persistence,
                    "proxy": self._proxy_context(),
                }
                self._send_json(response)
            except ValueError as exc:
                self._send_json({"error": "bad_request", "message": str(exc)}, status=400)
            except json.JSONDecodeError:
                self._send_json({"error": "bad_json"}, status=400)

        def _handle_auth_post(self, route: str) -> None:
            try:
                payload = self._read_json()
                db = UserDatabase(config.database_path)
                if route == "/api/auth/register":
                    user = db.register_user(
                        name=str(payload.get("name", "")),
                        email=str(payload.get("email", "")),
                        password=str(payload.get("password", "")),
                        target_title=str(payload.get("target_title", "")),
                    )
                    self._send_json({"user": user, "session": db.create_session(user["user_id"])})
                    return
                if route == "/api/auth/login":
                    login = db.login_with_session(
                        identifier=str(payload.get("email", "")),
                        password=str(payload.get("password", "")),
                    )
                    self._send_json(login)
                    return
                if route == "/api/auth/test-session":
                    self._send_json(db.create_test_session())
                    return
                if route == "/api/auth/test-reset":
                    self._send_json(db.reset_test_account())
                    return
                self._send_json({"error": "not_found"}, status=404)
            except ValueError as exc:
                self._send_json({"error": "bad_request", "message": str(exc)}, status=400)
            except json.JSONDecodeError:
                self._send_json({"error": "bad_json"}, status=400)

        def _handle_ai_post(self, route: str) -> None:
            try:
                payload = self._read_json()
                assistant = WorkspaceAIAssistant(self._optional_deepseek_client())
                if route == "/api/ai/autofill":
                    target = str(payload.get("target", "experience"))
                    context = dict(payload.get("context") or {})
                    self._send_json({"ai": assistant.autofill(context, target=target)})
                    return
                if route == "/api/ai/polish-experience":
                    context = dict(payload.get("context") or {})
                    self._send_json({"ai": assistant.polish_experience(context)})
                    return
                if route == "/api/ai/compose-resume":
                    user_id = str(payload.get("user_id") or "").strip()
                    project_id = str(payload.get("project_id") or "").strip()
                    db = UserDatabase(config.database_path)
                    user = db.get_user(user_id)
                    project = db.get_project(user_id, project_id) if user_id and project_id else None
                    if not user:
                        raise ValueError("user_not_found")
                    if not project:
                        raise ValueError("project_not_found")
                    context = {
                        "user": {
                            "user_id": user_id,
                            "name": user.get("name", ""),
                            "email": user.get("email", ""),
                            "phone": user.get("phone", ""),
                            "location": user.get("location", ""),
                            "target_title": user.get("target_title", ""),
                        },
                        "project": project,
                        "saved_experiences": db.list_experiences(user_id),
                        "jd_text": project.get("jd_text", ""),
                        "target_title": project.get("role_title", "") or user.get("target_title", ""),
                        "current_resume_content": project.get("resume_content", {}),
                    }
                    self._send_json({"ai": assistant.compose_resume(context)})
                    return
                if route == "/api/ai/chat/stream":
                    context = dict(payload.get("context") or {})
                    message = str(payload.get("message", ""))
                    self._send_json_stream(assistant.chat_stream(context, message))
                    return
                if route == "/api/ai/chat":
                    context = dict(payload.get("context") or {})
                    message = str(payload.get("message", ""))
                    self._send_json({"ai": assistant.chat(context, message)})
                    return
                self._send_json({"error": "not_found"}, status=404)
            except ValueError as exc:
                self._send_json({"error": "bad_request", "message": str(exc)}, status=400)
            except json.JSONDecodeError:
                self._send_json({"error": "bad_json"}, status=400)

        def _handle_user_post(self, route: str) -> None:
            parts = [part for part in route.split("/") if part]
            if len(parts) < 4:
                self._send_json({"error": "not_found"}, status=404)
                return
            user_id = unquote(parts[2])
            resource = parts[3]
            try:
                payload = self._read_json()
                db = UserDatabase(config.database_path)
                if resource == "experiences":
                    if not str(payload.get("title", "")).strip():
                        raise ValueError("title is required")
                    self._send_json({"experience": db.save_experience(user_id, payload)})
                    return
                if resource == "projects" and len(parts) == 6 and parts[5] == "restore":
                    self._send_json({"project": db.restore_project_version(user_id, parts[4], str(payload.get("version_id", "")))})
                    return
                if resource == "projects":
                    if not str(payload.get("company_name", "")).strip():
                        raise ValueError("company_name is required")
                    if not str(payload.get("role_title", "")).strip():
                        raise ValueError("role_title is required")
                    self._send_json({"project": db.save_project(user_id, payload)})
                    return
                self._send_json({"error": "not_found"}, status=404)
            except ValueError as exc:
                self._send_json({"error": "bad_request", "message": str(exc)}, status=400)
            except json.JSONDecodeError:
                self._send_json({"error": "bad_json"}, status=400)

        def log_message(self, format: str, *args: Any) -> None:
            if os.getenv("FAST_ONBOARDING_ACCESS_LOG", "1") != "0":
                super().log_message(format, *args)

        def _route_path(self) -> str:
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            if config.base_path and path.startswith(config.base_path + "/"):
                path = path[len(config.base_path):]
            elif config.base_path and path == config.base_path:
                path = "/"
            return path or "/"

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            data = json.loads(raw or "{}")
            if not isinstance(data, dict):
                raise ValueError("JSON body must be an object")
            return data

        def _handle_user_get(self, route: str) -> None:
            parts = [part for part in route.split("/") if part]
            if len(parts) < 3:
                self._send_json({"error": "not_found"}, status=404)
                return
            user_id = unquote(parts[2])
            db = UserDatabase(config.database_path)
            if len(parts) == 3:
                user = db.get_user(user_id)
                if not user:
                    self._send_json({"error": "user_not_found"}, status=404)
                    return
                self._send_json({"user": user})
                return
            if len(parts) == 4 and parts[3] == "generations":
                self._send_json({"generations": db.list_generations(user_id)})
                return
            if len(parts) == 4 and parts[3] == "experiences":
                self._send_json({"experiences": db.list_experiences(user_id)})
                return
            if len(parts) == 4 and parts[3] == "projects":
                self._send_json({"projects": db.list_projects(user_id)})
                return
            if len(parts) == 5 and parts[3] == "projects":
                project = db.get_project(user_id, parts[4])
                if not project:
                    self._send_json({"error": "project_not_found"}, status=404)
                    return
                self._send_json({"project": project})
                return
            if len(parts) == 6 and parts[3] == "projects" and parts[5] == "versions":
                self._send_json({"versions": db.list_project_versions(user_id, parts[4])})
                return
            self._send_json({"error": "not_found"}, status=404)

        def _send_json(self, payload: dict[str, Any], *, status: int = 200, include_body: bool = True) -> None:
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if include_body:
                self.wfile.write(body)

        def _send_json_stream(self, events) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            for event in events:
                line = json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n"
                self.wfile.write(line)
                self.wfile.flush()

        def _send_static(self, relative_path: str, *, include_body: bool = True) -> None:
            safe = Path(relative_path)
            if safe.is_absolute() or ".." in safe.parts:
                self._send_json({"error": "invalid_path"}, status=400)
                return
            path = config.static_dir / safe
            if not path.exists() or not path.is_file():
                self._send_json({"error": "not_found"}, status=404)
                return
            content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            if path.suffix in {".html", ".css", ".js"}:
                text = path.read_text(encoding="utf-8")
                text = text.replace("__BASE_PATH__", config.base_path)
                body = text.encode("utf-8")
                content_type += "; charset=utf-8"
            else:
                body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if include_body:
                self.wfile.write(body)

        def _proxy_context(self) -> dict[str, str]:
            return {
                "proto": self.headers.get("X-Forwarded-Proto", ""),
                "host": self.headers.get("X-Forwarded-Host", self.headers.get("Host", "")),
                "prefix": self.headers.get("X-Forwarded-Prefix", config.base_path),
            }

        def _optional_deepseek_client(self) -> DeepSeekClient | None:
            try:
                return DeepSeekClient(DeepSeekConfig.from_env())
            except RuntimeError:
                return None

    return ResumeWebHandler


def run_server(config: WebAppConfig | None = None) -> None:
    active = config or WebAppConfig.from_env()
    server = ThreadingHTTPServer((active.host, active.port), create_handler(active))
    print(f"Fast Onboarding Web UI listening on http://{active.host}:{active.port}{active.base_path or '/'}")
    server.serve_forever()
