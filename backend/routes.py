"""API routes for the Chami CMS — all /api/* CRUD endpoints."""

import os
import json
import re
import subprocess
import uuid
from datetime import datetime
from PIL import Image, ExifTags
from flask import request, jsonify

from backend.app import app
from backend.data import load_json, atomic_write_json, BASE_DIR, DATA_DIR
from backend.ssg import (
    _load_essay_template, _fe, _calc_read_time, _parse_date,
    _extract_first_image, _parse_tags, _build_nav,
    _build_tag_nav_json, _sync_essay_html, _html_to_md,
    _generate_feeds,
    _fmt_shutter, _fmt_aperture, _fmt_focal, _extract_gps,
    _set_gps, ESSAYS_DIR, MD_DIR, IMAGES_DIR,
)

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MD_DIR, exist_ok=True)


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

    # Re-sync the essay directly before the new one (appended at end — prev may gain next link)
    if len(essays) > 1:
        _sync_essay_html(essays[-2])
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
            # Only re-sync essays whose nav could have changed (share tags with updated essay)
            new_tags = _parse_tags(item.get('tag', ''), item)
            for e in essays:
                if e['slug'] != slug and new_tags & _parse_tags(e.get('tag', ''), e):
                    _sync_essay_html(e)
            _generate_feeds()
            return jsonify(essays[i])
    return jsonify({"error": "Not found"}), 404

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
        img_dir = os.path.join(IMAGES_DIR, 'essays', folder)
        url = f"/images/essays/{folder}/{filename}"
    else:
        img_dir = os.path.join(IMAGES_DIR, 'essays')
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



# Stack CRUD
@app.route('/api/stack', methods=['GET'])
def get_stack():
    return jsonify(load_json('stack.json'))

@app.route('/api/stack', methods=['PUT'])
def update_stack():
    if not isinstance(request.json, list):
        return jsonify({"error": "Expected a JSON array of strings"}), 400
    atomic_write_json('stack.json', request.json)
    return jsonify({"status": "updated"})


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