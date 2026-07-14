import json

from backend.site_health import run_site_health


def _write_json(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def _make_minimal_site(root):
    datasets = {
        'about.json': '{}', 'contact.json': '[]', 'essays.json': '[]',
        'friends.json': '[]', 'music.json': '[]', 'photos.json': '[]',
        'photo_stories.json': '[]', 'stack.json': '[]', 'tracks.json': '[]',
        'work.json': '[]',
    }
    for name, content in datasets.items():
        _write_json(root / 'data' / name, content)
    for relative in (
        'admin.html', 'index.html', 'templates/essay.html',
        'assets/js/admin-api.js', 'assets/js/admin-ui.js',
        'assets/js/admin-tabs.js', 'assets/js/admin-health.js',
        'assets/css/admin-foundation.css', 'assets/css/admin-health.css',
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('', encoding='utf-8')


def test_health_report_aggregates_error_warning_and_passed(tmp_path):
    _make_minimal_site(tmp_path)
    _write_json(tmp_path / 'data' / 'essays.json', '{broken')

    report = run_site_health(str(tmp_path), lambda _slug: False)

    assert report['status'] == 'error'
    assert report['summary']['errors'] >= 1
    assert report['summary']['passed'] >= 1
    assert all(
        set(item) == {'id', 'label', 'status', 'severity', 'message', 'details'}
        for item in report['checks']
    )


def test_json_check_reports_missing_wrong_type_and_invalid_json(tmp_path):
    _make_minimal_site(tmp_path)
    _write_json(tmp_path / 'data' / 'essays.json', '{}')
    _write_json(tmp_path / 'data' / 'photos.json', '{broken')

    report = run_site_health(str(tmp_path), lambda _slug: False)
    by_id = {item['id']: item for item in report['checks']}

    assert by_id['data.json']['status'] == 'error'
    assert any('essays.json' in detail for detail in by_id['data.json']['details'])
    assert any('photos.json' in detail for detail in by_id['data.json']['details'])


def test_health_detects_referenced_files_stories_links_and_orphans(tmp_path):
    _make_minimal_site(tmp_path)
    _write_json(tmp_path / 'data' / 'photos.json', json.dumps([
        {'filename': 'ok.jpg'},
    ]))
    _write_json(tmp_path / 'data' / 'photo_stories.json', json.dumps([
        {'id': 'story-1', 'photos': ['ok.jpg', 'missing.jpg']},
    ]))
    _write_json(tmp_path / 'data' / 'music.json', json.dumps([
        {'filename': 'song.mp3'},
    ]))
    _write_json(tmp_path / 'data' / 'tracks.json', json.dumps([
        {'file': 'route.gpx'},
    ]))
    _write_json(tmp_path / 'data' / 'work.json', json.dumps([
        {'url': 'javascript:alert(1)'},
    ]))
    (tmp_path / 'images' / 'lg').mkdir(parents=True)
    (tmp_path / 'images' / 'lg' / 'orphan.jpg').write_bytes(b'image')

    report = run_site_health(str(tmp_path), lambda _slug: False)
    by_id = {item['id']: item for item in report['checks']}

    assert by_id['photos.variants']['status'] == 'error'
    assert by_id['photos.stories']['status'] == 'error'
    assert by_id['media.files']['status'] == 'error'
    assert by_id['links.protocols']['status'] == 'warning'
    assert by_id['media.orphans']['status'] == 'warning'
    assert 'orphan.jpg' in '\n'.join(by_id['media.orphans']['details'])


def test_health_checks_encrypted_source_without_leaking_content(tmp_path):
    _make_minimal_site(tmp_path)
    secret = 'private essay body that must not be returned'
    encoded = __import__('base64').b64encode(bytes([2]) + b'x' * 17 + secret.encode()).decode()
    _write_json(tmp_path / 'data' / 'essays.json', json.dumps([{'slug': 'private-note'}]))
    _write_json(tmp_path / 'data' / 'work.json', json.dumps([{'url': 'https://example.com'}]))
    _write_json(tmp_path / 'data' / 'contact.json', '[]')
    _write_json(tmp_path / 'data' / 'friends.json', '[]')
    _write_json(tmp_path / 'data' / 'photo_stories.json', '[]')
    (tmp_path / 'md').mkdir()
    (tmp_path / 'md' / 'private-note.md').write_text(encoded, encoding='utf-8')

    report = run_site_health(str(tmp_path), lambda _slug: True)
    serialized = json.dumps(report, ensure_ascii=False)
    assert secret not in serialized
    assert report['status'] == 'healthy'
