"""Cheap guardrails for the backend and admin module boundaries."""

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_storage_primitives_do_not_depend_on_project_data_module():
    storage_dir = ROOT / 'backend' / 'storage'
    repository = (storage_dir / 'repository.py').read_text(encoding='utf-8')
    package = (storage_dir / '__init__.py').read_text(encoding='utf-8')
    composition_path = ROOT / 'backend' / 'repositories.py'

    assert 'backend.data' not in repository
    assert 'repository_for' not in repository
    assert 'repository_for' not in package
    assert composition_path.is_file()
    composition = composition_path.read_text(encoding='utf-8')
    assert 'from backend.data import STORE' in composition
    assert 'def repository_for(filename)' in composition


def test_routes_do_not_import_app_module():
    route_sources = list((ROOT / 'backend' / 'routes').glob('*.py')) + [ROOT / 'backend' / 'auth.py']
    assert all('from backend.app import app' not in path.read_text(encoding='utf-8') for path in route_sources)


def test_essay_routes_use_repository_boundary():
    route_dir = ROOT / 'backend' / 'routes'
    context = (route_dir / 'essay_context.py').read_text(encoding='utf-8')
    sources = ''.join(path.read_text(encoding='utf-8') for path in route_dir.glob('essay_*.py'))
    assert "load_json('essays.json')" not in sources
    assert "atomic_write_json('essays.json'" not in sources
    assert 'ESSAY_REPOSITORY = EssayRepository(STORE)' in context


def test_essay_routes_are_split_by_responsibility():
    route_dir = ROOT / 'backend' / 'routes'
    aggregator = (route_dir / 'essays.py').read_text(encoding='utf-8')
    modules = (
        'essay_catalog.py',
        'essay_metadata.py',
        'essay_content.py',
        'essay_media.py',
    )
    assert '@bp.route' not in aggregator
    assert 'from backend.routes.essay_context import bp' in aggregator
    assert 'ESSAY_REPOSITORY' not in aggregator
    for module in modules:
        source = (route_dir / module).read_text(encoding='utf-8')
        assert 'from backend.routes import essay_context' in source
        assert 'from backend.routes.essay_context import ESSAY_REPOSITORY' not in source
        assert len(source.splitlines()) <= 160


def test_photo_routes_are_split_by_responsibility():
    route_dir = ROOT / 'backend' / 'routes'
    aggregator = (route_dir / 'photos.py').read_text(encoding='utf-8')
    modules = ('photo_files.py', 'photo_details.py', 'photo_stories.py')
    assert '@bp.route' not in aggregator
    assert 'from backend.routes.photo_context import bp' in aggregator
    assert 'PHOTO_STORIES_REPOSITORY' not in aggregator
    for module in modules:
        source = (route_dir / module).read_text(encoding='utf-8')
        assert 'from backend.routes import photo_context' in source
        assert 'from backend.routes.photo_context import' not in source
        assert len(source.splitlines()) <= 160


def test_photos_json_has_one_repository_owner():
    checked = [
        *(ROOT / 'backend' / 'routes').glob('photo_*.py'),
        ROOT / 'backend' / 'photo_metadata.py',
        ROOT / 'backend' / 'ssg.py',
        ROOT / 'tools' / 'process_images.py',
    ]
    combined = ''.join(path.read_text(encoding='utf-8') for path in checked)

    assert "load_json('photos.json')" not in combined
    assert "atomic_write_json('photos.json'" not in combined
    assert "repository_for('photos.json')" not in combined
    context = (ROOT / 'backend' / 'routes' / 'photo_context.py').read_text(encoding='utf-8')
    assert 'PHOTO_REPOSITORY' in context


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


def test_essay_tags_are_split_by_responsibility():
    html = (ROOT / 'admin.html').read_text(encoding='utf-8')
    modules = (
        'admin-essay-tag-state.js',
        'admin-essay-taxonomy.js',
        'admin-essay-tag-order.js',
        'admin-essay-tag-actions.js',
    )
    positions = [html.index(f'assets/js/{module}') for module in modules]
    assert positions == sorted(positions)
    assert 'assets/js/admin-essay-tags.js' not in html


def test_photo_editor_is_split_by_responsibility():
    html = (ROOT / 'admin.html').read_text(encoding='utf-8')
    for module in ('admin-photo-list.js', 'admin-photo-tags.js', 'admin-photo-metadata.js', 'admin-photo-files.js'):
        assert f'assets/js/{module}' in html
    assert 'assets/js/admin-photo-editor.js' not in html
