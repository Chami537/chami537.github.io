"""Visibility controls listing/discovery while preserving direct article access."""
import json

import pytest

from backend.essay_service import EssayService
from backend.essay_navigation import build_nav
from backend.storage import JsonStore
from backend.essay_repository import EssayRepository


def test_hidden_essays_are_excluded_from_public_data_and_tags():
    essays = [
        {'slug': 'legacy', 'tag': '生活'},
        {'slug': 'hidden', 'tag': '隐藏分类', 'visible': False},
        {'slug': 'shown', 'tag': '技术', 'visible': True},
    ]
    public, tags = EssayService(None).public_listing(essays, str, lambda _: '')
    assert [e['slug'] for e in public] == ['legacy', 'shown']
    assert tags == {'生活', '技术'}


def test_hidden_essays_are_excluded_from_generated_discovery(tmp_path, monkeypatch):
    import backend.ssg as ssg
    essays = [
        {'slug': 'visibility-hidden-fixture', 'title': 'Hidden', 'tag': 'secret', 'visible': False},
        {'slug': 'shown', 'title': 'Shown', 'date': '2026-11-02'},
    ]
    monkeypatch.setattr(ssg, 'BASE_DIR', str(tmp_path))
    monkeypatch.setattr(ssg, 'DATA_DIR', str(tmp_path))
    monkeypatch.setattr(ssg, '_needs_regeneration', lambda *_: True)
    monkeypatch.setattr(ssg, '_ordered_public_tags', sorted)
    ssg._generate_public_essays(essays)
    ssg._generate_rss(essays)
    ssg._generate_sitemap(essays)
    ssg._generate_archive(essays)
    public = json.loads((tmp_path / 'essays_public.json').read_text())
    assert [e['slug'] for e in public['essays']] == ['shown']
    for name in ('rss.xml', 'sitemap.xml', 'archive.html'):
        output = (tmp_path / name).read_text()
        assert 'visibility-hidden-fixture' not in output
        assert 'shown' in output


def test_feed_limit_is_applied_after_visibility_filter():
    from backend.essay_feed_data import strip_enrich
    result = strip_enrich([
        {'slug': 'hidden', 'visible': False}, {'slug': 'shown'},
    ], 'pub_date', '%Y-%m-%d', limit=1)
    assert [e['slug'] for e in result] == ['shown']


def test_navigation_skips_hidden_articles_in_both_directions():
    essays = [
        {'slug': 'a', 'title': 'A'},
        {'slug': 'hidden', 'title': 'Hidden', 'visible': False},
        {'slug': 'b', 'title': 'B'},
    ]
    assert 'b.html' in build_nav(essays, 'a')[1]
    assert 'a.html' in build_nav(essays, 'b')[0]
    assert 'hidden.html' not in ''.join(build_nav(essays, 'a'))
    # A direct visit to a hidden article still has useful public navigation.
    assert 'a.html' in build_nav(essays, 'hidden')[0]
    assert 'b.html' in build_nav(essays, 'hidden')[1]


@pytest.fixture
def isolated_essays(tmp_path, monkeypatch):
    from backend.routes import essay_context
    repository = EssayRepository(JsonStore(str(tmp_path)))
    repository.save([])
    monkeypatch.setattr(essay_context, 'ESSAY_REPOSITORY', repository)
    monkeypatch.setattr(essay_context, 'ESSAY_SERVICE', EssayService(repository))
    synced = []
    monkeypatch.setattr(essay_context.ESSAY_WORKFLOW, 'sync', lambda essay, **_: synced.append(essay['slug']))
    monkeypatch.setattr(essay_context.ESSAY_WORKFLOW, 'regenerate_feeds', lambda: None)
    return repository, synced


def test_visibility_create_update_restore_and_preserve(client, isolated_essays):
    repository, synced = isolated_essays
    for slug, extra in [('legacy', {}), ('hidden', {'visible': False})]:
        response = client.post('/api/essays', json={'slug': slug, 'title': slug, **extra})
        assert response.status_code == 201
        assert response.json['visible'] is (slug == 'legacy')
    assert len(client.get('/api/essays').json) == 2
    assert client.put('/api/essays/hidden', json={'title': 'renamed'}).json['visible'] is False
    synced.clear()
    assert client.put('/api/essays/hidden', json={'visible': True}).json['visible'] is True
    assert set(synced) == {'legacy', 'hidden'}
    assert client.put('/api/essays/hidden', json={'visible': False}).json['visible'] is False
    assert repository.list()[1]['visible'] is False


@pytest.mark.parametrize('invalid', ['false', 'invisible', 0, 1, None, []])
def test_visibility_rejects_non_boolean_input(client, isolated_essays, invalid):
    repository, _ = isolated_essays
    repository.save([{'slug': 'existing'}])
    assert client.post('/api/essays', json={'slug': 'new', 'visible': invalid}).status_code == 400
    assert client.put('/api/essays/existing', json={'visible': invalid}).status_code == 400
    assert repository.list() == [{'slug': 'existing'}]


def test_hidden_essays_cannot_be_selected_for_stories():
    from backend.story_service import public_essay_slugs
    assert public_essay_slugs([
        {'slug': 'hidden', 'visible': False}, {'slug': 'legacy'},
    ], has_password=lambda _: False) == {'legacy'}
