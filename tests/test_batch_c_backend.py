"""C1/C4/C5 behavior checks; all generated artifacts live in pytest tmp_path."""

import json
import os
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from PIL import Image
from jinja2 import Environment, FileSystemLoader

from backend.asset_cache import asset_fingerprint, asset_url, cache_bust_assets
from backend.image_utils import photo_dimensions, write_photo_variants
from backend.markdown_utils import heading_id, heading_ids, render_markdown

ROOT = Path(__file__).resolve().parents[1]


def node(script):
    return subprocess.run(['node', '-e', script], cwd=ROOT, check=True,
                          capture_output=True, text=True, timeout=20).stdout


def test_fingerprints_follow_content_instead_of_mtime(tmp_path):
    asset = tmp_path / 'assets/js/a.js'
    asset.parent.mkdir(parents=True)
    asset.write_text('first')
    first = asset_url('/assets/js/a.js?v=123&mode=one#part', tmp_path)
    os.utime(asset, (100, 100))
    assert asset_url('/assets/js/a.js?v=123&mode=one#part', tmp_path) == first
    asset.write_text('other')
    os.utime(asset, (100, 100))
    assert asset_url('/assets/js/a.js?v=123&mode=one#part', tmp_path) != first
    assert 'mode=one' in first and first.endswith('#part')


def test_cache_bust_covers_essay_and_keeps_unchanged_output(tmp_path):
    asset = tmp_path / 'assets/js/a.js'
    asset.parent.mkdir(parents=True)
    asset.write_text('script')
    page = tmp_path / 'essays/a.html'
    page.parent.mkdir()
    page.write_text('<script src="/assets/js/a.js?v=old"></script>'
                    '<link href="../assets/js/a.js">'
                    '<!-- RAW_MD\n<script src="/assets/js/a.js?v=old"></script>\nRAW_MD -->'
                    '<script src="https://example.com/a.js?v=old"></script>')
    cache_bust_assets(tmp_path)
    assert page.read_text().count(asset_fingerprint(asset)) == 2
    assert 'https://example.com/a.js?v=old' in page.read_text()
    assert '<!-- RAW_MD\n<script src="/assets/js/a.js?v=old"></script>\nRAW_MD -->' in page.read_text()
    os.utime(page, (100, 100))
    cache_bust_assets(tmp_path)
    assert page.stat().st_mtime_ns == 100_000_000_000


def test_essay_dependencies_and_backdated_asset_rebuild(tmp_path, monkeypatch):
    import backend.ssg as ssg
    (tmp_path / 'templates/includes').mkdir(parents=True)
    (tmp_path / 'templates/essay.html').write_text('{% include "includes/assets.html" %}')
    (tmp_path / 'templates/includes/assets.html').write_text(
        '<script src="{{ asset_url(\'/assets/js/a.js\') }}"></script>')
    asset = tmp_path / 'assets/js/a.js'
    asset.parent.mkdir(parents=True)
    asset.write_text('first')
    page = tmp_path / 'essay.html'
    monkeypatch.setattr(ssg, 'BASE_DIR', str(tmp_path))
    monkeypatch.setattr(ssg, '_env', Environment(loader=FileSystemLoader(tmp_path / 'templates')))
    inputs = ssg.essay_dependencies()
    assert str(asset) in inputs
    page.write_text('<script src="' + asset_url('/assets/js/a.js', tmp_path) + '"></script>')
    for path in inputs:
        os.utime(path, (100, 100))
    os.utime(page, (200, 200))
    assert not ssg.essay_needs_regeneration(page, inputs)
    unrelated = tmp_path / 'assets/js/unrelated.js'
    unrelated.write_text('unrelated')
    assert not ssg.essay_needs_regeneration(page, inputs)
    asset.write_text('other')
    os.utime(asset, (100, 100))
    assert ssg.essay_needs_regeneration(page, inputs)


def test_real_essay_template_versions_every_local_stylesheet_and_script():
    import re
    from backend.essay_renderer import render_essay_html
    from backend.ssg import _env, _parse_date
    body = {'body_html': '', 'encrypted_body': '', 'password_protected': False,
            'encrypted_is_md': False, 'og_image': '', 'raw_md': ''}
    essay = {'slug': 'fixture', 'title': 'Fixture'}
    html = render_essay_html(essay, body, [essay], _env.get_template('essay.html'), _parse_date, ROOT)
    urls = re.findall(r'(?:href|src)="(/assets/(?:css|js)/[^\"]+)"', html)
    assert len(urls) == 10
    for url in urls:
        relative, version = url.split('?v=')
        assert version == asset_fingerprint(ROOT / relative.lstrip('/'))


@pytest.mark.parametrize('size', [(2400, 1200), (1200, 2400), (160, 120)])
def test_upload_and_sync_use_identical_resize_rule(tmp_path, size):
    from backend.routes import photo_context, photo_files
    from tools import process_images
    image = Image.new('RGB', size)
    # Test the shared implementation against both callers' size configurations.
    write_photo_variants(image, tmp_path / 'upload', 'a.jpg', photo_context.PHOTO_SIZES)
    write_photo_variants(image, tmp_path / 'sync', 'a.jpg', process_images.SIZES.items())
    assert photo_dimensions(tmp_path / 'upload', 'a.jpg') == photo_dimensions(tmp_path / 'sync', 'a.jpg')
    for name, limit in photo_context.PHOTO_SIZES:
        with Image.open(tmp_path / 'upload' / name / 'a.jpg') as resized:
            assert max(resized.size) == min(limit, max(size))
    assert photo_files.write_photo_variants is process_images.write_photo_variants


def test_sync_records_existing_variant_dimensions_without_resizing(tmp_path):
    for name, size in [('sm', (173, 400)), ('md', (347, 800)), ('lg', (833, 1920))]:
        path = tmp_path / name / 'p.jpg'
        path.parent.mkdir()
        Image.new('RGB', size).save(path)
    dimensions = photo_dimensions(tmp_path, 'p.jpg')
    assert dimensions['variants']['sm'] == {'width': 173, 'height': 400}
    assert (dimensions['width'], dimensions['height']) == (833, 1920)


def test_markdown_images_have_dimensions_and_only_later_images_are_lazy(tmp_path):
    (tmp_path / 'images/essays').mkdir(parents=True)
    Image.new('RGB', (90, 60)).save(tmp_path / 'images/essays/a b.jpg')
    result = render_markdown(
        '![first](/images/essays/a%20b.jpg)\n\n'
        '![next](../images/essays/a%20b.jpg)\n\n'
        '![remote](https://example.com/remote.jpg)', base_dir=tmp_path)
    images = ET.fromstring('<div>' + result + '</div>').findall('.//img')
    assert images[0].get('width') == '90' and images[0].get('height') == '60'
    assert images[0].get('loading') is None
    assert images[1].get('loading') == images[2].get('loading') == 'lazy'
    assert images[2].get('width') is None


def test_heading_and_wikilink_fragments_agree_before_javascript():
    html = render_markdown('## Hello 世界!\n\n[[Target#Hello 世界!|go]]\n\n[[#Hello 世界!|local]]',
                           [{'title': 'Target', 'slug': 'target'}])
    expected = heading_id('Hello 世界!')
    assert f'id="{expected}"' in html
    assert f'href="target.html#{expected}"' in html
    assert f'href="#{expected}"' in html


@pytest.mark.parametrize('texts', [
    ['Topic', 'Topic', 'Topic-2', 'Topic'],
    ['  Hello__世界!  ', 'A\tB', '㐀 中文', 'Été café', '!!!', ''],
    ['_Topic_', '-Topic-', 'A\ufeffB', 'A\x85B', 'A\x1cB', 'A\u2003B'],
])
def test_python_and_toc_pure_anchor_functions_agree(texts):
    script = """
const fs = require('fs'), vm = require('vm');
const context = {window: {}, document: {querySelector() {return null;}, getElementById() {return null;}}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('assets/js/essay-toc.js', 'utf8'), context);
console.log(JSON.stringify(context.essayHeadingIds(TEXTS)));
""".replace('TEXTS', json.dumps(texts))
    assert json.loads(node(script)) == heading_ids(texts)


def test_ssg_heading_ids_include_duplicates_inline_text_and_explicit_ids():
    html = render_markdown('# **Topic**\n\n## Topic\n\n### Topic\n\n#### ???\n\n## Custom {#custom}')
    headings = list(ET.fromstring('<div>' + html + '</div>'))
    assert [item.get('id') for item in headings] == [
        'heading-topic', 'heading-topic-2', 'heading-topic-3', 'heading-section', 'custom']


def test_photo_srcset_uses_measured_widths_and_layout_sizes():
    script = """
const assert = require('assert'), fs = require('fs'), vm = require('vm');
const context = {window: {_photoData: Array(45)}, Set};
vm.createContext(context);
vm.runInContext(fs.readFileSync('assets/js/index-photo-gallery.js', 'utf8'), context);
assert.strictEqual(context._photoSrcset('p.jpg', {sm: {width: 173}, md: {width: 347}, lg: {width: 833}}),
  'images/sm/p.jpg 173w, images/md/p.jpg 347w, images/lg/p.jpg 833w');
assert.strictEqual(context._photoSrcset('p.jpg', {sm: {width: 100}, md: {width: 100}}), 'images/sm/p.jpg 100w');
assert.strictEqual(context._photoSrcset('p.jpg'), '');
assert.strictEqual(context._photoSizes(), '(max-width: 768px) calc((100vw - 44px) / 2), (max-width: 1200px) calc((100vw - 108px) / 5), 218.4px');
context.window._photoData = Array(4);
assert(context._photoSizes().includes('/ 3)'));
"""
    node(script)


def test_photo_fallback_dimensions_match_small_variant():
    script = """
const assert = require('assert'), fs = require('fs'), vm = require('vm');
const context = {window: {}, Set, htmlEncode: String};
vm.createContext(context);
vm.runInContext(fs.readFileSync('assets/js/index-photo-gallery.js', 'utf8'), context);
context._photoMeta = () => ({date:'',exifText:'',gpsHtml:'',gpsText:''});
const html = context._photoItemHtml({filename:'p.jpg',width:833,height:1920,
  variants:{sm:{width:173,height:400},lg:{width:833,height:1920}}}, 0);
assert(html.includes('width="173" height="400"'));
"""
    node(script)


def test_chromium_toc_preserves_ssg_ids_and_builds_matching_links(tmp_path):
    import html as html_module
    import re
    shell = Path.home() / '.cache/ms-playwright/chromium_headless_shell-1169/chrome-linux/headless_shell'
    if not shell.is_file():
        pytest.skip('Existing Chromium headless shell is unavailable')
    body = render_markdown('# **Topic**\n\n## Topic\n\n### 世界\n\n#### Other')
    source = (ROOT / 'assets/js/essay-toc.js').read_text()
    check = """
const before = Array.from(document.querySelectorAll('.essay-body [id]')).map(h => h.id);
buildEssayToc();
const after = Array.from(document.querySelectorAll('.essay-body [id]')).map(h => h.id);
const links = Array.from(document.querySelectorAll('#essay-toc-list a')).map(a => decodeURIComponent(a.hash));
document.querySelector('#essay-toc-list a').click();
const report = {before, after, links, clicked: location.hash};
const pre = document.createElement('pre'); pre.id = 'result';
pre.textContent = JSON.stringify(report); document.body.appendChild(pre);
"""
    page = tmp_path / 'toc.html'
    page.write_text('<div class="essay-body">' + body + '</div>'
                    '<details id="essay-toc"><summary>TOC</summary><nav><ol id="essay-toc-list"></ol></nav></details>'
                    '<script>' + source + '</script><script>' + check + '</script>')
    process = subprocess.run([str(shell), '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu',
                              '--user-data-dir=' + str(tmp_path / 'profile'), '--dump-dom',
                              '--virtual-time-budget=1000', page.as_uri()],
                             capture_output=True, text=True, check=True, timeout=20)
    match = re.search(r'<pre id="result">(.*?)</pre>', process.stdout, re.S)
    assert match, process.stderr
    result = json.loads(html_module.unescape(match[1]))
    assert result['before'] == result['after'] == ['heading-topic', 'heading-topic-2', 'heading-世界', 'heading-other']
    assert result['links'] == ['#heading-topic', '#heading-topic-2', '#heading-世界']
    assert result['clicked'] == '#heading-topic'


def test_heading_ids_restore_placeholders_and_escapes():
    html = render_markdown('## Vec<T> \u7528\u6cd5\n\n## a\\_b\n\n## Tom &amp; Jerry\n\n## 5 &lt; 6')
    headings = list(ET.fromstring('<div>' + html + '</div>'))
    assert [item.get('id') for item in headings] == [
        heading_id('Vec<T> \u7528\u6cd5'), heading_id('a_b'),
        heading_id('Tom & Jerry'), heading_id('5 < 6')]
    legacy = render_markdown('## &copy 2024')
    assert list(ET.fromstring('<div>' + legacy + '</div>'))[0].get('id') == heading_id('&copy 2024')
    linked = render_markdown('## Vec<T> \u7528\u6cd5\n\n[[Target#Vec<T> \u7528\u6cd5|go]]',
                              [{'title': 'Target', 'slug': 'target'}])
    assert f'href="target.html#{heading_id("Vec<T> \u7528\u6cd5")}"' in linked
