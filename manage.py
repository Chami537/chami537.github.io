#!/usr/bin/env python3
"""Chami 个人网站管理工具 — 微型 SSG + 无头 CMS"""

import html as html_mod
import os
import json
import re
import subprocess
from datetime import datetime
import uuid
from flask import Flask, request, jsonify, send_from_directory
from markdown import markdown as md_to_html
from PIL import Image, ExifTags

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
ESSAYS_DIR = os.path.join(BASE_DIR, 'essays')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')

os.makedirs(DATA_DIR, exist_ok=True)

# ═══════════════════════════════════════════
# 原子写入
# ═══════════════════════════════════════════

def load_json(name):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def atomic_write_json(filename, data):
    filepath = os.path.join(DATA_DIR, filename)
    tmp_filepath = filepath + '.tmp'
    try:
        with open(tmp_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_filepath, filepath)
    except Exception as e:
        if os.path.exists(tmp_filepath):
            os.remove(tmp_filepath)
        raise


# ═══════════════════════════════════════════
# Admin UI
# ═══════════════════════════════════════════

@app.route('/')
def admin_panel():
    return send_from_directory(BASE_DIR, 'admin.html')


# ═══════════════════════════════════════════
# Work CRUD
# ═══════════════════════════════════════════

@app.route('/api/work', methods=['GET'])
def list_work():
    return jsonify(load_json('work.json'))

@app.route('/api/work', methods=['POST'])
def create_work():
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    work = load_json('work.json')
    item = request.json
    item['id'] = max((w['id'] for w in work), default=0) + 1
    work.append(item)
    atomic_write_json('work.json', work)
    return jsonify(item), 201

@app.route('/api/work/<int:id>', methods=['PUT'])
def update_work(id):
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    work = load_json('work.json')
    for i, w in enumerate(work):
        if w['id'] == id:
            work[i].update(request.json)
            work[i]['id'] = id
            atomic_write_json('work.json', work)
            return jsonify(work[i])
    return jsonify({"error": "Not found"}), 404

@app.route('/api/work/<int:id>', methods=['DELETE'])
def delete_work(id):
    work = load_json('work.json')
    work = [w for w in work if w['id'] != id]
    atomic_write_json('work.json', work)
    return jsonify({"status": "deleted"})


# ═══════════════════════════════════════════
# Essays CRUD + Markdown
# ═══════════════════════════════════════════

ESSAY_TEMPLATE = open(os.path.join(BASE_DIR, 'essay_template.html'), encoding='utf-8').read()


def _fe(s):
    """HTML-escape + brace-escape for Python .format() safety."""
    return html_mod.escape(str(s)).replace('{', '{{').replace('}', '}}')


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
    """Generate rss.xml from essays.json."""
    essays = load_json('essays.json')
    items = []
    for e in essays[:20]:
        slug = html_mod.escape(e.get('slug', ''), quote=False)
        title = html_mod.escape(e.get('title', ''), quote=False)
        excerpt = html_mod.escape(e.get('excerpt', ''), quote=False)
        date_str = e.get('date', '')
        pub_date = ''
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
            pub_date = dt.strftime('%a, %d %b %Y %H:%M:%S +0800')
        except ValueError:
            pass
        items.append(f'''    <item>
      <title>{title}</title>
      <link>https://chami537.github.io/essays/{slug}.html</link>
      <description>{excerpt}</description>
      <pubDate>{pub_date}</pubDate>
      <guid>https://chami537.github.io/essays/{slug}.html</guid>
    </item>''')
    last_build = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0800')
    rss = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Chami</title>
    <link>https://chami537.github.io</link>
    <description>Chami 的个人博客 — CS Student &amp; Photographer</description>
    <language>zh-CN</language>
    <lastBuildDate>{last_build}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>'''
    with open(os.path.join(BASE_DIR, 'rss.xml'), 'w', encoding='utf-8') as f:
        f.write(rss)


def _generate_sitemap():
    """Generate sitemap.xml."""
    essays = load_json('essays.json')
    urls = []
    urls.append('''  <url>
    <loc>https://chami537.github.io/</loc>
    <priority>1.0</priority>
  </url>''')
    urls.append('''  <url>
    <loc>https://chami537.github.io/archive.html</loc>
    <priority>0.8</priority>
  </url>''')
    for e in essays:
        slug = html_mod.escape(e.get('slug', ''), quote=False)
        date_str = e.get('date', '')
        lastmod = ''
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
            lastmod = dt.strftime('%Y-%m-%d')
        except ValueError:
            pass
        urls.append(f'''  <url>
    <loc>https://chami537.github.io/essays/{slug}.html</loc>
    <lastmod>{lastmod}</lastmod>
    <priority>0.7</priority>
  </url>''')
    sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''
    with open(os.path.join(BASE_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(sitemap)


def _generate_archive():
    """Generate archive.html — timeline grouped by year."""
    essays = load_json('essays.json')
    essays_sorted = sorted(essays, key=lambda e: e.get('date', ''), reverse=True)

    from collections import OrderedDict
    years = OrderedDict()
    for e in essays_sorted:
        date_str = e.get('date', '')
        year = date_str[:4] if len(date_str) >= 4 else 'Unknown'
        if year not in years:
            years[year] = []
        years[year].append(e)

    entries_html = ''
    for year, items in years.items():
        entries_html += f'<div class="archive-year"><h2 class="archive-year-heading">{year}</h2>'
        for e in items:
            slug = html_mod.escape(e['slug'])
            title = html_mod.escape(e['title'])
            tag = html_mod.escape((e.get('tag', '') or '').replace(', ', ' · ').replace(',', ' · '))
            date_str = e.get('date', '')
            month_day = ''
            try:
                dp = date_str.split(' ')[0].split('-') if ' ' in date_str else date_str.split('-')
                if len(dp) >= 3 and dp[2]:
                    M = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
                    month_day = f'{M[int(dp[1])-1]} {int(dp[2])}'
            except (ValueError, IndexError):
                pass
            entries_html += f'''<a href="essays/{slug}.html" class="archive-row">
              <span class="archive-date">{month_day}</span>
              <span class="archive-title">{title}</span>
              <span class="archive-tag">{tag}</span>
            </a>'''
        entries_html += '</div>'

    total = len(essays)
    archive = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Archive — Chami</title>
<meta name="description" content="Chami 的随笔归档 · 共 {total} 篇">
<meta property="og:title" content="Archive — Chami">
<meta property="og:description" content="Chami 的随笔归档 · 共 {total} 篇">
<meta property="og:type" content="website">
<meta property="og:image" content="https://chami537.github.io/images/avatar.jpg">
<meta property="og:site_name" content="Chami">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="images/avatar.jpg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400;1,700&family=Noto+Serif+SC:wght@400;700&family=Noto+Sans+SC:wght@400;500;700;900&display=swap">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
:root {{
  --bg: #fafaf8; --fg: #111; --c3: #ffb800; --line: #e0dcd5; --muted: #999;
}}
html.dark {{ --bg: #1a1a1c; --fg: #e8e6e3; --line: #2e2e30; --muted: #888; }}
html.dark nav {{ background: rgba(26,26,28,0.88); }}

body {{
  font-family: 'Inter', 'Noto Sans SC', sans-serif;
  background: var(--bg); color: var(--fg);
  -webkit-font-smoothing: antialiased;
}}

nav {{
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  padding: 0 48px;
  background: rgba(250,250,248,0.88); backdrop-filter: blur(12px);
  border-bottom: 2px solid var(--fg);
}}
nav .inner {{
  max-width: 1200px; margin: 0 auto; display: flex;
  align-items: center; justify-content: space-between; height: 56px;
}}
nav .logo {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  font-size: 17px; font-weight: 800; letter-spacing: -0.01em;
  text-decoration: none; color: var(--fg);
}}
nav .back {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  font-size: 12px; font-weight: 600; letter-spacing: .08em;
  color: var(--muted); text-decoration: none;
  display: flex; align-items: center; gap: 6px; transition: color .2s;
}}
nav .back:hover {{ color: var(--c3); }}
nav .theme-btn {{
  width: 32px; height: 32px; border-radius: 50%;
  border: 1px solid var(--line); background: none;
  font-size: 16px; cursor: pointer; display: flex;
  align-items: center; justify-content: center;
  transition: background .2s, border-color .2s;
  padding: 0; line-height: 1; color: inherit;
  flex-shrink: 0;
}}
nav .theme-btn:hover {{ background: var(--line); }}
html.dark nav .theme-btn {{ border-color: #666; color: #ffd43b; }}

.archive-wrap {{
  max-width: 680px; margin: 0 auto; padding: 120px 48px 100px;
}}
.archive-header {{
  margin-bottom: 48px;
}}
.archive-header h1 {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  font-size: clamp(40px, 7vw, 64px);
  font-weight: 900; line-height: 1.0;
  letter-spacing: -0.025em; margin-bottom: 12px;
}}
.archive-header .sub {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  font-size: 15px; color: var(--muted);
}}
.archive-year {{ margin-bottom: 40px; }}
.archive-year-heading {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  font-size: 28px; font-weight: 800; color: var(--c3);
  border-left: 3px solid var(--c3); padding-left: 14px;
  margin-bottom: 20px;
}}
.archive-row {{
  display: flex; align-items: baseline; gap: 16px;
  padding: 14px 0; border-bottom: 1px solid var(--line);
  text-decoration: none; color: var(--fg);
  transition: padding-left .3s, background .3s;
}}
.archive-row:hover {{
  padding-left: 24px; background: rgba(255,184,0,0.05);
}}
.archive-date {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  font-size: 12px; color: var(--muted); min-width: 72px;
}}
.archive-title {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  font-size: 17px; font-weight: 600; flex: 1;
}}
.archive-tag {{
  font-size: 10px; font-weight: 700; letter-spacing: 0.05em;
  text-transform: uppercase; color: var(--c3);
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
}}

footer {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  padding: 60px 0; text-align: center; font-size: 11px; color: #bbb;
  letter-spacing: .04em; border-top: 1px solid var(--line);
  max-width: 680px; margin: 0 auto;
}}

@media (max-width: 768px) {{
  nav {{ padding: 0 16px; }}
  .archive-wrap {{ padding: 100px 24px 80px; }}
  .archive-row {{ gap: 10px; }}
  .archive-date {{ min-width: 56px; font-size: 11px; }}
  .archive-tag {{ display: none; }}
}}
</style>
<script>
  if (localStorage.getItem('theme') === 'dark') {{
    document.documentElement.classList.add('dark');
  }}
</script>
</head>
<body>

<nav>
  <div class="inner">
    <a href="/" class="logo">Chami</a>
    <a href="/index.html#essays" class="back">
      <span>←</span>
      <span>Essays</span>
    </a>
    <button class="theme-btn" onclick="toggleTheme()" title="切换主题" id="theme-btn">🌙</button>
  </div>
</nav>

<main class="archive-wrap">
  <div class="archive-header">
    <h1>Archive</h1>
    <p class="sub">共 {total} 篇随笔</p>
  </div>
{entries_html}
</main>

<footer>
  &copy; <script>document.write(new Date().getFullYear())</script> Chami. All rights reserved.
</footer>

<script>
(function initThemeBtn() {{
  if (localStorage.getItem('theme') === 'dark') {{
    document.getElementById('theme-btn').textContent = '☀';
  }}
}})();
function toggleTheme() {{
  var html = document.documentElement;
  var btn = document.getElementById('theme-btn');
  if (html.classList.toggle('dark')) {{
    localStorage.setItem('theme', 'dark');
    btn.textContent = '☀';
  }} else {{
    localStorage.removeItem('theme');
    btn.textContent = '🌙';
  }}
}}
</script>

</body>
</html>'''
    with open(os.path.join(BASE_DIR, 'archive.html'), 'w', encoding='utf-8') as f:
        f.write(archive)


def _generate_feeds():
    """Regenerate all auto-generated files: RSS, sitemap, archive."""
    _generate_rss()
    _generate_sitemap()
    _generate_archive()


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


def _build_nav(essays, current_slug):
    """Build prev/next essay navigation links."""
    idx = next((i for i, e in enumerate(essays) if e['slug'] == current_slug), -1)
    prev_nav = '<div></div>'
    next_nav = '<div></div>'
    if idx > 0:
        p = essays[idx - 1]
        prev_nav = f'''<a href="{p['slug']}.html" class="prev-link">
      <span class="prev-label">上一篇</span>
      <div class="prev-title">
        <span class="prev-arr">←</span>
        <span>{html_mod.escape(p['title'])}</span>
      </div>
    </a>'''
    if idx >= 0 and idx + 1 < len(essays):
        n = essays[idx + 1]
        next_nav = f'''<a href="{n['slug']}.html" class="next-link">
      <span class="next-label">下一篇</span>
      <div class="next-title">
        <span>{html_mod.escape(n['title'])}</span>
        <span class="next-arr">→</span>
      </div>
    </a>'''
    return prev_nav, next_nav


@app.route('/api/essays', methods=['GET'])
def list_essays():
    return jsonify(load_json('essays.json'))

@app.route('/api/essays', methods=['POST'])
def create_essay():
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    essays = load_json('essays.json')
    item = request.json
    slug = item.get('slug', '')
    if not slug or not re.match(r'^[a-z0-9-]+$', slug):
        return jsonify({"error": "slug 只能包含小写字母、数字和连字符"}), 400
    if any(e['slug'] == slug for e in essays):
        return jsonify({"error": "slug 已存在"}), 409

    read_time = _calc_read_time(item.get('body', '') or item.get('content', ''))
    item['readTime'] = read_time
    essays.append(item)
    atomic_write_json('essays.json', essays)

    # Generate HTML file
    date_display = _parse_date(item.get('date', ''))
    prev_nav, next_nav = _build_nav(essays, slug)
    tag_raw = item.get('tag', '')
    tag_display = tag_raw.replace(', ', ' · ').replace(',', ' · ')
    og_image = _extract_first_image(item.get('body', '') or item.get('content', ''))
    be = lambda s: s.replace('{', '{{').replace('}', '}}')
    html = ESSAY_TEMPLATE.format(
        title=_fe(item.get('title', '')),
        excerpt=_fe(item.get('excerpt', '')),
        epigraph=_fe(item.get('epigraph', '')),
        tag=_fe(tag_display),
        date_display=_fe(date_display),
        read_time=read_time,
        body_html='',
        prev_nav=be(prev_nav),
        next_nav=be(next_nav),
        slug=slug,
        og_image=_fe(og_image),
    )
    os.makedirs(ESSAYS_DIR, exist_ok=True)
    with open(os.path.join(ESSAYS_DIR, f"{slug}.html"), 'w', encoding='utf-8') as f:
        f.write(html)

    # Re-sync all existing essays' nav links + regenerate feeds
    for e in essays[:-1]:  # exclude the just-created one
        _sync_essay_html(e)
    _generate_feeds()

    return jsonify(item), 201

@app.route('/api/essays/<slug>', methods=['PUT'])
def update_essay_meta(slug):
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    essays = load_json('essays.json')
    for i, e in enumerate(essays):
        if e['slug'] == slug:
            essays[i].update(request.json)
            essays[i]['slug'] = slug
            atomic_write_json('essays.json', essays)
            _sync_essay_html(essays[i])
            _generate_feeds()
            return jsonify(essays[i])
    return jsonify({"error": "Not found"}), 404


def _sync_essay_html(essay, raw_md_memory=None):
    """
    根据最新的 essay 元数据和存储的 Markdown 原文，
    直接重新渲染并覆盖对应的 HTML 文件，彻底抛弃正则修补。
    raw_md_memory: 可选，内存中的最新 Markdown 内容（跳过文件读取）。
    """
    slug = essay['slug']
    html_file = os.path.join(ESSAYS_DIR, f"{slug}.html")

    # 1. 提取现有的正文 Markdown
    raw_md = ""
    if raw_md_memory is not None:
        raw_md = raw_md_memory
    elif os.path.exists(html_file):
        with open(html_file, 'r', encoding='utf-8') as f:
            full_html = f.read()
        md_match = re.search(r'<!-- RAW_MD\n(.*?)\nRAW_MD -->', full_html, flags=re.DOTALL)
        if md_match:
            raw_md = md_match.group(1)
        else:
            # Fallback: extract HTML from legacy essays without RAW_MD comment
            content_match = re.search(r'<!-- CONTENT_START -->\n(.*?)\n\s*<!-- CONTENT_END -->', full_html, flags=re.DOTALL)
            if content_match:
                raw_md = _html_to_md(content_match.group(1))

    # 2. 将 Markdown 渲染为 HTML 正文
    rendered_html = md_to_html(raw_md, extensions=['extra', 'fenced_code', 'sane_lists']) if raw_md else ""
    date_str = essay.get('date', '')
    last_edited = _parse_date(date_str)
    time_part = date_str.split(' ')[1].split(':') if ' ' in date_str and len(date_str.split(' ')) > 1 else None
    if time_part and len(time_part) >= 2:
        last_edited = f"{time_part[0]}:{time_part[1]}, {last_edited}"
    body_html = f"{rendered_html}\n<p class=\"essay-updated\">Last edited at {last_edited}</p>\n<!-- RAW_MD\n{raw_md}\nRAW_MD -->"

    # 3. 准备渲染模板所需的数据
    essays = load_json('essays.json')
    prev_nav, next_nav = _build_nav(essays, slug)

    tag_raw = essay.get('tag', '')
    tag_display = _fe(tag_raw.replace(', ', ' · ').replace(',', ' · '))
    date_display = _fe(_parse_date(essay.get('date', '')))

    # 4. 全量重新渲染 HTML
    og_image = _extract_first_image(raw_md)
    be = lambda s: s.replace('{', '{{').replace('}', '}}')
    html = ESSAY_TEMPLATE.format(
        title=_fe(essay.get('title', '')),
        excerpt=_fe(essay.get('excerpt', '')),
        epigraph=_fe(essay.get('epigraph', '')),
        tag=tag_display,
        date_display=date_display,
        read_time=essay.get('readTime', 1),
        body_html=be(body_html),
        prev_nav=be(prev_nav),
        next_nav=be(next_nav),
        slug=slug,
        og_image=_fe(og_image),
    )

    # 5. 覆盖写入
    os.makedirs(ESSAYS_DIR, exist_ok=True)
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)

@app.route('/api/essays/<slug>', methods=['DELETE'])
def delete_essay(slug):
    essays = load_json('essays.json')
    essays = [e for e in essays if e['slug'] != slug]
    atomic_write_json('essays.json', essays)
    html_file = os.path.join(ESSAYS_DIR, f"{slug}.html")
    if os.path.exists(html_file):
        os.remove(html_file)
    # Re-sync all remaining essays' nav links
    for e in essays:
        _sync_essay_html(e)
    _generate_feeds()
    return jsonify({"status": "deleted"})

@app.route('/api/essays/<slug>/pin', methods=['POST'])
def toggle_pin(slug):
    essays = load_json('essays.json')
    for e in essays:
        e.setdefault('pinned', False)

    target = next((e for e in essays if e['slug'] == slug), None)
    if not target:
        return jsonify({"error": "Not found"}), 404

    if not target.get('pinned'):
        pinned_count = sum(1 for e in essays if e.get('pinned'))
        if pinned_count >= 5:
            return jsonify({"error": "最多置顶 5 篇文章"}), 400
        target['pinned'] = True
    else:
        target['pinned'] = False

    atomic_write_json('essays.json', essays)
    pinned_count = sum(1 for e in essays if e.get('pinned'))
    return jsonify({"pinned": target['pinned'], "count": pinned_count})

@app.route('/api/essays/<slug>/content', methods=['GET'])
def get_essay_content(slug):
    html_file = os.path.join(ESSAYS_DIR, f"{slug}.html")
    if not os.path.exists(html_file):
        return jsonify({"error": "Not found"}), 404
    with open(html_file, 'r', encoding='utf-8') as f:
        full_html = f.read()
    # Extract Markdown source from comment if stored
    md_match = re.search(r'<!-- RAW_MD\n(.*?)\nRAW_MD -->', full_html, flags=re.DOTALL)
    if md_match:
        return jsonify({"content": md_match.group(1), "format": "markdown"})
    # Extract HTML content between anchors, auto-convert to Markdown
    pattern = r'<!-- CONTENT_START -->\n(.*?)\n\s*<!-- CONTENT_END -->'
    match = re.search(pattern, full_html, flags=re.DOTALL)
    content = match.group(1).strip() if match else ''
    if content:
        md = _html_to_md(content)
        return jsonify({"content": md, "format": "markdown"})
    return jsonify({"content": "", "format": "markdown"})

@app.route('/api/essays/<slug>/content', methods=['PUT'])
def update_essay_content(slug):
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    md_content = request.json.get('content', '')

    # 1. 自动计算阅读时间
    read_time = _calc_read_time(md_content)

    # 2. 更新 JSON 数据
    essays = load_json('essays.json')
    target_essay = None
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    for e in essays:
        if e['slug'] == slug:
            e['readTime'] = read_time
            e['date'] = now
            target_essay = e
            atomic_write_json('essays.json', essays)
            break

    if not target_essay:
        return jsonify({"error": "Essay not found"}), 404

    # 3. 直接调用渲染函数，把最新的 Markdown 传过去
    _sync_essay_html(target_essay, raw_md_memory=md_content)
    _generate_feeds()

    return jsonify({"status": "success", "message": f"{slug}.html updated"})

@app.route('/api/essays/upload-image', methods=['POST'])
def upload_essay_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({"error": "No filename"}), 400
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
    if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        return jsonify({"error": f"不支持的文件类型: .{ext}"}), 400
    filename = f"{uuid.uuid4().hex[:8]}.{ext}"
    img_dir = os.path.join(BASE_DIR, 'images', 'essays')
    os.makedirs(img_dir, exist_ok=True)
    file.save(os.path.join(img_dir, filename))
    return jsonify({"url": "/images/essays/" + filename, "status": "uploaded"}), 201

@app.route('/api/essays/<slug>/html', methods=['GET', 'POST'])
def preview_essay_html(slug):
    """Preview Markdown → HTML (no save)"""
    if request.method == 'POST' and not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    md_content = request.args.get('md', '') if request.method == 'GET' else request.json.get('md', '')
    html_content = md_to_html(md_content, extensions=['extra', 'fenced_code', 'sane_lists'])
    return jsonify({"html": html_content})


# ═══════════════════════════════════════════
# Photos CRUD + Upload
# ═══════════════════════════════════════════

@app.route('/api/photos', methods=['GET'])
def list_photos():
    return jsonify(load_json('photos.json'))

@app.route('/api/photos', methods=['PUT'])
def reorder_photos():
    """Replace entire photo array (for reordering)"""
    if not isinstance(request.json, list):
        return jsonify({"error": "Expected a JSON array"}), 400
    atomic_write_json('photos.json', request.json)
    return jsonify({"status": "reordered"})

@app.route('/api/photos/<filename>', methods=['DELETE'])
def delete_photo(filename):
    photos = load_json('photos.json')
    photos = [p for p in photos if p['filename'] != filename]
    atomic_write_json('photos.json', photos)
    # Remove image files (basename to prevent path traversal)
    safe_name = os.path.basename(filename)
    for subdir in ['', 'lg', 'md', 'sm']:
        path = os.path.join(IMAGES_DIR, subdir, safe_name)
        if os.path.exists(path):
            os.remove(path)
    return jsonify({"status": "deleted"})

@app.route('/api/photos/upload', methods=['POST'])
def upload_photo():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({"error": "No filename"}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
    if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        return jsonify({"error": f"不支持的文件类型: .{ext}"}), 400
    filename = f"{uuid.uuid4().hex[:8]}.{ext}"
    try:
        img = Image.open(file.stream)
        img.verify()
        file.stream.seek(0)
        img = Image.open(file.stream)
    except Exception:
        return jsonify({"error": "Invalid or corrupted image file"}), 400

    # Extract EXIF
    exif_data = {}
    exif = img.getexif()
    if exif:
        exif_tags = {ExifTags.TAGS.get(k, k): str(v) for k, v in exif.items()}
        for tag in ['Make', 'Model', 'FNumber', 'ExposureTime', 'ISOSpeedRatings']:
            if tag in exif_tags:
                key_map = {'Make': 'camera', 'Model': 'model', 'FNumber': 'aperture',
                           'ExposureTime': 'shutter', 'ISOSpeedRatings': 'iso'}
                exif_data[key_map[tag]] = exif_tags[tag]

    # Generate thumbnails
    for size_name, max_w in [('lg', 1920), ('md', 800), ('sm', 400)]:
        thumb = img.copy()
        thumb.thumbnail((max_w, max_w), Image.LANCZOS)
        out_dir = os.path.join(IMAGES_DIR, size_name)
        os.makedirs(out_dir, exist_ok=True)
        thumb.save(os.path.join(out_dir, filename))

    # Save original
    img.save(os.path.join(IMAGES_DIR, filename))

    # Update JSON
    photos = load_json('photos.json')
    size = request.form.get('size', 'sm')
    photos.append({"filename": filename, "size": size, "exif": exif_data})
    atomic_write_json('photos.json', photos)

    return jsonify({"status": "success", "filename": filename, "exif": exif_data}), 201


# ═══════════════════════════════════════════
# Friends CRUD
# ═══════════════════════════════════════════

@app.route('/api/friends', methods=['GET'])
def list_friends():
    return jsonify(load_json('friends.json'))

@app.route('/api/friends', methods=['POST'])
def add_friend():
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    friends = load_json('friends.json')
    friends.append(request.json)
    atomic_write_json('friends.json', friends)
    return jsonify(request.json), 201

@app.route('/api/friends/<int:index>', methods=['PUT'])
def update_friend(index):
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    friends = load_json('friends.json')
    if index < 0 or index >= len(friends):
        return jsonify({"error": "Index out of range"}), 404
    friends[index].update(request.json)
    atomic_write_json('friends.json', friends)
    return jsonify(friends[index])

@app.route('/api/friends/<int:index>', methods=['DELETE'])
def delete_friend(index):
    friends = load_json('friends.json')
    if index < 0 or index >= len(friends):
        return jsonify({"error": "Index out of range"}), 404
    friends.pop(index)
    atomic_write_json('friends.json', friends)
    return jsonify({"status": "deleted"})


# ═══════════════════════════════════════════
# About
# ═══════════════════════════════════════════

@app.route('/api/about', methods=['GET'])
def get_about():
    return jsonify(load_json('about.json'))

@app.route('/api/about/upload-avatar', methods=['POST'])
def upload_avatar():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({"error": "No filename"}), 400
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
    if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        return jsonify({"error": f"不支持的文件类型: .{ext}"}), 400
    try:
        img = Image.open(file.stream)
        img.verify()
        file.stream.seek(0)
    except Exception:
        return jsonify({"error": "Invalid or corrupted image file"}), 400
    filename = 'avatar.' + ext
    filepath = os.path.join(BASE_DIR, 'images', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)
    return jsonify({"url": "images/" + filename}), 201

@app.route('/api/about', methods=['PUT'])
def update_about():
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    atomic_write_json('about.json', request.json)
    return jsonify({"status": "updated"})


# ═══════════════════════════════════════════
# Contact CRUD
# ═══════════════════════════════════════════

@app.route('/api/contact', methods=['GET'])
def list_contact():
    return jsonify(load_json('contact.json'))

@app.route('/api/contact', methods=['PUT'])
def update_contact():
    if not isinstance(request.json, list):
        return jsonify({"error": "Expected a JSON array"}), 400
    atomic_write_json('contact.json', request.json)
    return jsonify({"status": "updated"})

@app.route('/api/contact', methods=['POST'])
def add_contact():
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    contacts = load_json('contact.json')
    contacts.append(request.json)
    atomic_write_json('contact.json', contacts)
    return jsonify(request.json), 201

@app.route('/api/contact/<int:index>', methods=['PUT'])
def update_contact_item(index):
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    contacts = load_json('contact.json')
    if index < 0 or index >= len(contacts):
        return jsonify({"error": "Index out of range"}), 404
    contacts[index].update(request.json)
    atomic_write_json('contact.json', contacts)
    return jsonify(contacts[index])

@app.route('/api/contact/<int:index>', methods=['DELETE'])
def delete_contact(index):
    contacts = load_json('contact.json')
    if index < 0 or index >= len(contacts):
        return jsonify({"error": "Index out of range"}), 404
    contacts.pop(index)
    atomic_write_json('contact.json', contacts)
    return jsonify({"status": "deleted"})


# ═══════════════════════════════════════════
# Music CRUD
# ═══════════════════════════════════════════

@app.route('/api/music', methods=['GET'])
def list_music():
    return jsonify(load_json('music.json'))

@app.route('/api/music', methods=['POST'])
def create_music():
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    music = load_json('music.json')
    item = request.json
    item['id'] = max((m['id'] for m in music), default=0) + 1
    music.append(item)
    atomic_write_json('music.json', music)
    return jsonify(item), 201

@app.route('/api/music/<int:id>', methods=['PUT'])
def update_music(id):
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    music = load_json('music.json')
    for i, m in enumerate(music):
        if m['id'] == id:
            music[i].update(request.json)
            music[i]['id'] = id
            atomic_write_json('music.json', music)
            return jsonify(music[i])
    return jsonify({"error": "Not found"}), 404

@app.route('/api/music/upload', methods=['POST'])
def upload_music():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    if not file.filename or not file.filename.lower().endswith('.mp3'):
        return jsonify({"error": "Only .mp3 files"}), 400
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'mp3'
    filename = f"{uuid.uuid4().hex[:8]}.{ext}"
    music_dir = os.path.join(BASE_DIR, 'music')
    os.makedirs(music_dir, exist_ok=True)
    file.save(os.path.join(music_dir, filename))
    return jsonify({"filename": filename, "status": "uploaded"}), 201

@app.route('/api/music/<int:id>', methods=['DELETE'])
def delete_music(id):
    music = load_json('music.json')
    for m in music:
        if m['id'] == id:
            fn = m.get('filename', '')
            if fn:
                mp3_path = os.path.join(BASE_DIR, 'music', os.path.basename(fn))
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
    music = [m for m in music if m['id'] != id]
    atomic_write_json('music.json', music)
    return jsonify({"status": "deleted"})


# ═══════════════════════════════════════════
# Git Integration
# ═══════════════════════════════════════════

def _run_git(args):
    return subprocess.run(['git'] + args, cwd=BASE_DIR, capture_output=True, text=True, encoding='utf-8')

@app.route('/api/git/status', methods=['GET'])
def git_status():
    r = _run_git(['status', '--short'])
    diff = _run_git(['diff', '--stat'])
    branch = _run_git(['branch', '--show-current'])
    return jsonify({
        "branch": branch.stdout.strip(),
        "files": r.stdout.strip().split('\n') if r.stdout.strip() else [],
        "diffStat": diff.stdout.strip(),
        "clean": r.stdout.strip() == ''
    })

@app.route('/api/git/commit', methods=['POST'])
def git_commit():
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    msg = request.json.get('message', '').strip()
    if not msg:
        return jsonify({"error": "Commit message required"}), 400
    add_r = _run_git(['add', '-A'])
    if add_r.returncode != 0:
        return jsonify({"error": "git add failed: " + add_r.stderr.strip()}), 500
    r = _run_git(['commit', '-m', msg])
    if r.returncode != 0:
        return jsonify({"error": r.stderr.strip()}), 500
    return jsonify({"status": "success", "output": r.stdout.strip()})

@app.route('/api/git/revert', methods=['POST'])
def git_revert():
    # Auto-backup before destructive revert (include untracked files)
    _run_git(['stash', 'push', '--include-untracked', '-m', 'auto-backup-before-revert'])
    r = _run_git(['checkout', '.'])
    if r.returncode != 0:
        return jsonify({"error": "git checkout failed: " + r.stderr.strip()}), 500
    # Remove untracked files that checkout can't touch
    clean_r = _run_git(['clean', '-fd'])
    if clean_r.returncode != 0:
        return jsonify({"error": "git clean failed: " + clean_r.stderr.strip()}), 500
    return jsonify({"status": "reverted"})

@app.route('/api/git/diff', methods=['GET'])
def git_diff():
    unstaged = _run_git(['diff', '--color=never'])
    staged = _run_git(['diff', '--cached', '--color=never'])
    parts = []
    if staged.stdout.strip():
        parts.append('--- Staged (即将提交) ---\n' + staged.stdout)
    if unstaged.stdout.strip():
        if parts:
            parts.append('')
        parts.append('--- Unstaged (未暂存) ---\n' + unstaged.stdout)
    diff_text = '\n'.join(parts).strip() or '(no changes)'
    return jsonify({"diff": diff_text})

@app.route('/api/git/push', methods=['POST'])
def git_push():
    # Fetch remote first
    fetch_r = _run_git(['fetch'])
    if fetch_r.returncode != 0:
        return jsonify({"error": "git fetch failed: " + fetch_r.stderr.strip()}), 500
    status = _run_git(['status', '-sb']).stdout
    if 'behind' in status:
        return jsonify({"error": "检测到远程仓库有更新，请先通过终端执行 git pull 解决潜在冲突。"}), 409
    r = _run_git(['push'])
    if r.returncode != 0:
        return jsonify({"error": r.stderr.strip()}), 500
    return jsonify({"status": "success", "output": r.stdout.strip()})


# ═══════════════════════════════════════════
# Serve static files for index.html preview
# ═══════════════════════════════════════════

@app.route('/data/<path:filename>')
def serve_data(filename):
    return send_from_directory(DATA_DIR, filename)

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory(IMAGES_DIR, filename)

@app.route('/index.html')
def serve_index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/essays/<path:filename>')
def serve_essay(filename):
    return send_from_directory(ESSAYS_DIR, filename)

@app.route('/music/<path:filename>')
def serve_music(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'music'), filename)

@app.route('/rss.xml')
def serve_rss():
    return send_from_directory(BASE_DIR, 'rss.xml')

@app.route('/sitemap.xml')
def serve_sitemap():
    return send_from_directory(BASE_DIR, 'sitemap.xml')

@app.route('/archive.html')
def serve_archive():
    return send_from_directory(BASE_DIR, 'archive.html')


if __name__ == '__main__':
    print("  Admin  → http://127.0.0.1:5000")
    print("  网站预览 → http://127.0.0.1:5000/index.html")
    app.run(host='127.0.0.1', port=5000, debug=True)
