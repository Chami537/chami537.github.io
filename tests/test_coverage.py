"""Additional test coverage."""
import io
import os
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from pathlib import Path

import pytest
from PIL import Image

from backend.data import DATA_DIR
from backend.data import load_json


def test_photo_cards_fall_back_to_exif_date():
    source = Path('assets/js/index-photo-gallery.js').read_text(encoding='utf-8')
    assert 'function _photoDate(photo, exif)' in source
    assert "var date = photo.date || exif.date || '';" in source
    assert "var match = date.match(/^(\\d{4})-(\\d{1,2})-(\\d{1,2})/);" in source
    assert "months[+match[2] - 1]" in source
    assert "var dateHtml = meta.date ?" in source


def test_admin_photo_cards_format_exif_date_without_camera_model():
    source = Path('assets/js/admin-photo-list.js').read_text(encoding='utf-8')
    assert "var displayDate = photo.date || (photo.exif && photo.exif.date) || '';" in source
    assert "var match = displayDate.match(/^(\\d{4})-(\\d{1,2})-(\\d{1,2})/);" in source
    assert "MONTHS_ARR[+match[2] - 1]" in source
    assert "photo.exif.camera" not in source


def test_admin_photo_editor_uses_exif_date_and_clears_stale_marker():
    source = Path('assets/js/admin-photo-metadata.js').read_text(encoding='utf-8')
    assert "var currentDate = photo.date || (photo.exif && photo.exif.date) || '';" in source
    assert "_editorMap.removeLayer(_editorMarker);" in source
    assert "_editorMarker = null;" in source


def test_photo_maps_use_reliable_tiles_and_marker_assets():
    admin_source = Path('assets/js/admin-photo-metadata.js').read_text(encoding='utf-8')
    story_source = Path('assets/js/admin-photo-stories.js').read_text(encoding='utf-8')
    index_source = Path('assets/js/index-photo-map.js').read_text(encoding='utf-8')
    template_source = Path('templates/map.html').read_text(encoding='utf-8')
    assert 'basemaps.cartocdn.com/light_all' in admin_source
    assert 'basemaps.cartocdn.com/light_all' in index_source
    assert 'basemaps.cartocdn.com/light_all' in template_source
    assert "className: 'custom-marker'" in story_source
    assert "className: 'custom-marker'" in index_source


def test_admin_csp_allows_external_map_tiles():
    source = Path('admin.html').read_text(encoding='utf-8')
    assert "img-src 'self' data: blob: https:" in source


def test_admin_highlight_uses_browser_build_and_cdn_csp():
    source = Path('admin.html').read_text(encoding='utf-8')
    assert 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js' in source
    assert 'common.min.js' not in source
    assert "connect-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com" in source


def test_photo_gps_link_scrolls_map_into_view():
    source = Path('assets/js/index-photo-map.js').read_text(encoding='utf-8')
    assert "var mapContainer = document.getElementById('photo-map-container');" in source
    assert "mapContainer.scrollIntoView({behavior:'smooth', block:'start'});" in source


def test_photo_maps_hide_leaflet_attribution_control():
    index_source = Path('assets/js/index-photo-map.js').read_text(encoding='utf-8')
    admin_source = Path('assets/js/admin-photo-metadata.js').read_text(encoding='utf-8')
    template_source = Path('templates/map.html').read_text(encoding='utf-8')
    for source in (index_source, admin_source, template_source):
        assert 'attributionControl: false' in source


def test_photo_stories_get(client):
    r = client.get('/api/photo-stories')
    assert r.status_code == 200
    assert isinstance(r.json, list)


def test_photo_stories_put(client, data_backup):
    filename = load_json('photos.json')[0]['filename']
    stories = [{'id': 'x', 'name': 'T', 'date': '2026-01', 'cover': filename, 'caption': 'x', 'photos': [filename, filename]}]
    r = client.put('/api/photo-stories', json=stories)
    assert r.status_code == 200
    r2 = client.get('/api/photo-stories')
    assert len(r2.json) == 1
    assert r2.json[0]['photos'] == [filename]
    assert r2.json[0]['photo_count'] == 1


def test_photo_stories_put_rejects_non_list(client):
    r = client.put('/api/photo-stories', json={'x': 1})
    assert r.status_code == 400


def test_photo_stories_put_rejects_unknown_photo(client, data_backup):
    stories = [{'id': 'x', 'name': 'T', 'photos': ['missing.jpg']}]
    r = client.put('/api/photo-stories', json=stories)
    assert r.status_code == 400
    assert 'unknown photo' in r.json['error']


def test_photo_stories_put_defaults_cover(client, data_backup):
    filename = load_json('photos.json')[0]['filename']
    stories = [{'id': 'x', 'name': 'T', 'photos': [filename]}]
    r = client.put('/api/photo-stories', json=stories)
    assert r.status_code == 200
    assert r.json['stories'][0]['cover'] == filename


def test_photo_stories_put_rejects_path_cover(client, data_backup):
    filename = load_json('photos.json')[0]['filename']
    stories = [{'id': 'x', 'name': 'T', 'cover': '../' + filename, 'photos': [filename]}]
    r = client.put('/api/photo-stories', json=stories)
    assert r.status_code == 400
    assert 'invalid cover' in r.json['error']


def test_essay_preview_html(client):
    r = client.post('/api/essays/x/html', json={'md': '# H' + chr(10) + 'W'})
    assert r.status_code == 200
    assert 'html' in r.json


def test_essay_preview_html_get(client):
    r = client.get('/api/essays/x/html?md=hi')
    assert r.status_code == 200


def test_essay_preview_html_rejects_non_object(client):
    r = client.post('/api/essays/x/html', json='x', headers={'Content-Type': 'application/json'})
    assert r.status_code == 400


def test_essay_set_password_404(client):
    r = client.post('/api/essays/__x__/password', json={'password': 's'})
    assert r.status_code == 404


def test_essay_content_update_404(client):
    r = client.put('/api/essays/__x__/content', json={'content': 't'})
    assert r.status_code == 404


def test_assets_route_serves_frontend_files(client):
    r = client.get('/assets/js/index.js')
    assert r.status_code == 200
    assert b'buildEssayFilter' in r.data


def test_git_revert(client):
    r = client.post('/api/git/revert', json={'confirm': True})
    assert r.status_code == 200


def test_git_push(client):
    r = client.post('/api/git/push')
    assert r.status_code == 200


def test_contact_update_not_found(client):
    r = client.put('/api/contact/99999', json={'label': 'X'})
    assert r.status_code == 404

def test_friend_delete_not_found(client):
    r = client.delete('/api/friends/99999')
    assert r.status_code == 404


def test_list_essays_has_password_set(client):
    r = client.get('/api/essays')
    assert r.status_code == 200
    for e in r.json:
        assert 'password_set' in e
        assert 'password' not in e


def test_photo_upload_no_file(client):
    r = client.post('/api/photos/upload')
    assert r.status_code == 400


def test_photo_upload_preserves_exif(client, tmp_path, monkeypatch):
    from backend.routes import photo_context
    from backend.photo_repository import PhotoRepository
    from backend.storage import JsonStore

    source = Image.new('RGB', (10, 10), color='red')
    exif = source.getexif()
    exif[271] = 'OnePlus'
    exif[272] = 'OnePlus 13'
    exif[34665] = {34855: 3200, 36867: '2026:06:26 18:40:00'}
    source_bytes = io.BytesIO()
    source.save(source_bytes, 'JPEG', exif=exif.tobytes())
    source_bytes.seek(0)

    image_dir = tmp_path / 'images'
    base_dir = tmp_path
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    repository = PhotoRepository(JsonStore(data_dir))
    monkeypatch.setattr(photo_context, 'IMAGES_DIR', str(image_dir))
    monkeypatch.setattr(photo_context, 'BASE_DIR', str(base_dir))
    monkeypatch.setattr(photo_context, 'PHOTO_REPOSITORY', repository)

    response = client.post(
        '/api/photos/upload',
        data={'file': (source_bytes, 'camera.jpg')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 201
    filename = response.json['filename']
    assert response.json['exif']['date'] == '2026-06-26 18:40'
    assert repository.list()[0]['date'] == 'Jun 26, 2026'
    assert 'camera' not in response.json['exif']
    assert 'model' not in response.json['exif']
    with Image.open(base_dir / 'raw_photos' / filename) as uploaded:
        assert uploaded.getexif().get(272) == 'OnePlus 13'


def test_photo_upload_cleans_files_when_metadata_save_fails(client, tmp_path, monkeypatch):
    from backend.routes import photo_context, photo_files

    source = Image.new('RGB', (10, 10), color='blue')
    source_bytes = io.BytesIO()
    source.save(source_bytes, 'JPEG')
    source_bytes.seek(0)

    image_dir = tmp_path / 'images'
    base_dir = tmp_path
    monkeypatch.setattr(photo_context, 'IMAGES_DIR', str(image_dir))
    monkeypatch.setattr(photo_context, 'BASE_DIR', str(base_dir))
    monkeypatch.setattr(photo_files.uuid, 'uuid4', lambda: SimpleNamespace(hex='rollback12345678'))

    class FailingRepository:
        def append(self, _entry):
            raise RuntimeError('metadata save failed')

    monkeypatch.setattr(photo_context, 'PHOTO_REPOSITORY', FailingRepository())
    with pytest.raises(RuntimeError, match='metadata save failed'):
        client.post(
            '/api/photos/upload',
            data={'file': (source_bytes, 'rollback.jpg')},
            content_type='multipart/form-data',
        )

    assert not [path for path in image_dir.rglob('*') if path.is_file()]
    raw_dir = base_dir / 'raw_photos'
    assert not [path for path in raw_dir.rglob('*') if path.is_file()]


def test_parallel_photo_metadata_appends_are_serialized(monkeypatch):
    from backend.routes import photo_context, photo_files
    from backend.photo_repository import PhotoRepository

    state = []

    class SlowStore:
        def read(self, _name):
            snapshot = state.copy()
            time.sleep(0.01)
            return snapshot

        def write(self, _name, data):
            state[:] = data

    monkeypatch.setattr(photo_context, 'PHOTO_REPOSITORY', PhotoRepository(SlowStore()))
    entries = [{'filename': f'{index}.jpg'} for index in range(6)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(photo_files._append_photo_entry, entries))

    assert sorted(item['filename'] for item in state) == [f'{index}.jpg' for index in range(6)]

def test_essay_image_upload_no_file(client):
    r = client.post('/api/essays/upload-image')
    assert r.status_code == 400


def test_essay_image_upload_rejects_fake_image(client, monkeypatch):
    """Essay image uploads must validate file contents, not just the extension."""
    from backend.data import IMAGES_DIR
    import backend.routes.essay_media as essay_media_route

    monkeypatch.setattr(essay_media_route.uuid, 'uuid4', lambda: SimpleNamespace(hex='badimagebadimage'))
    path = os.path.join(IMAGES_DIR, 'essays', 'badimage.jpg')
    try:
        r = client.post(
            '/api/essays/upload-image',
            data={'file': (io.BytesIO(b'not really a jpeg'), 'bad.jpg')},
            content_type='multipart/form-data',
        )
        assert r.status_code == 400
        assert 'Invalid' in r.json.get('error', '')
        assert not os.path.exists(path)
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_music_upload_rejects_fake_mp3(client, monkeypatch):
    """MP3 uploads must do a minimal content check, not just trust .mp3."""
    import backend.routes.music as music_route

    monkeypatch.setattr(music_route.uuid, 'uuid4', lambda: SimpleNamespace(hex='badmusicbadmusic'))
    path = os.path.join(DATA_DIR, '..', 'music', 'badmusic.mp3')
    try:
        r = client.post(
            '/api/music/upload',
            data={'file': (io.BytesIO(b'not an mp3'), 'bad.mp3')},
            content_type='multipart/form-data',
        )
        assert r.status_code == 400
        assert 'Invalid' in r.json.get('error', '')
        assert not os.path.exists(path)
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_music_upload_rejects_large_file(client, monkeypatch):
    import backend.routes.music as music_route

    monkeypatch.setattr(music_route.uuid, 'uuid4', lambda: SimpleNamespace(hex='bigmusicbigmusic'))
    path = os.path.join(DATA_DIR, '..', 'music', 'bigmusic.mp3')
    try:
        r = client.post(
            '/api/music/upload',
            data={'file': (io.BytesIO(b'ID3' + (b'0' * (26 * 1024 * 1024))), 'big.mp3')},
            content_type='multipart/form-data',
        )
        assert r.status_code == 413
        assert not os.path.exists(path)
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_music_upload_accepts_basic_mp3(client, monkeypatch):
    import backend.routes.music as music_route

    monkeypatch.setattr(music_route.uuid, 'uuid4', lambda: SimpleNamespace(hex='okmusicokmusic'))
    path = os.path.join(DATA_DIR, '..', 'music', 'okmusico.mp3')
    try:
        r = client.post(
            '/api/music/upload',
            data={'file': (io.BytesIO(b'ID3' + (b'\0' * 32)), 'ok.mp3')},
            content_type='multipart/form-data',
        )
        assert r.status_code == 201
        assert r.json['filename'] == 'okmusico.mp3'
        assert os.path.exists(path)
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_music_delete_restores_file_when_metadata_save_fails(client, tmp_path, monkeypatch):
    import backend.routes.music as music_route

    music_dir = tmp_path / 'music'
    music_dir.mkdir()
    mp3_path = music_dir / 'song.mp3'
    mp3_path.write_bytes(b'ID3test')

    class FailingRepository:
        def list(self):
            return [{'id': 1, 'title': 'Song', 'filename': 'song.mp3'}]

        def save(self, _data):
            raise RuntimeError('metadata save failed')

    monkeypatch.setattr(music_route, 'BASE_DIR', str(tmp_path))
    monkeypatch.setattr(music_route, 'repository_for', lambda _name: FailingRepository())
    with pytest.raises(RuntimeError, match='metadata save failed'):
        client.delete('/api/music/1')

    assert mp3_path.exists()
    assert not (music_dir / 'song.mp3.deleting').exists()


def test_avatar_replace_failure_keeps_old_avatar(client, tmp_path, monkeypatch):
    import backend.routes.about as about_route

    images_dir = tmp_path / 'images'
    images_dir.mkdir()
    old_avatar = images_dir / 'avatar.png'
    old_avatar.write_bytes(b'old avatar')
    source = Image.new('RGB', (10, 10), color='green')
    source_bytes = io.BytesIO()
    source.save(source_bytes, 'JPEG')
    source_bytes.seek(0)

    monkeypatch.setattr(about_route, 'BASE_DIR', str(tmp_path))
    monkeypatch.setattr(about_route.os, 'replace', lambda _src, _dst: (_ for _ in ()).throw(OSError('replace failed')))
    with pytest.raises(OSError, match='replace failed'):
        client.post(
            '/api/about/upload-avatar',
            data={'file': (source_bytes, 'avatar.jpg')},
            content_type='multipart/form-data',
        )

    assert old_avatar.read_bytes() == b'old avatar'
    assert not (images_dir / 'avatar.jpg').exists()
    assert not (images_dir / 'avatar.jpg.uploading').exists()


def test_git_revert_requires_confirmation(client):
    r = client.post('/api/git/revert', json={})
    assert r.status_code == 400
    assert 'confirm' in r.json.get('error', '')


def test_git_revert_checks_stash_failure(monkeypatch):
    from backend.app import app
    import backend.routes.git_api as git_api

    calls = []

    def fake_run(args):
        calls.append(args)
        return SimpleNamespace(returncode=1, stderr='stash failed', stdout='')

    monkeypatch.setattr(git_api, '_run_git', fake_run)
    old_testing = app.config.get('TESTING')
    app.config['TESTING'] = False
    try:
        with app.test_request_context('/api/git/revert', method='POST', json={'confirm': True}):
            response, status = git_api.git_revert()
    finally:
        app.config['TESTING'] = old_testing

    assert status == 500
    assert 'git stash failed' in response.get_json()['error']
    assert calls == [['stash', 'push', '--include-untracked', '-m', 'auto-backup-before-revert']]


def test_git_revert_runs_each_production_step_in_order(monkeypatch):
    from backend.app import app
    import backend.routes.git_api as git_api

    calls = []

    def fake_run(args):
        calls.append(args)
        return SimpleNamespace(returncode=0, stderr='', stdout='ok')

    monkeypatch.setattr(git_api, '_run_git', fake_run)
    old_testing = app.config.get('TESTING')
    app.config['TESTING'] = False
    try:
        with app.test_request_context('/api/git/revert', method='POST', json={'confirm': True}):
            response = git_api.git_revert()
    finally:
        app.config['TESTING'] = old_testing

    assert response.get_json() == {'status': 'reverted'}
    assert calls == [
        ['stash', 'push', '--include-untracked', '-m', 'auto-backup-before-revert'],
        ['checkout', '.'],
        ['clean', '-fd'],
    ]


def test_git_push_stops_before_push_when_remote_is_ahead(monkeypatch):
    from backend.app import app
    import backend.routes.git_api as git_api

    calls = []

    def fake_run(args):
        calls.append(args)
        if args == ['status', '-sb']:
            return SimpleNamespace(returncode=0, stderr='', stdout='## master...origin/master [behind 1]')
        return SimpleNamespace(returncode=0, stderr='', stdout='ok')

    monkeypatch.setattr(git_api, '_run_git', fake_run)
    old_testing = app.config.get('TESTING')
    app.config['TESTING'] = False
    try:
        with app.test_request_context('/api/git/push', method='POST'):
            response, status = git_api.git_push()
    finally:
        app.config['TESTING'] = old_testing

    assert status == 409
    assert '远程仓库有更新' in response.get_json()['error']
    assert calls == [['fetch'], ['status', '-sb']]
