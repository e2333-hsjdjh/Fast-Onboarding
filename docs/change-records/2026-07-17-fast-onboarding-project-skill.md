# FastOnboarding Project Skill

## Request

为后续不同会话的持续开发创建项目 Skill，明确各子功能的位置、规范与未完成边界；信息不足时才重新归档。

## Architecture Snapshot

- 项目已按 Web、AI、SQLite、生成/导出和行业情报模块分层，现有文件职责清晰。
- 功能定位主要集中在 `src/fast_onboarding/web`、`core/user_database.py`、`resume_mvp.py`、`documents` 和 `intelligence`。

## Changes Applied

- 在 `~/.codex/skills/fast-onboarding-project` 创建可自动发现的项目 Skill。
- Skill 提供最小工作流，引用按需加载的功能地图和数据/API 契约。
- 明确真实性优先、用户数据隔离、nginx 子路径、响应式 UI、版本保存、测试和自动 Git 提交规范。

## Verification

- `quick_validate.py` 已通过。
- `agents/openai.yaml` 已生成，未来会话可通过 `$fast-onboarding-project` 使用。

## Remaining Risks

- Skill 位于用户级 Codex Skills 目录，不随当前仓库 Git 推送；仓库内保留本次变更记录和 CSV 索引。
