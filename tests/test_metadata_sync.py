"""Focused tests for the remaining high-risk metadata helpers."""

import json

from PIL import Image


def test_fetch_stars_updates_repository_and_etag(monkeypatch, tmp_path):
    import backend.github_sync as sync

    saved = [{'repo': 'owner/project', 'stars': 1}]
    etags = {}

    class Response:
        status = 200
        headers = {'ETag': 'etag-1'}

        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return json.dumps({'stargazers_count': 4}).encode()

    monkeypatch.setattr(sync, 'repository_for', lambda _: type('Repo', (), {
        'list': lambda self: saved,
        'save': lambda self, value: saved.__setitem__(slice(None), value),
    })())
    monkeypatch.setattr(sync, 'DATA_DIR', str(tmp_path))
    monkeypatch.setattr(sync.urllib.request, 'urlopen', lambda *args, **kwargs: Response())

    sync.fetch_stars()

    assert saved[0]['stars'] == 4
    assert json.loads((tmp_path / '_stars_etag.json').read_text()) == {'owner/project': 'etag-1'}


def test_fetch_stars_ignores_non_object_etag_cache(monkeypatch, tmp_path):
    import backend.github_sync as sync

    work = [{'repo': 'owner/project', 'stars': 1}]
    (tmp_path / '_stars_etag.json').write_text('[]', encoding='utf-8')

    class Response:
        status = 200
        headers = {}

        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return json.dumps({'stargazers_count': 1}).encode()

    monkeypatch.setattr(sync, 'repository_for', lambda _: type('Repo', (), {
        'list': lambda self: work,
        'save': lambda self, value: None,
    })())
    monkeypatch.setattr(sync, 'DATA_DIR', str(tmp_path))
    monkeypatch.setattr(sync.urllib.request, 'urlopen', lambda *args, **kwargs: Response())

    sync.fetch_stars()

    assert json.loads((tmp_path / '_stars_etag.json').read_text()) == {}


def test_fetch_stars_processes_all_repositories(monkeypatch, tmp_path):
    import backend.github_sync as sync

    work = [
        {'repo': 'owner/updated', 'stars': 1},
        {'repo': 'owner/unchanged', 'stars': 2},
    ]
    saved = []
    requests = []
    (tmp_path / '_stars_etag.json').write_text(
        json.dumps({'owner/unchanged': 'etag-old'}),
        encoding='utf-8',
    )

    class Response:
        headers = {}

        def __init__(self, status, stars=0):
            self.status = status
            self.stars = stars

        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return json.dumps({'stargazers_count': self.stars}).encode()

    def urlopen(request, timeout):
        requests.append(request)
        if request.full_url.endswith('/owner/updated'):
            return Response(200, 4)
        return Response(304)

    monkeypatch.setattr(sync, 'repository_for', lambda _: type('Repo', (), {
        'list': lambda self: work,
        'save': lambda self, value: saved.append(list(value)),
    })())
    monkeypatch.setattr(sync, 'DATA_DIR', str(tmp_path))
    monkeypatch.setattr(sync.urllib.request, 'urlopen', urlopen)

    sync.fetch_stars()

    assert [item['stars'] for item in work] == [4, 2]
    assert len(requests) == 2
    assert requests[1].get_header('If-none-match') == 'etag-old'
    assert saved == [work]


def test_set_gps_updates_raw_photo_and_repository(monkeypatch, tmp_path):
    import backend.photo_metadata as metadata
    from backend.photo_repository import PhotoRepository
    from backend.storage import JsonStore

    raw_dir = tmp_path / 'raw_photos'
    raw_dir.mkdir()
    path = raw_dir / 'photo.jpg'
    Image.new('RGB', (8, 8), 'white').save(path, 'JPEG')
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    repository = PhotoRepository(JsonStore(data_dir))

    monkeypatch.setattr(metadata, 'BASE_DIR', str(tmp_path))
    monkeypatch.setattr(metadata, 'PHOTO_REPOSITORY', repository)

    metadata.set_gps('photo.jpg', 22.5431, 113.9579)

    saved = repository.list()
    assert saved[0]['filename'] == 'photo.jpg'
    assert saved[0]['exif']['gps'] == {'lat': 22.5431, 'lng': 113.9579}
    with Image.open(path) as image:
        assert image.getexif()
