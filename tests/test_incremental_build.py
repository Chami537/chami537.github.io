"""Regression checks for build dependencies and unchanged output files."""

import json
import os
import runpy
import sys
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

import backend.data as data
import backend.ssg as ssg
from backend.essay_repository import EssayRepository
from backend.photo_repository import PhotoRepository
from backend.storage import JsonStore


ROOT = Path(__file__).resolve().parents[1]


def write_input(path, content, modified=100):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    os.utime(path, (modified, modified))


@pytest.fixture
def build_site(tmp_path, monkeypatch):
    essays = [{'slug': 'probe', 'title': 'Probe', 'tag': 'A, B', 'date': '2026-01'}]
    write_input(tmp_path / 'data/essays.json', json.dumps(essays))
    write_input(tmp_path / 'data/photos.json', '[]')
    write_input(tmp_path / 'data/tags_order.json', '["A", "B"]')
    write_input(tmp_path / 'md/probe.md', '# Body')
    for name in ('essay.html', 'archive.html', 'map.html'):
        write_input(
            tmp_path / 'templates' / name,
            '{% include "includes/base.css" %}'
            '{% include "includes/nav.html" %}'
            '{{ body_html }}{% include "includes/footer.html" %}',
        )
    write_input(tmp_path / 'templates/includes/base.css', 'old style')
    write_input(tmp_path / 'templates/includes/nav.html', '{% include "includes/link.html" %}')
    write_input(tmp_path / 'templates/includes/link.html', 'old nav')
    write_input(tmp_path / 'templates/includes/footer.html', 'old footer')
    write_input(tmp_path / 'templates/rss.xml', '<rss/>')
    write_input(tmp_path / 'templates/sitemap.xml', '<urlset/>')
    store = JsonStore(tmp_path / 'data')
    monkeypatch.setattr(ssg, 'ESSAY_REPOSITORY', EssayRepository(store))
    monkeypatch.setattr(ssg, 'PHOTO_REPOSITORY', PhotoRepository(store))
    monkeypatch.setattr(ssg, '_env', Environment(loader=FileSystemLoader(tmp_path / 'templates')))
    monkeypatch.setattr(ssg, 'get_essay_password', lambda _: '')
    for module in (data, ssg):
        for name, relative in (
            ('BASE_DIR', ''), ('DATA_DIR', 'data'), ('ESSAYS_DIR', 'essays'), ('MD_DIR', 'md'),
        ):
            monkeypatch.setattr(module, name, str(tmp_path / relative))
    monkeypatch.setattr(data, 'load_json', store.read)
    monkeypatch.setattr('backend.github_sync.fetch_stars', lambda: None)
    monkeypatch.setattr('backend.site_health.run_site_health', lambda *_: {'status': 'passed'})
    return tmp_path, essays


def test_public_listing_updates_when_only_tag_order_changes(build_site):
    root, essays = build_site
    ssg._generate_public_essays(essays)
    output = root / 'data/essays_public.json'
    os.utime(output, (200, 200))
    write_input(root / 'data/tags_order.json', '["B", "A"]', modified=300)

    ssg._generate_public_essays(essays)

    assert json.loads(output.read_text(encoding='utf-8'))['_tags'] == ['B', 'A']


@pytest.mark.parametrize('page,generator', [
    ('archive.html', ssg._generate_archive),
    ('map.html', ssg._generate_map),
])
def test_feed_page_rebuilds_after_nested_include_changes(build_site, page, generator):
    root, _ = build_site
    generator([])
    output = root / page
    os.utime(output, (200, 200))
    write_input(root / 'templates/includes/link.html', 'new nav', modified=300)

    generator([])

    assert 'new nav' in output.read_text(encoding='utf-8')


@pytest.mark.parametrize('include,content', [
    ('link.html', 'new nav'),
    ('base.css', 'new style'),
    ('footer.html', 'new footer'),
])
def test_build_command_rebuilds_essay_after_include_changes(build_site, monkeypatch, include, content):
    root, essays = build_site
    ssg.sync_essay_html(essays[0], essays=essays)
    output = root / 'essays/probe.html'
    os.utime(output, (200, 200))
    write_input(root / 'templates/includes' / include, content, modified=300)
    monkeypatch.setattr(sys, 'argv', ['manage.py', 'build'])

    runpy.run_path(str(ROOT / 'manage.py'), run_name='__main__')

    assert content in output.read_text(encoding='utf-8')
    assert '<h1>Body</h1>' in output.read_text(encoding='utf-8')


@pytest.mark.parametrize('page,generator', [
    ('archive.html', ssg._generate_archive),
    ('map.html', ssg._generate_map),
])
def test_feed_page_skips_rebuild_for_unrelated_template(build_site, page, generator):
    root, _ = build_site
    generator([])
    output = root / page
    os.utime(output, (200, 200))
    write_input(root / 'templates/unrelated.html', 'unrelated', modified=300)

    generator([])

    assert output.stat().st_mtime_ns == 200_000_000_000


def test_build_command_skips_unchanged_essay(build_site, monkeypatch):
    root, essays = build_site
    ssg.sync_essay_html(essays[0], essays=essays)
    output = root / 'essays/probe.html'
    os.utime(output, (200, 200))
    write_input(root / 'templates/unrelated.html', 'unrelated', modified=300)
    monkeypatch.setattr(sys, 'argv', ['manage.py', 'build'])

    runpy.run_path(str(ROOT / 'manage.py'), run_name='__main__')

    assert output.stat().st_mtime_ns == 200_000_000_000
