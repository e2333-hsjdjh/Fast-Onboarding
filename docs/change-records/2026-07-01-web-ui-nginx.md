# Web UI Nginx Compatibility

## Request

开发一个可以在网站上跑起来的简历生成器 UI，并且原生兼容用户服务器上的 nginx 反向代理。

## Architecture Snapshot

- Entry points: 之前只有 CLI `scripts/resume_mvp.py` 和包内 `fast_onboarding.cli.resume_mvp`。
- Relevant modules: `fast_onboarding.resume_mvp` 提供 profile + JD 到简历和 ATS 报告的核心 workflow。
- Data/control flow: CLI 读取本地 JSON/JD 文件，调用 workflow，输出 Markdown 和 JSON 文件。
- Dependencies or integration points: 项目以标准库为主，没有前端构建工具或 Web 框架依赖。
- Risks or unknowns: 服务器使用 nginx 反向代理，UI 不能假设部署在根路径 `/`。

## Execution Plan

1. 新增标准库 HTTP server，提供静态页面和 JSON API。
2. 新增无构建前端工作台，支持输入素材、JD 并展示简历和 ATS 报告。
3. 支持 `--base-path`，兼容 nginx 子路径反代。
4. 读取 `X-Forwarded-*` 请求头，为代理部署保留外部上下文。
5. 新增 nginx 示例配置、README 部署说明和 Web API 测试。

## Changes Applied

- `src/fast_onboarding/web/server.py`: 新增 stdlib Web server、静态资源服务、`/api/health` 和 `/api/generate`。
- `src/fast_onboarding/web/static/`: 新增 HTML/CSS/JS 工作台。
- `src/fast_onboarding/cli/web.py`: 新增 Web UI 包内启动入口。
- `scripts/serve_web.py`: 新增本地/部署兼容启动脚本。
- `deploy/nginx/fast-onboarding.conf`: 新增 nginx 反向代理示例。
- `README.md`: 新增 Web UI、nginx 反代和项目结构说明。
- `tests/test_web_server.py`: 覆盖 base path、健康检查、生成 API 和代理头。
- `pyproject.toml`: 新增 `fast-onboarding-web` console script。

## Verification

- 已运行：`python3 -m unittest discover -s tests`
- 结果：12 个测试通过，1 个 socket 绑定测试在沙箱环境中按预期跳过。
- 已运行：`python3 scripts/serve_web.py --host 127.0.0.1 --port 8791 --base-path /resume`
- 已请求：`GET /resume/api/health`
- 结果：返回 `{"status":"ok","base_path":"/resume"}`。
- 已请求：`HEAD /resume/` 和 `HEAD /resume/static/app.js`
- 结果：均返回 200，页面和静态资源可在 nginx 子路径模式访问。
- 已请求：`POST /resume/api/generate`，携带 `X-Forwarded-Proto`、`X-Forwarded-Host`、`X-Forwarded-Prefix`
- 结果：成功生成简历、JD 分析和 ATS 报告，并返回代理上下文。

## Remaining Risks

- 当前 Web UI 是单页 MVP，尚未加入登录、用户隔离、CSRF 防护和生产级鉴权。
- 生产部署时应由 nginx 负责 HTTPS、访问控制、请求大小限制和日志轮转。
