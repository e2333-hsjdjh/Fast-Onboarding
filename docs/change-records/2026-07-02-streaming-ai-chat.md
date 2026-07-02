# Streaming AI Chat

## Request

用户希望 AI 助手“最好做成流式输入”。结合当前 AI 助手场景，本次实现为 AI 聊天回复的流式显示，同时继续保持真实性约束。

## Architecture Snapshot

- Entry points: `src/fast_onboarding/web/server.py` handles AI JSON APIs; `src/fast_onboarding/web/static/app.js` controls frontend AI interactions.
- Relevant modules: `src/fast_onboarding/web/ai_assistant.py` owns AI coaching logic and now emits stream events.
- Data/control flow: frontend calls `/api/ai/chat/stream`; backend returns newline-delimited JSON events: `start`, multiple `delta`, and `final`.
- Dependencies or integration points: DeepSeek remains optional; if unavailable or failing, local authenticity checks still stream a response.
- Risks or unknowns: DeepSeek may return unsafe example text, so model output is sanitized before final suggestions are shown.

## Execution Plan

1. Add a stream event generator to the AI assistant.
2. Add a streaming Web API endpoint using NDJSON.
3. Update the frontend to read `ReadableStream` chunks and append text incrementally.
4. Preserve fallback to the existing non-streaming endpoint.
5. Add tests and smoke verify local HTTP output.

## Changes Applied

- `src/fast_onboarding/web/ai_assistant.py`: added `chat_stream()` and truth-safety sanitization for invented examples or unseen numbers.
- `src/fast_onboarding/web/server.py`: added `POST /api/ai/chat/stream` with `application/x-ndjson` streaming response.
- `src/fast_onboarding/web/static/app.js`: updated AI review to stream reply chunks and render final structured suggestions.
- `tests/test_ai_assistant.py`: added stream event tests and sanitization coverage.
- `tests/test_web_server.py`: added HTTP stream endpoint coverage.
- `README.md`: documented the streaming AI chat endpoint.

## Verification

- `python3 -m unittest discover -s tests`
- Result: 22 tests passed, 1 existing local socket-related test skipped.
- Local smoke test:
  - `POST /resume/api/ai/chat/stream`
  - Confirmed NDJSON events include `start`, `delta`, and `final`.
  - Confirmed invented example percentages are replaced with authenticity-safe guidance.

## Remaining Risks

- Browser-level tests should be added later to verify chunk-by-chunk rendering in the real UI.
