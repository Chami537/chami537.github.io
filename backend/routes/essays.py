import os
import re
import uuid
import time

from flask import request, jsonify
from markdown import markdown as md_to_html
from markupsafe import Markup

from backend.app import app
from backend.data import load_json, atomic_write_json, DATA_DIR
from backend.ssg import (
    _env, _fe, _calc_read_time, _parse_date,
    _extract_first_image, _parse_tags, _build_nav,
    _build_tag_nav_json, _sync_essay_html, _html_to_md,
    _generate_feeds,
    ESSAYS_DIR, MD_DIR, IMAGES_DIR,
)


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
    template = _env.get_template('essay.html')
    html = template.render(
        title=_fe(item.get('title', '')),
        excerpt=_fe(item.get('excerpt', '')),
        epigraph=_fe(item.get('epigraph', '')),
        tag=_fe(tag_display),
        date_display=_fe(date_display),
        read_time=read_time,
        body_html='',
        prev_nav=Markup(prev_nav),
        next_nav=Markup(next_nav),
        tag_nav_json=tag_nav_json,
        slug=slug,
        og_image=_fe(og_image),
        build_ts=int(time.time()),
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
            new_tags = _parse_tags(e.get('tag', ''), e)
            for e2 in essays:
                if e2['slug'] != slug and new_tags & _parse_tags(e2.get('tag', ''), e2):
                    _sync_essay_html(e2)
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
    now = __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')
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
    return jsonify({"html": html_content})
