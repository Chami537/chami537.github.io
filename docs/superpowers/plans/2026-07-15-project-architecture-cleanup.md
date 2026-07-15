# Project Architecture Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the confirmed storage cycle, consolidate photo persistence, expose a public essay workflow boundary, share duplicate code rendering, and delete proven dead wrappers while preserving behavior.

**Architecture:** Storage primitives remain dependency-free and are composed with the project `STORE` in a higher-level repository factory. Route modules depend on repository/workflow objects rather than JSON filenames or private SSG helpers, while browser pages share one code-highlighting implementation.

**Tech Stack:** Python 3.11, Flask, JSON repositories, pytest architecture contracts, plain JavaScript, Jinja2 templates, Node.js syntax checks.

## Global Constraints

- Begin only after the safety/reliability plan passes its phase verification.
- Preserve `backend.data.load_json` and `backend.data.atomic_write_json` as compatibility seams.
- Do not change JSON schemas, route URLs, success response bodies, or admin/public visual behavior.
- Remove code only after a full-repository reference check and a guarding test.
- Do not add dependencies.

---

### Task 1: Acyclic Storage Composition Root

**Files:**
- Modify: `backend/storage/repository.py`
- Modify: `backend/storage/__init__.py`
- Create: `backend/repositories.py`
- Modify: `backend/essay_repository.py`
- Modify: `backend/routes/essay_context.py`
- Modify: `backend/routes/photo_context.py`
- Modify: `backend/ssg.py`
- Modify: `tests/test_storage.py`
- Modify: `tests/test_architecture.py`

**Interfaces:**
- Produces: `JsonRepository(filename, store)` with an explicit store dependency.
- Produces: `backend.repositories.repository_for(filename) -> JsonRepository`, composed with `backend.data.STORE`.
- Produces: `EssayRepository(store)` with an explicit store dependency.

- [ ] **Step 1: Add dependency-direction contracts**

Assert `backend/storage/repository.py` contains no `backend.data` import, `backend/storage/__init__.py` exports no project-specific factory, and `backend/repositories.py` is the only module that combines `STORE` with `JsonRepository`. Extend storage unit tests to instantiate repositories with a temporary `JsonStore`.

- [ ] **Step 2: Verify the architecture contract fails**

Run: `python -m pytest tests/test_storage.py tests/test_architecture.py -v`

Expected: FAIL because `JsonRepository` currently imports `backend.data` lazily and the factory lives in the primitive package.

- [ ] **Step 3: Make repository dependencies explicit**

Change the constructor to:

```python
class JsonRepository:
    def __init__(self, filename, store):
        self.filename = filename
        self.store = store
```

Move the factory to `backend/repositories.py`:

```python
from backend.data import STORE
from backend.storage import JsonRepository

def repository_for(filename):
    return JsonRepository(filename, STORE)
```

Require `EssayRepository(store)` and pass `STORE` explicitly from `essay_context.py` and `ssg.py`. Update photo and SSG imports to use `backend.repositories`.

- [ ] **Step 4: Run storage and architecture tests**

Run: `python -m pytest tests/test_storage.py tests/test_architecture.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add -- backend/storage/repository.py backend/storage/__init__.py backend/repositories.py backend/essay_repository.py backend/routes/essay_context.py backend/routes/photo_context.py backend/ssg.py tests/test_storage.py tests/test_architecture.py
git commit -m "refactor: make storage composition acyclic"
```

### Task 2: Single Photo Metadata Repository

**Files:**
- Create: `backend/photo_repository.py`
- Modify: `backend/routes/photo_context.py`
- Modify: `backend/routes/photo_files.py`
- Modify: `backend/routes/photo_details.py`
- Modify: `backend/routes/photo_stories.py`
- Modify: `tools/process_images.py`
- Create: `tests/test_photo_repository.py`
- Modify: `tests/test_architecture.py`

**Interfaces:**
- Produces: `PhotoRepository(store, lock=None)`.
- Produces: `list() -> list[dict]`, `save(photos) -> None`, `find(filename) -> tuple[dict | None, list]`, `append(entry) -> None`, and `replace_preserving(new_data) -> set[str]`.
- Produces: `PHOTO_REPOSITORY` in `photo_context.py`; all `photos.json` access goes through this object.

- [ ] **Step 1: Add repository behavior tests**

Use a temporary `JsonStore` to assert `find` returns the matching object and collection, concurrent-safe `append` retains both entries, and `replace_preserving` returns lost filenames without writing. Assert successful replacement writes the exact requested order.

- [ ] **Step 2: Add a single-owner architecture contract**

Scan `backend/routes/photo_*.py` and `tools/process_images.py`; assert they do not contain `load_json('photos.json')`, `atomic_write_json('photos.json'`, or `repository_for('photos.json')`. Assert `photo_context.py` constructs `PHOTO_REPOSITORY` and callers use its public methods.

- [ ] **Step 3: Verify the tests fail**

Run: `python -m pytest tests/test_photo_repository.py tests/test_architecture.py -v`

Expected: FAIL because four independent read-modify-write paths still own the file.

- [ ] **Step 4: Implement and adopt `PhotoRepository`**

The repository wraps `store.read('photos.json')` and `store.write('photos.json', value)`. Its lock guards compound read-modify-write methods. Update listing, reorder, upload, delete, tags, date, GPS, story validation, and the sync tool to use this object. Keep image-file creation/deletion in `photo_files.py` and EXIF extraction in `process_images.py`.

- [ ] **Step 5: Run photo tests**

Run: `python -m pytest tests/test_photo_repository.py tests/test_process_images.py tests/test_routes.py tests/test_coverage.py -k 'photo' -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add -- backend/photo_repository.py backend/routes/photo_context.py backend/routes/photo_files.py backend/routes/photo_details.py backend/routes/photo_stories.py tools/process_images.py tests/test_photo_repository.py tests/test_architecture.py
git commit -m "refactor: centralize photo metadata ownership"
```

### Task 3: Public Essay Workflow Boundary

**Files:**
- Create: `backend/essay_workflow.py`
- Modify: `backend/routes/essay_context.py`
- Modify: `backend/routes/essay_catalog.py`
- Modify: `backend/routes/essay_metadata.py`
- Modify: `backend/routes/essay_content.py`
- Modify: `backend/ssg.py`
- Modify: `tests/test_essay_service.py`
- Modify: `tests/test_architecture.py`

**Interfaces:**
- Produces: `EssayWorkflow`, constructed with repository, password functions, renderer callback, feed callback, date parser, read-time calculator, and source directories.
- Produces: public methods `create`, `update_metadata`, `delete`, `update_content`, `change_password`, `sync`, and `regenerate_feeds`.
- Produces: `ESSAY_WORKFLOW` in `essay_context.py`.

- [ ] **Step 1: Add workflow and architecture tests**

Use an in-memory repository and temporary Markdown/HTML directories to test metadata update with slug/password migration, deletion, content update, and callback ordering. Add an architecture assertion that `backend/routes/essay_*.py` contains no `from backend.ssg import` and no identifiers beginning `_sync_essay`, `_generate_feeds`, `_calc_read_time`, or `_parse_date`.

- [ ] **Step 2: Verify workflow tests fail**

Run: `python -m pytest tests/test_essay_service.py tests/test_architecture.py -v`

Expected: FAIL because route modules directly import private SSG helpers.

- [ ] **Step 3: Implement the orchestration boundary**

Move cross-file ordering and rollback behavior out of route functions into `EssayWorkflow`. Routes retain request validation and JSON/status conversion, then call the workflow. Expose public SSG callbacks named `parse_date`, `calculate_read_time`, `sync_essay_html`, and `generate_feeds`; internal SSG generation remains in `ssg.py`.

The workflow validates every transition before saving metadata, performs password/source migration before rendering, and restores the previous metadata/password state if a later file operation raises.

- [ ] **Step 4: Run essay behavior tests**

Run: `python -m pytest tests/test_essay_service.py tests/test_routes.py tests/test_ssg.py -k 'essay or feed or password or markdown' -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add -- backend/essay_workflow.py backend/routes/essay_context.py backend/routes/essay_catalog.py backend/routes/essay_metadata.py backend/routes/essay_content.py backend/ssg.py tests/test_essay_service.py tests/test_architecture.py
git commit -m "refactor: isolate essay application workflows"
```

### Task 4: Shared Browser Code Rendering

**Files:**
- Create: `assets/js/code-rendering.js`
- Modify: `assets/js/admin-editor-rendering.js`
- Modify: `assets/js/essay-code.js`
- Modify: `admin.html`
- Modify: `templates/essay.html`
- Modify: `backend/asset_cache.py`
- Modify: `tests/test_architecture.py`
- Modify: `tests/test_browser_smoke.py`

**Interfaces:**
- Produces: global `highlightCodeBlocks(el)` with `attachCodeLanguageButton`, `escapeCodeHtml`, `fallbackHighlightCodeBlock`, and `highlightPlainCode` private inside an IIFE.
- Consumes: optional `window.hljs`, `navigator.clipboard`, and DOM nodes already used by both pages.

- [ ] **Step 1: Add shared-module contracts**

Assert both HTML entry points load `assets/js/code-rendering.js` before their page-specific renderer and that only the shared module defines `highlightPlainCode` and `fallbackHighlightCodeBlock`. Extend Chromium smoke coverage to render one Python code block in the admin preview and one essay page, checking `.hljs-keyword` and the copy-language button.

- [ ] **Step 2: Verify the architecture contract fails**

Run: `python -m pytest tests/test_architecture.py tests/test_browser_smoke.py -k 'code_rendering or code_block' -v`

Expected: FAIL because the implementation is duplicated and the shared asset is absent.

- [ ] **Step 3: Extract the shared implementation**

Move code-block discovery, language labels, clipboard button, HTML escaping, fallback highlighting, and token regexes into `code-rendering.js`. Export only `window.highlightCodeBlocks`. Leave KaTeX and essay-only Markdown helpers in their original files. Load the shared file before each consumer and let derived cache discovery version it automatically.

- [ ] **Step 4: Run browser and syntax tests**

Run all three files through `node --check`, then run `python -m pytest tests/test_architecture.py tests/test_browser_smoke.py -k 'code_rendering or code_block' -v`.

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add -- assets/js/code-rendering.js assets/js/admin-editor-rendering.js assets/js/essay-code.js admin.html templates/essay.html backend/asset_cache.py tests/test_architecture.py tests/test_browser_smoke.py
git commit -m "refactor: share browser code rendering"
```

### Task 5: Proven Dead-Code Removal

**Files:**
- Modify: `backend/crud.py`
- Modify: `backend/essay_repository.py`
- Modify: `backend/ssg.py`
- Modify: `manage.py`
- Modify: `tests/test_ssg.py`
- Modify: `tests/test_architecture.py`

**Interfaces:**
- Removes: `update_item_by_index`, `delete_item_by_index`, `EssayRepository.find`, `_fetch_stars`, and SSG wrappers whose callers have been migrated to their owning modules.
- Preserves: `backend.data.load_json` and `backend.data.atomic_write_json` compatibility APIs.

- [ ] **Step 1: Lock down absence and direct imports**

Add architecture assertions that the dead definitions are absent. Update SSG tests to import EXIF utilities, feed enrichment, asset cache busting, and GPS writing from their owning modules. Update `manage.py` to do the same.

- [ ] **Step 2: Run the reference search**

Run:

```powershell
rg -n "update_item_by_index|delete_item_by_index|EssayRepository.*find|_fetch_stars|_extract_gps|_extract_exif|_without_camera_model|_set_gps|_strip_enrich|_cache_bust_assets" --glob '*.py'
```

Expected: remaining hits are definitions or tests being updated in this task; no production consumer requires the wrappers.

- [ ] **Step 3: Remove the dead definitions and imports**

Delete only definitions proven unused by Step 2. Replace SSG internal `_strip_enrich` calls with direct `strip_enrich` calls, replace `manage.py` wrapper imports with `cache_bust_assets(BASE_DIR)` and `set_gps`, and remove the unused `fetch_stars` import.

- [ ] **Step 4: Run focused and full tests**

Run: `python -m pytest tests/test_architecture.py tests/test_ssg.py tests/test_storage.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add -- backend/crud.py backend/essay_repository.py backend/ssg.py manage.py tests/test_ssg.py tests/test_architecture.py
git commit -m "refactor: remove obsolete compatibility code"
```

### Task 6: Final Project Verification

**Files:**
- Verify all changed files and generated outputs.

- [ ] **Step 1: Build and run the complete test suite**

Run: `python manage.py build; python -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 2: Force Chromium smoke coverage**

Run: `$env:BROWSER_SMOKE_REQUIRED='1'; python -m pytest tests/test_browser_smoke.py -v`

Expected: PASS with Chromium. Clear `BROWSER_SMOKE_REQUIRED` afterward.

- [ ] **Step 3: Run static checks**

Run every JavaScript file beneath `assets/js` through `node --check`, run `python -m compileall -q backend tools manage.py`, then run `git diff --check`.

Expected: all exit with code 0.

- [ ] **Step 4: Refresh the project graph**

Run: `graphify update .`

Expected: the graph completes against the final HEAD/worktree; record node/edge totals and any warnings.

- [ ] **Step 5: Review generated noise and repository status**

Inspect `git status --short`, `git diff --stat`, and generated cache/JSON diffs. Revert only unrelated generated timestamp or remote-star noise introduced by verification; retain source, test, workflow, documentation, and deliberately changed build references.

- [ ] **Step 6: Produce the final audit summary**

Report fixed defects, architecture boundaries changed, exact verification results, remaining known risks, and commits created. Do not push or deploy without a separate user instruction.
