"""Smoke tests for all API routes."""
import json


# ── Data listing endpoints (GET) ──

def test_list_work(client):
    r = client.get('/api/work')
    assert r.status_code == 200
    assert isinstance(r.json, list)

def test_list_essays(client):
    r = client.get('/api/essays')
    assert r.status_code == 200
    assert isinstance(r.json, list)

def test_list_photos(client):
    r = client.get('/api/photos')
    assert r.status_code == 200
    assert isinstance(r.json, list)

def test_list_contact(client):
    r = client.get('/api/contact')
    assert r.status_code == 200
    assert isinstance(r.json, list)

def test_list_friends(client):
    r = client.get('/api/friends')
    assert r.status_code == 200
    assert isinstance(r.json, list)

def test_list_music(client):
    r = client.get('/api/music')
    assert r.status_code == 200
    assert isinstance(r.json, list)

def test_list_stack(client):
    r = client.get('/api/stack')
    assert r.status_code == 200
    assert isinstance(r.json, list)

def test_get_about(client):
    r = client.get('/api/about')
    assert r.status_code == 200
    assert isinstance(r.json, dict)

def test_get_readme(client):
    r = client.get('/api/readme')
    assert r.status_code == 200
    assert isinstance(r.json, dict)
    assert 'content' in r.json


# ── CRUD: create → update → delete (contact, index-based) ──

def test_contact_crud(client, data_backup):
    # Create
    r = client.post('/api/contact', json={'label': 'Test', 'handle': 'unit', 'url': 'https://x.com'})
    assert r.status_code == 201
    # List
    r = client.get('/api/contact')
    assert any(c['label'] == 'Test' for c in r.json)
    idx = next(i for i, c in enumerate(r.json) if c['label'] == 'Test')
    # Update
    r = client.put(f'/api/contact/{idx}', json={'label': 'Updated'})
    assert r.status_code == 200
    assert r.json['label'] == 'Updated'
    # Delete
    r = client.delete(f'/api/contact/{idx}')
    assert r.status_code == 200


# ── Friend CRUD ──

def test_friend_crud(client, data_backup):
    r = client.post('/api/friends', json={'name': 'Tester', 'url': 'https://test.dev'})
    assert r.status_code == 201
    r = client.get('/api/friends')
    idx = next(i for i, f in enumerate(r.json) if f['name'] == 'Tester')
    r = client.delete(f'/api/friends/{idx}')
    assert r.status_code == 200


# ── Stack replace ──

def test_stack_replace(client, data_backup):
    items = ['Python', 'Flask', 'Test']
    r = client.put('/api/stack', json=items)
    assert r.status_code == 200
    r = client.get('/api/stack')
    assert r.json == items


# ── About update ──

def test_about_update(client, data_backup):
    r = client.get('/api/about')
    original = dict(r.json)
    r = client.put('/api/about', json=original)
    assert r.status_code == 200


# ── Essays: slug validation ──

def test_create_essay_invalid_slug(client):
    r = client.post('/api/essays', json={'slug': 'INVALID', 'title': 'X'})
    assert r.status_code == 400

def test_create_essay_duplicate_slug(client):
    essays = client.get('/api/essays').json
    if not essays:
        return  # skip if no essays
    slug = essays[0]['slug']
    r = client.post('/api/essays', json={'slug': slug, 'title': 'Dup'})
    assert r.status_code == 409


# ── Photos: reorder validation ──

def test_photos_reorder_refuses_drop(client, data_backup):
    photos = client.get('/api/photos').json
    if not photos:
        return
    # Submit a subset should be rejected
    subset = [photos[0]]
    r = client.put('/api/photos', json=subset)
    # 409 if there are >1 photos, 200 if only 1
    if len(photos) > 1:
        assert r.status_code == 409


# ── Photo tags/date/gps validation ──

def test_photo_tags_missing_fields(client):
    r = client.put('/api/photo-tags', json={})
    assert r.status_code == 400

def test_photo_date_missing_fields(client):
    r = client.put('/api/photo-date', json={})
    assert r.status_code == 400

def test_photo_gps_not_found(client):
    r = client.put('/api/photo-gps', json={'filename': '__nonexistent__.jpg', 'lat': 0, 'lng': 0})
    assert r.status_code == 404


# ── Git API ──

def test_git_status(client):
    r = client.get('/api/git/status')
    assert r.status_code == 200
    assert 'branch' in r.json

def test_git_commit_no_message(client):
    r = client.post('/api/git/commit', json={})
    assert r.status_code == 400

def test_git_diff(client):
    r = client.get('/api/git/diff')
    assert r.status_code == 200
    assert 'diff' in r.json


# ── Static file serving ──

def test_serve_admin(client):
    r = client.get('/')
    assert r.status_code == 200

def test_serve_index(client):
    r = client.get('/index.html')
    assert r.status_code == 200

def test_serve_data_json(client):
    r = client.get('/data/about.json')
    assert r.status_code == 200


# ── Essay content read ──

def test_essay_content_404(client):
    r = client.get('/api/essays/__nonexistent__/content')
    assert r.status_code == 404
