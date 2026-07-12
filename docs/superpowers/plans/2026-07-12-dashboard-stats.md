# Admin Dashboard Stats Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a private admin dashboard overview with current content counts, essay tag distribution, and recently updated essays/photo stories.

**Architecture:** Add a focused Flask route module that aggregates existing JSON data behind the existing global admin auth guard. Add a focused browser module and a new Dashboard tab in the existing admin page; the browser requests one endpoint and renders independent loading, success, empty, and error states.

**Tech Stack:** Flask, existing JSON helpers, vanilla HTML/CSS/JavaScript, pytest, Node syntax checks.

## Global Constraints

- Do not add a database or dependency.
- Keep dashboard data private to authenticated admin API requests.
- Do not modify public static pages or existing CRUD contracts.
- Show current totals and recent updates only; do not add historical trends or polling.
- Preserve existing dirty-worktree changes and stage only feature files.

---

### Task 1: Add failing API aggregation tests

**Files:**
- Modify: `tests/test_routes.py`
- Test data: existing `data_backup` fixture and temporary JSON overrides used by route tests

**Interfaces:**
- Consumes: planned `GET /api/dashboard-stats` endpoint.
- Produces: executable expectations for authentication, aggregate counts, deterministic tag sorting, recent-item sorting, and read failures.

- [ ] **Step 1: Inspect existing route-test fixtures and add endpoint tests**

Add tests beside the existing route API tests. Cover these exact behaviors:

```python
def test_dashboard_stats_requires_auth(client):
    app.config['TESTING'] = False
    response = client.get('/api/dashboard-stats')
    assert response.status_code == 401


def test_dashboard_stats_aggregates_content(client):
    response = client.get('/api/dashboard-stats')
    assert response.status_code == 200
    body = response.get_json()
    assert body['counts']['essays']['total'] == len(load_json('essays.json'))
    assert body['counts']['essays']['public'] == body['counts']['essays']['total']
    assert body['counts']['photos'] == len(load_json('photos.json'))
    assert body['counts']['photo_stories'] == len(load_json('photo_stories.json'))
    assert body['counts']['work'] == len(load_json('work.json'))
    assert body['counts']['music'] == len(load_json('music.json'))
    assert body['counts']['friends'] == len(load_json('friends.json'))
    assert body['counts']['stack'] == len(load_json('stack.json'))
    assert body['tags'] == sorted(body['tags'], key=lambda item: (-item['count'], item['name']))
```

Use the existing test fixture conventions to avoid mutating repository data. Derive expected counts from the fixture data rather than hardcoding repository totals. Assert that `recent` is date-descending and includes both `essay` and `photo_story` when fixture data has both.

Add a test that monkeypatches the dashboard module's `load_json` to raise `OSError` and expects a 500 response with an `error` key.

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_routes.py -k dashboard_stats -q
```

Expected: FAIL because `/api/dashboard-stats` is not registered.

### Task 2: Implement the private dashboard stats endpoint

**Files:**
- Create: `backend/routes/dashboard.py`
- Modify: `backend/routes/__init__.py`
- Test: `tests/test_routes.py`

**Interfaces:**
- Consumes: `backend.data.load_json`, `backend.data.DATA_DIR`, and existing essay parsing/password helpers.
- Produces: `GET /api/dashboard-stats` returning `{counts, tags, recent}`.

- [ ] **Step 1: Add the route module and register it**

Create `backend/routes/dashboard.py` with a single route and small private helpers:

```python
@app.route('/api/dashboard-stats', methods=['GET'])
def dashboard_stats():
    essays = load_json('essays.json')
    photos = load_json('photos.json')
    stories = load_json('photo_stories.json')
    work = load_json('work.json')
    music = load_json('music.json')
    friends = load_json('friends.json')
    stack = load_json('stack.json')
    return jsonify({
        'counts': _build_counts(essays, photos, stories, work, music, friends, stack),
        'tags': _essay_tag_counts(essays),
        'recent': _recent_items(essays, stories),
    })
```

Register the module in `backend/routes/__init__.py` so Flask imports it with the other route modules. Rely on `backend.app._require_auth` for the private boundary; do not create a second authentication mechanism.

- [ ] **Step 2: Implement deterministic aggregation**

Implement `_build_counts` with these rules:

- Essay `total` is the full essay list length.
- `hidden` counts truthy `hidden` values.
- `encrypted` counts `has_essay_password(slug)`.
- `public` counts essays that are neither hidden nor encrypted.
- `photos`, `photo_stories`, `work`, `music`, `friends`, and `stack` are list lengths.
- `places` counts photos with a valid `exif.gps` object containing both `lat` and `lng`; count each photo once.

Implement `_essay_tag_counts` by splitting each essay's `tag` string with the existing comma conventions, trimming whitespace, ignoring empty labels, and sorting by descending count then ascending name. Return objects shaped as `{'name': label, 'count': count}`.

Implement `_recent_items` by normalizing essay `date` and story `date` values through a local sortable key that handles ISO-like essay dates and month-name story dates without throwing. Return at most 8 items, with essays shaped as `{'type': 'essay', 'title': ..., 'date': ..., 'url': '/essays/<slug>.html'}` and stories shaped as `{'type': 'photo_story', 'title': ..., 'date': ..., 'url': '/index.html#photos'}`. Use stable source-order tie-breaking.

Wrap the aggregate read in `try/except (OSError, ValueError, TypeError, KeyError)` and return `jsonify({'error': '无法读取统计数据'}), 500` so malformed or unavailable data fails clearly.

- [ ] **Step 3: Run focused tests and make them pass**

Run:

```powershell
python -m pytest tests/test_routes.py -k dashboard_stats -q
```

Expected: all dashboard stats tests pass.

### Task 3: Add the admin dashboard UI module

**Files:**
- Create: `assets/js/admin-dashboard.js`
- Modify: `admin.html`
- Modify: `assets/css/admin.css`
- Test: `tests/test_ssg.py`

**Interfaces:**
- Consumes: `/api/dashboard-stats` via the existing global `api()` helper.
- Produces: `loadDashboard()` and accessible dashboard markup for the new active tab.

- [ ] **Step 1: Add static UI contract tests**

Add tests asserting that `admin.html` contains a Dashboard tab, `tab-dashboard`, the stats sections, and the new script; assert that `admin-dashboard.js` references `/api/dashboard-stats`, renders `counts`, `tags`, `recent`, and has an error path.

- [ ] **Step 2: Add dashboard markup and script loading**

Make Dashboard the first active tab in `admin.html`, add the `tab-dashboard` panel before Work, and include containers with stable IDs:

```html
<div id="dashboard-loading" class="dashboard-state">加载中...</div>
<div id="dashboard-error" class="dashboard-state dashboard-error" hidden></div>
<div id="dashboard-content" hidden>
  <div id="dashboard-counts" class="dashboard-count-grid"></div>
  <div id="dashboard-essay-status" class="dashboard-stat-list"></div>
  <div id="dashboard-tags" class="dashboard-tag-list"></div>
  <div id="dashboard-recent" class="dashboard-recent-list"></div>
</div>
```

Load `assets/js/admin-dashboard.js` after `admin.js` and before the other admin modules. Change the inline startup call to `refreshGitStatus();loadDashboard();`.

- [ ] **Step 3: Implement loading, rendering, and failure states**

Implement `loadDashboard()` to call `api('GET', '/api/dashboard-stats')`, toggle the three top-level states, and render all values with text nodes or the existing `esc()` helper. Render links with fixed same-origin paths from the API response; do not insert untrusted HTML as markup. Empty tags and recent items should show the existing muted empty-state treatment. Catch errors and show `统计加载失败：` plus the error message while leaving other tabs usable.

- [ ] **Step 4: Add restrained responsive styles**

Add dashboard-specific classes to `assets/css/admin.css`: a four-column count grid collapsing to two columns on narrow screens, compact status rows, tag rows, recent links, loading/error states, and a mobile breakpoint. Reuse `--card-bg`, `--border`, `--muted`, and existing card typography; do not introduce a new visual system.

- [ ] **Step 5: Run syntax and static checks**

Run:

```powershell
node --check assets/js/admin-dashboard.js
python -m pytest tests/test_ssg.py -k dashboard -q
```

Expected: no syntax errors and all dashboard markup assertions pass.

### Task 4: Integrate and verify the feature

**Files:**
- Modify: `admin.html` if the build cache-bust step changes its asset query strings
- Modify: `assets/js/admin-dashboard.js` only for fixes found during verification
- Modify: `backend/routes/dashboard.py` only for fixes found during verification
- Test: `tests/test_routes.py`, `tests/test_ssg.py`

- [ ] **Step 1: Run the complete test suite**

Run:

```powershell
python -m pytest
```

Expected: all tests pass, including the existing 134-test baseline plus new dashboard tests.

- [ ] **Step 2: Run the SSG build and inspect the worktree**

Run:

```powershell
python manage.py build
git status --short
git diff --check
```

Confirm the build does not place dashboard markup or stats in public generated output, and stage only the dashboard feature files plus intentional cache-bust changes.

- [ ] **Step 3: Commit the implementation**

```powershell
git add backend/routes/dashboard.py backend/routes/__init__.py assets/js/admin-dashboard.js assets/css/admin.css admin.html tests/test_routes.py tests/test_ssg.py
git commit -m "feat: add admin content dashboard"
```
