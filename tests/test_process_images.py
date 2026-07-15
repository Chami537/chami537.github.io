import pytest
from PIL import Image

from backend.photo_repository import PhotoRepository
from backend.storage import DataCorruptionError, JsonStore
from tools import process_images


def _configure_photo_workspace(tmp_path, monkeypatch):
    raw_dir = tmp_path / 'raw_photos'
    image_dir = tmp_path / 'images'
    data_dir = tmp_path / 'data'
    raw_dir.mkdir()
    image_dir.mkdir()
    data_dir.mkdir()
    store = JsonStore(data_dir)
    monkeypatch.setattr(process_images, 'PHOTO_REPOSITORY', PhotoRepository(store))
    monkeypatch.setattr(process_images, 'RAW_DIR', str(raw_dir))
    monkeypatch.setattr(process_images, 'IMG_DIR', str(image_dir))
    monkeypatch.setattr(
        process_images,
        '_extract_exif',
        lambda _image: {'date': '2026-07-15 12:34'},
    )
    monkeypatch.setattr(process_images, '_without_camera_model', lambda value: value)
    return raw_dir, data_dir, store


def _write_jpeg(path, color):
    Image.new('RGB', (8, 6), color=color).save(path, 'JPEG')


def test_photo_sync_keeps_manual_fields_and_appends_exif_dated_new_photo(tmp_path, monkeypatch):
    raw_dir, _data_dir, store = _configure_photo_workspace(tmp_path, monkeypatch)
    _write_jpeg(raw_dir / 'old.jpg', 'red')
    _write_jpeg(raw_dir / 'new.jpg', 'blue')
    store.write('photos.json', [{
        'filename': 'old.jpg',
        'exif': {'model': 'Manual Camera'},
        'date': 'Jul 1, 2026',
        'size': 'lg',
        'tags': ['保留'],
    }])

    process_images.process_all_images()

    photos = {photo['filename']: photo for photo in store.read('photos.json')}
    assert set(photos) == {'old.jpg', 'new.jpg'}
    assert photos['old.jpg']['date'] == 'Jul 1, 2026'
    assert photos['old.jpg']['size'] == 'lg'
    assert photos['old.jpg']['tags'] == ['保留']
    assert photos['new.jpg']['date'] == 'Jul 15, 2026'


def test_photo_sync_does_not_overwrite_corrupted_metadata(tmp_path, monkeypatch):
    _raw_dir, data_dir, _store = _configure_photo_workspace(tmp_path, monkeypatch)
    photos_path = data_dir / 'photos.json'
    original = b'{broken'
    photos_path.write_bytes(original)

    with pytest.raises(DataCorruptionError, match='Invalid JSON data'):
        process_images.process_all_images()

    assert photos_path.read_bytes() == original
