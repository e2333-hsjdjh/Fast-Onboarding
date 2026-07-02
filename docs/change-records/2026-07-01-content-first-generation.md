# Content-First Resume Generation

## Request

用户更新总体需求：简历生成的内容优先级大于格式，生成器应先把内容做好，再考虑格式问题，因此内容生成逻辑需要进一步适配。

## Architecture Snapshot

- Entry points: `ResumeMVPWorkflow.run()` drives JD analysis, resume generation, ATS checking, and output file writing.
- Relevant modules: `src/fast_onboarding/resume_mvp.py` owns JD parsing, material selection, Markdown generation, ATS checking, and now content quality checking.
- Data/control flow: profile + JD are analyzed into `JDAnalysis`; `ResumeGenerator` selects and orders experiences; reports are written to `resume.md`, `jd_analysis.json`, `ats_report.json`, and `content_report.json`.
- Dependencies or integration points: Web API in `src/fast_onboarding/web/server.py` persists generation output paths and returns workflow results to the frontend.
- Risks or unknowns: the current scoring is rule-based when DeepSeek is not injected, so future model-backed generation should use the same content-first principle in prompts and validation.

## Execution Plan

1. Inspect the current MVP generation flow and tests.
2. Reweight resume material selection around required keywords, JD pain points, responsibilities, metrics, and evidence.
3. Add a content quality report separate from ATS and formatting checks.
4. Surface the content report through Web API and UI.
5. Update README and tests to lock in the content-first product principle.

## Changes Applied

- `src/fast_onboarding/resume_mvp.py`: added weighted content-first scoring, stronger DeepSeek prompt guidance, pain-point-aware summary text, and `ContentQualityChecker`.
- `src/fast_onboarding/resume_mvp.py`: `ResumeMVPWorkflow` now writes and returns `content_report.json`.
- `src/fast_onboarding/web/server.py`: persisted `content_report_path` with generation output paths.
- `src/fast_onboarding/web/static/index.html`: added content score and content gap display.
- `src/fast_onboarding/web/static/app.js`: renders content score and content gaps from API results.
- `tests/test_resume_mvp.py`: added tests for content-first selection and content gap reporting.
- `tests/test_web_server.py`: asserted that the Web API returns the content report.
- `README.md`: documented content-first as the system principle and added `content_report.json`.

## Verification

- `python3 -m unittest discover -s tests`
- Result: 16 tests passed, 1 existing local socket-related test skipped.

## Remaining Risks

- The content score is a rule-based heuristic in local/offline mode. DeepSeek-backed generation should later return structured evidence mapping so content quality can be audited more precisely.
