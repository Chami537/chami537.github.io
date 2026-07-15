# Project Safety and Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the nine reproduced security, data-integrity, cache, API, and CI defects without changing the site's content model or visible workflows.

**Architecture:** Validate and canonicalize data at HTTP/CLI boundaries, escape values for their exact browser context, and fail closed before atomic writes. Keep the current Flask, static JavaScript, JSON storage, and SSG structure intact during this phase.

**Tech Stack:** Python 3.11, Flask, pytest, Pillow, Markdown, plain JavaScript, Node.js syntax checks, Playwright Chromium, GitHub Actions.

## Global Constraints

- Do not add runtime dependencies or a frontend framework.
- Preserve current successful HTTP response shapes and public/admin interaction semantics.
- Add a failing regression test before every behavior change.
- Invalid or corrupted input must not replace an existing valid file.
- Do not modify user-authored content files except temporary fixtures created by tests.

---

### Task 1: Public Rendering and Markdown Link Safety

**Files:**
- Modify: `assets/js/index-core.js`
- Modify: `assets/js/index-photo-gallery.js`
- Modify: `backend/markdown_utils.py`
- Modify: `tests/test_frontend_helpers.py`
- Modify: `tests/test_ssg.py`

**Interfaces:**
- Produces: `htmlEncode(value) -> string`, safe for HTML text and quoted attributes.
- Produces: `inlineJsString(value) -> string`, safe when a legacy inline handler contains a single-quoted string.
- Produces: `render_markdown(md_content) -> str`, with scriptable link schemes rewritten to `#blocked:` after canonicalization.

- [ ] **Step 1: Add executable frontend regressions**

Add a Node/vm test that loads `index-core.js` and `index-photo-gallery.js`, then asserts:

```javascript
assert(context.htmlEncode('" onmouseover="alert(1)')
  .includes('&quot; onmouseover=&quot;'));
assert(!context.renderWork([{title:'X', url:'https://safe.test/" onmouseover="alert(1)'}])
  .includes(' onmouseover='));
assert(context._photoItemHtml({filename:'x.jpg', date:'<img src=x onerror=alert(1)>'})
  .includes('&lt;img'));
```

Also create a minimal fake `document` for `htmlEncode` and the photo story container, and assert a story date containing `<img ...>` is escaped.

- [ ] **Step 2: Verify frontend regressions fail**

Run: `python -m pytest tests/test_frontend_helpers.py -v`

Expected: FAIL because double quotes and photo/story dates are not escaped.

- [ ] **Step 3: Split HTML encoding from inline-JavaScript encoding**

Implement the browser helpers with explicit substitutions:

```javascript
function htmlEncode(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function inlineJsString(value) {
  return htmlEncode(String(value == null ? '' : value)
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'"));
}
```

Use `inlineJsString(t)` only inside photo-tag inline handlers. Continue using `htmlEncode` for text and HTML attributes. Wrap `_photoItemHtml` dates and `renderPhotoStories` dates with `htmlEncode`.

- [ ] **Step 4: Add encoded-scheme Markdown regressions**

Extend `test_render_markdown_blocks_javascript_links` with:

```python
@pytest.mark.parametrize('target', [
    'java&#x73;cript:alert(1)',
    'jav&#97;script:alert(1)',
    'java\tscript:alert(1)',
    'VBSCRIPT:msgbox(1)',
    'data:text/html,<script>alert(1)</script>',
])
def test_render_markdown_blocks_canonicalized_script_schemes(target):
    rendered = render_markdown(f'[unsafe]({target})')
    assert 'javascript:' not in html_mod.unescape(rendered).lower()
    assert '#blocked:' in rendered
```

Import the standard library `html` module under a non-conflicting name in the test.

- [ ] **Step 5: Verify the encoded-scheme regression fails**

Run: `python -m pytest tests/test_ssg.py -k 'markdown_blocks' -v`

Expected: FAIL for at least `java&#x73;cript:`.

- [ ] **Step 6: Canonicalize every rendered href before scheme validation**

In `backend/markdown_utils.py`, add a callback used by an `href` attribute regex. The callback must `html.unescape` the value, remove ASCII whitespace/control characters for protocol comparison, extract text before the first colon, and replace schemes in `{'javascript', 'vbscript', 'data'}` with `#blocked:`. Preserve the original encoded href for safe schemes and relative URLs.

- [ ] **Step 7: Run targeted safety tests**

Run: `python -m pytest tests/test_frontend_helpers.py tests/test_ssg.py -k 'frontend or markdown_blocks or render_markdown' -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add -- assets/js/index-core.js assets/js/index-photo-gallery.js backend/markdown_utils.py tests/test_frontend_helpers.py tests/test_ssg.py
git commit -m "fix: harden public rendering boundaries"
```

### Task 2: CSRF Trust Boundary and Login Type Validation

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/auth.py`
- Modify: `tests/test_routes.py`

**Interfaces:**
- Produces: `_trusted_origins() -> frozenset[str]`, derived only from `TRUSTED_ORIGINS` configuration.
- Produces: `_request_origin() -> str`, normalized as `scheme://netloc` from `Origin` or `Referer`.
- Consumes: `app.config['TRUSTED_ORIGINS']`, a comma-separated string or iterable of exact origins.

- [ ] **Step 1: Add hostile-Host and login-type tests**

Add tests that send `Host: evil.example` with `Origin: http://evil.example` and expect 403, set `app.config['TRUSTED_ORIGINS']` to local origins and expect 200 for `http://localhost`, and parameterize passwords over `123`, `None`, `[]`, and `{}` expecting 400 rather than 500.

- [ ] **Step 2: Verify the regressions fail**

Run: `python -m pytest tests/test_routes.py -k 'csrf or login_rejects_non_string' -v`

Expected: hostile Host returns 200 and non-string passwords return 500 before the fix.

- [ ] **Step 3: Configure exact trusted origins**

Initialize `TRUSTED_ORIGINS` from the environment with local defaults:

```python
_trusted_origin_env = os.environ.get(
    'TRUSTED_ORIGINS',
    'http://localhost,http://localhost:5000,http://127.0.0.1:5000',
)
app.config['TRUSTED_ORIGINS'] = tuple(
    value.strip().rstrip('/') for value in _trusted_origin_env.split(',') if value.strip()
)
```

Normalize the request `Origin`, or `Referer` when Origin is absent, with `urlparse`. Reject a present source unless its `scheme://netloc` exactly matches the configured set. Never read `request.host` to establish trust. Preserve the current behavior that requests with neither header are allowed.

- [ ] **Step 4: Validate password type before constant-time comparison**

Read JSON with `request.get_json(silent=True)`, require a dictionary and a string `password`, return `{"error": "Password must be a string"}, 400` otherwise, then call `hmac.compare_digest`.

- [ ] **Step 5: Run route regressions**

Run: `python -m pytest tests/test_routes.py -k 'csrf or login' -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add -- backend/app.py backend/auth.py tests/test_routes.py
git commit -m "fix: enforce configured request trust boundaries"
```

### Task 3: Fail-Closed Photo Synchronization

**Files:**
- Modify: `backend/data.py`
- Modify: `tools/process_images.py`
- Modify: `tests/test_storage.py`
- Create: `tests/test_process_images.py`

**Interfaces:**
- Produces: `load_json(name)`, which propagates `DataCorruptionError` for malformed existing JSON.
- Produces: `process_all_images()`, which preserves `date`, `size`, and `tags`, appends EXIF-dated new photos, and never writes after a metadata-load failure.

- [ ] **Step 1: Add corruption and merge regressions**

In `tests/test_storage.py`, monkeypatch `backend.data.STORE` to a `JsonStore(tmp_path)`, write `{broken`, and assert `backend.data.load_json('broken.json')` raises `DataCorruptionError`.

In `tests/test_process_images.py`, use temporary `raw_photos`, `images`, and `data` directories plus small Pillow images. Monkeypatch `_extract_exif` to return a date. Start with one existing photo containing `size` and `tags`, add one new photo, run sync, and assert both records exist and the old manual fields remain. A second test writes malformed `photos.json`, expects `DataCorruptionError`, and asserts the file bytes are unchanged.

- [ ] **Step 2: Verify photo regressions fail**

Run: `python -m pytest tests/test_storage.py tests/test_process_images.py -v`

Expected: corrupt data is converted to `[]`, the new photo is omitted or raises on `old_entry.get`, and manual fields disappear.

- [ ] **Step 3: Make compatibility loading fail closed**

Remove the `DataCorruptionError` catch from `backend.data.load_json`; retain the compatibility wrapper as `return STORE.read(name)`. Update its docstring to state that existing malformed files raise.

- [ ] **Step 4: Correct old/new photo record construction**

Build the record in this order:

```python
entry = {'filename': filename, 'exif': exif_info}
if old_entry:
    if old_entry.get('date'):
        entry['date'] = old_entry['date']
    elif exif_info.get('date'):
        entry['date'] = _parse_date(exif_info['date'])
    for field in ('size', 'tags'):
        if field in old_entry:
            entry[field] = old_entry[field]
elif exif_info.get('date'):
    entry['date'] = _parse_date(exif_info['date'])
```

Do not catch metadata-load errors. Per-image decode errors may keep the old record, but a new unreadable image produces no metadata record and is reported.

- [ ] **Step 5: Run photo/storage tests**

Run: `python -m pytest tests/test_storage.py tests/test_process_images.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add -- backend/data.py tools/process_images.py tests/test_storage.py tests/test_process_images.py
git commit -m "fix: prevent photo synchronization data loss"
```

### Task 4: Essay Password Lifecycle and Atomic README Writes

**Files:**
- Modify: `backend/data.py`
- Modify: `backend/routes/essay_metadata.py`
- Modify: `backend/routes/readme.py`
- Modify: `tests/test_essay_service.py`
- Modify: `tests/test_routes.py`

**Interfaces:**
- Produces: `rename_essay_password(old_slug, new_slug) -> None`.
- Produces: `delete_essay_password(slug) -> None`.
- Produces: README PUT returning 400 for non-string content and atomically replacing valid text.

- [ ] **Step 1: Add password lifecycle tests**

Use a temporary `PASSWORD_STORE`, write `{"old-slug": "secret"}`, invoke the rename helper, and assert only `new-slug` remains. Invoke deletion and assert the key is gone. Add route-level tests that monkeypatch the password store, rename an essay slug, delete it, and verify the mapping follows both operations.

- [ ] **Step 2: Add README non-truncation tests**

Monkeypatch `backend.routes.readme.BASE_DIR` to a temporary directory containing `README.md` with sentinel text. PUT `{"content": 123}` and assert status 400 and unchanged bytes. For a valid string, assert status 200, exact replacement, and no `.tmp` file remains.

- [ ] **Step 3: Verify lifecycle and README tests fail**

Run: `python -m pytest tests/test_essay_service.py tests/test_routes.py -k 'password_lifecycle or readme' -v`

Expected: rename/delete leave orphaned password keys and non-string README content truncates before raising.

- [ ] **Step 4: Implement password-store lifecycle helpers**

Read the password dictionary once, return early when slugs are equal, reject a destination collision with `ValueError`, move only a present local key, and persist once through `_write_password_store`. Deletion removes the key and persists only when it existed.

Call rename after source files are renamed but before HTML synchronization so the new slug resolves the password. Call deletion before derived feeds are regenerated. If lifecycle mutation fails, return 500 and do not continue deleting or synchronizing.

- [ ] **Step 5: Validate before an atomic README replacement**

Require `request.json['content']` to be a string. Write to `README.md.tmp` in the same directory with UTF-8, then `os.replace(temp_path, readme_path)`. Remove the temporary file in the exception path and re-raise unexpected I/O errors.

- [ ] **Step 6: Run lifecycle and README tests**

Run: `python -m pytest tests/test_essay_service.py tests/test_routes.py -k 'password or readme or essay' -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add -- backend/data.py backend/routes/essay_metadata.py backend/routes/readme.py tests/test_essay_service.py tests/test_routes.py
git commit -m "fix: preserve essay and README data lifecycles"
```

### Task 5: Derived Asset Cache Manifest and CI Artifact Gates

**Files:**
- Modify: `backend/asset_cache.py`
- Modify: `tests/test_ssg.py`
- Modify: `tests/test_coverage.py`
- Create: `tests/test_build_artifacts.py`
- Modify: `tests/test_ci_workflow.py`
- Modify: `.github/workflows/build-deploy.yml`

**Interfaces:**
- Produces: `cache_bust_assets(base_dir)`, deriving local CSS/JS references from each HTML page.
- Produces: unconditional build-artifact tests run only after `python manage.py build` in CI.

- [ ] **Step 1: Add cache-manifest regression**

Build an `admin.html` fixture that references `admin-core.js`, `admin-api.js`, and `admin-ui.js`, create those files with distinct mtimes, run `cache_bust_assets`, and assert every reference has the same newest timestamp. Include an external script URL and assert it is unchanged.

- [ ] **Step 2: Verify cache regression fails**

Run: `python -m pytest tests/test_ssg.py -k cache_bust -v`

Expected: `admin-api.js` and `admin-ui.js` retain their old versions.

- [ ] **Step 3: Derive local assets from actual HTML references**

Replace the manual tuples with a regex that finds quoted `href`/`src` values beginning with `assets/css/` or `assets/js/`, strips only an existing numeric `?v=`, filters to files that exist beneath `base_dir`, computes the newest mtime per page, and substitutes that version for every matched local reference. External URLs and missing assets remain unchanged.

- [ ] **Step 4: Replace conditional artifact assertions**

Move RSS, sitemap, archive, and map checks from `tests/test_coverage.py` into `tests/test_build_artifacts.py`. Each test must unconditionally assert that its file exists and contains its expected root marker (`<rss`, `<urlset`, archive HTML, map HTML).

- [ ] **Step 5: Add CI ordering contracts**

Assert the workflow contains, in order within the build job:

```text
python -m pytest tests/ -v --ignore=tests/test_build_artifacts.py
python manage.py build
python -m pytest tests/test_build_artifacts.py -v
```

Require the browser-smoke job to run `python manage.py build` before its required Playwright command. Keep `BROWSER_SMOKE_REQUIRED: '1'` and the explicit Chromium installation.

- [ ] **Step 6: Verify CI tests fail before workflow edits**

Run: `python -m pytest tests/test_ci_workflow.py tests/test_build_artifacts.py -v`

Expected: CI ordering assertions fail; build-artifact tests pass locally only when current generated files exist.

- [ ] **Step 7: Update the workflow and run build gates**

Run:

```powershell
python -m pytest tests/ -v --ignore=tests/test_build_artifacts.py
python manage.py build
python -m pytest tests/test_build_artifacts.py tests/test_ci_workflow.py -v
```

Expected: all commands PASS.

- [ ] **Step 8: Commit**

```powershell
git add -- backend/asset_cache.py tests/test_ssg.py tests/test_coverage.py tests/test_build_artifacts.py tests/test_ci_workflow.py .github/workflows/build-deploy.yml
git commit -m "ci: validate generated assets after build"
```

### Task 6: Phase-One Verification

**Files:**
- Verify only; normalize generated cache/JSON noise before any later commit.

- [ ] **Step 1: Run all Python tests after a build**

Run: `python manage.py build; python -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 2: Run JavaScript and Python syntax checks**

Run all `assets/js/*.js` files through `node --check`, then run `python -m compileall -q backend tools manage.py`.

Expected: exit code 0.

- [ ] **Step 3: Run required Chromium smoke tests**

Run: `$env:BROWSER_SMOKE_REQUIRED='1'; python -m pytest tests/test_browser_smoke.py -v`

Expected: PASS, with no assertion converted to skip. Remove the temporary environment override afterward.

- [ ] **Step 4: Check the patch**

Run: `git diff --check; git status --short`

Expected: no whitespace errors and only intentional source/test changes or generated files required by the build.
