# 2026-07-02 Home Portal Workspace Route

## Original Request

The workspace form area should not appear on the home page. The home page should only provide a simple product introduction and navigation into the workspace.

## Architecture Snapshot

- `server.py` owns HTTP routing, static file serving, base path normalization, and Nginx-friendly `__BASE_PATH__` replacement.
- `index.html` previously contained both the portal hero and the full workspace shell.
- `app.js` owns workspace-only behavior: page switching, persistence requests, AI autofill/chat, and resume generation.
- `styles.css` owns both portal and workspace layouts.

## Step Plan

1. Split the existing combined static page into a portal-only home page and a workspace page.
2. Add a `/workspace` route that serves the workspace shell while preserving reverse-proxy base path support.
3. Keep workspace tab switching internal, without hash routing.
4. Update regression tests so `/` is portal-only and `/workspace` contains the form workspace.
5. Run the unit test suite.

## Files Changed

- `src/fast_onboarding/web/static/index.html`: now contains only the portal introduction and workspace navigation links.
- `src/fast_onboarding/web/static/workspace.html`: new workspace entry page containing the previous form, AI, project, and results UI.
- `src/fast_onboarding/web/server.py`: serves `/workspace` and `/workspace/` as the workspace page.
- `src/fast_onboarding/web/static/styles.css`: adds portal action styling and compact workspace header styling.
- `tests/test_web_server.py`: verifies the home page does not include workspace forms and the workspace route still exposes all workspace pages.

## Verification

- `python3 -m unittest discover -s tests`
  - Ran 25 tests.
  - Passed with 1 skipped test.

## Remaining Notes

- The workspace remains a static multi-tab shell under `/workspace`; future deeper routes such as `/workspace/profile` can be added if browser history per tab becomes necessary.
