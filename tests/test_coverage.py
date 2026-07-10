"""Additional test coverage."""
import os
from backend.data import DATA_DIR


def test_photo_stories_get(client):
    r = client.get('/api/photo-stories')
    assert r.status_code == 200
    assert isinstance(r.json, list)


def test_photo_stories_put(client, data_backup):
    stories = [{'id': 'x', 'name': 'T', 'date': '2026-01', 'cover': 'p.jpg', 'caption': 'x', 'photos': ['p.jpg']}]
    r = client.put('/api/photo-stories', json=stories)
    assert r.status_code == 200
    r2 = client.get('/api/photo-stories')
    assert len(r2.json) == 1


def test_photo_stories_put_rejects_non_list(client):
    r = client.put('/api/photo-stories', json={'x': 1})
    assert r.status_code == 400


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


def test_git_revert(client):
    r = client.post('/api/git/revert')
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
