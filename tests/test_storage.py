import json

import pytest

import backend.data as data_module
from backend.storage import DataCorruptionError, JsonStore


def test_json_store_returns_default_for_missing_file(tmp_path):
    store = JsonStore(tmp_path)

    assert store.read('missing.json') == []
    assert store.read('missing.json', default={}) == {}


def test_json_store_reports_corrupt_existing_file(tmp_path):
    (tmp_path / 'broken.json').write_text('{broken', encoding='utf-8')
    store = JsonStore(tmp_path)

    with pytest.raises(DataCorruptionError, match='Invalid JSON data'):
        store.read('broken.json')


def test_data_load_json_propagates_corruption(tmp_path, monkeypatch):
    (tmp_path / 'broken.json').write_text('{broken', encoding='utf-8')
    monkeypatch.setattr(data_module, 'STORE', JsonStore(tmp_path))

    with pytest.raises(DataCorruptionError, match='Invalid JSON data'):
        data_module.load_json('broken.json')


def test_json_store_writes_json_atomically(tmp_path):
    store = JsonStore(tmp_path)

    store.write('items.json', [{'id': 1, 'title': '测试'}])

    assert json.loads((tmp_path / 'items.json').read_text(encoding='utf-8')) == [
        {'id': 1, 'title': '测试'}
    ]
    assert not (tmp_path / 'items.json.tmp').exists()
