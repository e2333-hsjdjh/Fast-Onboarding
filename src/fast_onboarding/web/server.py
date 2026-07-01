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

from fast_onboarding.core.user_database import UserDatabase
from fast_onboarding.resume_mvp import MaterialStore, ResumeMVPWorkflow


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
            if route.startswith("/api/users/"):
                self._handle_user_get(route)
                return
            if route in {"", "/"}:
                self._send_static("index.html")
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
            if route.startswith("/static/"):
                self._send_static(route.removeprefix("/static/"), include_body=False)
                return
            self._send_json({"error": "not_found"}, status=404, include_body=False)

        def do_POST(self) -> None:
            route = self._route_path()
            if route != "/api/generate":
                self._send_json({"error": "not_found"}, status=404)
                return
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

        def _send_static(self, relative_path: str, *, include_body: bool = True) -> None:
            safe = Path(relative_path)
            if safe.is_absolute() or ".." in safe.parts:
                self._send_json({"error": "invalid_path"}, status=400)
                return
            path = config.static_dir / safe
            if not path.exists() or not path.is_file():
                self._send_json({"error": "not_found"}, status=404)
                return
            text = path.read_text(encoding="utf-8")
            text = text.replace("__BASE_PATH__", config.base_path)
            body = text.encode("utf-8")
            content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            if path.suffix in {".html", ".css", ".js"}:
                content_type += "; charset=utf-8"
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

    return ResumeWebHandler


def run_server(config: WebAppConfig | None = None) -> None:
    active = config or WebAppConfig.from_env()
    server = ThreadingHTTPServer((active.host, active.port), create_handler(active))
    print(f"Fast Onboarding Web UI listening on http://{active.host}:{active.port}{active.base_path or '/'}")
    server.serve_forever()
