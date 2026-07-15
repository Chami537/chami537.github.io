from concurrent.futures import ThreadPoolExecutor
import time

from backend.storage import JsonStore


def _repository(tmp_path):
    from backend.photo_repository import PhotoRepository

    return PhotoRepository(JsonStore(tmp_path))


def test_photo_repository_finds_and_updates_one_entry(tmp_path):
    repository = _repository(tmp_path)
    repository.save([{'filename': 'one.jpg', 'tags': []}])

    found, photos = repository.find('one.jpg')
    updated = repository.update('one.jpg', lambda photo: photo.update(tags=['kept']))

    assert found == {'filename': 'one.jpg', 'tags': []}
    assert photos == [{'filename': 'one.jpg', 'tags': []}]
    assert updated == {'filename': 'one.jpg', 'tags': ['kept']}
    assert repository.list() == [{'filename': 'one.jpg', 'tags': ['kept']}]


def test_photo_repository_refuses_replacement_that_drops_entries(tmp_path):
    repository = _repository(tmp_path)
    repository.save([{'filename': 'one.jpg'}, {'filename': 'two.jpg'}])

    lost = repository.replace_preserving([{'filename': 'one.jpg'}])

    assert lost == {'two.jpg'}
    assert repository.list() == [{'filename': 'one.jpg'}, {'filename': 'two.jpg'}]

    assert repository.delete('two.jpg') is True
    assert repository.delete('missing.jpg') is False
    assert repository.list() == [{'filename': 'one.jpg'}]


def test_photo_repository_serializes_parallel_appends(tmp_path, monkeypatch):
    repository = _repository(tmp_path)
    original_read = repository.store.read

    def delayed_read(filename, default=None):
        result = original_read(filename, default)
        time.sleep(0.01)
        return result

    monkeypatch.setattr(repository.store, 'read', delayed_read)
    entries = [{'filename': f'{index}.jpg'} for index in range(6)]

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(repository.append, entries))

    assert sorted(item['filename'] for item in repository.list()) == [
        f'{index}.jpg' for index in range(6)
    ]
