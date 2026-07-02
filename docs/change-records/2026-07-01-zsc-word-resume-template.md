# ZSC Word Resume Template

## Request

按照用户提供的 `/Users/zzzzzz/Desktop/朱思潮-简历.docx` 制作一份可复用的简历模板。

## Architecture Snapshot

- Entry points: `fast_onboarding.documents.ResumeWordAgent` renders DOCX templates through placeholder replacement.
- Relevant modules: `src/fast_onboarding/documents/resume_word_agent.py` owns template registry and Word replacement behavior; `tests/test_resume_word_agent.py` verifies the document flow.
- Data/control flow: a template is registered in `TemplateRegistry`, `ResumeWordAgent.render()` builds replacements from `resume_facts`, and `DocxEditor.replace_text()` writes a rendered DOCX.
- Dependencies or integration points: Word template assets are packaged through `pyproject.toml`; visual QA uses the documents skill `render_docx.py`.
- Risks or unknowns: the provided source resume is a dense table-layout DOCX, so long generated content may require per-role pruning to remain one page.

## Execution Plan

1. Inspect the source DOCX structure and identify its table layout, sections, and content fields.
2. Create a committed built-in DOCX template with stable placeholders and no source personal content.
3. Add built-in template registration helpers and package-data configuration.
4. Add tests for built-in template registration and rendering.
5. Render the DOCX to page images and inspect layout quality.

## Changes Applied

- `src/fast_onboarding/documents/templates/zsc_table_resume.docx`: added the Word template derived from the provided resume, with personal content replaced by placeholders.
- `src/fast_onboarding/documents/resume_word_agent.py`: added built-in template metadata, path helper, and registration helper.
- `src/fast_onboarding/documents/__init__.py`: exported the built-in template helpers.
- `pyproject.toml`: included packaged DOCX templates in package data.
- `tests/test_resume_word_agent.py`: added coverage for registering and rendering the built-in template.
- `README.md`: documented the new Word template and example usage.

## Verification

- `python3 -m unittest discover -s tests`
- Result: 14 tests passed, 1 existing socket-related test skipped.
- Rendered `src/fast_onboarding/documents/templates/zsc_table_resume.docx` with `render_docx.py --emit_pdf`.
- Inspected rendered page PNGs. The template opens cleanly, has no source personal content residue, and has readable sections without text overlap.

## Remaining Risks

- The placeholder template renders as two pages because it exposes every optional experience and skill section. A future role-specific export step should omit empty or low-relevance optional rows when a strict one-page resume is required.
