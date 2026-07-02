# Authentic AI Assistant

## Request

用户希望在经历细化流程中加入 AI：AI 可以根据用户已经输入的内容自动化填写板块，也可以作为聊天机器人读取用户输入后提出改进意见或指导填写。用户特别强调真实性。

## Architecture Snapshot

- Entry points: `src/fast_onboarding/web/server.py` serves JSON APIs and static UI.
- Relevant modules: `src/fast_onboarding/web/ai_assistant.py` owns AI autofill and coaching; `DeepSeekClient` provides optional model integration.
- Data/control flow: frontend collects current workspace context, calls `/api/ai/autofill` or `/api/ai/chat`, then displays suggestions or fills form fields. AI suggestions are not persisted until the user explicitly saves the form.
- Dependencies or integration points: DeepSeek is used when `DEEPSEEK_API_KEY` is configured; otherwise the assistant falls back to local authenticity checks and questions.
- Risks or unknowns: model responses may vary, so API normalizes list-like fields and falls back to local logic on model errors.

## Execution Plan

1. Add an authenticity-first AI assistant service.
2. Add Web API endpoints for autofill and chat coaching.
3. Add AI controls to the workspace UI without silently saving AI output.
4. Add tests for fallback behavior, authenticity wording, and API responses.
5. Update documentation and verify the whole suite.

## Changes Applied

- `src/fast_onboarding/web/ai_assistant.py`: added `WorkspaceAIAssistant` with DeepSeek-backed and fallback autofill/chat modes.
- `src/fast_onboarding/web/server.py`: added `/api/ai/autofill` and `/api/ai/chat`.
- `src/fast_onboarding/web/static/index.html`: added AI assistant page and AI autofill buttons for experiences/projects.
- `src/fast_onboarding/web/static/app.js`: added workspace context collection, AI autofill, AI chat, and safe non-overwriting field application.
- `src/fast_onboarding/web/static/styles.css`: added AI page and assistant output styling.
- `tests/test_ai_assistant.py`: added AI assistant behavior tests.
- `tests/test_web_server.py`: added Web API coverage for AI endpoints and AI page presence.
- `README.md`: documented the authenticity-first AI assistant and APIs.

## Verification

- `python3 -m unittest discover -s tests`
- Result: 20 tests passed, 1 existing local socket-related test skipped.
- Local smoke test verified:
  - `GET /resume/` includes the AI assistant page.
  - `POST /resume/api/ai/autofill`
  - `POST /resume/api/ai/chat`

## Remaining Risks

- Browser-level click tests should be added later to verify AI autofill behavior visually across pages.
- DeepSeek prompts should be expanded into structured evidence mapping before using AI output for high-stakes resume claims.
