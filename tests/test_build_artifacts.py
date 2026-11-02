"""Post-build contracts for generated GitHub Pages artifacts."""

from pathlib import Path


ROOT = Path(__file__).parents[1]


def _assert_artifact(name, marker):
    path = ROOT / name
    assert path.is_file(), f'build did not create {name}'
    assert marker in path.read_text(encoding='utf-8')


def test_rss_feed_exists_after_build():
    _assert_artifact('rss.xml', '<rss version="2.0">')


def test_sitemap_exists_after_build():
    _assert_artifact('sitemap.xml', '<urlset xmlns=')


def test_archive_exists_after_build():
    _assert_artifact('archive.html', '<title>Archive — Chami</title>')


def test_map_exists_after_build():
    _assert_artifact('map.html', '<title>Map — Chami</title>')


def test_stories_live_on_homepage_and_legacy_page_redirects():
    import json
    _assert_artifact('shelf.html', '<title>留下来的故事 — Chami</title>')
    _assert_artifact('shelf.html', 'content="0;url=index.html#stories"')
    assert 'https://chami537.github.io/shelf.html' not in (ROOT / 'sitemap.xml').read_text(encoding='utf-8')
    _assert_artifact('index.html', 'id="stories-list"')
    assert isinstance(json.loads((ROOT / 'data/stories.json').read_text(encoding='utf-8')), list)
    for name in ('assets/js/index-stories.js', 'assets/js/shelf.js', 'assets/css/index-stories.css'):
        assert (ROOT / name).is_file()
