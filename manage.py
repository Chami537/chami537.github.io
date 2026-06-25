#!/usr/bin/env python3
"""Chami 个人网站管理工具 — 微型 SSG + 无头 CMS"""

import os
import json
import re
import subprocess
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
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
        return [] if name != 'friends.json' else []
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
        raise e


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
    work = load_json('work.json')
    item = request.json
    item['id'] = max((w['id'] for w in work), default=0) + 1
    work.append(item)
    atomic_write_json('work.json', work)
    return jsonify(item), 201

@app.route('/api/work/<int:id>', methods=['PUT'])
def update_work(id):
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

ESSAY_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Chami</title>
<meta name="description" content="{excerpt}">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⻖</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans+SC:wght@400;500;700;900&display=swap">
<style>

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

:root {{
  --bg: #fafaf8;
  --fg: #111;
  --c3: #ffb800;
  --line: #e0dcd5;
  --muted: #999;
}}

body {{
  font-family: 'Inter', 'Noto Sans SC', sans-serif;
  background: var(--bg);
  color: var(--fg);
  -webkit-font-smoothing: antialiased;
}}

.progress {{
  position: fixed; top: 0; left: 0; height: 2px;
  background: var(--c3); z-index: 999; width: 0; will-change: width;
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
  font-size: 17px; font-weight: 800; letter-spacing: -0.01em;
  text-decoration: none; color: var(--fg);
}}
nav .back {{
  font-size: 12px; font-weight: 600; letter-spacing: .08em;
  color: var(--muted); text-decoration: none;
  display: flex; align-items: center; gap: 6px; transition: color .2s;
}}
nav .back:hover {{ color: var(--c3); }}
nav .back .arr {{ transition: transform .2s ease; display: inline-block; }}
nav .back:hover .arr {{ transform: translateX(-4px); }}

.reading {{
  max-width: 680px;
  margin: 0 auto;
  padding: 120px 48px 100px;
}}

.section-tag {{
  display: inline-block; font-size: 12px; font-weight: 700;
  letter-spacing: 2px; text-transform: uppercase;
  color: var(--c3); border-left: 2px solid var(--c3);
  padding-left: 10px; margin-bottom: 24px;
}}

.essay-title {{
  font-size: clamp(40px, 7vw, 64px);
  font-weight: 900;
  line-height: 1.0;
  letter-spacing: -0.025em;
  margin-bottom: 16px;
}}

.essay-epigraph {{
  font-size: 15px;
  color: var(--muted);
  font-style: italic;
  font-weight: 400;
  margin-bottom: 28px;
}}

.essay-meta {{
  display: flex; gap: 16px; align-items: center;
  font-size: 12px; color: var(--muted); font-weight: 500;
  margin-bottom: 40px;
}}
.essay-meta .dot {{ color: #ddd; }}

.essay-divider {{
  border: none; border-top: 1px solid var(--line); margin-bottom: 40px;
}}

.essay-lede {{
  font-size: 19px;
  color: #555;
  line-height: 1.75;
  font-weight: 400;
  margin-bottom: 0;
}}

.essay-body p {{
  font-size: 17px;
  line-height: 1.9;
  color: var(--fg);
  margin-top: 1.6em;
}}

.essay-body h2 {{
  font-size: 21px; font-weight: 700;
  margin-top: 2.5em; margin-bottom: .4em;
  letter-spacing: -0.01em;
}}

.essay-body blockquote {{
  border-left: 2px solid var(--c3);
  padding-left: 20px;
  margin: 2em 0;
  color: #555;
  font-size: 16px;
  line-height: 1.85;
  font-style: italic;
}}

.essay-end {{
  margin-top: 64px; padding-top: 32px;
  border-top: 1px solid var(--line);
  display: flex; justify-content: space-between; align-items: flex-end;
}}

.essay-end .back-link {{
  font-size: 13px; font-weight: 600; color: var(--muted);
  text-decoration: none; display: flex; align-items: center; gap: 6px;
  transition: color .2s;
}}
.essay-end .back-link:hover {{ color: var(--c3); }}
.essay-end .back-link .arr {{ transition: transform .2s; display: inline-block; }}
.essay-end .back-link:hover .arr {{ transform: translateX(-4px); }}

.essay-end .next-link {{
  font-size: 13px; font-weight: 600; color: var(--muted);
  text-decoration: none; display: flex; flex-direction: column;
  align-items: flex-end; gap: 4px; transition: color .2s;
}}
.essay-end .next-link:hover {{ color: var(--fg); }}
.essay-end .next-label {{
  font-size: 10px; font-weight: 700; letter-spacing: .12em;
  text-transform: uppercase; color: #ccc;
}}
.essay-end .next-title {{
  display: flex; align-items: center; gap: 6px;
}}
.essay-end .next-arr {{ transition: transform .2s; display: inline-block; }}
.essay-end .next-link:hover .next-arr {{ transform: translateX(4px); }}

footer {{
  padding: 60px 0; text-align: center; font-size: 11px; color: #bbb;
  letter-spacing: .04em; border-top: 1px solid var(--line);
}}
.friends {{ margin-bottom: 20px; }}
.friends-label {{
  font-size: 10px; font-weight: 700; letter-spacing: .12em;
  text-transform: uppercase; color: #ccc; margin-bottom: 8px;
}}
.friends a {{
  font-size: 11px; color: #bbb; text-decoration: none;
  letter-spacing: .04em; transition: color .2s;
}}
.friends a:hover {{ color: var(--fg); }}
.friends .sep {{ color: #ddd; margin: 0 8px; }}

@media (max-width: 768px) {{
  nav {{ padding: 0 16px; }}
  .reading {{ padding: 100px 24px 80px; }}
}}

</style>
</head>
<body>

<div class="progress"></div>

<nav>
  <div class="inner">
    <a href="/" class="logo">Chami</a>
    <a href="/#essays" class="back">
      <span class="arr">←</span>
      <span>Essays</span>
    </a>
  </div>
</nav>

<main class="reading">

  <div class="section-tag">ESSAYS</div>

  <h1 class="essay-title">{title}</h1>

  <p class="essay-epigraph">{epigraph}</p>

  <div class="essay-meta">
    <span>{tag}</span>
    <span class="dot">·</span>
    <span>{date_display}</span>
    <span class="dot">·</span>
    <span>{read_time} min read</span>
  </div>

  <hr class="essay-divider">

  <p class="essay-lede">{lede}</p>

  <div class="essay-body">

<!-- CONTENT_START -->

{body_html}

<!-- CONTENT_END -->

  </div>

  <div class="essay-end">
    <a href="/#essays" class="back-link">
      <span class="arr">←</span>
      <span>返回随笔</span>
    </a>
    {next_nav}
  </div>

</main>

<footer>
  <div class="friends" id="friends-container">
    <div class="friends-label">FOLLOW</div>
  </div>
  &copy; <script>document.write(new Date().getFullYear())</script> Chami
</footer>

<script>
const bar = document.querySelector('.progress');
addEventListener('scroll', () => {{
  const h = document.documentElement.scrollHeight - innerHeight;
  if (h > 0) bar.style.width = (scrollY / h * 100) + '%';
}});

// Render friends
(async () => {{
  try {{
    const friends = await fetch('/data/friends.json?v=' + Date.now()).then(r => r.json());
    const container = document.getElementById('friends-container');
    let html = '<div class="friends-label">FOLLOW</div>';
    friends.forEach((f, i) => {{
      html += '<a href="' + f.url + '">' + f.name + '</a>';
      if (i < friends.length - 1) html += '<span class="sep">·</span>';
    }});
    container.innerHTML = html;
  }} catch(e) {{}}
}})();
</script>

</body>
</html>'''


def _parse_date(date_str):
    """'2025-07' → '2025年7月'"""
    parts = date_str.split('-')
    if len(parts) == 2:
        return f"{parts[0]}年{int(parts[1])}月"
    return date_str


def _build_next_nav(essays, current_slug):
    """Build next-essay navigation link."""
    idx = next((i for i, e in enumerate(essays) if e['slug'] == current_slug), -1)
    if idx >= 0 and idx + 1 < len(essays):
        next_e = essays[idx + 1]
        return f'''<a href="{next_e['slug']}.html" class="next-link">
      <span class="next-label">下一篇</span>
      <div class="next-title">
        <span>{next_e['title']}</span>
        <span class="next-arr">→</span>
      </div>
    </a>'''
    return ''


@app.route('/api/essays', methods=['GET'])
def list_essays():
    return jsonify(load_json('essays.json'))

@app.route('/api/essays', methods=['POST'])
def create_essay():
    essays = load_json('essays.json')
    item = request.json
    slug = item.get('slug', '')
    if not slug or not re.match(r'^[a-z0-9-]+$', slug):
        return jsonify({"error": "slug 只能包含小写字母、数字和连字符"}), 400
    if any(e['slug'] == slug for e in essays):
        return jsonify({"error": "slug 已存在"}), 409

    essays.append(item)
    atomic_write_json('essays.json', essays)

    # Generate HTML file
    date_display = _parse_date(item.get('date', ''))
    next_nav = _build_next_nav(essays, slug)
    html = ESSAY_TEMPLATE.format(
        title=item.get('title', ''),
        excerpt=item.get('excerpt', ''),
        epigraph=item.get('epigraph', ''),
        tag=item.get('tag', ''),
        date_display=date_display,
        read_time=item.get('readTime', 4),
        lede='',
        body_html='',
        next_nav=next_nav,
    )
    os.makedirs(ESSAYS_DIR, exist_ok=True)
    with open(os.path.join(ESSAYS_DIR, f"{slug}.html"), 'w', encoding='utf-8') as f:
        f.write(html)

    return jsonify(item), 201

@app.route('/api/essays/<slug>', methods=['PUT'])
def update_essay_meta(slug):
    essays = load_json('essays.json')
    for i, e in enumerate(essays):
        if e['slug'] == slug:
            essays[i].update(request.json)
            essays[i]['slug'] = slug
            atomic_write_json('essays.json', essays)
            return jsonify(essays[i])
    return jsonify({"error": "Not found"}), 404

@app.route('/api/essays/<slug>', methods=['DELETE'])
def delete_essay(slug):
    essays = load_json('essays.json')
    essays = [e for e in essays if e['slug'] != slug]
    atomic_write_json('essays.json', essays)
    html_file = os.path.join(ESSAYS_DIR, f"{slug}.html")
    if os.path.exists(html_file):
        os.remove(html_file)
    return jsonify({"status": "deleted"})

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
    # Extract HTML content between anchors
    pattern = r'<!-- CONTENT_START -->\n(.*?)\n\s*<!-- CONTENT_END -->'
    match = re.search(pattern, full_html, flags=re.DOTALL)
    content = match.group(1).strip() if match else ''
    return jsonify({"content": content, "format": "html"})

@app.route('/api/essays/<slug>/content', methods=['PUT'])
def update_essay_content(slug):
    md_content = request.json.get('content', '')
    html_content = md_to_html(md_content, extensions=['extra', 'fenced_code'])

    html_file = os.path.join(ESSAYS_DIR, f"{slug}.html")
    if not os.path.exists(html_file):
        return jsonify({"error": "Essay HTML file not found"}), 404

    with open(html_file, 'r', encoding='utf-8') as f:
        full_html = f.read()

    # Inject rendered HTML between anchors, and store raw MD in a comment
    pattern = r'(<!-- CONTENT_START -->).*?(<!-- CONTENT_END -->)'
    injection = f'\\1\n{html_content}\n<!-- RAW_MD\n{md_content}\nRAW_MD -->\n\\2'
    new_html = re.sub(pattern, injection, full_html, flags=re.DOTALL)

    if new_html == full_html:
        return jsonify({"error": "Content anchors not found in HTML file"}), 500

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(new_html)

    return jsonify({"status": "success", "message": f"{slug}.html updated"})

@app.route('/api/essays/<slug>/html', methods=['GET'])
def preview_essay_html(slug):
    """Preview Markdown → HTML (no save)"""
    md_content = request.args.get('md', '')
    html_content = md_to_html(md_content, extensions=['extra', 'fenced_code'])
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
    atomic_write_json('photos.json', request.json)
    return jsonify({"status": "reordered"})

@app.route('/api/photos/<filename>', methods=['DELETE'])
def delete_photo(filename):
    photos = load_json('photos.json')
    photos = [p for p in photos if p['filename'] != filename]
    atomic_write_json('photos.json', photos)
    # Remove image files
    for subdir in ['', 'lg', 'md', 'sm']:
        path = os.path.join(IMAGES_DIR, subdir, filename)
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

    filename = secure_filename(file.filename)
    img = Image.open(file.stream)

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
    friends = load_json('friends.json')
    friends.append(request.json)
    atomic_write_json('friends.json', friends)
    return jsonify(request.json), 201

@app.route('/api/friends/<int:index>', methods=['PUT'])
def update_friend(index):
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
# Git Integration
# ═══════════════════════════════════════════

def _run_git(args):
    return subprocess.run(['git'] + args, cwd=BASE_DIR, capture_output=True, text=True)

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
    msg = request.json.get('message', '').strip()
    if not msg:
        return jsonify({"error": "Commit message required"}), 400
    _run_git(['add', '-A'])
    r = _run_git(['commit', '-m', msg])
    if r.returncode != 0:
        return jsonify({"error": r.stderr.strip()}), 500
    return jsonify({"status": "success", "output": r.stdout.strip()})

@app.route('/api/git/revert', methods=['POST'])
def git_revert():
    r = _run_git(['checkout', '.'])
    return jsonify({"status": "reverted"})

@app.route('/api/git/push', methods=['POST'])
def git_push():
    # Fetch remote first
    _run_git(['fetch'])
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


if __name__ == '__main__':
    print("  Chami Site Admin → http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
