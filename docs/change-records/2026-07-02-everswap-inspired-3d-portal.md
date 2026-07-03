# 2026-07-02 Everswap Inspired 3D Portal

## Original Request

Rebuild the home page in a style similar to the referenced Everswap landing page and generate a matching 3D background image for the resume generator.

## Architecture Snapshot

- `index.html` is the portal-only home page.
- `workspace.html` remains the application workspace for profile, project, AI assistant, and generation flows.
- `styles.css` owns both home portal styling and workspace styling.
- `server.py` serves static files and replaces `__BASE_PATH__` for reverse-proxy compatibility.
- Static images are served from `src/fast_onboarding/web/static/assets`.

## Step Plan

1. Inspect the current portal/workspace split and static serving behavior.
2. Generate an original 3D hero background for the resume generator theme.
3. Store the generated image as a project static asset.
4. Restyle the home page as a full-screen immersive 3D portal with clean navigation and direct workspace links.
5. Make static serving binary-safe so PNG assets work behind the same server.
6. Add regression coverage for base-path CSS image URLs and PNG serving.
7. Run tests and HTTP smoke checks.

## Files Changed

- `src/fast_onboarding/web/static/assets/resume-hero-3d.png`: generated 3D hero background image.
- `src/fast_onboarding/web/static/index.html`: replaced the simple split portal with a full-screen 3D landing composition.
- `src/fast_onboarding/web/static/styles.css`: added dark immersive hero styling, glass navigation, large centered headline, and footer feature strip.
- `src/fast_onboarding/web/static/workspace.html`: aligned the browser title and top brand text with `FastOnboarding`.
- `src/fast_onboarding/web/server.py`: changed static serving to read binary files with `read_bytes()` while keeping text replacement for HTML/CSS/JS.
- `tests/test_web_server.py`: verifies CSS base-path replacement and PNG static asset serving.

## Follow-up Polish

- Replaced the home hero headline with `FastOnboarding`.
- Unified the visible brand name and browser title as `FastOnboarding`.
- Increased the hero wordmark scale, light depth, glow, and glass CTA styling.
- Added compact capability chips under the hero copy: `Evidence-first`, `JD-aware`, and `AI guided`.
- Generated a second hero background, `resume-hero-3d-v2.png`, with clearer 3D depth, brighter landscape detail, and a calmer center band for the wordmark.
- Adjusted the `FastOnboarding` wordmark so it no longer overflows the viewport, using fixed responsive breakpoints instead of an oversized viewport-scaled heading.
- Reduced the dark overlay strength and softened the bottom feature strip so the image remains visible.
- Moved the home hero image from a stacked `background` declaration into an independent `::before` layer, with the readability overlay moved to a lightweight `::after` layer. This prevents the frontend gradients from flattening the background into a near-solid color.
- Reduced the wordmark size again so the background remains visible around the brand text.

## Verification

- `python3 -m unittest discover -s tests`
  - Ran 25 tests.
  - Passed with 1 skipped test.
- HTTP smoke under `/resume` base path:
  - `HEAD /resume/` returned 200.
  - `HEAD /resume/workspace` returned 200.
  - `HEAD /resume/static/assets/resume-hero-3d.png` returned 200 with `Content-Type: image/png`.

## Remaining Notes

- The visual language is inspired by the reference page's immersive 3D landing style, but uses an original resume/career evidence landscape rather than copying the referenced site's artwork.
