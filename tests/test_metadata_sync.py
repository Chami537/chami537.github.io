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


def test_set_gps_updates_raw_photo_and_repository(monkeypatch, tmp_path):
    import backend.photo_metadata as metadata

    raw_dir = tmp_path / 'raw_photos'
    raw_dir.mkdir()
    path = raw_dir / 'photo.jpg'
    Image.new('RGB', (8, 8), 'white').save(path, 'JPEG')
    saved = []

    class Repo:
        def list(self): return []
        def save(self, value): saved[:] = value

    monkeypatch.setattr(metadata, 'BASE_DIR', str(tmp_path))
    monkeypatch.setattr(metadata, 'repository_for', lambda _: Repo())

    metadata.set_gps('photo.jpg', 22.5431, 113.9579)

    assert saved[0]['filename'] == 'photo.jpg'
    assert saved[0]['exif']['gps'] == {'lat': 22.5431, 'lng': 113.9579}
    with Image.open(path) as image:
        assert image.getexif()
