# Portal Workspace and Application Projects

## Request

用户希望 UI 进一步美化，借鉴 Dify 的门户与后续工作区结构；当前先在工作区实现两个功能：用户可以录入个人经历，并且可以像做项目一样把一个公司的一个岗位设定为一个项目；一个用户之下可以有多个项目，并同步更改数据库构建。

## Architecture Snapshot

- Entry points: `scripts/serve_web.py` and `fast_onboarding.cli.web` start the stdlib Web server.
- Relevant modules: `src/fast_onboarding/web/server.py` owns JSON API and static delivery; `src/fast_onboarding/core/user_database.py` owns SQLite persistence; `src/fast_onboarding/web/static/*` owns the no-build frontend.
- Data/control flow: browser saves experiences/projects through `/api/users/{user_id}/...`; generation still flows through `/api/generate`, `ResumeMVPWorkflow`, and persisted generation history.
- Dependencies or integration points: nginx subpath support remains through `base_path`; frontend uses native HTML/CSS/JS only.
- Risks or unknowns: project-specific generation history is not yet linked by `project_id`; current generation history is still user-level.

## Execution Plan

1. Add durable SQLite tables for user experiences and application projects.
2. Add API endpoints to create and list experiences/projects under a user.
3. Rework UI into a simple portal plus practical workspace.
4. Wire frontend state so saved experiences feed resume generation and projects sync JD/role inputs.
5. Update tests, README, and run smoke verification.

## Changes Applied

- `src/fast_onboarding/core/user_database.py`: added `user_experiences` and `application_projects` tables plus save/list methods.
- `src/fast_onboarding/web/server.py`: added `POST/GET /api/users/{user_id}/experiences` and `POST/GET /api/users/{user_id}/projects`.
- `src/fast_onboarding/web/static/index.html`: rebuilt the UI as a portal plus workspace with personal experience library, company-role projects, and result panel.
- `src/fast_onboarding/web/static/styles.css`: replaced the previous three-column panel styling with a cleaner portal/workspace visual system.
- `src/fast_onboarding/web/static/app.js`: added save/load logic for experiences and projects; generation now uses saved experience records.
- `tests/test_user_database.py`: added persistence coverage for experiences and application projects.
- `tests/test_web_server.py`: added API coverage for saving/listing experiences and projects.
- `README.md`: documented new tables, APIs, and UI structure.

## Verification

- `python3 -m unittest discover -s tests`
- Result: 17 tests passed, 1 existing local socket-related test skipped.
- Started local server at `http://127.0.0.1:8791/resume` and verified:
  - `GET /resume/api/health`
  - `HEAD /resume/`
  - `POST /resume/api/users/smoke@example.com/experiences`
  - `POST /resume/api/users/smoke@example.com/projects`
  - `POST /resume/api/generate`

## Remaining Risks

- Application projects do not yet own their own generation history or selected resume version. The next database step should link `resume_generations` to `project_id`.
