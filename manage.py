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
MD_DIR = os.path.join(BASE_DIR, 'md')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MD_DIR, exist_ok=True)

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
    except Exception:
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
    """Generate archive.html — timeline grouped by year, with tag filter + search."""
    essays = load_json('essays.json')
    essays_sorted = sorted(essays, key=lambda e: e.get('date', ''), reverse=True)
    essays_json = json.dumps(essays_sorted, ensure_ascii=False).replace('</', '<\\/')
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

/* Tag filter chips */
.essay-filter {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }}
.ef-chip {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  display: inline-block; padding: 3px 12px; border-radius: 20px;
  font-size: 11px; font-weight: 600; cursor: pointer;
  border: 1px solid var(--line); color: var(--muted);
  transition: all .15s; user-select: none;
}}
.ef-chip:hover {{ border-color: var(--c3); color: var(--c3); }}
.ef-chip.active {{ background: var(--c3); color: #fff; border-color: var(--c3); }}

/* Search */
.essay-search {{
  margin-bottom: 12px; position: relative;
}}
.essay-search input {{
  width: 100%; padding: 8px 14px 8px 34px;
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  font-size: 13px; color: var(--fg);
  background: var(--bg); border: 1px solid var(--line);
  border-radius: 8px; outline: none;
  transition: border-color .2s;
}}
.essay-search input:focus {{ border-color: var(--c3); }}
.essay-search input::placeholder {{ color: #bbb; }}
.essay-search::before {{
  content: "🔍"; position: absolute;
  left: 10px; top: 50%; transform: translateY(-50%);
  font-size: 13px; pointer-events: none;
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

/* Back link */
.back-link {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  font-size: 13px; font-weight: 600; color: var(--muted);
  text-decoration: none; display: flex; align-items: center; justify-content: center;
  gap: 6px; margin-top: 48px; transition: color .2s;
}}
.back-link:hover {{ color: var(--c3); }}
.back-link .arr {{ transition: transform .2s; display: inline-block; }}
.back-link:hover .arr {{ transform: translateX(-4px); }}

/* Friends */
.friends {{ margin-bottom: 20px; display: flex; flex-wrap: wrap; align-items: baseline; justify-content: center; }}
.friends-label {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  font-size: 10px; font-weight: 700; letter-spacing: .12em;
  text-transform: uppercase; color: #ccc; margin-bottom: 8px;
  width: 100%;
}}
.friends a {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  font-size: 11px; color: #bbb; text-decoration: none;
  letter-spacing: .04em; transition: color .2s;
  line-height: 2;
}}
.friends a:hover {{ color: var(--fg); }}
.friends a + a::before {{ content: '·'; margin: 0 8px; color: var(--muted); }}

.map-header {{ text-align: center; }}

.custom-marker {{ background: none !important; border: none !important; }}
.custom-marker .marker-dot {{
  width: 12px; height: 12px;
  background-color: #0066ff;
  border: 2px solid #fff;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0,0,0,0.3);
  transition: transform 0.2s;
}}
.custom-marker:hover .marker-dot {{ transform: scale(1.5); }}

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
  .ef-chip {{ font-size: 10px; padding: 2px 10px; }}
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
    <a href="/index.html" class="logo">Chami</a>
    <button class="theme-btn" onclick="toggleTheme()" title="切换主题" id="theme-btn">🌙</button>
  </div>
</nav>

<main class="archive-wrap">
  <div class="archive-header">
    <h1>Archive</h1>
    <p class="sub">共 {total} 篇随笔</p>
  </div>

  <div class="essay-search"><input type="text" id="archive-search" placeholder="搜索随笔..." oninput="onArchiveSearch(this.value)"></div>
  <div id="archive-tag-filter" class="essay-filter"></div>
  <div id="archive-entries"></div>

  <a href="/index.html" class="back-link">
    <span class="arr">←</span>
    <span>返回主页</span>
  </a>
</main>

<footer>
  <div class="friends" id="friends-container">
    <div class="friends-label">FRIEND</div>
  </div>
  &copy; <script>document.write(new Date().getFullYear())</script> Chami. All rights reserved.
</footer>

<script>
var _archiveEssays = {essays_json};
var _archiveFilter = '';
var _archiveSearchTimer = null;

// Theme init
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

var MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

function monthDay(dateStr) {{
  try {{
    var dp = (dateStr.indexOf(' ') !== -1 ? dateStr.split(' ')[0] : dateStr).split('-');
    if (dp.length >= 3 && dp[2]) {{
      var mi = +dp[1] - 1;
      if (mi >= 0 && mi < 12) return MONTHS[mi] + ' ' + (+dp[2]);
    }}
  }} catch(e) {{}}
  return '';
}}

function renderArchiveEntries(data) {{
  // Group by year
  var years = {{}};
  data.forEach(function(e) {{
    var dateStr = e.date || '';
    var year = dateStr.length >= 4 ? dateStr.slice(0, 4) : 'Unknown';
    if (!years[year]) years[year] = [];
    years[year].push(e);
  }});

  var yearKeys = Object.keys(years).sort().reverse();
  var html = '';
  yearKeys.forEach(function(year) {{
    html += '<div class="archive-year"><h2 class="archive-year-heading">' + year + '</h2>';
    years[year].forEach(function(e) {{
      var slug = e.slug.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      var title = e.title.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      var tag = (e.tag || '').replace(/, ?/g, ' · ').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      var md = monthDay(e.date);
      html += '<a href="essays/' + slug + '.html" class="archive-row">' +
        '<span class="archive-date">' + md + '</span>' +
        '<span class="archive-title">' + title + '</span>' +
        '<span class="archive-tag">' + tag + '</span>' +
        '</a>';
    }});
    html += '</div>';
  }});

  var container = document.getElementById('archive-entries');
  if (html) {{
    container.innerHTML = html;
  }} else {{
    container.innerHTML = '<p style="color:var(--muted);text-align:center;padding:60px 0;">没有匹配的随笔</p>';
  }}
}}

function buildTagFilter() {{
  var tags = new Set();
  _archiveEssays.forEach(function(e) {{
    (e.tag || '').split(/[,，]/).forEach(function(t) {{ t = t.trim(); if (t) tags.add(t); }});
  }});
  var html = '<span class="ef-chip' + (!_archiveFilter ? ' active' : '') + '" onclick="filterArchiveByTag(\\'\\')">全部</span>';
  tags.forEach(function(t) {{
    html += '<span class="ef-chip' + (_archiveFilter === t ? ' active' : '') + '" data-tag="' + t.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;') + '" onclick="filterArchiveByTag(this.getAttribute(\\'data-tag\\'))">' + t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</span>';
  }});
  document.getElementById('archive-tag-filter').innerHTML = html;
}}

function filterArchiveByTag(tag) {{
  _archiveFilter = tag;
  buildTagFilter();
  applyFilters();
}}

function onArchiveSearch(query) {{
  clearTimeout(_archiveSearchTimer);
  _archiveSearchTimer = setTimeout(function() {{
    applyFilters(query.toLowerCase().trim());
  }}, 100);
}}

function applyFilters(searchQuery) {{
  var filtered = _archiveEssays;
  if (_archiveFilter) {{
    filtered = filtered.filter(function(e) {{
      return (e.tag || '').split(/[,，]/).some(function(t) {{ return t.trim() === _archiveFilter; }});
    }});
  }}
  if (searchQuery) {{
    filtered = filtered.filter(function(e) {{
      return (e.title || '').toLowerCase().indexOf(searchQuery) !== -1 ||
             (e.excerpt || '').toLowerCase().indexOf(searchQuery) !== -1;
    }});
  }}
  renderArchiveEntries(filtered);
}}

// Initial render
buildTagFilter();
renderArchiveEntries(_archiveEssays);

// Render friends
(function() {{
  try {{
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/data/friends.json?v=' + Date.now(), true);
    xhr.onload = function() {{
      if (xhr.status < 200 || xhr.status >= 300) return;
      var friends = JSON.parse(xhr.responseText);
      var container = document.getElementById('friends-container');
      var html = '<div class="friends-label">FRIEND</div>';
      friends.forEach(function(f) {{
        var escUrl = f.url.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        var escName = f.name.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        if (/^https?:\\/\\//i.test(f.url)) {{
          html += '<a href="' + escUrl + '">' + escName + '</a>';
        }} else {{
          html += '<span>' + escName + '</span>';
        }}
      }});
      container.innerHTML = html;
    }};
    xhr.send();
  }} catch(e) {{}}
}})();
</script>

</body>
</html>'''
    with open(os.path.join(BASE_DIR, 'archive.html'), 'w', encoding='utf-8') as f:
        f.write(archive)


def _generate_map():
    """Generate map.html — Leaflet map with GPS-tagged photos."""
    photos = load_json('photos.json')
    gps_photos = [p for p in photos if p.get('exif', {}).get('gps')]
    photos_json = json.dumps(gps_photos, ensure_ascii=False).replace('</', '<\\/')
    total = len(gps_photos)
    center_lat, center_lng = 22.5431, 113.9579  # default: Shenzhen
    if gps_photos:
        lats = [p['exif']['gps']['lat'] for p in gps_photos]
        lngs = [p['exif']['gps']['lng'] for p in gps_photos]
        center_lat = sum(lats) / len(lats)
        center_lng = sum(lngs) / len(lngs)

    map_html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Map — Chami</title>
<meta name="description" content="Chami 的摄影足迹 · {total} 个地点">
<meta property="og:title" content="Map — Chami">
<meta property="og:description" content="Chami 的摄影足迹 · {total} 个地点">
<meta property="og:type" content="website">
<meta property="og:image" content="https://chami537.github.io/images/avatar.jpg">
<meta property="og:site_name" content="Chami">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="images/avatar.jpg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400;1,700&family=Noto+Serif+SC:wght@400;700&family=Noto+Sans+SC:wght@400;500;700;900&display=swap">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
:root {{
  --bg: #fafaf8; --fg: #111; --c4: #00c853; --line: #e0dcd5; --muted: #999;
}}
html.dark {{ --bg: #1a1a1c; --fg: #e8e6e3; --line: #2e2e30; --muted: #888; }}
html.dark nav {{ background: rgba(26,26,28,0.88); }}

body {{
  font-family: 'Inter', 'Noto Sans SC', sans-serif;
  background: var(--bg); color: var(--fg);
  -webkit-font-smoothing: antialiased;
}}

nav {{
  position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
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

.map-header {{
  max-width: 1200px; margin: 0 auto; padding: 120px 48px 40px;
}}
.map-header h1 {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  font-size: clamp(40px, 7vw, 64px);
  font-weight: 900; line-height: 1.0;
  letter-spacing: -0.025em; margin-bottom: 12px;
}}
.map-header .sub {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  font-size: 15px; color: var(--muted);
}}

#map {{
  width: 100%; max-width: 1000px; height: 65vh;
  margin: 40px auto; border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  z-index: 1;
}}
.map-wrap {{
  padding: 0 48px 60px;
}}

/* Dark mode tile inversion */
html.dark .leaflet-layer,
html.dark .leaflet-control-zoom-in,
html.dark .leaflet-control-zoom-out,
html.dark .leaflet-control-attribution {{
  filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%);
}}
html.dark .leaflet-marker-icon,
html.dark .leaflet-marker-shadow,
html.dark .leaflet-popup {{
  filter: none;
}}

.leaflet-popup-content {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  font-size: 12px; line-height: 1.6;
}}
.leaflet-popup-content img {{
  width: 100%; max-height: 180px; object-fit: cover;
  border-radius: 2px; margin-bottom: 6px;
}}
.leaflet-popup-content .popup-exif {{
  color: #888; font-size: 10px;
}}

.map-header {{ text-align: center; }}

.custom-marker {{ background: none !important; border: none !important; }}
.custom-marker .marker-dot {{
  width: 12px; height: 12px;
  background-color: #0066ff;
  border: 2px solid #fff;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0,0,0,0.3);
  transition: transform 0.2s;
}}
.custom-marker:hover .marker-dot {{ transform: scale(1.5); }}

footer {{
  font-family: 'Lora', 'Inter', 'Noto Serif SC', serif;
  padding: 60px 0; text-align: center; font-size: 11px; color: #bbb;
  letter-spacing: .04em; border-top: 1px solid var(--line);
}}

@media (max-width: 768px) {{
  nav {{ padding: 0 16px; }}
  .map-header {{ padding: 100px 24px 24px; }}
  .map-wrap {{ padding: 0 16px 40px; }}
  #map {{ height: 55vh; }}
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
    <a href="/index.html" class="logo">Chami</a>
    <button class="theme-btn" onclick="toggleTheme()" title="切换主题" id="theme-btn">🌙</button>
  </div>
</nav>

<div class="map-header">
  <h1>Footprints</h1>
  <p class="sub">Places I've been, routes I've ridden, and moments captured. ({total} locations)</p>
</div>

<div class="map-wrap">
  <div id="map"></div>
</div>

<footer>
  &copy; <script>document.write(new Date().getFullYear())</script> Chami. All rights reserved.
</footer>

<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
var photos = {photos_json};

var map = L.map('map').setView([{center_lat}, {center_lng}], 13);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  maxZoom: 19, subdomains: 'abcd',
  attribution: '&copy; <a href="https://openstreetmap.org/copyright">OSM</a> &copy; CARTO'
}}).addTo(map);

// Add photo markers
photos.forEach(function(p) {{
  var gps = p.exif.gps;
  var ex = p.exif;
  var popupHtml = '<img src="images/md/' + p.filename.replace(/&/g,'&amp;').replace(/"/g,'&quot;') + '">' +
    '<b>' + (ex.model || ex.camera || 'Photo').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</b>';
  var parts = [];
  if (ex.focal) parts.push(ex.focal.replace(/&/g,'&amp;').replace(/</g,'&lt;'));
  if (ex.aperture) parts.push(ex.aperture.replace(/&/g,'&amp;').replace(/</g,'&lt;'));
  if (ex.shutter) parts.push(ex.shutter.replace(/&/g,'&amp;').replace(/</g,'&lt;'));
  if (ex.iso) parts.push('ISO ' + String(ex.iso).replace(/&/g,'&amp;').replace(/</g,'&lt;'));
  if (parts.length) popupHtml += '<br><span class="popup-exif">' + parts.join(' · ') + '</span>';
  popupHtml += '<br><span class="popup-exif">×' + Math.abs(gps.lat).toFixed(4) + '°' + (gps.lat >= 0 ? 'N' : 'S') + ', ' + Math.abs(gps.lng).toFixed(4) + '°' + (gps.lng >= 0 ? 'E' : 'W') + '</span>';

  var icon = L.divIcon({{className: 'custom-marker', html: '<div class="marker-dot"></div>', iconSize: [16, 16], iconAnchor: [8, 8]}});
  L.marker([gps.lat, gps.lng], {{icon: icon}}).addTo(map).bindPopup(popupHtml);
}});

// Fit bounds if multiple markers
if (photos.length > 1) {{
  var bounds = photos.map(function(p) {{ return [p.exif.gps.lat, p.exif.gps.lng]; }});
  map.fitBounds(bounds, {{ padding: [40, 40] }});
  }}

  // Load GPX tracks
  (function() {{
    var colors = ['#0066ff', '#ff4d4d', '#00c853', '#ffb800', '#9c27b0'];
    var ci = 0;
    fetch('/data/tracks.json?v=' + Date.now()).then(function(r) {{ return r.ok ? r.json() : []; }}).then(function(tracks) {{
      tracks.forEach(function(t) {{
        fetch('/tracks/' + t.file).then(function(r) {{ return r.text(); }}).then(function(xml) {{
          var doc = new DOMParser().parseFromString(xml, 'text/xml');
          var pts = [];
          doc.querySelectorAll('trkpt').forEach(function(pt) {{
            pts.push([parseFloat(pt.getAttribute('lat')), parseFloat(pt.getAttribute('lon'))]);
          }});
          if (pts.length > 1) {{
            L.polyline(pts, {{color: colors[ci % colors.length], weight: 3, opacity: 0.7, smoothFactor: 1}}).addTo(map);
            ci++;
          }}
        }}).catch(function() {{}});
      }});
    }}).catch(function() {{}});
  }})();
}}

// Theme toggle
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
    with open(os.path.join(BASE_DIR, 'map.html'), 'w', encoding='utf-8') as f:
        f.write(map_html)


def _generate_feeds():
    """Regenerate all auto-generated files: RSS, sitemap, archive, map."""
    _generate_rss()
    _generate_sitemap()
    _generate_archive()
    _generate_map()


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
    tag_nav_json = _build_tag_nav_json(essays, slug)
    tag_raw = item.get('tag', '')
    tag_display = tag_raw.replace(', ', ' · ').replace(',', ' · ')
    og_image = _extract_first_image(item.get('body', '') or item.get('content', ''))
    html = _load_essay_template().format(
        title=_fe(item.get('title', '')),
        excerpt=_fe(item.get('excerpt', '')),
        epigraph=_fe(item.get('epigraph', '')),
        tag=_fe(tag_display),
        date_display=_fe(date_display),
        read_time=read_time,
        body_html='',
        prev_nav=(prev_nav),
        next_nav=(next_nav),
        tag_nav_json=tag_nav_json,
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
            new_slug = request.json.get('slug', slug)
            if not new_slug or not re.match(r'^[a-z0-9-]+$', new_slug):
                return jsonify({"error": "slug 只能包含小写字母、数字和连字符"}), 400
            if new_slug != slug and any(e2['slug'] == new_slug for e2 in essays):
                return jsonify({"error": "slug 已存在"}), 409
            essays[i].update(request.json)
            essays[i]['slug'] = new_slug
            atomic_write_json('essays.json', essays)
            # Rename HTML + MD files if slug changed
            if new_slug != slug:
                old_html = os.path.join(ESSAYS_DIR, f"{slug}.html")
                new_html = os.path.join(ESSAYS_DIR, f"{new_slug}.html")
                old_md = os.path.join(MD_DIR, f"{slug}.md")
                new_md = os.path.join(MD_DIR, f"{new_slug}.md")
                if os.path.exists(old_html):
                    os.replace(old_html, new_html)
                if os.path.exists(old_md):
                    os.replace(old_md, new_md)
            # Tag/order changes affect all sibling nav links — always re-sync all
            for e2 in essays:
                _sync_essay_html(e2)
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

@app.route('/api/essays/<slug>', methods=['DELETE'])
def delete_essay(slug):
    essays = load_json('essays.json')
    target = next((e for e in essays if e['slug'] == slug), None)
    title_folder = target.get('title', slug) if target else slug
    title_folder = title_folder.replace('/', '_').replace('\\', '_')
    essays = [e for e in essays if e['slug'] != slug]
    atomic_write_json('essays.json', essays)
    html_file = os.path.join(ESSAYS_DIR, f"{slug}.html")
    if os.path.exists(html_file):
        os.remove(html_file)
    md_file = os.path.join(MD_DIR, f"{slug}.md")
    if os.path.exists(md_file):
        os.remove(md_file)
    img_dir = os.path.join(IMAGES_DIR, 'essays', title_folder)
    if os.path.exists(img_dir):
        import shutil
        shutil.rmtree(img_dir)
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
    # 优先读 .md 文件
    md_file = os.path.join(MD_DIR, f"{slug}.md")
    if os.path.exists(md_file):
        with open(md_file, 'r', encoding='utf-8') as f:
            return jsonify({"content": f.read(), "format": "markdown"})

    # Fallback: 从 HTML 注释提取（兼容旧格式）
    html_file = os.path.join(ESSAYS_DIR, f"{slug}.html")
    if not os.path.exists(html_file):
        return jsonify({"error": "Not found"}), 404
    with open(html_file, 'r', encoding='utf-8') as f:
        full_html = f.read()
    md_match = re.search(r'<!-- RAW_MD\n(.*)\nRAW_MD -->', full_html, flags=re.DOTALL)
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
    slug = request.form.get('slug', '') or request.args.get('slug', '')
    if slug:
        essays = load_json('essays.json')
        essay = next((e for e in essays if e.get('slug') == slug), None)
        folder = essay.get('title', slug) if essay else slug
        folder = folder.replace('/', '_').replace('\\', '_')
        img_dir = os.path.join(BASE_DIR, 'images', 'essays', folder)
        url = f"/images/essays/{folder}/{filename}"
    else:
        img_dir = os.path.join(BASE_DIR, 'images', 'essays')
        url = f"/images/essays/{filename}"
    os.makedirs(img_dir, exist_ok=True)
    file.save(os.path.join(img_dir, filename))
    return jsonify({"url": url, "status": "uploaded"}), 201

@app.route('/api/essays/<slug>/html', methods=['GET', 'POST'])
def preview_essay_html(slug):
    """Preview Markdown → HTML (no save). `slug` from URL path — required by Flask routing."""
    if request.method == 'POST' and not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    md_content = request.args.get('md', '') if request.method == 'GET' else request.json.get('md', '')
    html_content = md_to_html(md_content, extensions=['extra', 'fenced_code', 'sane_lists', 'pymdownx.arithmatex'], extension_configs={'pymdownx.arithmatex': {'generic': True}})
    return jsonify({"html": html_content})


# ═══════════════════════════════════════════
# Photos CRUD + Upload
# ═══════════════════════════════════════════

@app.route('/api/photos', methods=['GET'])
def list_photos():
    return jsonify(load_json('photos.json'))

@app.route('/api/photos', methods=['PUT'])
def reorder_photos():
    """Replace entire photo array (for reordering). Validates no entries lost."""
    if not isinstance(request.json, list):
        return jsonify({"error": "Expected a JSON array"}), 400
    new_data = request.json
    existing = load_json('photos.json')
    existing_fns = {p['filename'] for p in existing}
    new_fns = {p.get('filename', '') for p in new_data}
    lost = existing_fns - new_fns
    if lost:
        return jsonify({"error": f"Refusing to drop {len(lost)} existing photos: {', '.join(sorted(lost))}"}), 409
    atomic_write_json('photos.json', new_data)
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
    raw_path = os.path.join(BASE_DIR, 'raw_photos', safe_name)
    if os.path.exists(raw_path):
        os.remove(raw_path)
    return jsonify({"status": "deleted"})

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

    # Extract EXIF (use _getexif() to read nested IFD sub-tags for aperture/shutter/ISO)
    exif_data = {}
    exif = img._getexif()
    if exif:
        exif_tags = {ExifTags.TAGS.get(k, k): str(v) for k, v in exif.items()}
        if 'Make' in exif_tags:
            exif_data['camera'] = exif_tags['Make']
        if 'Model' in exif_tags:
            exif_data['model'] = exif_tags['Model']
        if 'ExposureTime' in exif_tags:
            exif_data['shutter'] = _fmt_shutter(exif_tags['ExposureTime'])
        if 'FNumber' in exif_tags:
            exif_data['aperture'] = _fmt_aperture(exif_tags['FNumber'])
        if 'ISOSpeedRatings' in exif_tags:
            exif_data['iso'] = exif_tags['ISOSpeedRatings']
        if 'FocalLength' in exif_tags:
            exif_data['focal'] = _fmt_focal(exif_tags['FocalLength'])

        gps_data = _extract_gps(exif)
        if gps_data:
            exif_data['gps'] = gps_data

    # Generate thumbnails
    for size_name, max_w in [('lg', 1920), ('md', 800), ('sm', 400)]:
        thumb = img.copy()
        thumb.thumbnail((max_w, max_w), Image.LANCZOS)
        out_dir = os.path.join(IMAGES_DIR, size_name)
        os.makedirs(out_dir, exist_ok=True)
        thumb.save(os.path.join(out_dir, filename))

    # Save original to images/ and copy to raw_photos/
    img.save(os.path.join(IMAGES_DIR, filename))
    raw_dir = os.path.join(BASE_DIR, 'raw_photos')
    os.makedirs(raw_dir, exist_ok=True)
    img.save(os.path.join(raw_dir, filename))

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


@app.route('/tracks/<path:filename>')
def serve_tracks(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'tracks'), filename)

@app.route('/rss.xml')
def serve_rss():
    return send_from_directory(BASE_DIR, 'rss.xml')

@app.route('/sitemap.xml')
def serve_sitemap():
    return send_from_directory(BASE_DIR, 'sitemap.xml')

@app.route('/archive.html')
def serve_archive():
    return send_from_directory(BASE_DIR, 'archive.html')


@app.route('/map.html')
def serve_map():
    return send_from_directory(BASE_DIR, 'map.html')


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == 'build':
            print("Building static site...")
            essays = load_json('essays.json')
            for e in essays:
                _sync_essay_html(e)
                print(f"  ✓ essays/{e['slug']}.html")
            _generate_feeds()
            print()
            print(f"Done: {len(essays)} essays + archive + map + RSS + sitemap generated.")
        elif sys.argv[1] in ('process-images', 'sync-photos'):
            import sys; sys.path.insert(0, 'tools'); import process_images
            process_images.process_all_images()
        elif sys.argv[1] == 'set-gps':
            if len(sys.argv) < 5:
                print("Usage: python manage.py set-gps <filename> <lat> <lng>")
            else:
                _set_gps(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]))
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Usage: python manage.py [build|sync-photos|process-images|set-gps]")
    else:
        import webbrowser, threading
        print("  Admin  → http://127.0.0.1:5000")
        print("  网站预览 → http://127.0.0.1:5000/index.html")
        threading.Timer(0.5, lambda: (webbrowser.open('http://127.0.0.1:5000'), webbrowser.open('http://127.0.0.1:5000/index.html'))).start()
        app.run(host='127.0.0.1', port=5000, debug=False)
