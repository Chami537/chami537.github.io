import json

import backend.data as data_module
from backend.essay_service import EssayService
from backend.routes.essays import _apply_meta_updates, _validate_meta_slug


class MemoryEssayRepository:
    def __init__(self, essays):
        self.essays = essays

    def list(self):
        return self.essays


def test_essay_service_public_listing_marks_protected_metadata_only():
    service = EssayService(MemoryEssayRepository([]))
    essays = [{'slug': 'secret', 'title': 'Secret', 'tag': '技术', 'password': 'never-public'}]

    public, tags = service.public_listing(essays, lambda value: 'formatted', lambda slug: 'pw')

    assert public == [{
        'slug': 'secret', 'title': 'Secret', 'tag': '技术',
        'date_display': 'formatted', 'password_protected': True,
    }]
    assert tags == {'技术'}


def test_essay_service_admin_listing_adds_status_without_password_value():
    essays = [{'slug': 'secret', 'title': 'Secret'}]
    service = EssayService(MemoryEssayRepository(essays))

    result = service.list_for_admin(lambda value: 'formatted', lambda slug: True)

    assert result[0]['date_display'] == 'formatted'
    assert result[0]['password_set'] is True
    assert 'password' not in result[0]


def test_meta_slug_helpers_validate_conflicts_and_strip_password():
    essays = [{'slug': 'first'}, {'slug': 'second'}]
    assert _validate_meta_slug('first', 'bad slug', essays)
    assert _validate_meta_slug('first', 'second', essays) == 'slug 已存在'
    assert _validate_meta_slug('first', 'renamed', essays) is None

    essay = {'slug': 'first', 'title': 'Old'}
    _apply_meta_updates(essay, {'slug': 'renamed', 'password': 'secret', 'title': 'New'}, 'renamed')
    assert essay == {'slug': 'renamed', 'title': 'New'}


def test_password_store_helpers_follow_slug_lifecycle(tmp_path, monkeypatch):
    password_store = tmp_path / 'essay_passwords.json'
    password_store.write_text('{"old-slug": "secret"}', encoding='utf-8')
    monkeypatch.setattr(data_module, 'PASSWORD_STORE', str(password_store))

    rename_password = getattr(data_module, 'rename_essay_password', None)
    delete_password = getattr(data_module, 'delete_essay_password', None)
    assert rename_password is not None
    assert delete_password is not None

    rename_password('old-slug', 'new-slug')
    assert json.loads(password_store.read_text(encoding='utf-8')) == {
        'new-slug': 'secret',
    }

    delete_password('new-slug')
    assert json.loads(password_store.read_text(encoding='utf-8')) == {}
