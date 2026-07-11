"""Additional test coverage."""
import io
import os
from types import SimpleNamespace

from backend.data import DATA_DIR
from backend.data import load_json


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


def test_rss_feed_exists():
    p = os.path.join(DATA_DIR, '..', 'rss.xml')
    if os.path.exists(p): assert '<' in open(p).read()

def test_sitemap_exists():
    p = os.path.join(DATA_DIR, '..', 'sitemap.xml')
    if os.path.exists(p): assert '<' in open(p).read()

def test_archive_html_exists():
    p = os.path.join(DATA_DIR, '..', 'archive.html')
    if os.path.exists(p): assert '<' in open(p).read()

def test_map_html_exists():
    p = os.path.join(DATA_DIR, '..', 'map.html')
    if os.path.exists(p): assert '<' in open(p).read()


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

def test_essay_image_upload_no_file(client):
    r = client.post('/api/essays/upload-image')
    assert r.status_code == 400


def test_essay_image_upload_rejects_fake_image(client, monkeypatch):
    """Essay image uploads must validate file contents, not just the extension."""
    from backend.data import IMAGES_DIR
    import backend.routes.essays as essays_route

    monkeypatch.setattr(essays_route.uuid, 'uuid4', lambda: SimpleNamespace(hex='badimagebadimage'))
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
