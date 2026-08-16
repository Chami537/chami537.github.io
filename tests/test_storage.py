import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

import backend.data as data_module
from backend.storage import DataCorruptionError, JsonRepository, JsonStore


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


def test_json_repository_uses_an_explicit_store(tmp_path):
    repository = JsonRepository('items.json', JsonStore(tmp_path))

    repository.save([{'id': 1}])

    assert repository.list() == [{'id': 1}]


def test_json_repository_serializes_read_modify_write_transactions(tmp_path):
    store = JsonStore(tmp_path)
    first = JsonRepository('items.json', store)
    second = JsonRepository('items.json', store)

    def append(repository, value):
        def callback(items):
            time.sleep(0.01)
            items.append({'value': value})
            return True
        repository.mutate(callback)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda args: append(*args), [(first, 'a'), (second, 'b')]))

    assert sorted(item['value'] for item in first.list()) == ['a', 'b']
