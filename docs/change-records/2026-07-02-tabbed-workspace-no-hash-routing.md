# 2026-07-02 Tabbed Workspace No Hash Routing

## Request

The workspace should not use URL hash fragments such as `#profile` or `#projects` when switching pages from `http://127.0.0.1:8787/`. Page switching should behave like loading a new workspace tab while keeping the URL clean.

## Architecture

- Keep the existing single-page static workspace shell.
- Use `data-page-link` and `data-page` as the internal tab/page contract.
- Avoid browser hash APIs so the app remains friendly to Nginx reverse proxy paths and clean URLs.

## Changes

- Replaced the portal CTA hash anchor with a button-driven page action.
- Removed `location.hash`, `hashchange`, and `history.replaceState(... #page)` routing from the frontend app script.
- Kept page switching as internal DOM state with active tab/page classes.
- Added regression coverage to ensure static page switching does not reintroduce hash routing.

## Verification

- `python3 -m unittest discover -s tests`
  - Ran 25 tests.
  - Passed with 1 skipped test.
