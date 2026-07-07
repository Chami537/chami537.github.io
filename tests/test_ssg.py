"""Tests for SSG functions and EXIF helpers."""
import os
import json
import pytest
from PIL import Image
from backend.ssg import (
    _extract_exif, _extract_gps, _calc_read_time, _parse_date,
    _parse_tags, _find_adjacent_siblings, _extract_first_image,
    _cache_bust_assets, _encrypt_content, _decrypt_content,
    _generate_public_essays, _sync_essay_html,
    ESSAYS_DIR, MD_DIR,
)
from backend.data import load_json


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


# ── _cache_bust_assets ──

def test_cache_bust_assets(tmp_path, monkeypatch):
    """Verify cache bust replaces ?v=old → ?v=new in CSS/JS links."""
    import time
    from backend.ssg import _cache_bust_assets
    from backend.data import BASE_DIR

    # Create temp copies of all HTML, CSS, JS files
    configs = [('index.html', 'index.css', ('index.js',)),
               ('admin.html', 'admin.css', ('admin.js', 'admin-content.js', 'admin-essays.js', 'admin-photos.js'))]
    for html_fn, css_fn, js_fns in configs:
        (tmp_path / css_fn).write_text('/* css */')
        for js_fn in js_fns:
            (tmp_path / js_fn).write_text('/* js */')
        js_tags = '\n'.join(f'<script src="{js_fn}?v=999"></script>' for js_fn in js_fns)
        (tmp_path / html_fn).write_text(f'<link href="{css_fn}?v=999" rel="stylesheet">\n{js_tags}')

    now = int(time.time())
    monkeypatch.setattr('backend.ssg.BASE_DIR', str(tmp_path))
    monkeypatch.setattr('os.path.getmtime', lambda p: now)
    monkeypatch.setattr('os.path.exists', lambda p: True)

    _cache_bust_assets()

    for html_fn, css_fn, js_fns in configs:
        result = (tmp_path / html_fn).read_text()
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

def test_generate_public_essays_strips_passwords(tmp_path, monkeypatch):
    """Verify _generate_public_essays includes all essays but strips password field."""
    test_essays = [
        {'slug': 'a', 'title': 'Visible', 'password': 'secret123'},
        {'slug': 'b', 'title': 'Protected', 'password': 'top'},
        {'slug': 'c', 'title': 'Also Visible'},
    ]
    monkeypatch.setattr('backend.ssg.load_json', lambda f: test_essays)
    public_path = tmp_path / 'essays_public.json'
    monkeypatch.setattr('backend.ssg.DATA_DIR', str(tmp_path))

    _generate_public_essays()

    with open(public_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # New format: {_tags: [...], essays: [...]}
    visible = data['essays']
    assert len(visible) == 3  # all visible
    slugs = [e['slug'] for e in visible]
    assert 'a' in slugs and 'b' in slugs and 'c' in slugs
    # Password must be stripped
    for e in visible:
        assert 'password' not in e


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
        f.write('Hello World')

    _sync_essay_html(essay)

    html = (essays_dir / 'test.html').read_text()
    assert 'id="essay-gate"' not in html
    assert 'essay-body' in html
    assert 'Hello World' in html
    assert '_encryptedBody' not in html


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
