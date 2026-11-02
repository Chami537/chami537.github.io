"""Shelf contracts: persistence, public links, limits, media and access controls."""

import io
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest
from PIL import Image

from backend.data import BASE_DIR
from backend.health_checks.stories import check_stories
from backend.repositories import repository_for
from backend.story_service import StoryError, save_story, validate_story


def story(**updates):
    return dict(title='测试作品', type='movie', recommendation='因为这个故事留了下来。', **updates)


@pytest.fixture
def empty_stories(data_backup):
    repository_for('stories.json').save([])


def test_shelf_crud_order_and_public_static_files(client, empty_stories):
    a = client.post('/api/stories', json=story(featured=True, favorite=True, rating=4.5))
    assert a.status_code == 201
    first = a.json
    second = client.post('/api/stories', json=story(creator='作者', type_unused='ignored')).json
    assert first['id'] != second['id']
    assert client.put('/api/stories/order', json={'order':[second['id'], first['id']]}).status_code == 200
    assert [s['id'] for s in client.get('/data/stories.json').json] == [second['id'], first['id']]
    updated = client.put(f"/api/stories/{first['id']}", json=story(rating=None, finished_on='2026-10-31'))
    assert updated.status_code == 200 and updated.json['id'] == first['id']
    assert client.get('/shelf.html').status_code == 200
    assert client.delete(f"/api/stories/{first['id']}").status_code == 200
    assert client.delete(f"/api/stories/{first['id']}").status_code == 404
    assert client.put('/api/stories/99999', json=story()).status_code == 404
    assert len(client.get('/api/stories').json) == 1


@pytest.mark.parametrize('updates', [
    {'title':''}, {'recommendation':' '}, {'title':7}, {'type':'other'},
    {'rating':True}, {'rating':0}, {'rating':4.2}, {'rating':float('inf')}, {'rating':10**400},
    {'featured':1}, {'favorite':'false'}, {'finished_on':'2026-02-30'},
    {'finished_on':'2026-1-01'}, {'recommendation':'x' * 1001},
    {'cover':'https://example.com/image.jpg'}, {'cover':'images/stories/../../avatar.jpg'},
    {'essay_slug':'missing'},
])
def test_invalid_story_never_changes_data(client, empty_stories, updates):
    payload = story(); payload.update(updates)
    assert client.post('/api/stories', json=payload).status_code == 400
    assert client.get('/api/stories').json == []


def test_concurrent_creates_keep_all_stories_without_featured_limit(client, empty_stories):
    def create(_):
        try:
            return save_story(story(featured=True))
        except StoryError:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(create, range(10)))
    assert sum(r is not None for r in results) == 10
    entries = client.get('/api/stories').json
    assert len({s['id'] for s in entries}) == 10
    assert client.put(f"/api/stories/{entries[0]['id']}", json=story(featured=True)).status_code == 200
    assert client.post('/api/stories', json=story(featured=True)).status_code == 201
    assert client.post('/api/stories', json=story(featured=False)).status_code == 201


@pytest.mark.parametrize('order', [None, [], [1,1], [True], ['1'], [999]])
def test_invalid_reorder_preserves_data(client, empty_stories, order):
    original = client.post('/api/stories', json=story()).json
    assert client.put('/api/stories/order', json={'order':order}).status_code == 400
    assert client.get('/api/stories').json == [original]


def test_link_only_allows_public_unencrypted_essays(client, empty_stories, monkeypatch):
    repository_for('essays.json').save([
        {'slug':'public'}, {'slug':'hidden', 'hidden':True}, {'slug':'secret'},
    ])
    monkeypatch.setattr('backend.story_service.public_essay_slugs', lambda essays: {'public'})
    assert client.post('/api/stories', json=story(essay_slug='public')).status_code == 201
    for slug in ('hidden','secret','missing'):
        assert client.post('/api/stories', json=story(essay_slug=slug)).status_code == 400


def test_essay_visibility_rules():
    from backend.story_service import public_essay_slugs
    assert public_essay_slugs([
        {'slug':'public'}, {'slug':'hidden','hidden':True}, {'slug':'secret'},
        {'slug':'legacy','password':'secret'}, {'slug':'flag','password_protected':True},
    ], lambda slug: slug == 'secret') == {'public'}


def test_upload_verifies_bytes_and_keeps_cover_after_delete(client, empty_stories):
    image = io.BytesIO(); Image.new('RGB',(4,6)).save(image,format='PNG'); image.seek(0)
    response = client.post('/api/stories/upload-cover', data={'file':(image,'cover.png')})
    assert response.status_code == 201
    path = Path(BASE_DIR) / response.json['cover']
    try:
        item = client.post('/api/stories', json=story(cover=response.json['cover'])).json
        assert client.get('/' + item['cover']).status_code == 200
        client.delete(f"/api/stories/{item['id']}")
        assert path.is_file()
    finally:
        path.unlink(missing_ok=True)
    assert client.post('/api/stories/upload-cover', data={'file':(io.BytesIO(b'fake'),'cover.png')}).status_code == 400
    assert client.post('/api/stories/upload-cover', data={}).status_code == 400


def test_symlink_cover_cannot_escape_root(tmp_path):
    outside = tmp_path / 'outside.png'; outside.write_bytes(b'test')
    root = tmp_path / 'site'; (root / 'images' / 'stories').mkdir(parents=True)
    (root / 'images' / 'stories' / 'escape.png').symlink_to(outside)
    with pytest.raises(StoryError):
        validate_story(story(cover='images/stories/escape.png'), root=root)


def test_stories_auth_csrf_and_public_preview(client_no_auth):
    assert client_no_auth.get('/api/stories').status_code == 401
    assert client_no_auth.get('/data/stories.json').status_code == 200
    assert client_no_auth.get('/shelf.html').status_code == 200
    with client_no_auth.session_transaction() as session:
        session['authenticated'] = True
    assert client_no_auth.post('/api/stories', json=story(), headers={'Origin':'https://evil.example'}).status_code == 403


def test_shelf_health_errors_and_stale_link_warning(tmp_path):
    report = check_stories(tmp_path, [dict(story(), id=1, essay_slug='gone')], [], lambda _:False)
    assert report['status'] == 'warning'
    report = check_stories(tmp_path, [dict(story(), id=1), dict(story(), id=1)], [], lambda _:False)
    assert report['status'] == 'error'
    report = check_stories(tmp_path, [dict(story(), id=1, cover='images/stories/missing.png')], [], lambda _:False)
    assert report['status'] == 'error'
    folder = tmp_path / 'images' / 'stories'; folder.mkdir(parents=True)
    (folder / 'orphan.jpg').write_bytes(b'image')
    assert check_stories(tmp_path, [], [], lambda _:False)['status'] == 'warning'
