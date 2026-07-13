"""Tests for SSG functions and EXIF helpers."""
import os
import json
from pathlib import Path
import pytest
from PIL import Image
from backend.ssg import (
    _extract_exif, _extract_gps, _calc_read_time, _parse_date,
    _parse_tags, _find_adjacent_siblings, _extract_first_image,
    _cache_bust_assets, _encrypt_content, _decrypt_content, _is_encrypted_v3,
    _generate_public_essays, _sync_essay_html,
    ESSAYS_DIR, MD_DIR,
)
from backend.data import load_json
from backend.markdown_utils import render_markdown


# ── _calc_read_time ──

def test_calc_read_time_empty():
    assert _calc_read_time('') == 1
    assert _calc_read_time(None) == 1

def test_calc_read_time_english():
    # 300 words → 1.5 char equiv per word = 450 → ~2 min
    words = 'hello ' * 300
    assert _calc_read_time(words) >= 1

def test_calc_read_time_chinese():
    # 300 chars → 1 min
    text = '测试' * 150
    assert _calc_read_time(text) == 1


# ── _parse_date ──

def test_parse_date_full():
    assert 'Jun' in _parse_date('2026-06-25 14:30')

def test_parse_date_month():
    assert _parse_date('2026-06') == 'Jun 2026'

def test_parse_date_invalid():
    assert _parse_date('') == ''
    assert _parse_date(None) == ''


# ── _parse_tags ──

def test_parse_tags_simple():
    assert _parse_tags('生活, 摄影') == {'生活', '摄影'}

def test_parse_tags_pinned():
    result = _parse_tags('随笔', {'pinned': True})
    assert '置顶' in result

def test_parse_tags_empty():
    assert _parse_tags('') == set()
    assert _parse_tags(None) == set()


# ── _extract_first_image ──

def test_extract_first_image_markdown():
    md = 'text ![alt](https://example.com/img.jpg) more'
    assert _extract_first_image(md) == 'https://example.com/img.jpg'

def test_extract_first_image_none():
    assert 'avatar.jpg' in _extract_first_image(None)
    assert 'avatar.jpg' in _extract_first_image('')


# ── _find_adjacent_siblings ──

def test_find_adjacent_siblings():
    essays = [
        {'slug': 'a'}, {'slug': 'b'}, {'slug': 'c'}, {'slug': 'd'}
    ]
    # Find siblings around index 1 (b) in [a, c]
    prev_sib, next_sib = _find_adjacent_siblings(essays, 1, [essays[0], essays[2]])
    assert prev_sib['slug'] == 'a'
    assert next_sib['slug'] == 'c'

def test_find_adjacent_siblings_edges():
    essays = [{'slug': 'a'}, {'slug': 'b'}, {'slug': 'c'}]
    # First element, only next sibling
    prev_sib, next_sib = _find_adjacent_siblings(essays, 0, essays)
    assert prev_sib is None
    assert next_sib['slug'] == 'b'


# ── _extract_gps ──

def test_extract_gps_none():
    assert _extract_gps(None) is None
    assert _extract_gps({}) is None


# ── _extract_exif with real image ──

def test_extract_exif_no_exif():
    import io
    # Create a minimal JPEG (binary) — Image.new() doesn't support _getexif()
    buf = io.BytesIO()
    Image.new('RGB', (10, 10), color='red').save(buf, 'JPEG')
    buf.seek(0)
    img = Image.open(buf)
    result = _extract_exif(img)
    assert result == {}


def test_extract_exif_reads_nested_ifds():
    import io

    source = Image.new('RGB', (10, 10), color='red')
    exif = source.getexif()
    exif[271] = 'OnePlus'
    exif[272] = 'OnePlus 13'
    exif[34665] = {
        33434: 0.02,
        33437: 2.6,
        34855: 3200,
        37386: 13.85,
        36867: '2026:07:11 21:23:27',
    }
    exif[34853] = {
        1: 'N',
        2: (22.0, 35.0, 11.85),
        3: 'E',
        4: (113.0, 57.0, 54.65),
    }
    buf = io.BytesIO()
    source.save(buf, 'JPEG', exif=exif.tobytes())
    buf.seek(0)

    with Image.open(buf) as img:
        result = _extract_exif(img)

    assert result['camera'] == 'OnePlus'
    assert result['model'] == 'OnePlus 13'
    assert result['shutter'] == '1/50s'
    assert result['aperture'] == 'f/2.6'
    assert result['iso'] == '3200'
    assert result['focal'] == '13mm'
    assert result['date'] == '2026-07-11 21:23'
    assert result['gps'] == {'lat': 22.586625, 'lng': 113.965181}


# ── _cache_bust_assets ──

def test_cache_bust_assets(tmp_path, monkeypatch):
    """Verify cache bust replaces ?v=old → ?v=new in CSS/JS links."""
    import time
    from backend.ssg import _cache_bust_assets
    from backend.data import BASE_DIR

    # Create temp copies of all HTML, CSS, JS files
    configs = [
        ('index.html', (
            'assets/css/index-foundation.css',
            'assets/css/index-work.css',
            'assets/css/index-photos.css',
            'assets/css/index-content.css',
            'assets/css/index-essays.css',
            'assets/css/index-polish.css',
        ), (
            'assets/js/theme.js',
            'assets/js/index-core.js',
            'assets/js/index-essays.js',
            'assets/js/index-photo-gallery.js',
            'assets/js/index-photo-map.js',
            'assets/js/index-content.js',
            'assets/js/index-lightbox.js',
            'assets/js/index.js',
        )),
        ('admin.html', (
            'assets/css/admin-foundation.css',
            'assets/css/admin-photo.css',
            'assets/css/admin-git.css',
            'assets/css/admin-essay.css',
        ), (
            'assets/js/theme.js',
            'assets/js/admin.js',
            'assets/js/admin-work.js',
            'assets/js/admin-social.js',
            'assets/js/admin-music.js',
            'assets/js/admin-stack.js',
            'assets/js/admin-git.js',
            'assets/js/admin-essay-tags.js',
            'assets/js/admin-essay-security.js',
            'assets/js/admin-about.js',
            'assets/js/admin-essay-editor.js',
            'assets/js/admin-photo-editor.js',
            'assets/js/admin-photo-stories.js',
        )),
    ]
    for html_fn, css_fns, js_fns in configs:
        for css_fn in css_fns:
            (tmp_path / css_fn).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / css_fn).write_text('/* css */')
        for js_fn in js_fns:
            (tmp_path / js_fn).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / js_fn).write_text('/* js */')
        css_tags = '\n'.join(f'<link href="{css_fn}?v=999" rel="stylesheet">' for css_fn in css_fns)
        js_tags = '\n'.join(f'<script src="{js_fn}?v=999"></script>' for js_fn in js_fns)
        (tmp_path / html_fn).write_text(f'{css_tags}\n{js_tags}')

    now = int(time.time())
    monkeypatch.setattr('backend.ssg.BASE_DIR', str(tmp_path))
    monkeypatch.setattr('os.path.getmtime', lambda p: now)
    monkeypatch.setattr('os.path.exists', lambda p: True)

    _cache_bust_assets()

    for html_fn, css_fns, js_fns in configs:
        result = (tmp_path / html_fn).read_text()
        for css_fn in css_fns:
            assert f'{css_fn}?v={now}' in result
        for js_fn in js_fns:
            assert f'{js_fn}?v={now}' in result
            assert '?v=999' not in result


# ── Encryption roundtrip ──

def test_encrypt_decrypt_roundtrip():
    plaintext = "Hello, this is a test essay content with Unicode: 你好世界!"
    password = "test-password-123"
    encrypted = _encrypt_content(plaintext, password)
    # Encrypted should be a base64 string, not plaintext
    assert plaintext not in encrypted
    decrypted = _decrypt_content(encrypted, password)
    assert decrypted == plaintext

def test_encrypt_different_salts():
    """Same plaintext + password should produce different ciphertext each time."""
    encrypted1 = _encrypt_content("test", "pw")
    encrypted2 = _encrypt_content("test", "pw")
    assert encrypted1 != encrypted2  # different salts

def test_decrypt_wrong_password():
    encrypted = _encrypt_content("secret", "correct")
    with pytest.raises(ValueError, match='Wrong password'):
        _decrypt_content(encrypted, "wrong")


# ── Public essays generation ──

def test_generate_public_essays_lists_protected_essays_without_passwords(tmp_path, monkeypatch):
    """Protected essays remain discoverable while their passwords stay private."""
    test_essays = [
        {'slug': 'a', 'title': 'Visible', 'password': 'secret123'},
        {'slug': 'b', 'title': 'Protected', 'password': 'top'},
        {'slug': 'c', 'title': 'Also Visible'},
    ]
    monkeypatch.setattr('backend.ssg.load_json', lambda f: test_essays)
    monkeypatch.setattr('backend.ssg.get_essay_password', lambda slug: 'secret' if slug in ('a', 'b') else '')
    public_path = tmp_path / 'essays_public.json'
    monkeypatch.setattr('backend.ssg.DATA_DIR', str(tmp_path))

    _generate_public_essays()

    with open(public_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # New format: {_tags: [...], essays: [...]}
    visible = data['essays']
    assert len(visible) == 3
    slugs = [e['slug'] for e in visible]
    assert slugs == ['a', 'b', 'c']
    assert [e['password_protected'] for e in visible] == [True, True, False]
    # Password must be stripped
    for e in visible:
        assert 'password' not in e


def test_render_markdown_blocks_javascript_links():
    html = render_markdown('[unsafe](javascript:alert(1))')

    assert 'javascript:' not in html.lower()


# ── _sync_essay_html password / no-password output ──

def test_sync_essay_html_without_password(tmp_path, monkeypatch):
    """No password → generated HTML has normal body without gate."""
    md_dir = tmp_path / 'md'
    essays_dir = tmp_path / 'essays'
    md_dir.mkdir()
    essays_dir.mkdir()
    monkeypatch.setattr('backend.ssg.MD_DIR', str(md_dir))
    monkeypatch.setattr('backend.ssg.ESSAYS_DIR', str(essays_dir))
    monkeypatch.setattr('backend.ssg.IMAGES_DIR', str(tmp_path / 'images'))
    monkeypatch.setattr('backend.ssg.DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr('backend.ssg.BASE_DIR', str(tmp_path))

    # Create essays.json with one essay
    (tmp_path / 'data').mkdir()
    essay = {'slug': 'test', 'title': 'Test', 'date': '2026-01-01',
             'tag': '', 'epigraph': '', 'excerpt': '', 'readTime': 1}
    with open(tmp_path / 'data' / 'essays.json', 'w') as f:
        json.dump([essay], f)

    # Save markdown
    with open(md_dir / 'test.md', 'w') as f:
        f.write("\n".join([
            'Hello World',
            '',
            '~~deleted~~',
            '',
            '- [ ] todo',
            '- [x] done',
            '',
            '```c',
            '#include <stdio.h>',
            '',
            'int main(void) { return 0; }',
            '```',
        ]))

    _sync_essay_html(essay)

    html = (essays_dir / 'test.html').read_text()
    assert 'id="essay-gate"' not in html
    assert 'essay-body' in html
    assert 'Hello World' in html
    assert '<del>deleted</del>' in html
    assert 'type="checkbox"' in html
    assert 'checked' in html
    assert 'class="language-c"' in html
    assert '#include &lt;stdio.h&gt;' in html
    assert '#include &amp;lt;stdio.h&amp;gt;' not in html
    assert 'highlight.js' in html
    assert 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js' in html
    assert '<script src="/assets/js/essay-code.js?v=' in html
    essay_code = (Path(__file__).resolve().parents[1] / 'assets' / 'js' / 'essay-code.js').read_text(encoding='utf-8')
    assert 'highlightCodeBlocks' in essay_code
    assert 'fallbackHighlightCodeBlock' in essay_code
    assert 'code-language' in essay_code
    assert 'COPY' in essay_code
    assert '_encryptedBody' not in html


def test_sync_essay_html_csp_allows_giscus(tmp_path, monkeypatch):
    """Giscus comments need both script and iframe permission in the essay CSP."""
    md_dir = tmp_path / 'md'
    essays_dir = tmp_path / 'essays'
    md_dir.mkdir()
    essays_dir.mkdir()
    monkeypatch.setattr('backend.ssg.MD_DIR', str(md_dir))
    monkeypatch.setattr('backend.ssg.ESSAYS_DIR', str(essays_dir))
    monkeypatch.setattr('backend.ssg.IMAGES_DIR', str(tmp_path / 'images'))
    monkeypatch.setattr('backend.ssg.DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr('backend.ssg.BASE_DIR', str(tmp_path))

    (tmp_path / 'data').mkdir()
    essay = {'slug': 'test', 'title': 'Test', 'date': '2026-01-01',
             'tag': '', 'epigraph': '', 'excerpt': '', 'readTime': 1}
    with open(tmp_path / 'data' / 'essays.json', 'w') as f:
        json.dump([essay], f)
    with open(md_dir / 'test.md', 'w') as f:
        f.write('Hello World')

    _sync_essay_html(essay)

    html = (essays_dir / 'test.html').read_text(encoding='utf-8')
    csp = html.split('Content-Security-Policy" content="', 1)[1].split('"', 1)[0]
    assert 'script-src' in csp
    assert 'https://giscus.app' in csp
    assert 'style-src-elem' in csp
    assert 'connect-src \'self\' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://giscus.app' in csp
    assert 'https://cdnjs.cloudflare.com' in csp
    assert 'frame-src https://giscus.app' in csp


def test_sync_essay_html_giscus_loads_in_preview_and_full_width(tmp_path, monkeypatch):
    """Local preview should load Giscus, and the iframe should fill the essay column."""
    md_dir = tmp_path / 'md'
    essays_dir = tmp_path / 'essays'
    md_dir.mkdir()
    essays_dir.mkdir()
    monkeypatch.setattr('backend.ssg.MD_DIR', str(md_dir))
    monkeypatch.setattr('backend.ssg.ESSAYS_DIR', str(essays_dir))
    monkeypatch.setattr('backend.ssg.IMAGES_DIR', str(tmp_path / 'images'))
    monkeypatch.setattr('backend.ssg.DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr('backend.ssg.BASE_DIR', str(tmp_path))

    (tmp_path / 'data').mkdir()
    essay = {'slug': 'test', 'title': 'Test', 'date': '2026-01-01',
             'tag': '', 'epigraph': '', 'excerpt': '', 'readTime': 1}
    with open(tmp_path / 'data' / 'essays.json', 'w') as f:
        json.dump([essay], f)
    with open(md_dir / 'test.md', 'w') as f:
        f.write('Hello World')

    _sync_essay_html(essay)

    html = (essays_dir / 'test.html').read_text(encoding='utf-8')
    assert "location.hostname !== 'localhost'" not in html
    assert "location.hostname !== '127.0.0.1'" not in html
    assert '<div class="comments-section" id="giscus-container"></div>' in html
    assert '<link rel="stylesheet" href="/assets/css/essay.css?v=' in html
    essay_css = (Path(__file__).resolve().parents[1] / 'assets' / 'css' / 'essay.css').read_text(encoding='utf-8')
    assert '.comments-section .giscus-frame' in essay_css
    assert 'width: 100% !important' in essay_css


def test_theme_sync_covers_system_tabs_and_giscus_initial_state():
    """Theme changes should propagate beyond the page that initiated them."""
    theme_js = (Path(__file__).resolve().parents[1] / 'assets' / 'js' / 'theme.js').read_text(encoding='utf-8')
    essay_template = (Path(__file__).resolve().parents[1] / 'templates' / 'essay.html').read_text(encoding='utf-8')
    giscus_js = (Path(__file__).resolve().parents[1] / 'assets' / 'js' / 'essay-giscus.js').read_text(encoding='utf-8')
    comments_js = (Path(__file__).resolve().parents[1] / 'assets' / 'js' / 'essay-comments.js').read_text(encoding='utf-8')
    archive_template = (Path(__file__).resolve().parents[1] / 'templates' / 'archive.html').read_text(encoding='utf-8')
    map_template = (Path(__file__).resolve().parents[1] / 'templates' / 'map.html').read_text(encoding='utf-8')

    assert "window.addEventListener('storage'" in theme_js
    assert "event.key !== 'theme'" in theme_js
    assert "matchMedia('(prefers-color-scheme: dark)')" in theme_js
    assert 'src="/assets/js/essay-giscus.js?v={{ build_ts }}"' in essay_template
    assert "window.addEventListener('themechange', syncGiscusTheme)" in giscus_js
    assert 'src="/assets/js/essay-comments.js?v={{ build_ts }}"' in essay_template
    assert "gs.setAttribute('data-theme', document.documentElement.classList.contains('dark')" in comments_js
    assert 'src="/assets/js/theme.js?v={{ build_ts }}"' in essay_template
    assert 'src="/assets/js/theme.js?v={{ build_ts }}"' in archive_template
    assert 'src="/assets/js/theme.js?v={{ build_ts }}"' in map_template


def test_admin_dashboard_stats_ui_is_registered():
    root = Path(__file__).resolve().parents[1]
    admin_html = (root / 'admin.html').read_text(encoding='utf-8')
    admin_js = (root / 'assets' / 'js' / 'admin.js').read_text(encoding='utf-8')
    dashboard_js = (root / 'assets' / 'js' / 'admin-dashboard.js').read_text(encoding='utf-8')

    assert 'data-tab="dashboard"' in admin_html
    assert 'id="tab-dashboard"' in admin_html
    assert 'id="dashboard-counts"' in admin_html
    assert 'id="dashboard-primary-tags"' in admin_html
    assert 'id="dashboard-secondary-tags"' in admin_html
    assert 'id="dashboard-recent"' in admin_html
    assert 'assets/js/admin-dashboard.js' in admin_html
    assert "if (name === 'dashboard') loadDashboard();" in admin_js
    assert "/api/dashboard-stats" in dashboard_js
    assert 'dashboard-error' in dashboard_js
    assert 'data.counts' in dashboard_js
    assert 'tags.primary' in dashboard_js
    assert 'tags.secondary' in dashboard_js
    assert 'data.recent' in dashboard_js


def test_theme_toggle_cycles_between_system_light_and_dark_preferences():
    """The shared theme module must offer an explicit route back to system mode."""
    root = Path(__file__).resolve().parents[1]
    theme_js = (root / 'assets' / 'js' / 'theme.js').read_text(encoding='utf-8')
    theme_heads = [
        root / 'index.html',
        root / 'admin.html',
        root / 'templates' / 'essay.html',
        root / 'templates' / 'archive.html',
        root / 'templates' / 'map.html',
    ]

    assert "saved === 'system'" in theme_js
    assert "? 'light' : 'system'" in theme_js
    assert "_notifyThemeChange(nextMode, next)" in theme_js
    for path in theme_heads:
        assert "_saved === 'system' || !_saved" in path.read_text(encoding='utf-8')


def test_mobile_essay_rows_keep_metadata_on_one_centered_line():
    """Mobile essay rows should not leave an orphaned 'read' label below the date."""
    index_js = (Path(__file__).resolve().parents[1] / 'assets' / 'js' / 'index-essays.js').read_text(encoding='utf-8')
    index_css = (Path(__file__).resolve().parents[1] / 'assets' / 'css' / 'index-polish.css').read_text(encoding='utf-8')

    assert " + ' min</span>'" in index_js
    assert " + ' min read</span>'" not in index_js
    assert '.essay-row    { padding: 18px 0; align-items: center; }' in index_css
    assert '.essay-right  { flex-direction: row; align-items: center;' in index_css


def test_sync_essay_html_with_password(tmp_path, monkeypatch):
    """Password set → generated HTML has gate with encrypted body."""
    md_dir = tmp_path / 'md'
    essays_dir = tmp_path / 'essays'
    md_dir.mkdir()
    essays_dir.mkdir()
    monkeypatch.setattr('backend.ssg.MD_DIR', str(md_dir))
    monkeypatch.setattr('backend.ssg.ESSAYS_DIR', str(essays_dir))
    monkeypatch.setattr('backend.ssg.IMAGES_DIR', str(tmp_path / 'images'))
    monkeypatch.setattr('backend.ssg.DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr('backend.ssg.BASE_DIR', str(tmp_path))

    (tmp_path / 'data').mkdir()
    monkeypatch.setattr('backend.ssg.get_essay_password', lambda slug: 'secret' if slug == 'test' else '')
    essay = {'slug': 'test', 'title': 'Test', 'date': '2026-01-01',
             'tag': '', 'epigraph': '', 'excerpt': '', 'readTime': 1}
    with open(tmp_path / 'data' / 'essays.json', 'w') as f:
        json.dump([essay], f)

    with open(md_dir / 'test.md', 'w') as f:
        f.write('Hello World')

    _sync_essay_html(essay)

    html = (essays_dir / 'test.html').read_text()
    assert 'id="essay-gate"' in html
    assert '_encryptedBody' in html
    assert '此内容已隐藏' in html
    # Plaintext body must NOT be in the HTML
    assert 'Hello World' not in html
    # MD file must be encrypted
    md_content = (md_dir / 'test.md').read_text()
    assert 'Hello' not in md_content  # encrypted


def test_password_roundtrip(tmp_path, monkeypatch):
    """Set password → build → clear password → back to normal."""
    md_dir = tmp_path / 'md'
    essays_dir = tmp_path / 'essays'
    md_dir.mkdir()
    essays_dir.mkdir()
    monkeypatch.setattr('backend.ssg.MD_DIR', str(md_dir))
    monkeypatch.setattr('backend.ssg.ESSAYS_DIR', str(essays_dir))
    monkeypatch.setattr('backend.ssg.IMAGES_DIR', str(tmp_path / 'images'))
    monkeypatch.setattr('backend.ssg.DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr('backend.ssg.BASE_DIR', str(tmp_path))

    (tmp_path / 'data').mkdir()

    # Password stored in local gitignored store, not in essays.json
    _passwords = {'test': 'secret'}
    monkeypatch.setattr('backend.ssg.get_essay_password', lambda slug: _passwords.get(slug, ''))

    # Phase 1: set password, build
    essay = {'slug': 'test', 'title': 'Test', 'date': '2026-01-01',
             'tag': '', 'epigraph': '', 'excerpt': '', 'readTime': 1}
    with open(tmp_path / 'data' / 'essays.json', 'w') as f:
        json.dump([essay], f)
    with open(md_dir / 'test.md', 'w') as f:
        f.write('Hello World')

    _sync_essay_html(essay)
    html1 = (essays_dir / 'test.html').read_text()
    assert 'id="essay-gate"' in html1
    assert 'Hello World' not in html1

    # Phase 2: clear password, rebuild (decrypt .md first — like set_essay_password does)
    _passwords.pop('test')
    with open(tmp_path / 'data' / 'essays.json', 'w') as f:
        json.dump([essay], f)
    # Decrypt .md before rebuilding (simulates what set_essay_password does)
    encrypted_md = (md_dir / 'test.md').read_text()
    (md_dir / 'test.md').write_text(_decrypt_content(encrypted_md, 'secret'))

    _sync_essay_html(essay)
    html2 = (essays_dir / 'test.html').read_text()
    assert 'id="essay-gate"' not in html2
    assert 'Hello World' in html2

    # MD must be decrypted
    md_content = (md_dir / 'test.md').read_text()
    assert 'Hello World' in md_content


# ── _is_encrypted_v3 ──

def test_is_encrypted_v3_valid():
    from backend.ssg import _is_encrypted_v3, _encrypt_content
    encrypted = _encrypt_content("test content", "pw")
    assert _is_encrypted_v3(encrypted) is True

def test_is_encrypted_v3_plaintext():
    from backend.ssg import _is_encrypted_v3
    assert _is_encrypted_v3("Hello World") is False
    assert _is_encrypted_v3("# Markdown title\n\ncontent") is False

def test_is_encrypted_v3_empty():
    from backend.ssg import _is_encrypted_v3
    assert not _is_encrypted_v3("")


# ── SSG pass-through for encrypted essays ──

def test_sync_essay_html_encrypted_pass_through(tmp_path, monkeypatch):
    """Encrypted .md → HTML has password gate with encrypted_body and encrypted_is_md."""
    md_dir = tmp_path / 'md'
    essays_dir = tmp_path / 'essays'
    md_dir.mkdir()
    essays_dir.mkdir()
    monkeypatch.setattr('backend.ssg.MD_DIR', str(md_dir))
    monkeypatch.setattr('backend.ssg.ESSAYS_DIR', str(essays_dir))
    monkeypatch.setattr('backend.ssg.IMAGES_DIR', str(tmp_path / 'images'))
    monkeypatch.setattr('backend.ssg.DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr('backend.ssg.BASE_DIR', str(tmp_path))

    (tmp_path / 'data').mkdir()
    (tmp_path / 'templates').mkdir()
    essay = {'slug': 'test', 'title': 'Test', 'date': '2026-01-01',
             'tag': '', 'epigraph': '', 'excerpt': '', 'readTime': 1}
    with open(tmp_path / 'data' / 'essays.json', 'w') as f:
        json.dump([essay], f)

    # Pre-encrypt the .md with a password (simulating already-encrypted at rest)
    encrypted_md = _encrypt_content("# Secret\n\nTop secret content.", "pw")
    with open(md_dir / 'test.md', 'w') as f:
        f.write(encrypted_md)

    # Build without get_essay_password returning anything (CI mode)
    monkeypatch.setattr('backend.ssg.get_essay_password', lambda slug: '')
    _sync_essay_html(essay)

    html = (essays_dir / 'test.html').read_text()
    assert 'id="essay-gate"' in html
    assert '_encryptedBody' in html
    assert '_encryptedIsMd = true' in html
    assert '此内容已隐藏' in html
    assert 'Top secret' not in html  # plaintext must not leak

def test_sync_essay_html_encrypted_no_password_ci(tmp_path, monkeypatch):
    """No password available (CI) but .md is encrypted → still gets password gate."""
    md_dir = tmp_path / 'md'
    essays_dir = tmp_path / 'essays'
    md_dir.mkdir()
    essays_dir.mkdir()
    monkeypatch.setattr('backend.ssg.MD_DIR', str(md_dir))
    monkeypatch.setattr('backend.ssg.ESSAYS_DIR', str(essays_dir))
    monkeypatch.setattr('backend.ssg.IMAGES_DIR', str(tmp_path / 'images'))
    monkeypatch.setattr('backend.ssg.DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr('backend.ssg.BASE_DIR', str(tmp_path))

    (tmp_path / 'data').mkdir()
    (tmp_path / 'templates').mkdir()
    essay = {'slug': 'test', 'title': 'Test', 'date': '2026-01-01',
             'tag': '', 'epigraph': '', 'excerpt': '', 'readTime': 1}
    with open(tmp_path / 'data' / 'essays.json', 'w') as f:
        json.dump([essay], f)

    encrypted_md = _encrypt_content("# CI test", "pw")
    with open(md_dir / 'test.md', 'w') as f:
        f.write(encrypted_md)

    monkeypatch.setattr('backend.ssg.get_essay_password', lambda slug: '')
    _sync_essay_html(essay)

    html = (essays_dir / 'test.html').read_text()
    assert 'id="essay-gate"' in html         # gate must appear
    assert '_encryptedIsMd' in html          # flag for client-side MD rendering
    assert 'CI test' not in html             # plaintext must not appear


# ── get_image_ext ──

def test_get_image_ext_valid():
    from backend.data import get_image_ext
    assert get_image_ext('photo.jpg') == 'jpg'
    assert get_image_ext('photo.JPEG') == 'jpeg'
    assert get_image_ext('photo.PNG') == 'png'
    assert get_image_ext('photo.gif') == 'gif'
    assert get_image_ext('photo.webp') == 'webp'

def test_get_image_ext_invalid():
    from backend.data import get_image_ext
    assert get_image_ext('file.exe') is None
    assert get_image_ext('file') is None
    assert get_image_ext('file.bmp') is None
    assert get_image_ext('') is None


# ── _strip_enrich ──

def test_strip_enrich_strips_password():
    from backend.ssg import _strip_enrich
    essays = [{'slug': 'a', 'title': 'A', 'date': '2026-01-01', 'password': 'secret'}]
    result = _strip_enrich(essays, 'pub_date', '%Y-%m-%d')
    assert 'password' not in result[0]

def test_strip_enrich_rss_format():
    from backend.ssg import _strip_enrich
    essays = [{'slug': 'a', 'title': 'A', 'date': '2026-06-15 14:30', 'password': 'x'}]
    result = _strip_enrich(essays, 'pub_date', '%a, %d %b %Y %H:%M:%S +0800', 20)
    assert result[0]['pub_date'] != ''
    assert 'Jun' in result[0]['pub_date']

def test_strip_enrich_sitemap_format():
    from backend.ssg import _strip_enrich
    essays = [{'slug': 'a', 'title': 'A', 'date': '2026-06-15', 'password': 'x'}]
    result = _strip_enrich(essays, 'lastmod', '%Y-%m-%d')
    assert result[0]['lastmod'] == '2026-06-15'

def test_strip_enrich_invalid_date():
    from backend.ssg import _strip_enrich
    essays = [{'slug': 'a', 'title': 'A', 'date': 'not-a-date'}]
    result = _strip_enrich(essays, 'pub_date', '%Y-%m-%d')
    assert result[0]['pub_date'] == ''

def test_strip_enrich_limit():
    from backend.ssg import _strip_enrich
    essays = [
        {'slug': 'a', 'date': '2026-01-01'},
        {'slug': 'b', 'date': '2026-01-02'},
        {'slug': 'c', 'date': '2026-01-03'},
    ]
    result = _strip_enrich(essays, 'pub_date', '%Y-%m-%d', 2)
    assert len(result) == 2


# ── Encryption full-chain (HMAC v2 / Fernet) ──

def test_encrypt_decrypt_long_content():
    """Multi-paragraph essay with special chars should roundtrip correctly."""
    plaintext = """# 长文测试

这是第一段内容，包含中文标点：，。！？「」『』【】、…—～

```python
def hello():
    print("Hello, World!")
```

> 引用文字：这是一段引用内容。**加粗** 和 *斜体* 混合。

第二段，带数学公式：$E = mc^2$

最后一段。✨🎉 Unicode emoji test. 日本語テスト。한국어 테스트。
"""
    password = "my-secret-password-长密码🔑"
    encrypted = _encrypt_content(plaintext, password)
    assert plaintext not in encrypted
    assert len(encrypted) > len(plaintext)  # base64 overhead
    decrypted = _decrypt_content(encrypted, password)
    assert decrypted == plaintext


def test_encrypt_decrypt_empty_password():
    """Empty password should still work (PBKDF2 handles empty input)."""
    encrypted = _encrypt_content("some content", "")
    assert encrypted
    decrypted = _decrypt_content(encrypted, "")
    assert decrypted == "some content"


def test_encrypt_decrypt_unicode_only():
    """纯中文 + 日文 + 韩文内容，无双字节英文。"""
    plaintext = "你好世界！这是一篇纯中文测试文章。人生若只如初见，何事秋风悲画扇。"
    password = "中文密码测试"
    encrypted = _encrypt_content(plaintext, password)
    decrypted = _decrypt_content(encrypted, password)
    assert decrypted == plaintext


# ── HMAC verification failure paths ──

def test_decrypt_tampered_ciphertext():
    """Valid base64 but one byte flipped → HMAC mismatch → ValueError."""
    import base64 as b64
    encrypted = _encrypt_content("secret content", "password123")
    raw = bytearray(b64.b64decode(encrypted))
    # Flip a bit in the Fernet token portion (after version + salt = 17 bytes)
    raw[-10] ^= 0x01  # tamper with last portion (inside HMAC region)
    tampered = b64.b64encode(bytes(raw)).decode('ascii')
    with pytest.raises(ValueError):
        _decrypt_content(tampered, "password123")


def test_decrypt_truncated_ciphertext():
    """Truncated base64 data → should raise ValueError."""
    encrypted = _encrypt_content("secret", "pw")
    # Take only first 20 chars of base64 (too short for valid format)
    truncated = encrypted[:20]
    with pytest.raises((ValueError, IndexError)):
        _decrypt_content(truncated, "pw")


def test_decrypt_wrong_version_byte():
    """Content where first decoded byte is not 2 → legacy format error."""
    import base64 as b64
    # Construct: version=0x01 + random 16 salt + random data (min 1 byte)
    fake = bytes([1]) + os.urandom(16) + os.urandom(32)
    encoded = b64.b64encode(fake).decode('ascii')
    with pytest.raises(ValueError, match=r'legacy'):
        _decrypt_content(encoded, "pw")


def test_decrypt_garbage_base64():
    """Random base64 string that decodes to garbage (< 18 bytes) → format error."""
    import base64 as b64
    # "AAAA" decodes to 3 null bytes
    with pytest.raises(ValueError, match=r'legacy'):
        _decrypt_content("AAAA", "pw")


# ── _sync_essay_html: hidden = encrypted 联动 ──

def test_sync_essay_encrypted_md_stays_encrypted(tmp_path, monkeypatch):
    """Encrypted .md already exists, no password available → SSG passes through as-is."""
    md_dir = tmp_path / 'md'
    essays_dir = tmp_path / 'essays'
    md_dir.mkdir()
    essays_dir.mkdir()
    monkeypatch.setattr('backend.ssg.MD_DIR', str(md_dir))
    monkeypatch.setattr('backend.ssg.ESSAYS_DIR', str(essays_dir))
    monkeypatch.setattr('backend.ssg.IMAGES_DIR', str(tmp_path / 'images'))
    monkeypatch.setattr('backend.ssg.DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr('backend.ssg.BASE_DIR', str(tmp_path))

    (tmp_path / 'data').mkdir()
    (tmp_path / 'templates').mkdir()
    essay = {'slug': 'enc-stays', 'title': 'Enc Stays', 'date': '2026-01-01',
             'tag': '', 'epigraph': '', 'excerpt': '', 'readTime': 1}
    with open(tmp_path / 'data' / 'essays.json', 'w') as f:
        json.dump([essay], f)

    original = _encrypt_content("# Original secret content", "mypw")
    with open(md_dir / 'enc-stays.md', 'w') as f:
        f.write(original)

    monkeypatch.setattr('backend.ssg.get_essay_password', lambda slug: '')
    _sync_essay_html(essay)

    # .md must be unchanged (pass-through, no server-side re-encryption)
    md_after = (md_dir / 'enc-stays.md').read_text()
    assert md_after == original

    # HTML must have gate
    html = (essays_dir / 'enc-stays.html').read_text()
    assert 'id="essay-gate"' in html
    assert '_encryptedIsMd = true' in html


def test_sync_essay_first_time_encryption(tmp_path, monkeypatch):
    """Plaintext .md + password → first-time encryption on the fly, gate in HTML."""
    md_dir = tmp_path / 'md'
    essays_dir = tmp_path / 'essays'
    md_dir.mkdir()
    essays_dir.mkdir()
    monkeypatch.setattr('backend.ssg.MD_DIR', str(md_dir))
    monkeypatch.setattr('backend.ssg.ESSAYS_DIR', str(essays_dir))
    monkeypatch.setattr('backend.ssg.IMAGES_DIR', str(tmp_path / 'images'))
    monkeypatch.setattr('backend.ssg.DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setattr('backend.ssg.BASE_DIR', str(tmp_path))

    (tmp_path / 'data').mkdir()
    (tmp_path / 'templates').mkdir()
    essay = {'slug': 'first-time', 'title': 'First Time', 'date': '2026-01-01',
             'tag': '', 'epigraph': '', 'excerpt': '', 'readTime': 1}
    with open(tmp_path / 'data' / 'essays.json', 'w') as f:
        json.dump([essay], f)

    # Plaintext .md exists
    with open(md_dir / 'first-time.md', 'w') as f:
        f.write('Fresh content here.')

    # Password is set
    monkeypatch.setattr('backend.ssg.get_essay_password', lambda slug: 'newpw')

    _sync_essay_html(essay)

    # .md must now be encrypted
    md_content = (md_dir / 'first-time.md').read_text()
    assert _is_encrypted_v3(md_content)
    assert 'Fresh' not in md_content

    # HTML must have gate
    html = (essays_dir / 'first-time.html').read_text()
    assert 'id="essay-gate"' in html
