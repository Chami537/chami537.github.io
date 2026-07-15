"""SSG generators and essay helpers for the Chami CMS."""

import html as html_mod
import os
import json
import re
from datetime import datetime
from markupsafe import Markup
from backend.markdown_utils import render_markdown

# ── Encryption helpers (cryptography Fernet: AES-128-CBC + HMAC-SHA256) ──

from backend.essay_crypto import (
    _derive_fernet, decrypt_content as _decrypt_content,
    encrypt_content as _encrypt_content,
)

from backend.data import get_essay_password, BASE_DIR, DATA_DIR, ESSAYS_DIR, MD_DIR, IMAGES_DIR, STORE
from backend.exif_utils import extract_exif, extract_gps, without_camera_model
from backend.photo_metadata import set_gps
from backend.github_sync import fetch_stars
from backend.essay_navigation import parse_tags as _parse_tags, find_adjacent_siblings as _find_adjacent_siblings, build_nav as _build_nav
from backend.asset_cache import cache_bust_assets
from backend.essay_feed_data import strip_enrich
from backend.essay_repository import EssayRepository
from backend.essay_service import EssayService
from backend.essay_renderer import render_essay_html, write_essay_html
from backend.repositories import PHOTO_REPOSITORY, repository_for
from jinja2 import Environment, FileSystemLoader

_env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, 'templates')))
ESSAY_REPOSITORY = EssayRepository(STORE)
ESSAY_SERVICE = EssayService(ESSAY_REPOSITORY)


def load_json(name):
    """Compatibility seam for SSG callers; reads through the repository layer."""
    return repository_for(name).list()

# ═══════════════════════════════════════════

def _cache_bust_assets():
    return cache_bust_assets(BASE_DIR)


def _calc_read_time(text):
    """Estimate reading time from text. Chinese ~300 chars/min, English ~200 words/min. Minimum 1 min."""
    if not text:
        return 1
    cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf')
    words = len(re.findall(r'[a-zA-Z]+', text))
    # Chinese ~300 cpm, English ~200 wpm, convert to a unified "char equivalent" at 300/min
    total = cjk + words * 1.5  # English words count as ~1.5 Chinese chars worth of reading time
    minutes = max(1, round(total / 300))
    return minutes


def _parse_date(date_str, include_time=False):
    """'2026-06' or '2026-06-25 14:30' → 'Jun 2026' or 'Jun 25, 2026'
    If include_time=True, '2026-06-25 14:30' → '14:30, Jun 25, 2026'"""
    if not isinstance(date_str, str) or not date_str.strip():
        return date_str if isinstance(date_str, str) else ''
    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m'):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            date_part = dt.strftime('%b %d, %Y') if fmt.endswith('%H:%M') else dt.strftime('%b %Y')
            if include_time and fmt.endswith('%H:%M'):
                return f"{dt.hour:02d}:{dt.minute:02d}, {date_part}"
            return date_part
        except ValueError:
            continue
    return date_str


def _extract_first_image(md_text):
    """Extract first image URL from Markdown for Open Graph og:image."""
    if not md_text:
        return 'https://chami537.github.io/images/avatar.jpg'
    m = re.search(r'!\[.*?\]\((.*?)\)', md_text)
    if m:
        url = m.group(1)
        if url.startswith('http'):
            return url
        return 'https://chami537.github.io/' + url.lstrip('/')
    return 'https://chami537.github.io/images/avatar.jpg'


def _strip_enrich(essays, date_key, date_fmt, limit=None):
    return strip_enrich(essays, date_key, date_fmt, limit)


def _generate_rss():
    """Generate rss.xml from essays.json (Jinja2 template)."""
    essays = ESSAY_REPOSITORY.list()
    enriched = _strip_enrich(essays, 'pub_date', '%a, %d %b %Y %H:%M:%S +0800', 20)
    last_build = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0800')
    html = _env.get_template('rss.xml').render(essays=enriched, last_build=last_build)
    with open(os.path.join(BASE_DIR, 'rss.xml'), 'w', encoding='utf-8') as f:
        f.write(html)


def _generate_sitemap():
    """Generate sitemap.xml (Jinja2 template)."""
    essays = ESSAY_REPOSITORY.list()
    enriched = _strip_enrich(essays, 'lastmod', '%Y-%m-%d')
    html = _env.get_template('sitemap.xml').render(essays=enriched)
    with open(os.path.join(BASE_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(html)


def _prepare_archive_data(essays):
    cleaned = [{k: v for k, v in e.items() if k != 'password'} for e in essays]
    essays_sorted = sorted(cleaned, key=lambda e: e.get('date', ''), reverse=True)
    return {
        'total': len(cleaned),
        'essays_json': json.dumps(essays_sorted, ensure_ascii=False).replace('</', '<\\/'),
    }


def _generate_archive():
    """Generate archive.html — timeline grouped by year (Jinja2 template)."""
    context = _prepare_archive_data(ESSAY_REPOSITORY.list())
    html = _env.get_template('archive.html').render(
        **context,
        build_ts=int(datetime.now().timestamp()))
    with open(os.path.join(BASE_DIR, 'archive.html'), 'w', encoding='utf-8') as f:
        f.write(html)


def _prepare_map_data(photos):
    gps_photos = [p for p in photos if p.get('exif', {}).get('gps')]
    center_lat, center_lng = 22.5431, 113.9579
    if gps_photos:
        try:
            lats = [p['exif']['gps']['lat'] for p in gps_photos]
            lngs = [p['exif']['gps']['lng'] for p in gps_photos]
            center_lat = sum(lats) / len(lats)
            center_lng = sum(lngs) / len(lngs)
        except KeyError:
            pass
    return {
        'photos_json': json.dumps(gps_photos, ensure_ascii=False).replace('</', '<\\/'),
        'total': len(gps_photos),
        'center_lat': center_lat,
        'center_lng': center_lng,
    }


def _generate_map():
    """Generate map.html — Leaflet map with GPS-tagged photos (Jinja2 template)."""
    context = _prepare_map_data(PHOTO_REPOSITORY.list())
    html = _env.get_template('map.html').render(
        **context,
        build_ts=int(datetime.now().timestamp()))
    with open(os.path.join(BASE_DIR, 'map.html'), 'w', encoding='utf-8') as f:
        f.write(html)


def _public_essay_data(essays):
    return ESSAY_SERVICE.public_listing(essays, _parse_date, get_essay_password)


def _ordered_public_tags(all_tags):
    ordered = []
    for t in ESSAY_REPOSITORY.read_tag_order():
        if t in all_tags:
            ordered.append(t)
            all_tags.discard(t)
    ordered.extend(sorted(all_tags))  # new tags not in saved order, alphabetical at end
    return ordered


def _generate_public_essays():
    """Write public listing metadata without exposing passwords or essay bodies."""
    visible, all_tags = _public_essay_data(load_json('essays.json'))
    public_data = {'_tags': _ordered_public_tags(all_tags), 'essays': visible}
    public_path = os.path.join(DATA_DIR, 'essays_public.json')
    with open(public_path, 'w', encoding='utf-8') as f:
        json.dump(public_data, f, ensure_ascii=False, indent=2)


def _generate_feeds():
    """Regenerate all auto-generated files: RSS, sitemap, archive, map, public essays."""
    _generate_public_essays()
    _generate_rss()
    _generate_sitemap()
    _generate_archive()
    _generate_map()





def _extract_gps(exif_dict):
    return extract_gps(exif_dict)


def _extract_exif(img):
    return extract_exif(img)


def _without_camera_model(exif_data):
    return without_camera_model(exif_data)


def _set_gps(filename, lat, lng):
    return set_gps(filename, lat, lng)




def _is_encrypted_v3(content):
    """Detect v3 Fernet encrypted content by inspecting the first-line base64."""
    try:
        import base64
        raw = base64.b64decode(content.split('\n')[0])
        return raw and raw[0] == 2
    except (ValueError, IndexError):
        return False


def _persist_essay_source(slug, content):
    password = get_essay_password(slug)
    os.makedirs(MD_DIR, exist_ok=True)
    stored = _encrypt_content(content, password) if password and content.strip() else content
    with open(os.path.join(MD_DIR, f'{slug}.md'), 'w', encoding='utf-8') as f:
        f.write(stored)
    return stored


def _read_essay_source(slug):
    md_file = os.path.join(MD_DIR, f'{slug}.md')
    html_file = os.path.join(ESSAYS_DIR, f'{slug}.html')
    if os.path.exists(md_file):
        with open(md_file, 'r', encoding='utf-8') as f:
            return f.read()
    if os.path.exists(html_file):
        with open(html_file, 'r', encoding='utf-8') as f:
            match = re.search(r'<!-- RAW_MD\n(.*)\nRAW_MD -->', f.read(), flags=re.DOTALL)
        return match.group(1) if match else ''
    return ''


def _prepare_essay_body(slug, raw_md, last_edited):
    if raw_md and _is_encrypted_v3(raw_md):
        return {'password_protected': True, 'encrypted_body': raw_md, 'body_html': '', 'encrypted_is_md': True, 'og_image': ''}
    if not raw_md or not raw_md.strip():
        return {'password_protected': False, 'encrypted_body': '', 'body_html': '', 'encrypted_is_md': False, 'og_image': ''}
    password = get_essay_password(slug)
    if password:
        stored = _persist_essay_source(slug, raw_md)
        return {'password_protected': True, 'encrypted_body': stored, 'body_html': '', 'encrypted_is_md': True, 'og_image': ''}
    rendered_html = render_markdown(raw_md)
    return {
        'password_protected': False,
        'encrypted_body': '',
        'body_html': f'{rendered_html}\n<p class="essay-updated">Last edited at {last_edited}</p>',
        'encrypted_is_md': False,
        'og_image': _extract_first_image(raw_md),
    }


def _sync_essay_html(essay, raw_md_memory=None, essays=None):
    """
    Regenerate essay HTML from the .md source file.

    Encrypted essays: raw ciphertext is passed through — no server-side
    decryption, rendering, or re-encryption. The browser handles everything:
    Web Crypto decrypt -> marked.js render MD to HTML -> KaTeX -> display.
    Passwords never touch the SSG build path.

    essays: optional pre-loaded essays list. When not provided, loaded from disk.
    """
    slug = essay['slug']
    if raw_md_memory is not None:
        _persist_essay_source(slug, raw_md_memory)
    raw_md = _read_essay_source(slug)
    body_data = _prepare_essay_body(slug, raw_md, _parse_date(essay.get('date', ''), include_time=True))
    essays = ESSAY_REPOSITORY.list() if essays is None else essays
    html = render_essay_html(essay, body_data, essays, _env.get_template('essay.html'), _parse_date)
    write_essay_html(os.path.join(ESSAYS_DIR, f"{slug}.html"), html)


def _fetch_stars():
    return fetch_stars()


# Public generation boundary used by the essay application workflow.
calculate_read_time = _calc_read_time
parse_date = _parse_date
generate_feeds = _generate_feeds
sync_essay_html = _sync_essay_html
