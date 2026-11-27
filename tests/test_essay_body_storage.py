"""Essay bodies belong in Markdown sources, never in publishable metadata."""

import copy
import json
import re
import runpy
import shutil
import sys
from pathlib import Path

import pytest

import backend.data as data
import backend.repositories as repositories
import backend.ssg as ssg
from backend.essay_crypto import decrypt_content, encrypt_content
from backend.essay_repository import EssayRepository
from backend.essay_service import EssayService
from backend.photo_repository import PhotoRepository
from backend.routes import essay_content, essay_context, essay_metadata
from backend.storage import JsonRepository, JsonStore


ROOT = Path(__file__).resolve().parents[1]
BODY_FIELDS = ('body', 'content', 'markdown', 'raw_md', 'body_html', 'html')
PRIVATE_BODY = 'PROTECTED_BODY_MUST_NEVER_SHIP_8d917b'


@pytest.fixture
def essay_site(tmp_path, monkeypatch):
    root = tmp_path / 'site'
    for name in ('data', 'md', 'essays', 'images'):
        (root / name).mkdir(parents=True)
    shutil.copytree(ROOT / 'templates', root / 'templates')
    store = JsonStore(root / 'data')
    repository = EssayRepository(store)
    service = EssayService(repository)
    monkeypatch.setattr(data, 'STORE', store)
    monkeypatch.setattr(repositories, 'STORE', store)
    monkeypatch.setattr(data, 'PASSWORD_STORE', str(tmp_path / 'local-passwords.json'))
    for key in ('ESSAY_MASTER_PASSWORD', 'ESSAY_PASSWORD_PRIVATE_FIXTURE', 'ESSAY_PASSWORD_PUBLIC_FIXTURE'):
        monkeypatch.delenv(key, raising=False)
    for module in (data, ssg, essay_content, essay_metadata):
        for name, relative in (
            ('BASE_DIR', ''), ('DATA_DIR', 'data'), ('MD_DIR', 'md'),
            ('ESSAYS_DIR', 'essays'), ('IMAGES_DIR', 'images'),
        ):
            if hasattr(module, name):
                monkeypatch.setattr(module, name, str(root / relative))
    for module in (ssg, essay_context):
        monkeypatch.setattr(module, 'ESSAY_REPOSITORY', repository)
        monkeypatch.setattr(module, 'ESSAY_SERVICE', service)
    monkeypatch.setattr(ssg, 'PHOTO_REPOSITORY', PhotoRepository(store))
    store.write('photos.json', [])
    store.write('tags_order.json', [])
    return root, repository


def seed_legacy_metadata(root, essays):
    # Deliberately bypass the application writer to model already committed data.
    (root / 'data/essays.json').write_text(json.dumps(essays), encoding='utf-8')


@pytest.mark.parametrize('writer', ['store', 'essay-repository', 'generic-repository', 'compatibility'])
def test_every_metadata_writer_discards_body_copies_without_passwords(essay_site, monkeypatch, writer):
    root, repository = essay_site
    essays = [
        {'slug': 'private-fixture', 'title': 'Private', **dict.fromkeys(BODY_FIELDS, PRIVATE_BODY)},
        {'slug': 'public-fixture', 'title': 'Public', 'custom_metadata': {'keep': True}, 'body': 'Public body'},
    ]
    original = copy.deepcopy(essays)
    seed_legacy_metadata(root, essays)
    assert repository.list() == essays  # Also prime the store's read cache.
    (root / 'md/private-fixture.md').write_text(encrypt_content(PRIVATE_BODY, 'pw'), encoding='utf-8')

    def unexpected_password_lookup(_slug):
        pytest.fail('Metadata sanitization must work without deployment passwords')

    monkeypatch.setattr(data, 'get_essay_password', unexpected_password_lookup)
    writers = {
        'store': lambda value: repository.store.write('essays.json', value),
        'essay-repository': repository.save,
        'generic-repository': JsonRepository('essays.json', repository.store).save,
        'compatibility': lambda value: data.atomic_write_json('essays.json', value),
    }
    writers[writer](essays)

    expected = [
        {'slug': 'private-fixture', 'title': 'Private'},
        {'slug': 'public-fixture', 'title': 'Public', 'custom_metadata': {'keep': True}},
    ]
    assert json.loads((root / 'data/essays.json').read_text()) == expected
    assert repository.list() == expected
    assert essays == original  # Serialization must not mutate caller-owned data.
    repository.store.write('other.json', original)
    assert repository.store.read('other.json') == original


def test_setting_password_strips_legacy_body_before_saving_and_rendering(client, essay_site, monkeypatch):
    root, repository = essay_site
    seed_legacy_metadata(root, [{
        'slug': 'private-fixture', 'title': 'Private', 'password': 'obsolete',
        **dict.fromkeys(BODY_FIELDS, PRIVATE_BODY),
    }])
    (root / 'md/private-fixture.md').write_text(PRIVATE_BODY, encoding='utf-8')
    saved = []
    original_save = repository.save

    def record_save(essays):
        saved.append(copy.deepcopy(essays))
        original_save(essays)

    monkeypatch.setattr(repository, 'save', record_save)
    response = client.post('/api/essays/private-fixture/password', json={'password': 'new-password'})

    assert response.status_code == 200
    assert response.json == {'password_set': True}
    assert saved[0] == [{'slug': 'private-fixture', 'title': 'Private'}]
    assert repository.list() == saved[0]
    assert PRIVATE_BODY not in (root / 'data/essays.json').read_text()
    encrypted = (root / 'md/private-fixture.md').read_text()
    assert decrypt_content(encrypted, 'new-password') == PRIVATE_BODY
    assert client.get('/api/essays/private-fixture/content').json['content'] == PRIVATE_BODY
    for path in root.rglob('*'):
        if path.is_file():
            assert PRIVATE_BODY.encode() not in path.read_bytes(), path.relative_to(root)


def test_metadata_update_cannot_reintroduce_a_protected_body(client, essay_site):
    root, repository = essay_site
    repository.save([{'slug': 'private-fixture', 'title': 'Private'}])
    (root / 'md/private-fixture.md').write_text(encrypt_content(PRIVATE_BODY, 'pw'), encoding='utf-8')

    response = client.put('/api/essays/private-fixture', json={
        'title': 'Updated', **dict.fromkeys(BODY_FIELDS, PRIVATE_BODY),
    })

    assert response.status_code == 200
    assert repository.list() == [{'slug': 'private-fixture', 'title': 'Updated'}]
    for path in root.rglob('*'):
        if path.is_file():
            assert PRIVATE_BODY.encode() not in path.read_bytes(), path.relative_to(root)


@pytest.mark.parametrize('source_format', ['markdown', 'html-fallback'])
def test_build_removes_legacy_protected_body_from_every_uploaded_file(essay_site, monkeypatch, source_format):
    root, repository = essay_site
    essays = [
        {'slug': 'private-fixture', 'title': 'Private', **dict.fromkeys(BODY_FIELDS, PRIVATE_BODY)},
        {'slug': 'public-fixture', 'title': 'Public', 'date': '2026-11-27', 'body': 'Public body'},
    ]
    seed_legacy_metadata(root, essays)
    encrypted = encrypt_content(PRIVATE_BODY, 'build-does-not-know-this-password')
    if source_format == 'markdown':
        (root / 'md/private-fixture.md').write_text(encrypted, encoding='utf-8')
    else:
        (root / 'essays/private-fixture.html').write_text(f'<!-- RAW_MD\n{encrypted}\nRAW_MD -->', encoding='utf-8')
    (root / 'md/public-fixture.md').write_text('# Public body', encoding='utf-8')
    # The build entrypoint and generators run normally; health/stars are unrelated.
    monkeypatch.setattr('backend.site_health.run_site_health', lambda *_: {'status': 'passed'})
    monkeypatch.setattr('backend.github_sync.fetch_stars', lambda: None)
    monkeypatch.setattr(sys, 'argv', ['manage.py', 'build', '--force'])

    runpy.run_path(str(ROOT / 'manage.py'), run_name='__main__')

    assert all(not set(essay) & set(BODY_FIELDS) for essay in repository.list())
    public = json.loads((root / 'data/essays_public.json').read_text())['essays']
    assert [essay['password_protected'] for essay in public] == [True, False]
    assert 'id="essay-gate"' in (root / 'essays/private-fixture.html').read_text()
    assert '<h1>Public body</h1>' in (root / 'essays/public-fixture.html').read_text()
    for name in ('data/essays.json', 'data/essays_public.json', 'essays/private-fixture.html',
                 'essays/public-fixture.html', 'archive.html', 'rss.xml', 'sitemap.xml'):
        assert (root / name).is_file(), name
    # The workflow uploads '.', so inspect every file, including sources and temps.
    for path in root.rglob('*'):
        if path.is_file():
            assert PRIVATE_BODY.encode() not in path.read_bytes(), path.relative_to(root)
    assert not list(root.rglob('*.tmp'))
    sanitized_mtime = (root / 'data/essays.json').stat().st_mtime_ns
    monkeypatch.setattr(sys, 'argv', ['manage.py', 'build'])
    runpy.run_path(str(ROOT / 'manage.py'), run_name='__main__')
    assert (root / 'data/essays.json').stat().st_mtime_ns == sanitized_mtime


def test_public_list_render_editor_and_feeds_preserve_behavior(client, essay_site):
    root, repository = essay_site
    essay = {
        'slug': 'public-fixture', 'title': 'Public title', 'date': '2026-11-27',
        'excerpt': 'Public excerpt', 'epigraph': 'Public epigraph', 'tag': '生活',
        'readTime': 2, 'pinned': True, 'visible': True,
        'body': 'Unused metadata body', 'content': 'Unused metadata content',
    }
    source = '# Public heading\n\nPublic prose with **formatting**.'
    seed_legacy_metadata(root, [essay])
    (root / 'md/public-fixture.md').write_text(source, encoding='utf-8')
    ssg.sync_essay_html(essay, essays=[essay])
    for generator in (ssg._generate_public_essays, ssg._generate_archive, ssg._generate_rss, ssg._generate_sitemap):
        generator([essay])
    names = ('data/essays_public.json', 'essays/public-fixture.html', 'archive.html', 'rss.xml', 'sitemap.xml')

    def outputs():
        normalized = {}
        for name in names:
            text = (root / name).read_text()
            text = re.sub(r'(?<=v=)\d+|(?<=data-build-ts=")\d+', 'BUILD', text)
            normalized[name] = re.sub(r'<lastBuildDate>.*?</lastBuildDate>', '<lastBuildDate/>', text)
        return normalized

    before = outputs()
    repository.save([essay])
    ssg.sync_essay_html(repository.list()[0])
    ssg.generate_feeds()

    assert outputs() == before
    assert repository.list() == [{key: value for key, value in essay.items() if key not in ('body', 'content')}]
    assert '<h1>Public heading</h1>' in before['essays/public-fixture.html']
    assert '<strong>formatting</strong>' in before['essays/public-fixture.html']
    assert client.get('/api/essays/public-fixture/content').json['content'] == source
    listed = client.get('/api/essays').json
    assert len(listed) == 1
    assert listed[0]['title'] == 'Public title'
    assert listed[0]['password_set'] is False
    assert (root / 'md/public-fixture.md').read_text() == source
