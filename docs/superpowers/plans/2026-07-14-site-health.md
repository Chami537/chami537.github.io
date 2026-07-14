# Site Health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an authenticated, read-only admin health report that detects broken content/file relationships and presents a compact Dashboard summary plus a detailed Health tab.

**Architecture:** A Flask-independent `backend/site_health.py` scans only known project directories and returns a stable JSON-compatible report. A thin blueprint exposes the report, while a dedicated admin JavaScript module renders both the full Health tab and Dashboard summary without injecting untrusted HTML.

**Tech Stack:** Python 3.11, Flask 3.1.3, plain JavaScript/DOM APIs, HTML/CSS, pytest 9.0.3, Playwright smoke tests.

## Global Constraints

- The feature is read-only: it must not delete, rewrite, rebuild, or normalize project files.
- Do not make external HTTP requests or persist scan results.
- Scan only `data/`, `md/`, `essays/`, `images/`, `music/`, `tracks/`, templates, and declared frontend assets under the configured project root.
- Never include passwords, ciphertext bodies, or file contents in API details.
- Keep the UI lightweight and consistent with the current editorial admin styling.
- Preserve all existing API, build, encryption, and public-site behavior.

---

### Task 1: Health report core and JSON/build checks

**Files:**
- Create: `backend/site_health.py`
- Create: `tests/test_site_health.py`

**Interfaces:**
- Consumes: `base_dir: str`, `has_password: Callable[[str], bool]`.
- Produces: `run_site_health(base_dir, has_password) -> dict` with `status`, `summary`, and `checks`.
- Produces internal constructors `_check(id, label, status, message, details=None)` and `_aggregate(checks)` used by later tasks.

- [ ] **Step 1: Write failing aggregation and JSON tests**

```python
from pathlib import Path

from backend.site_health import run_site_health


def write_json(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def test_health_report_aggregates_error_warning_and_passed(tmp_path):
    write_json(tmp_path / 'data' / 'essays.json', '{broken')
    report = run_site_health(str(tmp_path), lambda _slug: False)
    assert report['status'] == 'error'
    assert report['summary']['errors'] >= 1
    assert report['summary']['passed'] >= 1
    assert all(set(item) == {'id', 'label', 'status', 'severity', 'message', 'details'} for item in report['checks'])


def test_json_check_reports_missing_wrong_type_and_invalid_json(tmp_path):
    write_json(tmp_path / 'data' / 'essays.json', '{}')
    write_json(tmp_path / 'data' / 'photos.json', '{broken')
    report = run_site_health(str(tmp_path), lambda _slug: False)
    by_id = {item['id']: item for item in report['checks']}
    assert by_id['data.json']['status'] == 'error'
    assert any('essays.json' in detail for detail in by_id['data.json']['details'])
    assert any('photos.json' in detail for detail in by_id['data.json']['details'])
```

- [ ] **Step 2: Run tests and verify the missing module failure**

Run: `pytest -q tests/test_site_health.py`

Expected: collection fails with `ModuleNotFoundError: No module named 'backend.site_health'`.

- [ ] **Step 3: Implement the report shell and deterministic JSON/build checks**

```python
import json
import os
from pathlib import Path


_DATA_TYPES = {
    'about.json': dict, 'contact.json': list, 'essays.json': list,
    'friends.json': list, 'music.json': list, 'photos.json': list,
    'photo_stories.json': list, 'stack.json': list, 'tracks.json': list,
    'work.json': list,
}
_CORE_FILES = (
    'admin.html', 'index.html', 'templates/essay.html',
    'assets/js/admin-api.js', 'assets/js/admin-ui.js',
    'assets/js/admin-tabs.js', 'assets/css/admin-foundation.css',
)


def _check(check_id, label, status, message, details=None):
    return {
        'id': check_id, 'label': label, 'status': status,
        'severity': 'error' if status == 'error' else 'warning' if status == 'warning' else 'info',
        'message': message, 'details': list(details or []),
    }


def _aggregate(checks):
    counts = {
        'passed': sum(item['status'] == 'passed' for item in checks),
        'warnings': sum(item['status'] == 'warning' for item in checks),
        'errors': sum(item['status'] == 'error' for item in checks),
    }
    status = 'error' if counts['errors'] else 'warning' if counts['warnings'] else 'healthy'
    order = {'error': 0, 'warning': 1, 'passed': 2}
    return {'status': status, 'summary': counts, 'checks': sorted(checks, key=lambda item: order[item['status']])}


def _load_data(root):
    loaded, details = {}, []
    for filename, expected_type in _DATA_TYPES.items():
        path = root / 'data' / filename
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(value, expected_type):
                details.append(f'{filename}: 顶层类型应为 {expected_type.__name__}')
            else:
                loaded[filename] = value
        except FileNotFoundError:
            details.append(f'{filename}: 文件缺失')
        except json.JSONDecodeError:
            details.append(f'{filename}: JSON 无法解析')
    return loaded, _check('data.json', 'JSON 数据', 'error' if details else 'passed', '数据文件存在问题' if details else '数据文件正常', details)


def run_site_health(base_dir, has_password):
    root = Path(base_dir).resolve()
    data, data_check = _load_data(root)
    missing = [relative for relative in _CORE_FILES if not (root / relative).is_file()]
    build_check = _check('build.core', '核心构建文件', 'error' if missing else 'passed', '核心文件缺失' if missing else '核心文件正常', missing)
    checks = [data_check, build_check]
    return _aggregate(checks)
```

- [ ] **Step 4: Run the focused tests**

Run: `pytest -q tests/test_site_health.py`

Expected: both tests pass.

- [ ] **Step 5: Commit the report foundation**

```powershell
git add -- backend/site_health.py tests/test_site_health.py
git commit -m "feat: add site health report core"
```

### Task 2: Essay, media, orphan, and link checks

**Files:**
- Modify: `backend/site_health.py`
- Modify: `tests/test_site_health.py`

**Interfaces:**
- Consumes Task 1's `_check`, `_aggregate`, and loaded data mapping.
- Produces `_check_essays`, `_check_photos`, `_check_photo_stories`, `_check_media`, `_check_orphans`, and `_check_links`, each returning one JSON-compatible check dictionary.

- [ ] **Step 1: Add failing fixture-driven domain tests**

```python
def make_minimal_site(root):
    datasets = {
        'about.json': '{}', 'contact.json': '[]', 'essays.json': '[]',
        'friends.json': '[]', 'music.json': '[]', 'photos.json': '[]',
        'photo_stories.json': '[]', 'stack.json': '[]', 'tracks.json': '[]',
        'work.json': '[]',
    }
    for name, content in datasets.items():
        write_json(root / 'data' / name, content)
    for relative in ('admin.html', 'index.html', 'templates/essay.html', 'assets/js/admin-api.js', 'assets/js/admin-ui.js', 'assets/js/admin-tabs.js', 'assets/css/admin-foundation.css'):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('', encoding='utf-8')


def test_health_detects_broken_essay_photo_music_track_and_link_references(tmp_path):
    make_minimal_site(tmp_path)
    write_json(tmp_path / 'data' / 'essays.json', '[{"slug":"secret","title":"Secret"}]')
    write_json(tmp_path / 'data' / 'photos.json', '[{"filename":"missing.jpg"}]')
    write_json(tmp_path / 'data' / 'photo_stories.json', '[{"id":"s","cover":"missing.jpg","photos":["other.jpg"]}]')
    write_json(tmp_path / 'data' / 'music.json', '[{"id":1,"filename":"missing.mp3"}]')
    write_json(tmp_path / 'data' / 'tracks.json', '[{"file":"missing.gpx"}]')
    write_json(tmp_path / 'data' / 'work.json', '[{"url":"javascript:alert(1)"}]')
    report = run_site_health(str(tmp_path), lambda slug: slug == 'secret')
    by_id = {item['id']: item for item in report['checks']}
    for check_id in ('essays.sources', 'photos.variants', 'photos.stories', 'media.files', 'links.protocols'):
        assert by_id[check_id]['status'] == 'error'


def test_health_reports_orphans_without_exposing_contents(tmp_path):
    make_minimal_site(tmp_path)
    orphan = tmp_path / 'music' / 'orphan.mp3'
    orphan.parent.mkdir(parents=True)
    orphan.write_bytes(b'ID3secret bytes')
    report = run_site_health(str(tmp_path), lambda _slug: False)
    item = next(check for check in report['checks'] if check['id'] == 'media.orphans')
    assert item['status'] == 'warning'
    assert item['details'] == ['music/orphan.mp3']
    assert 'secret bytes' not in str(report)
```

- [ ] **Step 2: Run focused tests and confirm missing check IDs**

Run: `pytest -q tests/test_site_health.py`

Expected: failures show that the domain check IDs are absent.

- [ ] **Step 3: Implement the domain checks and append them in fixed order**

Implement each check with these exact rules:

```python
def _safe_relative(root, path):
    resolved = path.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return None


def _valid_http_url(value):
    return not value or str(value).strip().lower().startswith(('http://', 'https://'))


def _encrypted_source(text):
    import base64
    try:
        raw = base64.b64decode(text.split('\n', 1)[0], validate=True)
        return len(raw) > 17 and raw[0] == 2
    except (ValueError, TypeError):
        return False
```

- `essays.sources`: require a safe `^[a-z0-9-]+$` slug and `md/<slug>.md`; if `essays/` exists but HTML is absent, add a warning detail. Password-protected sources must satisfy `_encrypted_source`; their existing HTML must contain `password-gate`. A source encrypted without a configured password is an error.
- `photos.variants`: for every photo filename require `images/<name>` plus `images/lg`, `images/md`, and `images/sm` variants.
- `photos.stories`: every cover and listed story photo must be present in `photos.json`.
- `media.files`: require every `music.json[].filename` under `music/` and every `tracks.json[].file` under `tracks/`.
- `media.orphans`: compare regular files in `images/lg`, `images/md`, `images/sm`, `music`, and `tracks` with referenced basenames. Ignore names ending in `.tmp`, `.uploading`, or `.deleting`. Report normalized relative names only.
- `links.protocols`: validate non-empty `url` values from work, contact, and friends with `_valid_http_url`.

Append checks in this fixed order after `data.json`: essays, photos, stories, media files, orphans, links, build core. If required JSON data failed to load, the corresponding check returns `warning` with `message='数据不可用，已跳过'` rather than raising.

- [ ] **Step 4: Run health tests and the existing encryption tests**

Run: `pytest -q tests/test_site_health.py tests/test_ssg.py -k "health or encrypt or password"`

Expected: all selected tests pass.

- [ ] **Step 5: Commit complete checks**

```powershell
git add -- backend/site_health.py tests/test_site_health.py
git commit -m "feat: check site content integrity"
```

### Task 3: Authenticated health API

**Files:**
- Create: `backend/routes/health.py`
- Modify: `backend/routes/__init__.py`
- Modify: `tests/test_routes.py`
- Modify: `tests/test_architecture.py`

**Interfaces:**
- Consumes `run_site_health(BASE_DIR, has_essay_password)`.
- Produces authenticated `GET /api/site-health` returning the Task 1 report schema.

- [ ] **Step 1: Add failing route and registration tests**

```python
def test_site_health_requires_auth(client_no_auth):
    assert client_no_auth.get('/api/site-health').status_code == 401


def test_site_health_returns_report(client, monkeypatch):
    import backend.routes.health as health
    expected = {'status': 'healthy', 'summary': {'passed': 1, 'warnings': 0, 'errors': 0}, 'checks': []}
    monkeypatch.setattr(health, 'run_site_health', lambda _root, _lookup: expected)
    response = client.get('/api/site-health')
    assert response.status_code == 200
    assert response.get_json() == expected


def test_site_health_returns_500_for_unexpected_failure(client, monkeypatch):
    import backend.routes.health as health
    monkeypatch.setattr(health, 'run_site_health', lambda _root, _lookup: (_ for _ in ()).throw(RuntimeError('boom')))
    response = client.get('/api/site-health')
    assert response.status_code == 500
    assert response.get_json() == {'error': '健康检查失败'}
```

Add to `tests/test_architecture.py`:

```python
def test_health_route_uses_service_boundary():
    source = (ROOT / 'backend' / 'routes' / 'health.py').read_text(encoding='utf-8')
    assert 'run_site_health' in source
    assert 'os.walk' not in source
```

- [ ] **Step 2: Run route tests and confirm import/404 failures**

Run: `pytest -q tests/test_routes.py -k site_health tests/test_architecture.py`

Expected: the health module import or route lookup fails before implementation.

- [ ] **Step 3: Implement and register the thin blueprint**

```python
from flask import Blueprint, jsonify

from backend.data import BASE_DIR, has_essay_password
from backend.site_health import run_site_health

bp = Blueprint('health', __name__)


@bp.route('/api/site-health', methods=['GET'])
def site_health():
    try:
        return jsonify(run_site_health(BASE_DIR, has_essay_password))
    except Exception:
        return jsonify({'error': '健康检查失败'}), 500
```

Import `health` in `backend/routes/__init__.py` and insert `health.bp` into `_BLUEPRINTS` after `dashboard.bp`.

- [ ] **Step 4: Run route, architecture, and full backend tests**

Run: `pytest -q tests/test_routes.py tests/test_architecture.py tests/test_site_health.py`

Expected: all tests pass.

- [ ] **Step 5: Commit the API**

```powershell
git add -- backend/routes/health.py backend/routes/__init__.py tests/test_routes.py tests/test_architecture.py
git commit -m "feat: expose authenticated site health API"
```

### Task 4: Health tab and safe DOM renderer

**Files:**
- Create: `assets/js/admin-health.js`
- Create: `assets/css/admin-health.css`
- Modify: `admin.html`
- Modify: `assets/js/admin-tabs.js`
- Modify: `tests/test_architecture.py`
- Modify: `tests/test_browser_smoke.py`

**Interfaces:**
- Consumes `api('GET', '/api/site-health')` and Task 1 report schema.
- Produces `loadSiteHealth()`, `renderSiteHealth(report)`, and `loadDashboardHealth()` globals.

- [ ] **Step 1: Add failing static-order and browser tests**

Add architecture assertions that `admin-health.js` is loaded after `admin-api.js` and before `admin-tabs.js`, the Health tab exists, and `_loadTab` calls `loadSiteHealth()`.

Add this browser smoke flow:

```python
def test_admin_health_tab_renders_and_refreshes(live_server, browser):
    page = browser.new_page()
    try:
        page.goto(live_server + '/', wait_until='networkidle')
        page.locator('.tab-btn[data-tab="health"]').click()
        page.locator('#health-content').wait_for(state='visible')
        assert page.locator('#health-checks .health-check').count() > 0
        page.locator('#health-refresh').click()
        page.locator('#health-content').wait_for(state='visible')
    finally:
        page.close()
```

- [ ] **Step 2: Run tests and confirm missing Health UI**

Run: `pytest -q tests/test_architecture.py tests/test_browser_smoke.py -k health`

Expected: failures report missing Health tab/module/elements.

- [ ] **Step 3: Add markup, module loading, and tab orchestration**

Add a `Health` tab button after Dashboard. Add `#tab-health` containing `#health-loading`, `#health-error`, `#health-content`, `#health-summary`, `#health-checks`, and a `#health-refresh` button calling `loadSiteHealth()`.

Load `assets/css/admin-health.css` after `admin-foundation.css`. Load `assets/js/admin-health.js` after `admin-dashboard.js` and before `admin-tabs.js`. Add this branch to `_loadTab`:

```javascript
if (name === 'health') loadSiteHealth();
```

- [ ] **Step 4: Implement DOM-only rendering**

```javascript
function _healthState(state, message) {
  document.getElementById('health-loading').hidden = state !== 'loading';
  document.getElementById('health-error').hidden = state !== 'error';
  document.getElementById('health-content').hidden = state !== 'ready';
  if (state === 'error') document.getElementById('health-error').textContent = message;
}

function _healthCheckNode(item) {
  var card = document.createElement('section');
  card.className = 'health-check health-' + item.status;
  var title = document.createElement('strong');
  title.textContent = item.label;
  var message = document.createElement('p');
  message.textContent = item.message;
  card.append(title, message);
  if (item.details && item.details.length) {
    var details = document.createElement('details');
    var summary = document.createElement('summary');
    summary.textContent = item.details.length + ' 项详情';
    var list = document.createElement('ul');
    item.details.forEach(function(detail) {
      var row = document.createElement('li');
      row.textContent = detail;
      list.appendChild(row);
    });
    details.append(summary, list);
    card.appendChild(details);
  }
  return card;
}

function renderSiteHealth(report) {
  var summary = document.getElementById('health-summary');
  summary.textContent = '错误 ' + report.summary.errors + ' · 警告 ' + report.summary.warnings + ' · 通过 ' + report.summary.passed;
  var checks = document.getElementById('health-checks');
  checks.replaceChildren();
  report.checks.forEach(function(item) { checks.appendChild(_healthCheckNode(item)); });
}

async function loadSiteHealth() {
  _healthState('loading');
  try {
    var report = await api('GET', '/api/site-health');
    renderSiteHealth(report);
    _healthState('ready');
  } catch (error) {
    _healthState('error', '健康检查失败：' + (error.message || '未知错误'));
  }
}
```

Style `.health-summary`, `.health-check`, status borders, detail lists, and the responsive header using existing color variables. Do not use charts, fixed panels, or inline styles.

- [ ] **Step 5: Run JavaScript and browser checks**

Run: `node --check assets/js/admin-health.js; pytest -q tests/test_architecture.py tests/test_browser_smoke.py -k health`

Expected: syntax and selected tests pass.

- [ ] **Step 6: Commit the Health tab**

```powershell
git add -- admin.html assets/js/admin-health.js assets/js/admin-tabs.js assets/css/admin-health.css tests/test_architecture.py tests/test_browser_smoke.py
git commit -m "feat: add admin health tab"
```

### Task 5: Dashboard health summary and release verification

**Files:**
- Modify: `admin.html`
- Modify: `assets/js/admin-health.js`
- Modify: `tests/test_browser_smoke.py`
- Modify: `tests/test_ssg.py`

**Interfaces:**
- Consumes Task 4's `/api/site-health` response and renderer state.
- Produces `loadDashboardHealth()` and `#dashboard-health-summary`; does not change `/api/dashboard-stats`.

- [ ] **Step 1: Add failing Dashboard summary tests**

Add static assertions that `admin.html` contains `dashboard-health-summary` and `admin-health.js`. Extend the existing Dashboard browser smoke test:

```python
page.locator('#dashboard-health-summary').wait_for(state='visible')
assert page.locator('#dashboard-health-summary').text_content().strip()
```

- [ ] **Step 2: Run tests and confirm the missing summary**

Run: `pytest -q tests/test_ssg.py -k dashboard tests/test_browser_smoke.py -k dashboard`

Expected: failure reports missing `dashboard-health-summary`.

- [ ] **Step 3: Implement the compact Dashboard summary**

Add a small Dashboard section with `#dashboard-health-summary` and a button calling `switchTab('health')`. Implement:

```javascript
function _healthSummaryText(report) {
  if (report.status === 'healthy') return '站点健康 · ' + report.summary.passed + ' 项检查通过';
  return '错误 ' + report.summary.errors + ' · 警告 ' + report.summary.warnings;
}

async function loadDashboardHealth() {
  var element = document.getElementById('dashboard-health-summary');
  if (!element) return;
  element.textContent = '正在检查...';
  try {
    var report = await api('GET', '/api/site-health');
    element.textContent = _healthSummaryText(report);
    element.dataset.status = report.status;
  } catch (error) {
    element.textContent = '健康状态暂不可用';
    element.dataset.status = 'error';
  }
}
```

Call `loadDashboardHealth()` from the existing startup line and whenever the Dashboard tab loads. Do not merge this data into `/api/dashboard-stats`.

- [ ] **Step 4: Run complete verification**

Run:

```powershell
pytest -q
Get-ChildItem assets\js\*.js | ForEach-Object { node --check $_.FullName }
python -m compileall -q backend manage.py tools
git diff --check
& (Get-Content graphify-out\.graphify_python) -m graphify update .
```

Expected: all tests pass, all syntax checks succeed, diff check is clean, and Graphify reports a non-empty updated graph without warnings.

- [ ] **Step 5: Review security and scope**

Confirm from the final diff that the feature exposes only normalized relative names, never passwords/content, performs no writes, makes no external requests, and stages no generated/data files.

- [ ] **Step 6: Commit and push**

```powershell
git add -- admin.html assets/js/admin-health.js tests/test_browser_smoke.py tests/test_ssg.py
git commit -m "feat: show health summary on dashboard"
git push origin master
```
