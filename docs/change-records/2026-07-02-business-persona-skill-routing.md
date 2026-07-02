# Business Persona Skill Routing

## Request

用户希望为聊天助手搭载 `tmstack/awesome-persona-skills` 中商业思维相关 skill，并在不同领域自动识别、找到合适 skill。

## Architecture Snapshot

- Entry points: `WorkspaceAIAssistant.chat()` and `chat_stream()` power the AI assistant.
- Relevant modules: `src/fast_onboarding/web/ai_assistant.py` owns authenticity-first coaching; `src/fast_onboarding/web/persona_skills.py` now owns persona skill metadata and routing.
- Data/control flow: frontend sends workspace context and message; backend selects business persona skills from the context; AI response includes `selected_skills` for UI display.
- Dependencies or integration points: source inspiration is the `tmstack/awesome-persona-skills` README business-thinking category. The app stores a stable local metadata index rather than pulling external repos at runtime.
- Risks or unknowns: persona skill metadata is manually curated from the public list and should be refreshed when the upstream list changes.

## Execution Plan

1. Inspect the upstream awesome-persona-skills business-thinking list.
2. Create a local business persona skill registry and keyword router.
3. Inject selected skills into AI chat prompts and fallback suggestions.
4. Display matched skills in the AI assistant UI.
5. Add tests and documentation.

## Changes Applied

- `src/fast_onboarding/web/persona_skills.py`: added local metadata for business-thinking skills and a keyword-based router.
- `src/fast_onboarding/web/ai_assistant.py`: selected persona skills for chat and included them in prompts, fallback suggestions, stream final payloads, and normal chat payloads.
- `src/fast_onboarding/web/static/index.html`: added matched skill display area.
- `src/fast_onboarding/web/static/app.js`: renders selected persona skills as chips.
- `tests/test_persona_skills.py`: added routing tests for growth/product and engineering/automation contexts.
- `tests/test_ai_assistant.py`: asserted chat responses expose selected skills.
- `README.md`: documented the business persona skill routing and authenticity boundary.

## Verification

- `python3 -m unittest discover -s tests`
- Result: 24 tests passed, 1 existing local socket-related test skipped.

## Remaining Risks

- Future work can add a background updater or import pipeline for upstream skill metadata, but runtime behavior should remain pinned and testable.
