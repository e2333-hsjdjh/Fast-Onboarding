# User Database

## Request

为用户构建数据库，保存相关的数据。

## Architecture Snapshot

- Entry points: Web UI 通过 `POST /api/generate` 调用 `ResumeMVPWorkflow` 生成简历和 ATS 报告。
- Relevant modules: `fast_onboarding.web.server` 负责 API；`fast_onboarding.resume_mvp` 负责生成逻辑；此前只有文件输出，没有用户级持久化。
- Data/control flow: 浏览器提交用户素材和 JD，后端生成 Markdown/JSON 文件后返回结果。
- Dependencies or integration points: 项目使用标准库为主，适合继续采用 SQLite 避免新增部署依赖。
- Risks or unknowns: 后续生产环境需要权限控制、用户认证和隐私策略。

## Execution Plan

1. 新增 SQLite 用户数据库模块。
2. 建立 `users`、`profile_snapshots`、`job_descriptions`、`resume_generations` 表。
3. 在 Web 生成接口中保存用户、素材快照、JD、简历和 ATS 报告。
4. 新增用户查询和生成历史查询 API。
5. 在前端显示保存后的用户 ID 和最近生成历史。
6. 补充数据库和 Web API 测试。

## Changes Applied

- `src/fast_onboarding/core/user_database.py`: 新增 SQLite 持久化层。
- `src/fast_onboarding/core/__init__.py`: 导出 `UserDatabase`。
- `src/fast_onboarding/web/server.py`: 生成简历时写入数据库，并新增用户/历史查询 API。
- `src/fast_onboarding/cli/web.py`: 新增 `--database` 参数。
- `src/fast_onboarding/web/static/`: 前端新增用户 ID 输入、保存状态和最近生成历史展示。
- `tests/test_user_database.py`: 覆盖用户、JD 和生成历史持久化。
- `tests/test_web_server.py`: 覆盖 Web API 写入和读取用户历史。
- `README.md`: 补充数据库路径、表职责、API 和部署配置说明。

## Verification

- 已运行：`python3 -m unittest discover -s tests`
- 结果：13 个测试通过，1 个 socket 绑定测试在沙箱环境中按预期跳过。

## Remaining Risks

- 当前数据库是单机 SQLite，适合 MVP 和小规模部署。
- 尚未加入登录鉴权、用户隔离策略、加密字段和数据导出/删除接口。
