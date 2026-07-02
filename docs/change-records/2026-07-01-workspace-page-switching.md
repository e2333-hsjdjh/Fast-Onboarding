# Workspace Page Switching

## Request

用户指出 UI 不应该一个页面全部搞定，需要设置可以切换的页面。

## Architecture Snapshot

- Entry points: `scripts/serve_web.py` serves `src/fast_onboarding/web/static/index.html`, CSS, and JS through the stdlib web server.
- Relevant modules: `index.html` defines the workspace structure; `styles.css` controls visibility and layout; `app.js` owns client-side state and interactions.
- Data/control flow: existing save/load/generate API flows remain unchanged; this change only reorganizes the frontend into page containers.
- Dependencies or integration points: nginx subpath support remains through static replacement of `__BASE_PATH__`.
- Risks or unknowns: no frontend browser automation test exists yet; static and API smoke tests cover server delivery, not click-level UI behavior.

## Execution Plan

1. Convert workspace sections into explicit page containers.
2. Replace sidebar anchor navigation with page-switching controls.
3. Add client-side routing through `data-page` and `data-page-link`.
4. Update CSS so only the active page is visible.
5. Verify tests and local server smoke checks.

## Changes Applied

- `src/fast_onboarding/web/static/index.html`: added four pages: overview, personal experience, company-role projects, and generation results.
- `src/fast_onboarding/web/static/styles.css`: added `.page` visibility states, active navigation styling, and overview page cards.
- `src/fast_onboarding/web/static/app.js`: added page routing, hash handling, and automatic navigation after save/generate actions.
- `tests/test_web_server.py`: added static HTML assertions for all page containers.

## Verification

- `python3 -m unittest discover -s tests`
- Result: 17 tests passed, 1 existing local socket-related test skipped.
- Started local server at `http://127.0.0.1:8791/resume` and verified:
  - `GET /resume/api/health`
  - `GET /resume/`
  - Static HTML includes `data-page="overview"`, `profile`, `projects`, and `results`.

## Remaining Risks

- Add browser-level UI tests later to verify click switching and mobile layout visually.
