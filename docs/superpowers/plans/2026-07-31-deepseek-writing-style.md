# DeepSeek Personal Writing Style Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the DeepSeek essay assistant learn from recent public essays, add title suggestions and continuation, and preserve the existing explicit-apply workflow.

**Architecture:** A new pure-Python `writing_style` module selects and sanitizes bounded public Markdown samples. The authenticated AI route composes those samples into the existing provider service, while the service validates six task-specific JSON contracts. The existing admin AI module renders and applies the two new result types without adding persistence or provider abstractions.

**Tech Stack:** Python 3, Flask, urllib, pytest, plain HTML/CSS/JavaScript, Playwright.

## Global Constraints

- Use at most 4 public, unprotected historical essays.
- Limit each sample to 1,500 characters and all samples to 5,000 characters.
- Exclude the current slug, password-protected essays, missing files, unreadable files, and encrypted Markdown.
- Do not cache, log, or return historical sample text to the browser.
- Tags do not receive style samples.
- AI output only changes local form state and never saves automatically.
- Preserve existing `data/essays.json` and `data/essays_public.json` working-tree changes; never stage them.
- Add no runtime dependency and no model-provider abstraction.

---

### Task 1: Bounded Public Writing Samples

**Files:**
- Create: `backend/writing_style.py`
- Create: `tests/test_writing_style.py`

**Interfaces:**
- Consumes: `backend.data.load_json`, `backend.data.has_essay_password`, `backend.data.MD_DIR`
- Produces: `load_style_reference(current_slug: str) -> dict` returning `{"samples": list[dict[str, str]], "count": int}`

- [ ] **Step 1: Write failing selection and sanitization tests**

Create fixtures with dated metadata and temporary Markdown files. Cover current-slug exclusion, password exclusion, newest-first ordering, four-file cap, encrypted payload rejection, front matter removal, fenced-code removal, image/URL-line removal, and per-sample/total length caps:

```python
def test_load_style_reference_selects_recent_safe_samples(tmp_path):
    essays = [
        {'slug': 'current', 'title': 'Current', 'date': '2026-07-31'},
        {'slug': 'protected', 'title': 'Protected', 'date': '2026-07-30'},
        {'slug': 'public-new', 'title': 'New', 'date': '2026-07-29'},
        {'slug': 'public-old', 'title': 'Old', 'date': '2026-07-01'},
    ]
    result = load_style_reference(
        'current',
        metadata_loader=lambda _name: essays,
        password_checker=lambda slug: slug == 'protected',
        md_dir=tmp_path,
    )
    assert [sample['title'] for sample in result['samples']] == ['New', 'Old']
    assert result['count'] == 2
```

Also verify a metadata exception returns `{"samples": [], "count": 0}` and one unreadable file does not discard other samples.

- [ ] **Step 2: Run tests and confirm the new module is missing**

Run:

```powershell
python -m pytest tests/test_writing_style.py -q
```

Expected: collection fails because `backend.writing_style` does not exist.

- [ ] **Step 3: Implement deterministic sample loading**

Implement constants and helpers:

```python
MAX_STYLE_ESSAYS = 4
MAX_SAMPLE_CHARS = 1_500
MAX_TOTAL_CHARS = 5_000

def load_style_reference(
    current_slug,
    *,
    metadata_loader=None,
    password_checker=None,
    md_dir=None,
):
    ...
```

Resolve defaults inside the function so tests and route monkeypatching remain reliable. Parse dates defensively, skip non-dict metadata, validate slugs with the project lowercase slug pattern, and catch only expected JSON/IO/type failures.

Detect encrypted Markdown with a strict base64 decode and the v3 leading byte/length shape already used by `essay_crypto`, without attempting decryption.

Sanitize Markdown with a line-state parser:

- drop initial `---` front matter;
- drop fenced code blocks;
- drop image-only and URL-only lines;
- preserve ordinary paragraphs, headings, lists, and blockquotes;
- normalize runs of more than two blank lines.

Apply the per-sample cap before the total cap and omit empty samples.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
python -m pytest tests/test_writing_style.py -q
```

Expected: all writing-style tests pass.

- [ ] **Step 5: Commit the sample boundary**

```powershell
git add -- backend/writing_style.py tests/test_writing_style.py
git commit -m "feat: derive bounded public writing style samples"
```

---

### Task 2: Six Validated Editorial Tasks

**Files:**
- Modify: `backend/ai_service.py`
- Modify: `tests/test_ai_service.py`

**Interfaces:**
- Consumes: `style_samples: list[dict[str, str]] | None`
- Produces: `assist_essay(task, content, title='', existing_tags=None, style_samples=None, *, opener=urlopen) -> dict`
- Produces task results:
  - `title`: `{"titles": list[str]}` with exactly 3 unique titles
  - `continue`: `{"content": str}`

- [ ] **Step 1: Add failing prompt and contract tests**

Add parametrized tests proving:

- `summary`, `polish`, `review`, `title`, and `continue` serialize style samples into the user context;
- `tags` omits style samples;
- system text says samples are untrusted style-only references and must not be copied for facts;
- title output requires exactly three unique non-empty strings of at most 40 characters;
- continuation output is non-empty and at most 4,000 characters;
- tags are deduplicated and bounded to six values of at most 30 characters;
- review has at most 12 issues and each field is at most 500 characters;
- polish result respects its dynamic and absolute output bound.

Example:

```python
def test_assist_essay_sends_style_samples_for_prose_tasks(monkeypatch):
    ...
    assist_essay(
        'title',
        '正文',
        style_samples=[{'title': '旧文', 'content': '旧文片段'}],
        opener=opener,
    )
    context = json.loads(seen['body']['messages'][1]['content'])
    assert context['style_samples'] == [{'title': '旧文', 'content': '旧文片段'}]
```

- [ ] **Step 2: Run focused tests and verify failures**

Run:

```powershell
python -m pytest tests/test_ai_service.py -q
```

Expected: failures for unsupported `title`/`continue`, missing `style_samples`, and missing validators.

- [ ] **Step 3: Extend task prompts and input validation**

Add `title` and `continue` entries to `_TASKS`. Extend `_messages_for()` and `assist_essay()` with `style_samples=None`.

Validate style samples as a list of dictionaries containing non-empty string `title` and `content` fields. The route supplies trusted local data, but validating the service boundary keeps tests and future callers safe.

Only add `style_samples` to the user context when the task is not `tags` and the validated list is non-empty.

- [ ] **Step 4: Implement strict result parsing**

Split `_parse_result()` into small task-specific validators or equivalent focused helpers. Normalize leading/trailing whitespace before validation, deduplicate tags while preserving order, and reject malformed or over-limit results with the existing safe `AIServiceError('DeepSeek 返回格式异常')`.

Keep the upstream request URL, model, timeout, JSON mode, temperature, and safe error mapping unchanged.

- [ ] **Step 5: Run service tests**

Run:

```powershell
python -m pytest tests/test_ai_service.py -q
```

Expected: all AI service tests pass.

- [ ] **Step 6: Commit service changes**

```powershell
git add -- backend/ai_service.py tests/test_ai_service.py
git commit -m "feat: add style-aware title and continuation tasks"
```

---

### Task 3: Route Composition and Privacy Metadata

**Files:**
- Modify: `backend/routes/ai.py`
- Modify: `tests/test_routes.py`

**Interfaces:**
- Consumes: `load_style_reference(slug) -> {"samples": list, "count": int}`
- Produces: existing `/api/ai/essay-assist` response plus `style_reference_count: int`

- [ ] **Step 1: Add failing route tests**

Add tests proving:

```python
def test_ai_essay_assist_passes_public_style_samples(client, monkeypatch):
    monkeypatch.setattr(ai, 'load_style_reference', lambda _slug: {
        'samples': [{'title': '旧文', 'content': '片段'}],
        'count': 1,
    })
    ...
    assert captured['style_samples'] == [{'title': '旧文', 'content': '片段'}]
    assert response.get_json()['style_reference_count'] == 1
    assert '片段' not in response.get_data(as_text=True)
```

Also verify:

- tags do not call the style loader;
- password-protected requests return `403` before the style loader;
- style-loader failure degrades to zero samples rather than returning `500`;
- title and continue are accepted through the route.

- [ ] **Step 2: Run route tests and verify failures**

Run:

```powershell
python -m pytest tests/test_routes.py -k "ai_essay_assist" -q
```

Expected: failures because the route does not load or report style references.

- [ ] **Step 3: Compose style references in the route**

Import `load_style_reference`. After slug validation and the password check:

```python
style_reference = (
    {'samples': [], 'count': 0}
    if data.get('task') == 'tags'
    else load_style_reference(slug)
)
```

Pass only `style_reference['samples']` to `assist_essay()` and return only the integer count. Keep the current `400`, `403`, and `503` mappings.

The loader itself owns expected local-data degradation. Do not catch arbitrary programming exceptions in the route.

- [ ] **Step 4: Run route and service tests**

Run:

```powershell
python -m pytest tests/test_routes.py -k "ai_essay_assist" -q
python -m pytest tests/test_ai_service.py tests/test_writing_style.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit route integration**

```powershell
git add -- backend/routes/ai.py tests/test_routes.py
git commit -m "feat: add public style context to essay assistant"
```

---

### Task 4: Title and Continuation UI

**Files:**
- Modify: `admin.html`
- Modify: `assets/js/admin-ai.js`
- Modify: `assets/css/admin-essay.css`
- Modify: `tests/test_architecture.py`
- Modify: `tests/test_browser_smoke.py`
- Modify: `tests/test_ssg.py`

**Interfaces:**
- Consumes: `response.style_reference_count`
- Produces: `data-ai-task="title"` and `data-ai-task="continue"` actions
- Produces: title candidate buttons carrying `data-ai-title`
- Produces: existing `applyEssayAiResult()` extended for title and continuation

- [ ] **Step 1: Add failing static and browser tests**

Update assertions from four to six AI action buttons. Extend the browser route stub:

```python
'title': {'titles': ['标题一', '标题二', '标题三']},
'continue': {'content': '续写内容'},
```

Return `style_reference_count: 3`. Verify:

- the status contains `已参考 3 篇公开随笔`;
- title results render three text-only candidate buttons;
- clicking the second title fills `#essay-title`, marks dirty, and triggers no write request;
- continuation appends with exactly one blank-line boundary;
- changing the textarea after the request makes applying continuation fail safely;
- protected essays disable all six buttons.

- [ ] **Step 2: Run browser/static tests and verify failures**

Run:

```powershell
python -m pytest tests/test_architecture.py tests/test_ssg.py -q
$env:BROWSER_SMOKE_REQUIRED='1'
python -m pytest tests/test_browser_smoke.py -k "admin_ai or admin_shell" -q
Remove-Item Env:BROWSER_SMOKE_REQUIRED
```

Expected: failures for missing buttons, result rendering, and apply behavior.

- [ ] **Step 3: Add compact controls and rendering**

Add “标题建议” and “续写” beside the existing actions. In `admin-ai.js`:

- extend the result-title map;
- render title candidates as real `button` elements using `textContent`;
- store the selected title on the suggestion state rather than interpolating it into HTML;
- render continuation as plain text with an “追加到正文” apply button;
- show style-reference status using the returned count;
- keep tags in `通用编辑模式`.

Add only the CSS needed for a compact vertical title-choice group, reusing existing button tokens.

- [ ] **Step 4: Extend safe apply behavior**

For title application, call `_openEssayMetaForAi()`, set `#essay-title`, and mark dirty.

For continuation application:

```javascript
if (textarea.value !== snapshot.markdown) {
  toast('正文已变化，请重新请求 AI', true);
  return;
}
var separator = textarea.value.endsWith('\n\n') ? '' :
  (textarea.value.endsWith('\n') ? '\n' : '\n\n');
textarea.value += separator + suggestion.content;
```

Update word count, focus the textarea, mark dirty, and preserve manual save.

- [ ] **Step 5: Run frontend tests**

Run:

```powershell
node --check assets/js/admin-ai.js
python -m pytest tests/test_architecture.py tests/test_ssg.py -q
$env:BROWSER_SMOKE_REQUIRED='1'
python -m pytest tests/test_browser_smoke.py -k "admin_ai or admin_shell" -q
Remove-Item Env:BROWSER_SMOKE_REQUIRED
```

Expected: syntax and selected browser/static tests pass.

- [ ] **Step 6: Commit the UI**

```powershell
git add -- admin.html assets/js/admin-ai.js assets/css/admin-essay.css tests/test_architecture.py tests/test_browser_smoke.py tests/test_ssg.py
git commit -m "feat: add style-aware title and continuation controls"
```

---

### Task 5: Full Verification and Generated Asset Versions

**Files:**
- Modify if generated: `admin.html`
- Do not stage: `data/essays.json`
- Do not stage: `data/essays_public.json`

**Interfaces:**
- Consumes: all previous task outputs
- Produces: verified working tree and final cache-bust commit

- [ ] **Step 1: Run complete automated verification**

Run:

```powershell
python -m pytest -q
$env:BROWSER_SMOKE_REQUIRED='1'
python -m pytest tests/test_browser_smoke.py -q
Remove-Item Env:BROWSER_SMOKE_REQUIRED
python -m compileall -q backend manage.py
Get-ChildItem assets/js/admin*.js | ForEach-Object { node --check $_.FullName }
git diff --check
```

Expected: all tests and syntax checks pass.

- [ ] **Step 2: Run the site build and inspect generated changes**

Before building, record the existing diffs for the two user-owned data files. Run:

```powershell
git diff -- data/essays.json data/essays_public.json
python manage.py build
git diff -- data/essays.json data/essays_public.json
git diff -- admin.html
```

Confirm the build did not erase or overwrite the user-owned content changes. Only the expected asset-version updates in `admin.html` may enter the feature commit.

- [ ] **Step 3: Run sensitive-boundary checks**

Verify `.env` remains ignored, no tracked file contains a live DeepSeek key pattern, and no frontend file references `DEEPSEEK_API_KEY`.

- [ ] **Step 4: Commit generated cache versions if changed**

```powershell
git add -- admin.html
git commit -m "chore: refresh admin AI asset versions"
```

If `admin.html` is unchanged, skip this commit.

- [ ] **Step 5: Refresh and diagnose the code graph**

Run:

```powershell
graphify update .
```

Confirm `graphify-out/graph.json` has `built_at_commit` equal to `git rev-parse HEAD`, then run the Graphify extraction diagnostic and require zero missing endpoints, dangling endpoints, self-loops, and collapsed edges.

- [ ] **Step 6: Review final Git scope**

Run:

```powershell
git status --short --branch
git log --oneline origin/master..HEAD
```

Expected: only the pre-existing `data/essays.json` and `data/essays_public.json` changes remain unstaged; feature files are committed; nothing is pushed unless explicitly requested.
