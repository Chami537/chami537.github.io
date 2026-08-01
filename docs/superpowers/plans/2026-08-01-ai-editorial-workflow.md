# AI Editorial Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing admin AI buttons into a useful review loop with iterative feedback, trustworthy text diffs, and dashboard findings that open the exact editor field needing attention.

**Architecture:** Extend the existing authenticated AI routes and service validation with a bounded `refine` operation. Keep candidate sessions in browser memory, put generic request/snapshot/diff behavior in a shared frontend module, and let each domain provide only its field adapter. Add stable locator metadata to dashboard findings; do not persist a repair queue.

**Tech Stack:** Flask, Python standard library, existing `backend/ai_service.py`, vanilla JavaScript, existing admin tab/event model, pytest, Playwright browser smoke tests.

## Global Constraints

- AI only generates candidates; it never saves, commits, builds, deploys, or batch-applies content.
- Feedback is limited to 500 characters and uses the current candidate as its input.
- Password-protected essays, encrypted content, API keys, prompts, and raw upstream responses never cross the existing privacy boundary.
- Photo-story assistance cannot invent visual details; Work assistance remains factual card copy.
- Dashboard repair items are recalculated from current content and are not persisted.
- Do not add SDK dependencies, vector storage, conversation persistence, or automatic retries.
- Existing uncommitted `data/essays.json` and `data/essays_public.json` must remain untouched.

---

### Task 1: Add the bounded refinement contract to the AI service

**Files:**
- Modify: `backend/ai_service.py` (`_TASKS`, validation constants, message construction, result validation)
- Modify: `backend/routes/ai.py` (`essay_assist` and `admin_assist` request handling)
- Test: `tests/test_ai_service.py`
- Test: `tests/test_routes.py`

**Interfaces:**
- Consumes: existing essay/admin task validators and style-profile loading.
- Produces: `assist_essay(..., task='refine', content=<current_candidate>, instruction=<feedback>, surrounding_context=<context>)` with the same safe result envelope as the original task; admin refinement accepts `task='refine'` plus `domain` and `source_task`.

- [ ] **Step 1: Write failing service tests** for a refine request that includes the original source, current candidate and feedback in the user JSON; assert the system prompt keeps the source task constraints and forbids invented facts. Add rejection tests for missing feedback, non-string feedback, feedback over 500 characters, unknown source task and oversized candidate.

- [ ] **Step 2: Run the focused tests**

```powershell
pytest tests/test_ai_service.py -k "refine" -v
```

Expected: FAIL because the refine task and validation do not exist.

- [ ] **Step 3: Implement the minimal service contract.** Add `MAX_FEEDBACK_LENGTH = 500`, a refine task prompt that returns `{"content":"...","changes":[...]}`, and optional `source_task`/`source_content` context fields. Reuse the original task's prompt fragment so `polish`, `about`, `project`, and `photo_story` restrictions remain active. Validate output with the existing content/change validators and never log request bodies.

- [ ] **Step 4: Add route tests** for essay and admin refinement, including style-profile use for essay tasks, unsupported domain/task rejection, password-essay rejection before model invocation, and safe `503` mapping for upstream failure.

- [ ] **Step 5: Run focused route/service tests**

```powershell
pytest tests/test_ai_service.py tests/test_routes.py -k "ai or assist or refine" -v
```

Expected: PASS.

- [ ] **Step 6: Commit the backend contract**

```powershell
git add backend/ai_service.py backend/routes/ai.py tests/test_ai_service.py tests/test_routes.py
git commit -m "feat: add bounded AI candidate refinement"
```

### Task 2: Build shared candidate sessions and text-diff rendering

**Files:**
- Create: `assets/js/admin-ai-workflow.js`
- Modify: `admin.html` (load order and shared feedback/diff containers)
- Modify: `assets/css/admin.css` (candidate, diff, feedback and stale-state styles)
- Test: `tests/test_frontend_helpers.py`

**Interfaces:**
- Consumes: existing global `api`, `toast`, `markDirty`, and domain callbacks.
- Produces: `window.AdminAiWorkflow.open(options)`, `AdminAiWorkflow.requestRefinement(session, feedback)`, `AdminAiWorkflow.renderDiff(container, original, candidate)`, and `AdminAiWorkflow.isSnapshotCurrent(session)`.

- [ ] **Step 1: Add failing frontend contract tests** that load the shared script in the existing Node helper harness and assert the exported methods exist, diff output uses text nodes, and stale snapshots return false after the supplied getter changes.

- [ ] **Step 2: Run the focused frontend tests**

```powershell
pytest tests/test_frontend_helpers.py -k "ai_workflow or diff"
```

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement the session object** with `task`, `domain`, `sourceTask`, `original`, `candidate`, `snapshot`, `context`, an `AbortController`, and one feedback input. Abort the previous request for the same editor, discard responses from old sessions, and clear sessions when the record changes.

- [ ] **Step 4: Implement token-level diff rendering** using DOM text nodes and `document.createElement`, with added/deleted/unchanged spans. If input exceeds the safe diff limit or tokenization fails, render escaped original/candidate blocks side by side. Expose an apply callback but never call a save API.

- [ ] **Step 5: Add CSS and load the module** before domain AI modules; keep the existing layout usable on narrow admin screens.

- [ ] **Step 6: Run static checks**

```powershell
node --check assets/js/admin-ai-workflow.js
pytest tests/test_frontend_helpers.py -k "ai_workflow or diff"
```

Expected: PASS.

- [ ] **Step 7: Commit the shared workflow UI**

```powershell
git add assets/js/admin-ai-workflow.js assets/css/admin.css admin.html tests/test_frontend_helpers.py
git commit -m "feat: add reusable AI candidate review workflow"
```

### Task 3: Wire iterative feedback and diffs into essay and copy editors

**Files:**
- Modify: `assets/js/admin-ai.js` (essay candidate session, refinement, diff, apply guards)
- Modify: `assets/js/admin-ai-tools.js` (About, Work, photo-story candidate sessions and refinement)
- Modify: `admin.html` (feedback control and diff region in essay/copy dialogs)
- Modify: `assets/css/admin.css` (domain-specific minor layout rules only if needed)
- Test: `tests/test_browser_smoke.py`

**Interfaces:**
- Consumes: `AdminAiWorkflow` from Task 2 and `/api/ai/essay-assist` / `/api/ai/admin-assist` refine contracts from Task 1.
- Produces: every replaceable candidate has “继续调整”, a feedback field, a diff/全文 view, stale snapshot protection, and an apply action that only marks the form dirty.

- [ ] **Step 1: Extend browser smoke fixtures** to return deterministic refine responses and record all save endpoints, then add failing assertions for a second feedback request, visible added/deleted diff markers, and zero save calls before explicit save.

- [ ] **Step 2: Run the new smoke test**

```powershell
pytest tests/test_browser_smoke.py -k "ai_candidate_workflow" -v
```

Expected: FAIL because the feedback controls and refine request are absent.

- [ ] **Step 3: Wire essay refinement.** Preserve the existing task snapshot and selection range; send `source_task`, `source_content`, current candidate, feedback, title/tags and surrounding context. Render diff for `polish`, `continue`, and summary-like text replacements; keep title/tags/review on their existing specialized renderers.

- [ ] **Step 4: Wire non-essay refinement.** Store the original field value and record identity when opening About, Work, or photo-story suggestions. Pass the current candidate and feedback to the matching domain task. Keep photo-story context limited to existing caption/date/tags and refuse image-detail generation in the UI copy.

- [ ] **Step 5: Guard application.** Before applying, compare the current record identifier and field snapshot. On mismatch, leave the form untouched and ask the user to request a fresh candidate. On success, update only the field, call `markDirty()`, and show “已应用到表单，请手动保存”.

- [ ] **Step 6: Run browser and syntax checks**

```powershell
pytest tests/test_browser_smoke.py -k "ai_candidate_workflow or admin_ai" -v
node --check assets/js/admin-ai.js
node --check assets/js/admin-ai-tools.js
```

Expected: PASS.

- [ ] **Step 7: Commit editor integration**

```powershell
git add admin.html assets/css/admin.css assets/js/admin-ai.js assets/js/admin-ai-tools.js tests/test_browser_smoke.py
git commit -m "feat: make admin AI suggestions iteratively reviewable"
```

### Task 4: Turn dashboard findings into stable repair actions

**Files:**
- Modify: `backend/routes/ai.py` (`_deterministic_content_findings`, `_public_site_audit_context`, audit response)
- Modify: `backend/routes/dashboard.py` (if dashboard payload owns health/summary aggregation)
- Modify: `assets/js/admin-ai-tools.js` (finding rendering and repair actions)
- Modify: `assets/js/admin-dashboard.js` (queue placement and refresh state)
- Modify: `assets/js/admin-tabs.js` (stable tab/record/field navigation event)
- Modify: `admin.html` (repair queue container and action buttons)
- Test: `tests/test_routes.py`
- Test: `tests/test_browser_smoke.py`

**Interfaces:**
- Consumes: current deterministic/AI finding objects and domain editor entry functions.
- Produces: findings with `locator: {domain, record_id, field, task, can_suggest}`; frontend actions `openAdminFinding(finding)` and `suggestAdminFinding(finding)`.

- [ ] **Step 1: Add failing route tests** asserting every deterministic finding has a stable locator, unsupported/ambiguous findings have `can_suggest: false`, protected essays are excluded, and the response contains no file paths or raw content.

- [ ] **Step 2: Run focused route tests**

```powershell
pytest tests/test_routes.py -k "audit or dashboard"
```

Expected: FAIL because locators and capability flags are absent.

- [ ] **Step 3: Add locator metadata at creation time.** Pass domain, record ID and exact field into the `add()` helper; use essay slug, work ID/title key, about singleton, and photo-story ID/index according to existing storage contracts. Only enable candidate generation for text fields with a direct source value.

- [ ] **Step 4: Render the repair queue** with priority, source, issue, and buttons. “去处理” switches to the correct tab and invokes the existing domain editor opener; it must not parse the issue string. “生成修复候选” opens the same workflow session used in Task 3.

- [ ] **Step 5: Add browser smoke coverage** for one deterministic Work issue and one essay metadata issue, checking tab/field focus, candidate generation, and no automatic save.

- [ ] **Step 6: Run route and smoke checks**

```powershell
pytest tests/test_routes.py -k "audit or dashboard" -v
pytest tests/test_browser_smoke.py -k "repair or dashboard" -v
```

Expected: PASS.

- [ ] **Step 7: Commit the repair queue**

```powershell
git add backend/routes/ai.py backend/routes/dashboard.py assets/js/admin-ai-tools.js assets/js/admin-dashboard.js assets/js/admin-tabs.js admin.html tests/test_routes.py tests/test_browser_smoke.py
git commit -m "feat: connect dashboard findings to repair workflow"
```

### Task 5: Full verification and handoff

**Files:**
- Modify: only files exposed by failing verification; do not stage `data/essays.json` or `data/essays_public.json`.
- Test: all existing test suites and CI/browser contracts.

- [ ] **Step 1: Run the complete verification gate**

```powershell
pytest -q
python -m compileall backend manage.py
node --check assets/js/admin-ai-workflow.js
node --check assets/js/admin-ai.js
node --check assets/js/admin-ai-tools.js
python manage.py build
git diff --check
```

- [ ] **Step 2: Run forced Chromium smoke** with `BROWSER_SMOKE_REQUIRED=1` and confirm the admin AI workflow, repair queue, and existing protected-content behavior.

- [ ] **Step 3: Scan the staged diff** for API keys, request bodies in logs, accidental data-file changes, and any automatic save call from an AI apply handler.

- [ ] **Step 4: Commit only verification fixes**

```powershell
git add -u -- backend assets admin.html tests
git diff --cached --check
git commit -m "test: verify AI editorial workflow"
```

- [ ] **Step 5: Report** changed files, test counts, remaining limitations, and the fact that every AI result still requires manual application and saving.
