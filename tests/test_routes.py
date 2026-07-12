"""Smoke tests for all API routes."""
import json
import os
from backend.data import DATA_DIR


def test_dashboard_stats_requires_auth(client_no_auth):
    response = client_no_auth.get('/api/dashboard-stats')
    assert response.status_code == 401


def test_dashboard_stats_aggregates_content(client, monkeypatch):
    import backend.routes.dashboard as dashboard

    datasets = {
        'essays.json': [
            {'slug': 'a', 'title': 'A', 'date': '2026-07-01', 'tag': '技术, Python'},
            {'slug': 'b', 'title': 'B', 'date': '2026-07-02', 'tag': '技术, Python, 教程', 'hidden': True},
            {'slug': 'c', 'title': 'C', 'date': '2026-07-03', 'tag': '生活'},
        ],
        'photos.json': [
            {'filename': 'with-gps.jpg', 'exif': {'gps': {'lat': 1, 'lng': 2}}},
            {'filename': 'without-gps.jpg', 'exif': {}},
        ],
        'photo_stories.json': [
            {'id': 'story', 'name': 'Story', 'date': 'Jul 2026', 'photos': ['with-gps.jpg']},
        ],
        'work.json': [{'id': 1}],
        'music.json': [{'id': 1}, {'id': 2}],
        'friends.json': [{'id': 1}],
        'stack.json': ['Python', 'Flask'],
    }
    monkeypatch.setattr(dashboard, 'load_json', lambda name: datasets[name])
    monkeypatch.setattr(dashboard, 'has_essay_password', lambda slug: slug == 'b')

    response = client.get('/api/dashboard-stats')

    assert response.status_code == 200
    body = response.get_json()
    assert body['counts'] == {
        'essays': {'total': 3, 'public': 2, 'hidden': 1, 'encrypted': 1},
        'photos': 2,
        'photo_stories': 1,
        'places': 1,
        'work': 1,
        'music': 2,
        'friends': 1,
        'stack': 2,
    }
    assert body['tags'] == [
        {'name': 'Python', 'count': 2},
        {'name': '技术', 'count': 2},
        {'name': '教程', 'count': 1},
        {'name': '生活', 'count': 1},
    ]
    assert [item['type'] for item in body['recent']] == ['essay', 'essay', 'essay', 'photo_story']
    assert body['recent'][0]['title'] == 'C'


def test_dashboard_stats_returns_500_when_data_cannot_be_read(client, monkeypatch):
    import backend.routes.dashboard as dashboard

    def fail_to_read(_name):
        raise OSError('data unavailable')

    monkeypatch.setattr(dashboard, 'load_json', fail_to_read)

    response = client.get('/api/dashboard-stats')

    assert response.status_code == 500
    assert response.get_json() == {'error': '无法读取统计数据'}


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


# ── CRUD: create → update → delete (contact, id-based) ──

def test_contact_crud(client, data_backup):
    # Create (auto_id=True)
    r = client.post('/api/contact', json={'label': 'Test', 'handle': 'unit', 'url': 'https://x.com'})
    assert r.status_code == 201
    cid = r.json['id']
    # List
    r = client.get('/api/contact')
    assert any(c['label'] == 'Test' for c in r.json)
    # Update
    r = client.put(f'/api/contact/{cid}', json={'label': 'Updated'})
    assert r.status_code == 200
    assert r.json['label'] == 'Updated'
    # Delete
    r = client.delete(f'/api/contact/{cid}')
    assert r.status_code == 200


# ── Friend CRUD ──

def test_friend_crud(client, data_backup):
    r = client.post('/api/friends', json={'name': 'Tester', 'url': 'https://test.dev'})
    assert r.status_code == 201
    fid = r.json['id']
    r = client.delete(f'/api/friends/{fid}')
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


# ── Essay CRUD with tags (exercises _parse_tags in update_essay_meta) ──

def test_essay_crud_with_tags(client, data_backup):
    # Create two essays sharing a tag
    a = client.post('/api/essays', json={
        'slug': 'test-tag-a', 'title': 'Essay A', 'tag': 'shared, only-a',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'A'
    })
    assert a.status_code == 201
    b = client.post('/api/essays', json={
        'slug': 'test-tag-b', 'title': 'Essay B', 'tag': 'shared, only-b',
        'date': '2026-01-02', 'epigraph': '', 'excerpt': 'B'
    })
    assert b.status_code == 201

    # Update essay A metadata — triggers _parse_tags in update_essay_meta
    # on the tag-sync branch (essays sharing 'shared' tag)
    r = client.put('/api/essays/test-tag-a', json={
        'slug': 'test-tag-a', 'title': 'Essay A Updated',
        'tag': 'shared, only-a', 'date': '2026-01-03',
        'epigraph': '', 'excerpt': 'Updated'
    })
    assert r.status_code == 200
    assert r.json['title'] == 'Essay A Updated'

    # Verify essay B still exists (was re-synced, not deleted)
    r2 = client.get('/api/essays/test-tag-b/content')
    assert r2.status_code == 200

    # Cleanup
    client.delete('/api/essays/test-tag-a')
    client.delete('/api/essays/test-tag-b')


# ── Photo tags: success + not-found paths ──

def test_photo_tags_set(client, data_backup):
    photos = client.get('/api/photos').json
    if not photos:
        return
    fn = photos[0]['filename']
    r = client.put('/api/photo-tags', json={'filename': fn, 'tags': ['test-tag']})
    assert r.status_code == 200
    assert r.json['tags'] == ['test-tag']


def test_photo_tags_not_found(client):
    r = client.put('/api/photo-tags', json={'filename': '__none__.jpg', 'tags': []})
    assert r.status_code == 404


# ── toggle_pin ──

def test_toggle_pin(client, data_backup):
    # Create a test essay
    r = client.post('/api/essays', json={
        'slug': 'test-toggle-pin', 'title': 'Toggle Pin Test',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'pin test',
        'tag': ''
    })
    slug = r.json.get('slug', 'test-toggle-pin')

    # Default: not pinned
    essays = client.get('/api/essays').json
    essay = next((e for e in essays if e['slug'] == slug), None)
    assert essay is not None
    assert essay.get('pinned') != True

    # Toggle: pin it
    r2 = client.post(f'/api/essays/{slug}/pin')
    assert r2.status_code == 200
    essays2 = client.get('/api/essays').json
    essay2 = next((e for e in essays2 if e['slug'] == slug), None)
    assert essay2.get('pinned') == True

    # Toggle again: unpin
    r3 = client.post(f'/api/essays/{slug}/pin')
    assert r3.status_code == 200
    essays3 = client.get('/api/essays').json
    essay3 = next((e for e in essays3 if e['slug'] == slug), None)
    assert essay3.get('pinned') != True

    # Cleanup
    client.delete(f'/api/essays/{slug}')


# ── Password = hidden ──

def test_password_hides_essay(client, data_backup):
    """Setting a password hides the essay from public; clearing restores it."""
    r = client.post('/api/essays', json={
        'slug': 'test-pw-hide', 'title': 'Password Hide Test',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'pw hide test', 'tag': ''
    })
    slug = r.json.get('slug', 'test-pw-hide')

    # Set password
    r2 = client.post(f'/api/essays/{slug}/password', json={'password': 'secret123'})
    assert r2.status_code == 200
    assert r2.json['password_set'] == True

    # Essay still in admin API
    essays = client.get('/api/essays').json
    essay = next((e for e in essays if e['slug'] == slug), None)
    assert essay is not None
    assert essay['password_set'] == True

    # Clear password
    r3 = client.post(f'/api/essays/{slug}/password', json={'password': ''})
    assert r3.status_code == 200
    assert r3.json['password_set'] == False

    # Cleanup
    client.delete(f'/api/essays/{slug}')


def test_set_password(client, data_backup):
    r = client.post('/api/essays', json={
        'slug': 'test-set-password', 'title': 'Password Test',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'password test', 'tag': ''
    })
    slug = r.json.get('slug', 'test-set-password')

    # Set password
    r2 = client.post(f'/api/essays/{slug}/password', json={'password': 'secret123'})
    assert r2.status_code == 200
    assert r2.json['password_set'] == True

    # Verify admin can see password_set flag (password value never exposed via API)
    essays = client.get('/api/essays').json
    essay = next((e for e in essays if e['slug'] == slug), None)
    assert essay.get('password_set') == True
    assert 'password' not in essay

    # Clear password
    r3 = client.post(f'/api/essays/{slug}/password', json={'password': ''})
    assert r3.status_code == 200
    assert r3.json['password_set'] == False

    # Verify password is cleared
    essays2 = client.get('/api/essays').json
    essay2 = next((e for e in essays2 if e['slug'] == slug), None)
    assert essay2.get('password_set') == False
    assert essay2.get('password') == None

    # Cleanup
    client.delete(f'/api/essays/{slug}')


def test_preview_markdown_supports_common_extensions(client):
    md = "\n".join([
        "~~deleted~~",
        "",
        "- [ ] todo",
        "- [x] done",
        "",
        "$$",
        "f(x)=x^2+x",
        "$$",
    ])

    r = client.post('/api/essays/test/html', json={'md': md})

    assert r.status_code == 200
    html = r.json['html']
    assert '<del>deleted</del>' in html
    assert 'type="checkbox"' in html
    assert 'checked' in html
    assert 'class="arithmatex"' in html
    assert r'\[' in html
    assert 'f(x)=x^2+x' in html
    assert r'\]' in html


def test_password_visible_in_admin_api(client, data_backup):
    r = client.post('/api/essays', json={
        'slug': 'test-no-pwd-leak', 'title': 'No Leak Test',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'no leak', 'tag': ''
    })
    slug = r.json.get('slug', 'test-no-pwd-leak')
    client.post(f'/api/essays/{slug}/password', json={'password': 'topsecret'})

    # Admin API returns password_set flag but never the actual password value
    essays = client.get('/api/essays').json
    essay = next((e for e in essays if e['slug'] == slug), None)
    assert 'password' not in essay
    assert essay.get('password_set') == True

    # Cleanup
    client.delete(f'/api/essays/{slug}')


# ── Tag order API ──

def test_tag_order_crud(client, data_backup):
    """PUT and GET tag order; order persists in essays_public.json."""
    order = ['摄影', '随笔', '生活']
    r = client.put('/api/tags/order', json={'order': order})
    assert r.status_code == 200
    r2 = client.get('/api/tags/order')
    assert r2.status_code == 200
    assert r2.json == order


# ── Pin regenerates public data ──

def test_pin_toggle_regenerates_public(client, data_backup):
    r = client.post('/api/essays', json={
        'slug': 'test-pin-public', 'title': 'Pin Public Test',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'pin public', 'tag': ''
    })
    slug = r.json.get('slug', 'test-pin-public')

    # Pin it → triggers _generate_feeds
    client.post(f'/api/essays/{slug}/pin')
    # Verify essays_public.json was regenerated (has date_display)
    import json, os
    from backend.data import DATA_DIR
    public = json.load(open(os.path.join(DATA_DIR, 'essays_public.json')))
    pinned = [e for e in public['essays'] if e['slug'] == slug]
    assert len(pinned) == 1
    assert pinned[0].get('pinned') == True
    assert 'date_display' in pinned[0]

    # Unpin
    client.post(f'/api/essays/{slug}/pin')
    public2 = json.load(open(os.path.join(DATA_DIR, 'essays_public.json')))
    pinned2 = [e for e in public2['essays'] if e['slug'] == slug]
    assert pinned2[0].get('pinned') != True

    # Cleanup
    client.delete(f'/api/essays/{slug}')


# ── Content API handles encrypted .md ──

def test_content_api_decrypts_encrypted_md(client, data_backup):
    r = client.post('/api/essays', json={
        'slug': 'test-content-crypt', 'title': 'Crypto Content Test',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'crypto content',
        'tag': ''
    })
    slug = r.json.get('slug', 'test-content-crypt')

    # Write content first (creates .md file)
    client.put(f'/api/essays/{slug}/content', json={'content': '秘密内容在这里'})
    # Set password → encrypts .md
    client.post(f'/api/essays/{slug}/password', json={'password': 'secret'})

    # Read content → should return decrypted plaintext
    r2 = client.get(f'/api/essays/{slug}/content')
    assert r2.status_code == 200
    assert '秘密内容在这里' in r2.json['content']

    # Cleanup
    client.delete(f'/api/essays/{slug}')


# ── Auth ──

def test_login_success(client_no_auth):
    r = client_no_auth.post('/api/login', json={'password': 'chami'})
    assert r.status_code == 200
    assert r.json == {"status": "ok"}

def test_login_wrong_password(client_no_auth):
    r = client_no_auth.post('/api/login', json={'password': 'wrong'})
    assert r.status_code == 401

def test_logout(client_no_auth):
    client_no_auth.post('/api/login', json={'password': 'chami'})
    r = client_no_auth.post('/api/logout')
    assert r.status_code == 200
    assert r.json == {"status": "logged out"}

def test_api_unauthorized_without_login(client_no_auth):
    r = client_no_auth.get('/api/work')
    assert r.status_code == 401
    assert 'Unauthorized' in r.json.get('error', '')

def test_api_ok_after_login(client_no_auth):
    client_no_auth.post('/api/login', json={'password': 'chami'})
    r = client_no_auth.get('/api/work')
    assert r.status_code == 200


# ── Music CRUD ──

def test_music_crud(client, data_backup):
    # Create
    r = client.post('/api/music', json={'title': 'Test Song', 'artist': 'Test Artist', 'filename': 'test.mp3'})
    assert r.status_code == 201
    music_id = r.json['id']

    # List & verify
    r = client.get('/api/music')
    assert any(m['id'] == music_id for m in r.json)

    # Update
    r = client.put(f'/api/music/{music_id}', json={'title': 'Updated Song', 'artist': 'Updated Artist', 'filename': 'test.mp3'})
    assert r.status_code == 200
    assert r.json['title'] == 'Updated Song'

    # Delete
    r = client.delete(f'/api/music/{music_id}')
    assert r.status_code == 200


# ── Work CRUD ──

def test_work_crud(client, data_backup):
    # Create
    r = client.post('/api/work', json={'name': 'Test Project', 'description': 'desc', 'repo': 'user/repo'})
    assert r.status_code == 201
    work_id = r.json['id']

    # List & verify
    r = client.get('/api/work')
    assert any(w['id'] == work_id for w in r.json)

    # Update
    r = client.put(f'/api/work/{work_id}', json={'name': 'Updated Project', 'description': 'desc', 'repo': 'user/repo'})
    assert r.status_code == 200
    assert r.json['name'] == 'Updated Project'

    # Delete
    r = client.delete(f'/api/work/{work_id}')
    assert r.status_code == 200


# ── CSRF protection ──

def test_csrf_rejects_cross_origin_post(client):
    """POST with foreign Origin header should be rejected."""
    r = client.post('/api/login', json={'password': 'chami'},
                    headers={'Origin': 'https://evil.com'})
    assert r.status_code == 403
    assert 'CSRF' in r.json.get('error', '')

def test_csrf_allows_same_origin_post(client):
    """POST with matching Origin header should pass."""
    r = client.post('/api/login', json={'password': 'chami'},
                    headers={'Origin': 'http://localhost'})
    assert r.status_code == 200

def test_csrf_allows_no_origin(client):
    """POST without Origin header (old browsers) should pass."""
    r = client.post('/api/login', json={'password': 'chami'})
    assert r.status_code == 200


# ── Content API decrypt failure ──

def test_content_api_decrypt_corrupted_ciphertext(client, data_backup):
    """Corrupted ciphertext should return error, not the raw blob."""
    r = client.post('/api/essays', json={
        'slug': 'test-corrupt', 'title': 'Corrupt Test',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'corrupt',
        'tag': ''
    })
    slug = r.json.get('slug', 'test-corrupt')

    client.put(f'/api/essays/{slug}/content', json={'content': 'plaintext'})
    client.post(f'/api/essays/{slug}/password', json={'password': 'secret'})

    # Corrupt the .md file by writing garbage
    md_file = os.path.join(DATA_DIR, '..', 'md', f'{slug}.md')
    with open(md_file, 'w') as f:
        f.write('this is not valid base64!!!')

    r2 = client.get(f'/api/essays/{slug}/content')
    assert r2.status_code == 500
    assert 'error' in r2.json

    # Cleanup
    client.delete(f'/api/essays/{slug}')


# ── Session security config ──

def test_session_cookie_secure():
    """SESSION_COOKIE_SECURE should be True."""
    from backend.app import app
    assert app.config.get('SESSION_COOKIE_SECURE') is True


# ── Tagless essay re-sync ──

def test_delete_tagless_essay_resyncs_siblings(client, data_backup):
    """Deleting a tagless essay should re-sync all remaining essays (not just tag-sharing ones)."""
    # Create two tagless essays
    r1 = client.post('/api/essays', json={
        'slug': 'test-tagless-a', 'title': 'Tagless A',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'a', 'tag': ''
    })
    r2 = client.post('/api/essays', json={
        'slug': 'test-tagless-b', 'title': 'Tagless B',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'b', 'tag': ''
    })
    assert r1.status_code == 201
    assert r2.status_code == 201

    # Delete one — should succeed and re-sync the other
    r3 = client.delete('/api/essays/test-tagless-a')
    assert r3.status_code == 200

    # Verify the other essay's HTML was regenerated
    from backend.data import ESSAYS_DIR
    html_path = os.path.join(ESSAYS_DIR, 'test-tagless-b.html')
    assert os.path.exists(html_path)
    assert 'Tagless B' in open(html_path, encoding='utf-8').read()

    # Cleanup
    client.delete('/api/essays/test-tagless-b')


def test_update_tagless_essay_meta_resyncs_siblings(client, data_backup):
    """Updating meta of a tagless essay should re-sync all siblings."""
    r1 = client.post('/api/essays', json={
        'slug': 'test-tagless-c', 'title': 'Tagless C',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'c', 'tag': ''
    })
    r2 = client.post('/api/essays', json={
        'slug': 'test-tagless-d', 'title': 'Tagless D',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'd', 'tag': ''
    })
    assert r1.status_code == 201
    assert r2.status_code == 201

    # Update meta of tagless essay
    r3 = client.put('/api/essays/test-tagless-c', json={
        'title': 'Tagless C Updated', 'date': '2026-01-01',
        'epigraph': '', 'excerpt': 'c', 'tag': '', 'slug': 'test-tagless-c'
    })
    assert r3.status_code == 200

    # Cleanup
    client.delete('/api/essays/test-tagless-c')
    client.delete('/api/essays/test-tagless-d')


# ── Password change (hidden = encrypted 联动) ──

def test_change_password_roundtrip(client, data_backup):
    """Set password → change to new password → content still accessible."""
    r = client.post('/api/essays', json={
        'slug': 'test-pw-change', 'title': 'Password Change Test',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'pw change', 'tag': ''
    })
    slug = r.json.get('slug', 'test-pw-change')

    # Write content
    client.put(f'/api/essays/{slug}/content', json={'content': '原始秘密内容'})
    # Set password
    r1 = client.post(f'/api/essays/{slug}/password', json={'password': 'oldpass'})
    assert r1.status_code == 200
    assert r1.json['password_set'] == True

    # Verify content is encrypted at rest
    md_file = os.path.join(DATA_DIR, '..', 'md', f'{slug}.md')
    assert os.path.exists(md_file)
    with open(md_file, encoding='utf-8') as f:
        encrypted_md = f.read()
    from backend.ssg import _is_encrypted_v3
    assert _is_encrypted_v3(encrypted_md)

    # Change to new password
    r2 = client.post(f'/api/essays/{slug}/password', json={'password': 'newpass'})
    assert r2.status_code == 200
    assert r2.json['password_set'] == True

    # Content API must still return decrypted content
    r3 = client.get(f'/api/essays/{slug}/content')
    assert r3.status_code == 200
    assert '原始秘密内容' in r3.json['content']

    # Cleanup
    client.delete(f'/api/essays/{slug}')


def test_change_password_wrong_old(client, data_backup):
    """Changing password returns 400 when running but old password unknown."""
    r = client.post('/api/essays', json={
        'slug': 'test-pw-wrong-old', 'title': 'Wrong Old PW',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'wrong old', 'tag': ''
    })
    slug = r.json.get('slug', 'test-pw-wrong-old')

    # Write content and set first password
    client.put(f'/api/essays/{slug}/content', json={'content': '内容'})
    client.post(f'/api/essays/{slug}/password', json={'password': 'firstpass'})

    # Corrupt the .md to simulate unknown-password scenario
    # (Since the test has the password, direct manipulation of the store is needed)
    md_file = os.path.join(DATA_DIR, '..', 'md', f'{slug}.md')
    # Replace with new encrypted content (using different password, unknown to the store)
    from backend.ssg import _encrypt_content
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(_encrypt_content("内容", "differentpw"))

    # Now the password store has 'firstpass' but .md was encrypted with 'differentpw'
    # Trying to set a new password should fail because old password can't decrypt
    r2 = client.post(f'/api/essays/{slug}/password', json={'password': 'thirdpass'})
    assert r2.status_code == 400
    assert '旧密码错误' in r2.json.get('error', '')

    # Cleanup
    client.delete(f'/api/essays/{slug}')


def test_encrypted_essay_content_update(client, data_backup):
    """Update content of an encrypted essay → re-encrypted with same password."""
    r = client.post('/api/essays', json={
        'slug': 'test-upd-crypt', 'title': 'Update Encrypted',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'update', 'tag': ''
    })
    slug = r.json.get('slug', 'test-upd-crypt')

    # Write content + set password
    client.put(f'/api/essays/{slug}/content', json={'content': '第一版内容'})
    client.post(f'/api/essays/{slug}/password', json={'password': 'securepw'})

    # Update content while encrypted
    r2 = client.put(f'/api/essays/{slug}/content', json={'content': '第二版内容——更新后'})
    assert r2.status_code == 200

    # Content API must return NEW content (decrypted)
    r3 = client.get(f'/api/essays/{slug}/content')
    assert r3.status_code == 200
    assert '第二版内容——更新后' in r3.json['content']
    assert '第一版内容' not in r3.json['content']

    # .md must still be encrypted
    md_file = os.path.join(DATA_DIR, '..', 'md', f'{slug}.md')
    with open(md_file, encoding='utf-8') as f:
        md_content = f.read()
    from backend.ssg import _is_encrypted_v3
    assert _is_encrypted_v3(md_content)
    assert '第二版' not in md_content  # not plaintext

    # Cleanup
    client.delete(f'/api/essays/{slug}')


def test_encrypted_essay_is_hidden_in_html(client, data_backup):
    """Password = hidden = gate in HTML, plaintext body absent."""
    r = client.post('/api/essays', json={
        'slug': 'test-hidden-crypt', 'title': 'Hidden = Encrypted',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'hidden', 'tag': ''
    })
    slug = r.json.get('slug', 'test-hidden-crypt')

    # Write content + set password (which means "hidden")
    client.put(f'/api/essays/{slug}/content', json={'content': '这是隐藏内容'})
    client.post(f'/api/essays/{slug}/password', json={'password': 'hidepw'})

    # Verify generated HTML has gate and no plaintext body
    from backend.data import ESSAYS_DIR
    html_path = os.path.join(ESSAYS_DIR, f'{slug}.html')
    assert os.path.exists(html_path)
    html = open(html_path, encoding='utf-8').read()
    assert 'id="essay-gate"' in html
    assert '此内容已隐藏' in html
    assert '这是隐藏内容' not in html

    # essays_public.json must strip password
    public_path = os.path.join(DATA_DIR, 'essays_public.json')
    public = json.load(open(public_path, encoding='utf-8'))
    essay = next((e for e in public['essays'] if e['slug'] == slug), None)
    assert essay is not None
    assert 'password' not in essay

    # Cleanup
    client.delete(f'/api/essays/{slug}')


def test_clear_password_restores_visibility(client, data_backup):
    """Clear password → essay no longer hidden → plaintext body in HTML."""
    r = client.post('/api/essays', json={
        'slug': 'test-restore-vis', 'title': 'Restore Visibility',
        'date': '2026-01-01', 'epigraph': '', 'excerpt': 'restore', 'tag': ''
    })
    slug = r.json.get('slug', 'test-restore-vis')

    client.put(f'/api/essays/{slug}/content', json={'content': '可见内容'})
    client.post(f'/api/essays/{slug}/password', json={'password': 'pw'})
    # Clear password → unhides
    client.post(f'/api/essays/{slug}/password', json={'password': ''})

    from backend.data import ESSAYS_DIR
    html_path = os.path.join(ESSAYS_DIR, f'{slug}.html')
    html = open(html_path, encoding='utf-8').read()
    assert 'id="essay-gate"' not in html
    assert '可见内容' in html

    # Cleanup
    client.delete(f'/api/essays/{slug}')
