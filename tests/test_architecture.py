"""Cheap guardrails for the backend and admin module boundaries."""

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_routes_do_not_import_app_module():
    route_sources = list((ROOT / 'backend' / 'routes').glob('*.py')) + [ROOT / 'backend' / 'auth.py']
    assert all('from backend.app import app' not in path.read_text(encoding='utf-8') for path in route_sources)


def test_essay_routes_use_repository_boundary():
    source = (ROOT / 'backend' / 'routes' / 'essays.py').read_text(encoding='utf-8')
    assert "load_json('essays.json')" not in source
    assert "atomic_write_json('essays.json'" not in source
    assert 'ESSAY_REPOSITORY' in source


def test_admin_shared_modules_load_before_domain_modules():
    html = (ROOT / 'admin.html').read_text(encoding='utf-8')
    api_pos = html.index('assets/js/admin-api.js')
    ui_pos = html.index('assets/js/admin-ui.js')
    domain_pos = html.index('assets/js/admin-dashboard.js')
    assert api_pos < domain_pos
    assert ui_pos < domain_pos


def test_health_route_and_admin_module_are_registered():
    route_source = (ROOT / 'backend' / 'routes' / 'health.py').read_text(encoding='utf-8')
    init_source = (ROOT / 'backend' / 'routes' / '__init__.py').read_text(encoding='utf-8')
    html = (ROOT / 'admin.html').read_text(encoding='utf-8')
    tabs = (ROOT / 'assets' / 'js' / 'admin-tabs.js').read_text(encoding='utf-8')
    assert "'/api/site-health'" in route_source
    assert 'health.bp' in init_source
    assert 'data-tab="health"' in html
    assert 'assets/js/admin-health.js' in html
    assert "name === 'health'" in tabs


def test_admin_domain_modules_are_loaded_explicitly():
    html = (ROOT / 'admin.html').read_text(encoding='utf-8')
    for module in ('admin-about.js', 'admin-tracks.js', 'admin-readme.js', 'admin-editor-rendering.js'):
        assert f'assets/js/{module}' in html
    assert 'assets/js/admin.js' not in html


def test_essay_editor_is_split_by_responsibility():
    html = (ROOT / 'admin.html').read_text(encoding='utf-8')
    for module in ('admin-essay-meta.js', 'admin-essay-content.js', 'admin-essay-formatting.js', 'admin-essay-media.js'):
        assert f'assets/js/{module}' in html
    assert 'assets/js/admin-essay-editor.js' not in html
