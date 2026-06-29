"""SSG generators and essay helpers for the Chami CMS."""

import html as html_mod
import os
import json
import re
from datetime import datetime
from markdown import markdown as md_to_html
from PIL import Image, ExifTags

from data import load_json, atomic_write_json, BASE_DIR, DATA_DIR
from jinja2 import Environment, FileSystemLoader

ESSAYS_DIR = os.path.join(BASE_DIR, 'essays')
MD_DIR = os.path.join(BASE_DIR, 'md')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')

os.makedirs(MD_DIR, exist_ok=True)
os.makedirs(ESSAYS_DIR, exist_ok=True)

_env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, 'templates')))

# ═══════════════════════════════════════════

def _load_essay_template():
    """Read essay HTML template from disk on each call — always up-to-date."""
    with open(os.path.join(BASE_DIR, 'templates/essay.html'), encoding='utf-8') as f:
        return f.read()


def _fe(s):
    """HTML-escape user content for safe embedding in HTML."""
    return html_mod.escape(str(s))


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


def _parse_date(date_str):
    """'2026-06' or '2026-06-25 14:30' → 'Jun 2026' or 'Jun 25, 2026'"""
    if not isinstance(date_str, str) or not date_str.strip():
        return date_str if isinstance(date_str, str) else ''
    try:
        MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        date_segments = date_str.split(' ')[0].split('-')

        result = ''
        if len(date_segments) >= 3 and date_segments[2] and date_segments[1]:
            m = MONTHS[int(date_segments[1]) - 1]
            result = f"{m} {int(date_segments[2])}, {date_segments[0]}"
        elif len(date_segments) >= 2 and date_segments[1]:
            m = MONTHS[int(date_segments[1]) - 1]
            result = f"{m} {date_segments[0]}"

        return result or date_str
    except (ValueError, IndexError):
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


def _generate_rss():
    """Generate rss.xml from essays.json (Jinja2 template)."""
    essays = load_json('essays.json')
    enriched = []
    for e in essays[:20]:
        item = dict(e)
        date_str = e.get('date', '')
        item['pub_date'] = ''
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
            item['pub_date'] = dt.strftime('%a, %d %b %Y %H:%M:%S +0800')
        except ValueError:
            pass
        enriched.append(item)
    last_build = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0800')
    html = _env.get_template('rss.xml').render(essays=enriched, last_build=last_build)
    with open(os.path.join(BASE_DIR, 'rss.xml'), 'w', encoding='utf-8') as f:
        f.write(html)


def _generate_sitemap():
    """Generate sitemap.xml (Jinja2 template)."""
    essays = load_json('essays.json')
    enriched = []
    for e in essays:
        item = dict(e)
        date_str = e.get('date', '')
        item['lastmod'] = ''
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
            item['lastmod'] = dt.strftime('%Y-%m-%d')
        except ValueError:
            pass
        enriched.append(item)
    html = _env.get_template('sitemap.xml').render(essays=enriched)
    with open(os.path.join(BASE_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(html)


def _generate_archive():
    """Generate archive.html — timeline grouped by year (Jinja2 template)."""
    essays = load_json('essays.json')
    essays_sorted = sorted(essays, key=lambda e: e.get('date', ''), reverse=True)
    essays_json = json.dumps(essays_sorted, ensure_ascii=False).replace('</', '<\\/')
    total = len(essays)
    html = _env.get_template('archive.html').render(total=total, essays_json=essays_json)
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
        lats = [p['exif']['gps']['lat'] for p in gps_photos]
        lngs = [p['exif']['gps']['lng'] for p in gps_photos]
        center_lat = sum(lats) / len(lats)
        center_lng = sum(lngs) / len(lngs)
    html = _env.get_template('map.html').render(
        photos_json=photos_json, total=total,
        center_lat=center_lat, center_lng=center_lng)
    with open(os.path.join(BASE_DIR, 'map.html'), 'w', encoding='utf-8') as f:
        f.write(html)


def _generate_feeds():
    """Regenerate all auto-generated files: RSS, sitemap, archive, map."""
    _generate_rss()
    _generate_sitemap()
    _generate_archive()
    _generate_map()




def _fmt_shutter(val):
    try:
        v = float(val)
        if 0 < v < 1:
            return f"1/{int(round(1/v))}s"
        return f"{int(v)}s" if v == int(v) else f"{v}s"
    except (ValueError, TypeError):
        return str(val)

def _fmt_aperture(val):
    try:
        return f"f/{float(val):g}"
    except (ValueError, TypeError):
        return str(val)

def _fmt_focal(val):
    try:
        return f"{int(float(val))}mm"
    except (ValueError, TypeError):
        return str(val)


def _extract_gps(exif_dict):
    """从 _getexif() 原始字典中安全提取 GPS 经纬度"""
    if not exif_dict or 34853 not in exif_dict:
        return None
    gps_info = exif_dict[34853]
    try:
        def dms_to_decimal(value):
            return float(value[0]) + (float(value[1]) / 60.0) + (float(value[2]) / 3600.0)

        lat = dms_to_decimal(gps_info[2])
        if gps_info.get(1, 'N') == 'S':
            lat = -lat

        lng = dms_to_decimal(gps_info[4])
        if gps_info.get(3, 'E') == 'W':
            lng = -lng

        return {"lat": round(lat, 6), "lng": round(lng, 6)}
    except Exception:
        return None


def _set_gps(filename, lat, lng):
    """给 raw_photos/ 中的照片写入 GPS 坐标 + 同步更新 photos.json"""
    path = os.path.join(BASE_DIR, 'raw_photos', filename)
    if not os.path.exists(path):
        print(f"文件不存在: {path}")
        return

    img = Image.open(path)
    exif = img.getexif()

    # 十进制 → 度分秒（始终正值，方向由 N/S/E/W tag 承载）
    def decimal_to_dms(d):
        d = abs(d)
        deg = int(d)
        m = (d - deg) * 60
        min_val = int(m)
        sec = (m - min_val) * 60
        return (deg, min_val, sec)

    lat_dms = decimal_to_dms(lat)
    lng_dms = decimal_to_dms(lng)

    gps_ifd = {
        1: 'N' if lat >= 0 else 'S',
        2: lat_dms,
        3: 'E' if lng >= 0 else 'W',
        4: lng_dms,
    }
    exif[34853] = gps_ifd

    img.save(path, 'JPEG', quality=95, exif=exif.tobytes())
    img.close()

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


def _html_to_md(html):
    """Convert essay body HTML to Markdown (p, blockquote, h2, strong, em, br, div wrapper)."""
    md = html.strip()
    # Remove <div class="essay-body"> wrapper
    md = re.sub(r'<div\s+class="essay-body"\s*>\s*', '', md, flags=re.DOTALL)
    md = re.sub(r'\s*</div>\s*$', '', md, flags=re.DOTALL)
    # Unwrap <blockquote><p>...</p></blockquote> → > text
    md = re.sub(
        r'<blockquote>\s*<p[^>]*>(.*?)</p>\s*</blockquote>',
        r'\n> \1\n', md, flags=re.DOTALL
    )
    # Plain <blockquote> without nested <p>
    md = re.sub(r'<blockquote>\s*(.*?)\s*</blockquote>', r'\n> \1\n', md, flags=re.DOTALL)
    # Paragraphs with optional attributes
    md = re.sub(r'<p[^>]*>\s*(.*?)\s*</p>', r'\n\1\n', md, flags=re.DOTALL)
    # h2
    md = re.sub(r'<h2[^>]*>\s*(.*?)\s*</h2>', r'\n## \1\n', md, flags=re.DOTALL)
    # inline tags
    md = re.sub(r'<strong>(.*?)</strong>', r'**\1**', md)
    md = re.sub(r'<em>(.*?)</em>', r'*\1*', md)
    md = re.sub(r'<br\s*/?>', '\n', md)
    # clean whitespace
    md = re.sub(r'\n{3,}', '\n\n', md)
    md = re.sub(r'\n> \n', '\n> ', md)  # Fix "> \n" blockquote spacing
    return md.strip()


def _parse_tags(tag_str, essay=None):
    """'生活, 摄影' → {'生活', '摄影'}. Pinned essays implicitly get '置顶' tag."""
    tags = set(t.strip() for t in re.split(r'[,，]', tag_str) if t.strip()) if tag_str else set()
    if essay and essay.get('pinned'):
        tags.add('置顶')
    return tags

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
    prev_sib, next_sib = None, None
    for i in range(idx - 1, -1, -1):
        if essays[i] in siblings:
            prev_sib = essays[i]; break
    for i in range(idx + 1, len(essays)):
        if essays[i] in siblings:
            next_sib = essays[i]; break

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


def _build_tag_nav_json(essays, slug):
    """Build per-tag prev/next navigation data as JSON, keyed by tag name.
    Returns a JS object string like: {"置顶":{"prev":{"slug":"x","title":"X"},"next":null},...}
    """
    current = next((e for e in essays if e['slug'] == slug), None)
    if not current:
        return '{}'
    current_tags = _parse_tags(current.get('tag', ''), current)
    if not current_tags:
        return '{}'
    result = {}
    idx = next((i for i, e in enumerate(essays) if e['slug'] == slug), -1)
    for tag in current_tags:
        siblings = [e for e in essays if e['slug'] != slug and tag in _parse_tags(e.get('tag', ''), e)]
        prev_sib, next_sib = None, None
        for i in range(idx - 1, -1, -1):
            if essays[i] in siblings:
                prev_sib = essays[i]; break
        for i in range(idx + 1, len(essays)):
            if essays[i] in siblings:
                next_sib = essays[i]; break
        result[tag] = {
            'prev': {'slug': prev_sib['slug'], 'title': prev_sib['title']} if prev_sib else None,
            'next': {'slug': next_sib['slug'], 'title': next_sib['title']} if next_sib else None,
        }
    return json.dumps(result, ensure_ascii=False).replace('</', '<\\/')



def _sync_essay_html(essay, raw_md_memory=None):
    """
    根据最新的 essay 元数据和存储的 Markdown 原文，
    直接重新渲染并覆盖对应的 HTML 文件，彻底抛弃正则修补。
    raw_md_memory: 可选，内存中的最新 Markdown 内容（跳过文件读取）。
    """
    slug = essay['slug']
    html_file = os.path.join(ESSAYS_DIR, f"{slug}.html")

    # 1. 提取正文 Markdown（优先 .md 文件，其次内存传入，最后回退 HTML 注释）
    raw_md = ""
    md_file = os.path.join(MD_DIR, f"{slug}.md")
    if raw_md_memory is not None:
        raw_md = raw_md_memory
    elif os.path.exists(md_file):
        with open(md_file, 'r', encoding='utf-8') as f:
            raw_md = f.read()
    elif os.path.exists(html_file):
        with open(html_file, 'r', encoding='utf-8') as f:
            full_html = f.read()
        md_match = re.search(r'<!-- RAW_MD\n(.*)\nRAW_MD -->', full_html, flags=re.DOTALL)
        if md_match:
            raw_md = md_match.group(1)
        else:
            # Fallback: extract HTML from legacy essays without RAW_MD comment
            content_match = re.search(r'<!-- CONTENT_START -->\n(.*?)\n\s*<!-- CONTENT_END -->', full_html, flags=re.DOTALL)
            if content_match:
                raw_md = _html_to_md(content_match.group(1))

    # 2. 将 Markdown 渲染为 HTML 正文
    rendered_html = md_to_html(raw_md, extensions=['extra', 'fenced_code', 'sane_lists', 'pymdownx.arithmatex'], extension_configs={'pymdownx.arithmatex': {'generic': True}}) if raw_md else ""
    date_str = essay.get('date', '')
    last_edited = _parse_date(date_str)
    time_part = date_str.split(' ')[1].split(':') if ' ' in date_str and len(date_str.split(' ')) > 1 else None
    if time_part and len(time_part) >= 2:
        last_edited = f"{time_part[0]}:{time_part[1]}, {last_edited}"
    body_html = f"{rendered_html}\n<p class=\"essay-updated\">Last edited at {last_edited}</p>"

    # 2.5 写独立 .md 文件（正源）
    if raw_md:
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(raw_md)

    # 3. 准备渲染模板所需的数据
    essays = load_json('essays.json')
    prev_nav, next_nav = _build_nav(essays, slug)
    tag_nav_json = _build_tag_nav_json(essays, slug)

    tag_raw = essay.get('tag', '')
    tag_display = _fe(tag_raw.replace(', ', ' · ').replace(',', ' · '))
    date_display = _fe(_parse_date(essay.get('date', '')))

    # 4. 全量重新渲染 HTML
    og_image = _extract_first_image(raw_md)
    html = _load_essay_template().format(
        title=_fe(essay.get('title', '')),
        excerpt=_fe(essay.get('excerpt', '')),
        epigraph=_fe(essay.get('epigraph', '')),
        tag=tag_display,
        date_display=date_display,
        read_time=essay.get('readTime', 1),
        body_html=(body_html),
        prev_nav=(prev_nav),
        next_nav=(next_nav),
        tag_nav_json=tag_nav_json,
        slug=slug,
        og_image=_fe(og_image),
    )

    # 5. 覆盖写入
    os.makedirs(ESSAYS_DIR, exist_ok=True)
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
