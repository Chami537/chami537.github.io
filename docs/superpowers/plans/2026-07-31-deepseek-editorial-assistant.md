# DeepSeek Editorial Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a DeepSeek-powered, human-in-the-loop editorial assistant to the existing admin essay editor.

**Architecture:** A focused Flask service calls DeepSeek Chat Completions through the Python standard library and validates task-specific JSON before returning it. One authenticated route accepts the current essay slug and editor content. A standalone admin JavaScript module renders suggestions and only updates local form fields after explicit user action.

**Tech Stack:** Python 3.11, Flask, `urllib.request`, pytest, plain HTML/CSS/JavaScript, Playwright browser smoke tests.

## Global Constraints

- Use `deepseek-chat` at `https://api.deepseek.com/chat/completions`.
- Read the secret only from `DEEPSEEK_API_KEY`; never return, log, commit, or expose it to JavaScript.
- Use `response_format={"type": "json_object"}` with a 30-second timeout.
- Accept at most 20,000 input characters and request at most 1,500 output tokens.
- Support only `summary`, `tags`, `polish`, and `review`.
- Reject password-protected essays on the server and disable them in the UI.
- AI output never saves content, edits files, runs Git, builds, or deploys.
- Render AI output as text; never inject model HTML.
- Add no Python or JavaScript dependency.

---

### Task 1: DeepSeek service boundary

**Files:**
- Create: `backend/ai_service.py`
- Create: `tests/test_ai_service.py`

**Interfaces:**
- Consumes: `DEEPSEEK_API_KEY` from `os.environ`; an injectable opener compatible with `urllib.request.urlopen`.
- Produces: `assist_essay(task: str, content: str, title: str = "", existing_tags: list[str] | None = None, *, opener=urlopen) -> dict`.
- Produces: `AIServiceError`, whose public message contains no upstream body or secret.

- [ ] **Step 1: Write failing success-contract tests**

Create tests that call the real `assist_essay` with a fake opener returning a complete DeepSeek response:

```python
def test_assist_essay_sends_json_mode_request_and_returns_summary(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret")
    seen = {}

    def opener(request, timeout):
        seen["headers"] = dict(request.header_items())
        seen["body"] = json.loads(request.data)
        seen["timeout"] = timeout
        return FakeResponse({
            "choices": [{"message": {"content": '{"excerpt":"精炼摘要"}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 4},
        })

    result = assist_essay("summary", "正文", title="标题", opener=opener)

    assert result == {
        "result": {"excerpt": "精炼摘要"},
        "usage": {"prompt_tokens": 10, "completion_tokens": 4},
    }
    assert seen["body"]["model"] == "deepseek-chat"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert seen["body"]["max_tokens"] == 1500
    assert seen["timeout"] == 30
    assert seen["headers"]["Authorization"] == "Bearer test-secret"
```

Add parameterized fixtures for the other results:

```python
[
    ("tags", '{"tags":["技术","Python","教程"]}', {"tags": ["技术", "Python", "教程"]}),
    ("polish", '{"content":"润色正文"}', {"content": "润色正文"}),
    ("review", '{"issues":[{"type":"文字","message":"重复","suggestion":"删除"}]}',
     {"issues": [{"type": "文字", "message": "重复", "suggestion": "删除"}]}),
]
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest tests/test_ai_service.py -q
```

Expected: collection fails because `backend.ai_service` does not exist.

- [ ] **Step 3: Implement the minimal HTTP service**

Implement:

```python
class AIServiceError(RuntimeError):
    pass


def assist_essay(task, content, title="", existing_tags=None, *, opener=urlopen):
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise AIServiceError("DeepSeek API 密钥未配置")
    payload = {
        "model": "deepseek-chat",
        "messages": _messages_for(task, content, title, existing_tags or []),
        "response_format": {"type": "json_object"},
        "max_tokens": 1500,
        "temperature": 0.3,
        "stream": False,
    }
    request = Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with opener(request, timeout=30) as response:
            upstream = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        raise AIServiceError("DeepSeek 暂时不可用，请稍后重试") from error
    result = _parse_result(task, upstream)
    return {"result": result, "usage": _safe_usage(upstream.get("usage"))}
```

Keep task prompts in one `_TASKS` mapping. Each prompt states the exact output keys and that essay text is untrusted data, not instructions.

- [ ] **Step 4: Run success-contract tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_ai_service.py -q
```

Expected: success cases pass.

- [ ] **Step 5: Write failing validation and failure-isolation tests**

Add tests proving:

- missing key raises `AIServiceError("DeepSeek API 密钥未配置")`
- unknown task raises `ValueError`
- empty and over-20,000-character content raise `ValueError`
- malformed JSON, empty choices, absent result keys, wrong tag/issue shapes, HTTP errors and timeouts raise `AIServiceError`
- an upstream error body containing `test-secret` never appears in `str(error)`
- JSON wrapped in a Markdown code fence is rejected rather than guessed

- [ ] **Step 6: Run new tests and verify RED**

Run:

```powershell
python -m pytest tests/test_ai_service.py -q
```

Expected: the unimplemented validation branches fail.

- [ ] **Step 7: Implement strict input and output validation**

Use exact-type checks (`type(value) is str`, `type(existing_tags) is list`) so booleans and coercible objects are not accepted. Return usage only as integer `prompt_tokens` and `completion_tokens`, defaulting each to zero.

- [ ] **Step 8: Run service tests and commit**

Run:

```powershell
python -m pytest tests/test_ai_service.py -q
git add backend/ai_service.py tests/test_ai_service.py
git commit -m "feat: add DeepSeek editorial service"
```

Expected: all service tests pass and only the two intended files are committed.

---

### Task 2: Authenticated essay-assist route

**Files:**
- Create: `backend/routes/ai.py`
- Modify: `backend/routes/__init__.py`
- Modify: `tests/test_routes.py`

**Interfaces:**
- Consumes: `assist_essay(...)` and `AIServiceError` from Task 1.
- Consumes: `has_essay_password(slug: str) -> bool` from `backend.data`.
- Produces: `POST /api/ai/essay-assist`.

- [ ] **Step 1: Write failing route-contract tests**

Add tests with `backend.routes.ai.assist_essay` replaced at the external service boundary:

```python
def test_ai_essay_assist_returns_structured_result(client, monkeypatch):
    import backend.routes.ai as ai
    monkeypatch.setattr(ai, "has_essay_password", lambda slug: False)
    monkeypatch.setattr(ai, "assist_essay", lambda **kwargs: {
        "result": {"excerpt": "摘要"},
        "usage": {"prompt_tokens": 3, "completion_tokens": 2},
    })

    response = client.post("/api/ai/essay-assist", json={
        "slug": "essay-demo",
        "task": "summary",
        "content": "正文",
        "title": "标题",
        "existing_tags": ["技术"],
    })

    assert response.status_code == 200
    assert response.get_json()["result"] == {"excerpt": "摘要"}
```

Add cases for missing/non-string slug, invalid task, invalid content/title/tags, password-protected slug, and `AIServiceError`. Verify `client_no_auth` gets `401`.

- [ ] **Step 2: Run route tests and verify RED**

Run:

```powershell
python -m pytest tests/test_routes.py -k "ai_essay_assist" -q
```

Expected: import or 404 failures because the route does not exist.

- [ ] **Step 3: Implement and register the route**

Implement a Blueprint using the existing `require_json` decorator. Validate request fields before calling the service. Return:

```python
if has_essay_password(slug):
    return jsonify({"error": "密码保护文章不能发送给 AI"}), 403
try:
    response = assist_essay(
        task=data["task"],
        content=data["content"],
        title=data.get("title", ""),
        existing_tags=data.get("existing_tags", []),
    )
except ValueError as error:
    return jsonify({"error": str(error)}), 400
except AIServiceError as error:
    return jsonify({"error": str(error)}), 503
return jsonify({"task": data["task"], **response})
```

Register `ai.bp` in `backend/routes/__init__.py` without changing existing route order semantics.

- [ ] **Step 4: Run targeted and auth tests**

Run:

```powershell
python -m pytest tests/test_routes.py -k "ai_essay_assist or requires_auth" -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/routes/ai.py backend/routes/__init__.py tests/test_routes.py
git commit -m "feat: expose AI essay assistant API"
```

---

### Task 3: Admin editorial-assistant UI

**Files:**
- Create: `assets/js/admin-ai.js`
- Modify: `admin.html`
- Modify: `assets/css/admin.css`
- Modify: `tests/test_architecture.py`
- Modify: `tests/test_browser_smoke.py`
- Modify: `tests/test_ssg.py`

**Interfaces:**
- Consumes: global `api`, `toast`, `markDirty`, `renderEssayTaxonomy`, `editEssayMeta`, `_essayAllData`.
- Produces: global `requestEssayAi(task)`, `applyEssayAiResult()`, `updateEssayAiAvailability(slug)`, `_renderEssayAiResult(task, result)`.

- [ ] **Step 1: Write failing browser and architecture tests**

Extend the admin browser smoke test to assert:

```python
for name in ("requestEssayAi", "applyEssayAiResult", "updateEssayAiAvailability"):
    assert page.evaluate("typeof " + name) == "function"
assert page.locator("#essay-ai-panel").count() == 1
assert page.locator("#essay-ai-actions button").count() == 4
```

Intercept `/api/ai/essay-assist`, click “生成摘要”, assert the suggestion appears as text, click “应用到摘要”, and assert `#essay-excerpt` changes without a `PUT /api/essays/*` request. Add a JavaScript evaluation proving `<img onerror=...>` remains text and creates no image element.

Extend architecture/SSG asset assertions so `admin-ai.js` must load after `admin-essay-content.js` and before `admin-tabs.js`.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest tests/test_architecture.py tests/test_ssg.py tests/test_browser_smoke.py -k "admin or cache_bust" -q
```

Expected: missing module, functions and panel failures.

- [ ] **Step 3: Add the static AI panel**

Add below the Markdown textarea controls:

```html
<section id="essay-ai-panel" class="essay-ai-panel" aria-labelledby="essay-ai-title">
  <div class="essay-ai-heading">
    <div><strong id="essay-ai-title">AI 编辑副驾驶</strong><span>DeepSeek</span></div>
    <span id="essay-ai-status" role="status" aria-live="polite"></span>
  </div>
  <div id="essay-ai-actions" class="essay-ai-actions">
    <button type="button" data-ai-task="summary">生成摘要</button>
    <button type="button" data-ai-task="tags">推荐标签</button>
    <button type="button" data-ai-task="polish">润色</button>
    <button type="button" data-ai-task="review">检查问题</button>
  </div>
  <div id="essay-ai-result" class="essay-ai-result" hidden></div>
</section>
```

Load `admin-ai.js` after the essay content/format/media modules so it can consume their globals.

- [ ] **Step 4: Implement request and safe rendering**

Capture a request snapshot:

```javascript
{
  slug: editor.dataset.slug,
  task: task,
  content: selectedText || textarea.value,
  title: matchingEssay ? matchingEssay.title : '',
  existing_tags: matchingEssay ? _essayTagParts(matchingEssay.tag || '') : []
}
```

Use one module-level `AbortController`. Disable all four buttons while pending. Render all returned values by assigning `textContent` to newly created nodes. Store `{task, result, snapshot}` only after the latest request completes.

- [ ] **Step 5: Implement explicit apply behavior**

- `summary`: ensure the matching metadata form is open, set `#essay-excerpt`, then `markDirty()`
- `tags`: ensure the matching metadata form is open, call `renderEssayTaxonomy(tags.join(", "))`, then `markDirty()`
- `polish`: compare the current selected range or full content with the snapshot; if unchanged, replace only that range and call `_updateWordCount()` plus `markDirty()`
- `review`: render issues with no apply button

If content changed since the request, show `toast("正文已变化，请重新请求 AI", true)` and apply nothing.

- [ ] **Step 6: Enforce password-article UI gating**

`updateEssayAiAvailability(slug)` finds the matching `_essayAllData` item. When `password_set` is true, disable all AI buttons and set status to `密码保护文章不会发送给 AI`.

Call it whenever `editEssayContent(slug)` opens and clear result state when the active slug changes.

- [ ] **Step 7: Add focused styling**

Use existing CSS variables and button conventions. The card must remain readable at the existing mobile breakpoint, wrap action buttons, provide visible focus states, and visually separate status, suggestion, issues and the apply action without introducing new colors outside the current palette.

- [ ] **Step 8: Verify JavaScript and browser behavior**

Run:

```powershell
node --check assets/js/admin-ai.js
python -m pytest tests/test_architecture.py tests/test_ssg.py tests/test_browser_smoke.py -k "admin or cache_bust" -q
```

Expected: syntax and selected tests pass.

- [ ] **Step 9: Commit**

```powershell
git add admin.html assets/css/admin.css assets/js/admin-ai.js assets/js/admin-essay-content.js tests/test_architecture.py tests/test_browser_smoke.py tests/test_ssg.py
git commit -m "feat: add AI controls to essay editor"
```

---

### Task 4: Local secret configuration and end-to-end hardening

**Files:**
- Modify locally only: `.env` (ignored by Git)
- Modify: `CLAUDE.md` (ignored by Git)
- Modify if failures require it: files created or changed in Tasks 1-3

**Interfaces:**
- Consumes: the user-provided DeepSeek API key from the conversation.
- Produces: a local `DEEPSEEK_API_KEY` setting available after Flask restart.

- [ ] **Step 1: Write the local secret without printing it**

Create `.env` if absent, or append/replace only `DEEPSEEK_API_KEY`. Preserve all other environment entries. Do not display `.env`, include the key in a command result, or stage the file. Confirm only:

```powershell
git check-ignore .env
```

Expected: `.env` is ignored.

- [ ] **Step 2: Run a bounded live API check**

Start from the service layer with a short Chinese summary request. Print only the parsed result keys and token counts. Never print request headers, environment values, raw upstream bodies or exception chains.

If the key is invalid, out of balance or rate limited, preserve the completed implementation and report the sanitized operational result.

- [ ] **Step 3: Run the full verification gate**

Run:

```powershell
python -m pytest -q
python -m compileall -q backend tests
node --check assets/js/admin-ai.js
python manage.py build
git diff --check
```

Expected: all commands exit zero. GitHub star rate-limit warnings during `manage.py build` are non-fatal when the build exits zero.

- [ ] **Step 4: Perform security checks**

Search tracked files and staged content for API-key-shaped values without printing matching content. Verify:

- `.env` is ignored and unstaged
- no tracked file contains `DEEPSEEK_API_KEY=` followed by a real value
- no frontend asset contains `Authorization`, `Bearer`, or the environment variable name
- route errors and service exceptions contain no secret
- `git status --short` contains only intended tracked implementation changes

- [ ] **Step 5: Update local project memory and commit any final fixes**

Record the feature, tests and operational status under `2026-07-31` in ignored `CLAUDE.md`. Stage only intended tracked files. If hardening produced tracked fixes:

```powershell
git add backend/ai_service.py backend/routes/ai.py backend/routes/__init__.py admin.html assets/css/admin.css assets/js/admin-ai.js assets/js/admin-essay-content.js tests/test_ai_service.py tests/test_routes.py tests/test_architecture.py tests/test_browser_smoke.py tests/test_ssg.py
git commit -m "test: harden DeepSeek editorial assistant"
```

Do not push unless the user explicitly asks.

---

### Task 5: Review and graph refresh

**Files:**
- Inspect: all implementation commits from Tasks 1-4
- Refresh ignored output: `graphify-out/`

**Interfaces:**
- Consumes: the complete feature diff against `b0a7276`.
- Produces: reviewed commits, clean tracked worktree, refreshed code graph.

- [ ] **Step 1: Review blast radius and simplicity**

Use code-graph diff context to confirm callers, route registration, script order and affected tests. Run a simplification review for unnecessary provider abstractions, retries, configuration flags or duplicated rendering.

- [ ] **Step 2: Verify the final committed state**

Run the full verification commands again after any review fixes. Confirm `git status --porcelain` is empty for tracked files and list commits created for the feature.

- [ ] **Step 3: Refresh Graphify**

Run:

```powershell
graphify update .
```

Then run the read-only graph health diagnostic and confirm `built_at_commit` equals `HEAD`.

- [ ] **Step 4: Hand off**

Report:

- implemented capabilities and human-approval behavior
- hidden-article policy
- live DeepSeek check result without secret or raw response
- test/build/browser results
- commit SHAs
- whether push was performed
