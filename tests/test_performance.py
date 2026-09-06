"""Low-cost performance budgets for the static site and local CMS."""

import re
import time
from pathlib import Path

from backend.app import app
from backend.storage import JsonStore


ROOT = Path(__file__).resolve().parents[1]


def test_entry_pages_defer_javascript_and_admin_does_not_preload_heavy_libraries():
    index = (ROOT / 'index.html').read_text(encoding='utf-8')
    admin = (ROOT / 'admin.html').read_text(encoding='utf-8')

    assert len(re.findall(r'<script\s+defer\s+src=', index)) >= 9
    assert len(re.findall(r'<script\s+defer\s+src=', admin)) >= 10
    assert len(re.findall(r'<script\s+type="text/plain"\s+data-lazy-src=', admin)) >= 25
    assert 'cdn.staticfile.net/KaTeX/0.16.9/katex.min.js' not in admin
    assert '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js' not in admin


def test_homepage_images_have_async_decoding_and_first_photo_priority():
    gallery = (ROOT / 'assets' / 'js' / 'index-photo-gallery.js').read_text(encoding='utf-8')
    homepage = (ROOT / 'index.html').read_text(encoding='utf-8')

    assert 'decoding="async"' in gallery
    assert "loading=\"' + (index === 0 ? 'eager' : 'lazy')" in gallery
    assert 'fetchpriority="high"' in homepage


def test_static_cache_headers_are_long_lived_for_immutable_assets():
    app.config['TESTING'] = True
    client = app.test_client()

    asset = client.get('/assets/js/index.js')
    image = client.get('/images/sm/020660bd.jpg')
    assert asset.headers['Cache-Control'] == 'public, max-age=31536000'
    assert image.headers['Cache-Control'] == 'public, max-age=31536000'


def test_json_store_cache_detects_external_file_changes(tmp_path):
    path = tmp_path / 'items.json'
    path.write_text('[1]', encoding='utf-8')
    store = JsonStore(tmp_path)

    assert store.read('items.json') == [1]
    path.write_text('[1, 2]', encoding='utf-8')
    assert store.read('items.json') == [1, 2]


def test_key_read_endpoints_stay_within_local_latency_budget():
    app.config['TESTING'] = True
    client = app.test_client()
    paths = ('/api/about', '/api/work', '/api/essays', '/api/photos', '/api/dashboard-stats')

    for path in paths:
        samples = []
        for _ in range(5):
            started = time.perf_counter()
            response = client.get(path)
            samples.append(time.perf_counter() - started)
            assert response.status_code == 200
        samples.sort()
        assert samples[-1] < 0.1, f'{path} exceeded 100ms local p95 budget'
