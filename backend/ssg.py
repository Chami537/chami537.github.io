"""SSG generators and essay helpers for the Chami CMS."""

import base64
import html as html_mod
import os
import json
import re
import urllib.request
from datetime import datetime
from markupsafe import Markup
from PIL import Image, ExifTags
from backend.markdown_utils import render_markdown

# ── Encryption helpers (cryptography Fernet: AES-128-CBC + HMAC-SHA256) ──

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes as _crypto_hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_ENCRYPT_V3 = b'\x02'  # version byte for Fernet-based format


def _derive_fernet(password, salt):
    """Derive a 32-byte Fernet key from password + salt via PBKDF2-SHA256 (100k iter)."""
    kdf = PBKDF2HMAC(
        algorithm=_crypto_hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))


def _encrypt_content(plaintext, password):
    """PBKDF2 + Fernet (AES-128-CBC + HMAC-SHA256). Returns base64(version + salt + token)."""
    salt = os.urandom(16)
    key = _derive_fernet(password, salt)
    token = Fernet(key).encrypt(plaintext.encode('utf-8'))
    return base64.b64encode(_ENCRYPT_V3 + salt + token).decode('ascii')


def _decrypt_content(encrypted_b64, password):
    """Decrypt v3 Fernet format. Raises ValueError on wrong password or unknown format."""
    raw = base64.b64decode(encrypted_b64)

    if not raw or raw[0] != 2 or len(raw) <= 17:
        raise ValueError('Unknown or legacy encryption format — re-encrypt with v3 Fernet')

    salt = raw[1:17]
    token = raw[17:]
    key = _derive_fernet(password, salt)
    try:
        return Fernet(key).decrypt(token).decode('utf-8')
    except InvalidToken:
        raise ValueError('Wrong password or corrupted data')

from backend.data import load_json, atomic_write_json, decimal_to_dms, dms_to_decimal, format_shutter, format_aperture, format_focal, get_essay_password, BASE_DIR, DATA_DIR, ESSAYS_DIR, MD_DIR, IMAGES_DIR
from jinja2 import Environment, FileSystemLoader

_env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, 'templates')))

# ═══════════════════════════════════════════

def _cache_bust_assets():
    """Append ?v=<mtime> to CSS/JS links in index.html and admin.html.
    Uses regex to safely replace existing version strings — idempotent, no stacking.
    """
    for html_fn, css_fn, js_fns in [
        ('index.html', 'assets/css/index.css', ('assets/js/index.js',)),
        ('admin.html', 'assets/css/admin.css', (
            'assets/js/admin.js',
            'assets/js/admin-content.js',
            'assets/js/admin-essays.js',
            'assets/js/admin-photos.js',
        )),
    ]:
        html_path = os.path.join(BASE_DIR, html_fn)
        if not os.path.exists(html_path):
            continue
        css_path = os.path.join(BASE_DIR, css_fn)
        ts = 0
        if os.path.exists(css_path):
            ts = max(ts, int(os.path.getmtime(css_path)))
        for js_fn in js_fns:
            js_path = os.path.join(BASE_DIR, js_fn)
            if os.path.exists(js_path):
                ts = max(ts, int(os.path.getmtime(js_path)))
        if ts == 0:
            continue
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
        css_ref = re.escape(css_fn)
        html = re.sub(rf'href="{css_ref}(\?v=\d+)?"', f'href="{css_fn}?v={ts}"', html)
        for js_fn in js_fns:
            js_ref = re.escape(js_fn)
            html = re.sub(rf'src="{js_ref}(\?v=\d+)?"', f'src="{js_fn}?v={ts}"', html)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)


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
    """Shared: strip password, parse dates. Used by RSS and sitemap generators."""
    enriched = []
    for e in (essays[:limit] if limit else essays):
        item = {k: v for k, v in e.items() if k != 'password'}
        date_str = e.get('date', '')
        item[date_key] = ''
        for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d'):
            try:
                item[date_key] = datetime.strptime(date_str, fmt).strftime(date_fmt)
                break
            except ValueError:
                continue
        enriched.append(item)
    return enriched


def _generate_rss():
    """Generate rss.xml from essays.json (Jinja2 template)."""
    essays = load_json('essays.json')
    enriched = _strip_enrich(essays, 'pub_date', '%a, %d %b %Y %H:%M:%S +0800', 20)
    last_build = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0800')
    html = _env.get_template('rss.xml').render(essays=enriched, last_build=last_build)
    with open(os.path.join(BASE_DIR, 'rss.xml'), 'w', encoding='utf-8') as f:
        f.write(html)


def _generate_sitemap():
    """Generate sitemap.xml (Jinja2 template)."""
    essays = load_json('essays.json')
    enriched = _strip_enrich(essays, 'lastmod', '%Y-%m-%d')
    html = _env.get_template('sitemap.xml').render(essays=enriched)
    with open(os.path.join(BASE_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(html)


def _generate_archive():
    """Generate archive.html — timeline grouped by year (Jinja2 template)."""
    essays = load_json('essays.json')
    cleaned = [{k: v for k, v in e.items() if k != 'password'} for e in essays]
    essays_sorted = sorted(cleaned, key=lambda e: e.get('date', ''), reverse=True)
    essays_json = json.dumps(essays_sorted, ensure_ascii=False).replace('</', '<\\/')
    total = len(cleaned)
    html = _env.get_template('archive.html').render(
        total=total, essays_json=essays_json,
        build_ts=int(datetime.now().timestamp()))
    with open(os.path.join(BASE_DIR, 'archive.html'), 'w', encoding='utf-8') as f:
        f.write(html)

def _generate_map():
    """Generate map.html — Leaflet map with GPS-tagged photos (Jinja2 template)."""
    photos = load_json('photos.json')
    gps_photos = [p for p in photos if p.get('exif', {}).get('gps')]
    photos_json = json.dumps(gps_photos, ensure_ascii=False).replace('</', '<\/')
    total = len(gps_photos)
    center_lat, center_lng = 22.5431, 113.9579  # default: Shenzhen
    if gps_photos:
        try:
            lats = [p['exif']['gps']['lat'] for p in gps_photos]
            lngs = [p['exif']['gps']['lng'] for p in gps_photos]
            center_lat = sum(lats) / len(lats)
            center_lng = sum(lngs) / len(lngs)
        except KeyError:
            pass  # malformed GPS entry — keep default center
    html = _env.get_template('map.html').render(
        photos_json=photos_json, total=total,
        center_lat=center_lat, center_lng=center_lng,
        build_ts=int(datetime.now().timestamp()))
    with open(os.path.join(BASE_DIR, 'map.html'), 'w', encoding='utf-8') as f:
        f.write(html)


def _generate_public_essays():
    """Write data/essays_public.json — all essays visible, passwords stripped, plus _tags."""
    essays = load_json('essays.json')
    visible = []
    all_tags = set()
    for e in essays:
        tag_str = e.get('tag', '')
        if tag_str:
            for t in tag_str.replace(',', '，').split('，'):
                t = t.strip()
                if t:
                    all_tags.add(t)
        item = {k: v for k, v in e.items() if k != 'password'}
        item['date_display'] = _parse_date(e.get('date', ''))
        visible.append(item)
    public_path = os.path.join(DATA_DIR, 'essays_public.json')
    # Use saved order from tags_order.json, filter to only tags that exist in essays
    tag_order_path = os.path.join(DATA_DIR, 'tags_order.json')
    ordered = []
    if os.path.exists(tag_order_path):
        with open(tag_order_path, 'r', encoding='utf-8') as f:
            for t in json.load(f):
                if t in all_tags:
                    ordered.append(t)
                    all_tags.discard(t)
    ordered.extend(sorted(all_tags))  # new tags not in saved order, alphabetical at end
    public_data = {'_tags': ordered, 'essays': visible}
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
    """从 _getexif() 原始字典中安全提取 GPS 经纬度"""
    if not exif_dict or 34853 not in exif_dict:
        return None
    gps_info = exif_dict[34853]
    try:
        lat = dms_to_decimal(gps_info[2])
        if gps_info.get(1, 'N') == 'S':
            lat = -lat

        lng = dms_to_decimal(gps_info[4])
        if gps_info.get(3, 'E') == 'W':
            lng = -lng

        return {"lat": round(lat, 6), "lng": round(lng, 6)}
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def _extract_exif(img):
    """从 PIL Image 提取 EXIF 元数据（相机/镜头/ISO/GPS 等），返回 dict。"""
    exif_data = {}
    exif_raw = img.getexif()
    if not exif_raw:
        return exif_data
    tags = {}
    for k, v in exif_raw.items():
        name = ExifTags.TAGS.get(k, k)
        if hasattr(v, 'numerator') and hasattr(v, 'denominator'):
            v = float(v)
        tags[name] = str(v)
    if 'Make' in tags:
        exif_data['camera'] = tags['Make']
    if 'Model' in tags:
        exif_data['model'] = tags['Model']
    if 'ExposureTime' in tags:
        exif_data['shutter'] = format_shutter(tags['ExposureTime'])
    if 'FNumber' in tags:
        exif_data['aperture'] = format_aperture(tags['FNumber'])
    if 'ISOSpeedRatings' in tags:
        exif_data['iso'] = tags['ISOSpeedRatings']
    if 'FocalLength' in tags:
        exif_data['focal'] = format_focal(tags['FocalLength'])
    for date_key in ('DateTimeOriginal', 'DateTimeDigitized', 'DateTime'):
        if date_key in tags:
            raw_date = str(tags[date_key])
            exif_data['date'] = raw_date.replace(':', '-', 2).rsplit(':', 1)[0]
            break
    gps_data = _extract_gps(exif_raw)
    if gps_data:
        exif_data['gps'] = gps_data
    return exif_data


def _set_gps(filename, lat, lng):
    """给 raw_photos/ 中的照片写入 GPS 坐标 + 同步更新 photos.json"""
    filename = os.path.basename(filename)
    path = os.path.join(BASE_DIR, 'raw_photos', filename)
    if not os.path.exists(path):
        print(f"文件不存在: {path}")
        return

    with Image.open(path) as img:
        exif = img.getexif()

        # 十进制 → 度分秒（始终正值，方向由 N/S/E/W tag 承载，见 backend/data.py）
        lat_dms = decimal_to_dms(lat)
        lng_dms = decimal_to_dms(lng)

        gps_ifd = {
            1: 'N' if lat >= 0 else 'S',
            2: lat_dms,
            3: 'E' if lng >= 0 else 'W',
            4: lng_dms,
        }
        exif[34853] = gps_ifd

        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(path, 'JPEG', quality=95, exif=exif.tobytes())

    # 同步更新 photos.json
    photos_json_path = os.path.join(DATA_DIR, 'photos.json')
    photos_data = []
    if os.path.exists(photos_json_path):
        with open(photos_json_path, 'r', encoding='utf-8') as f:
            photos_data = json.load(f)

    found = False
    for p in photos_data:
        if p['filename'] == filename:
            if 'exif' not in p:
                p['exif'] = {}
            p['exif']['gps'] = {'lat': round(lat, 6), 'lng': round(lng, 6)}
            found = True
            break

    if not found:
        photos_data.append({
            'filename': filename,
            'exif': {'gps': {'lat': round(lat, 6), 'lng': round(lng, 6)}}
        })

    atomic_write_json('photos.json', photos_data)

    print(f"GPS 已写入: {filename}")
    print(f"  纬度: {lat} ({'N' if lat >= 0 else 'S'})")
    print(f"  经度: {lng} ({'E' if lng >= 0 else 'W'})")
    print(f"  photos.json 已同步更新")




def _parse_tags(tag_str, essay=None):
    """'生活, 摄影' → {'生活', '摄影'}. Pinned essays implicitly get '置顶' tag."""
    tags = set(t.strip() for t in re.split(r'[,，]', tag_str) if t.strip()) if tag_str else set()
    if essay and essay.get('pinned'):
        tags.add('置顶')
    return tags

def _find_adjacent_siblings(essays, idx, siblings):
    """Find prev/next sibling essays within *siblings* list, ordered by *essays* date order."""
    prev_sib, next_sib = None, None
    for i in range(idx - 1, -1, -1):
        if essays[i] in siblings:
            prev_sib = essays[i]; break
    for i in range(idx + 1, len(essays)):
        if essays[i] in siblings:
            next_sib = essays[i]; break
    return prev_sib, next_sib


def _build_nav(essays, current_slug):
    """Build prev/next essay navigation links, scoped to essays sharing at least one tag."""
    current = next((e for e in essays if e['slug'] == current_slug), None)
    current_tags = _parse_tags(current.get('tag', ''), current) if current else set()

    if current_tags:
        siblings = [e for e in essays if e['slug'] != current_slug and _parse_tags(e.get('tag', ''), e) & current_tags]
    else:
        siblings = [e for e in essays if e['slug'] != current_slug]

    # Find prev/next among siblings by global date order
    idx = next((i for i, e in enumerate(essays) if e['slug'] == current_slug), -1)
    prev_sib, next_sib = _find_adjacent_siblings(essays, idx, siblings)

    prev_nav = '<div></div>'
    next_nav = '<div></div>'
    if prev_sib:
        prev_nav = f'''<a href="{prev_sib['slug']}.html" class="prev-link">
      <span class="prev-label">上一篇</span>
      <div class="prev-title">
        <span class="prev-arr">←</span>
        <span>{html_mod.escape(prev_sib['title'])}</span>
      </div>
    </a>'''
    if next_sib:
        next_nav = f'''<a href="{next_sib['slug']}.html" class="next-link">
      <span class="next-label">下一篇</span>
      <div class="next-title">
        <span>{html_mod.escape(next_sib['title'])}</span>
        <span class="next-arr">→</span>
      </div>
    </a>'''
    return prev_nav, next_nav




def _is_encrypted_v3(content):
    """Detect v3 Fernet encrypted content by inspecting the first-line base64."""
    try:
        raw = base64.b64decode(content.split('\n')[0])
        return raw and raw[0] == 2
    except (ValueError, IndexError):
        return False


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
    html_file = os.path.join(ESSAYS_DIR, f"{slug}.html")
    md_file = os.path.join(MD_DIR, f"{slug}.md")

    # 1. Persist raw_md_memory to .md if provided (admin content save).
    #    Password is only used for at-rest encryption of the .md file.
    if raw_md_memory is not None:
        password = get_essay_password(slug)
        os.makedirs(MD_DIR, exist_ok=True)
        if password and raw_md_memory.strip():
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(_encrypt_content(raw_md_memory, password))
        else:
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(raw_md_memory)

    # 2. Read .md content (prefer file, fallback to HTML comment for legacy)
    raw_md = ""
    if os.path.exists(md_file):
        with open(md_file, 'r', encoding='utf-8') as f:
            raw_md = f.read()
    elif os.path.exists(html_file):
        with open(html_file, 'r', encoding='utf-8') as f:
            full_html = f.read()
        md_match = re.search(r'<!-- RAW_MD\n(.*)\nRAW_MD -->', full_html, flags=re.DOTALL)
        if md_match:
            raw_md = md_match.group(1)

    # 3. Detect encrypted content by inspecting the content itself
    last_edited = _parse_date(essay.get('date', ''), include_time=True)
    encrypted_is_md = False
    if raw_md and _is_encrypted_v3(raw_md):
        # Encrypted at rest -> pass through for client-side decryption + rendering
        password_protected = True
        encrypted_body = raw_md
        body_html = ''
        encrypted_is_md = True
        og_image = ''
    elif raw_md and raw_md.strip():
        # Plaintext content. Check if this essay should be encrypted (first-time setup).
        password = get_essay_password(slug)
        if password:
            # First-time encryption: encrypt now, then pass through
            os.makedirs(MD_DIR, exist_ok=True)
            raw_md = _encrypt_content(raw_md, password)
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(raw_md)
            password_protected = True
            encrypted_body = raw_md
            body_html = ''
            encrypted_is_md = True
            og_image = ''
        else:
            password_protected = False
            encrypted_body = ''
            rendered_html = render_markdown(raw_md)
            body_html = f"{rendered_html}\n<p class=\"essay-updated\">Last edited at {last_edited}</p>"
            og_image = _extract_first_image(raw_md)
    else:
        # No content at all
        password_protected = False
        encrypted_body = ''
        body_html = ''
        og_image = ''

    # 4. Prepare template data
    if essays is None:
        essays = load_json('essays.json')
    prev_nav, next_nav = _build_nav(essays, slug)

    tag_raw = essay.get('tag', '')
    tag_display = html_mod.escape(tag_raw.replace(', ', ' · ').replace(',', ' · '))
    date_display = html_mod.escape(_parse_date(essay.get('date', '')))

    # 5. Render template
    template = _env.get_template('essay.html')
    html = template.render(
        title=html_mod.escape(essay.get('title', '')),
        excerpt=html_mod.escape(essay.get('excerpt', '')),
        epigraph=html_mod.escape(essay.get('epigraph', '')),
        tag=tag_display,
        date_display=date_display,
        read_time=essay.get('readTime', 1),
        body_html=Markup(body_html),
        encrypted_body=encrypted_body,
        password_protected=password_protected,
        encrypted_is_md=encrypted_is_md,
        last_edited=html_mod.escape(last_edited),
        prev_nav=Markup(prev_nav),
        next_nav=Markup(next_nav),
        slug=slug,
        og_image=html_mod.escape(og_image),
        build_ts=int(datetime.now().timestamp()),
    )

    # 6. Write output
    os.makedirs(ESSAYS_DIR, exist_ok=True)
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)


def _fetch_stars():
    """Pre-fetch GitHub star counts for work items and cache in work.json.
    Uses conditional GET (If-None-Match) to avoid hitting rate limits on repeat runs.
    Writes an _stars_etag key to track last-seen ETags.
    """
    work = load_json('work.json')
    # Load cached ETags from a sidecar file (avoids polluting work.json)
    etag_path = os.path.join(DATA_DIR, '_stars_etag.json')
    etags = {}
    if os.path.exists(etag_path):
        try:
            with open(etag_path, 'r', encoding='utf-8') as f:
                etags = json.load(f)
        except (json.JSONDecodeError, ValueError):
            etags = {}  # corrupted — reset

    updated = False
    for w in work:
        repo = w.get('repo', '')
        if not repo:
            continue
        url = f'https://api.github.com/repos/{repo}'
        req = urllib.request.Request(url)
        req.add_header('Accept', 'application/vnd.github.v3+json')
        req.add_header('User-Agent', 'Chami-SSG/1.0')
        etag = etags.get(repo, '')
        if etag:
            req.add_header('If-None-Match', etag)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 304:
                    continue
                if resp.status != 200:
                    print(f"  WARNING: GitHub API returned {resp.status} for {repo}")
                    continue
                data = json.loads(resp.read().decode())
                stars = data.get('stargazers_count', 0)
                if w.get('stars') != stars:
                    w['stars'] = stars
                    updated = True
                new_etag = resp.headers.get('ETag', '')
                if new_etag:
                    etags[repo] = new_etag
        except Exception as exc:
            print(f"  WARNING: failed to fetch stars for {repo}: {exc}")
            continue

    if updated:
        atomic_write_json('work.json', work)
    # Atomic write to avoid corruption on crash
    etag_tmp = etag_path + '.tmp'
    with open(etag_tmp, 'w', encoding='utf-8') as f:
        json.dump(etags, f)
    os.replace(etag_tmp, etag_path)
