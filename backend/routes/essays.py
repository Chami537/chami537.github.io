import json
import os
import re
import shutil
import uuid
from datetime import datetime

from flask import request, jsonify

from backend.app import app
from backend.data import load_json, atomic_write_json, DATA_DIR, get_essay_password, set_essay_password as store_password, has_essay_password
from backend.crud import require_json
from backend.markdown_utils import render_markdown
from backend.ssg import (
    _calc_read_time, _parse_date, _parse_tags, _sync_essay_html, _generate_feeds,
    _encrypt_content, _decrypt_content,
    ESSAYS_DIR, MD_DIR, IMAGES_DIR,
)
from backend.upload_utils import UploadValidationError, upload_error_response, validate_image_upload


@app.route('/api/tags/order', methods=['GET'])
def get_tag_order():
    tag_order_path = os.path.join(DATA_DIR, 'tags_order.json')
    if os.path.exists(tag_order_path):
        with open(tag_order_path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify([])


@app.route('/api/tags/order', methods=['PUT'])
@require_json
def save_tag_order():
    order = request.json.get('order', [])
    if not isinstance(order, list):
        return jsonify({"error": "order must be a list"}), 400
    atomic_write_json('tags_order.json', order)
    _generate_feeds()
    return jsonify({"status": "saved"})


@app.route('/api/essays', methods=['GET'])
def list_essays():
    essays = load_json('essays.json')
    for e in essays:
        e['date_display'] = _parse_date(e.get('date', ''))
        e['password_set'] = has_essay_password(e['slug'])
    return jsonify(essays)

@app.route('/api/essays', methods=['POST'])
@require_json
def create_essay():
    essays = load_json('essays.json')
    item = request.json
    slug = item.get('slug', '')
    if not slug or not re.match(r'^[a-z0-9-]+$', slug):
        return jsonify({"error": "slug 只能包含小写字母、数字和连字符"}), 400
    if any(e['slug'] == slug for e in essays):
        return jsonify({"error": "slug 已存在"}), 409

    # Extract password to local store, never persist in essays.json
    password = item.pop('password', '')
    if password:
        store_password(slug, password)

    read_time = _calc_read_time(item.get('body', '') or item.get('content', ''))
    item['readTime'] = read_time
    essays.append(item)
    atomic_write_json('essays.json', essays)

    body_md = item.get('body', '')
    _sync_essay_html(item, raw_md_memory=body_md if body_md else None, essays=essays)
    if len(essays) > 1:
        _sync_essay_html(essays[-2], essays=essays)
    _generate_feeds()

    return jsonify(item), 201

@app.route('/api/essays/<slug>', methods=['PUT'])
@require_json
def update_essay_meta(slug):
    essays = load_json('essays.json')
    for i, e in enumerate(essays):
        if e['slug'] == slug:
            new_slug = request.json.get('slug', slug)
            if not new_slug or not re.match(r'^[a-z0-9-]+$', new_slug):
                return jsonify({"error": "slug 只能包含小写字母、数字和连字符"}), 400
            if new_slug != slug and any(e2['slug'] == new_slug for e2 in essays):
                return jsonify({"error": "slug 已存在"}), 409
            essays[i].update(request.json)
            essays[i].pop('password', None)  # password never stored in essays.json
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
            # Re-sync updated essay + essays sharing tags (nav links may have changed)
            _sync_essay_html(essays[i], essays=essays)
            new_tags = _parse_tags(essays[i].get('tag', ''), essays[i])
            for e2 in essays:
                if e2['slug'] != slug and (not new_tags or new_tags & _parse_tags(e2.get('tag', ''), e2)):
                    _sync_essay_html(e2, essays=essays)
            _generate_feeds()
            return jsonify(essays[i])
    return jsonify({"error": "Not found"}), 404

@app.route('/api/essays/<slug>', methods=['DELETE'])
def delete_essay(slug):
    essays = load_json('essays.json')
    target = next((e for e in essays if e['slug'] == slug), None)
    if not target:
        return jsonify({"error": "Not found"}), 404
    title_folder = target['title']
    title_folder = title_folder.replace('/', '_').replace('\\', '_')
    if '..' in title_folder.split(os.sep):
        return jsonify({"error": "Invalid title"}), 400
    essays = [e for e in essays if e['slug'] != slug]
    atomic_write_json('essays.json', essays)
    html_file = os.path.join(ESSAYS_DIR, f"{slug}.html")
    if os.path.exists(html_file):
        os.remove(html_file)
    md_file = os.path.join(MD_DIR, f"{slug}.md")
    if os.path.exists(md_file):
        os.remove(md_file)
    img_dir = os.path.join(IMAGES_DIR, 'essays', title_folder)
    essays_img_dir = os.path.realpath(os.path.join(IMAGES_DIR, 'essays'))
    if os.path.realpath(img_dir).startswith(essays_img_dir + os.sep) and os.path.exists(img_dir):
        shutil.rmtree(img_dir)
    # Re-sync essays sharing tags with the deleted essay (or all siblings if tagless)
    deleted_tags = _parse_tags(target.get('tag', ''), target)
    for e in essays:
        if not deleted_tags or deleted_tags & _parse_tags(e.get('tag', ''), e):
            _sync_essay_html(e, essays=essays)
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
    _generate_feeds()
    pinned_count = sum(1 for e in essays if e.get('pinned'))
    return jsonify({"pinned": target['pinned'], "count": pinned_count})


@app.route('/api/essays/<slug>/password', methods=['POST'])
@require_json
def set_essay_password(slug):
    essays = load_json('essays.json')
    target = next((e for e in essays if e['slug'] == slug), None)
    if not target:
        return jsonify({"error": "Not found"}), 404

    new_password = request.json.get('password', '')
    old_password = get_essay_password(slug)
    md_file = os.path.join(MD_DIR, f"{slug}.md")
    had_password = bool(old_password)

    if new_password:
        # Re-encrypt .md if already encrypted
        if had_password and os.path.exists(md_file):
            with open(md_file, 'r', encoding='utf-8') as f:
                raw_md = f.read()
            if old_password:
                try:
                    raw_md = _decrypt_content(raw_md, old_password)
                except ValueError:
                    return jsonify({"error": "旧密码错误，无法重新加密内容"}), 400
                except UnicodeDecodeError:
                    return jsonify({"error": "旧密码错误，无法重新加密内容"}), 400
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(_encrypt_content(raw_md, new_password))
        store_password(slug, new_password)
    else:
        # Clearing password: decrypt .md, remove from store
        if os.path.exists(md_file) and old_password:
            with open(md_file, 'r', encoding='utf-8') as f:
                raw_md = f.read()
            try:
                raw_md = _decrypt_content(raw_md, old_password)
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(raw_md)
            except ValueError:
                return jsonify({"error": "旧密码错误，无法解密内容"}), 400
            except UnicodeDecodeError:
                return jsonify({"error": "旧密码错误，无法解密内容"}), 400
        store_password(slug, '')

    # Strip password from essays.json (safety net)
    for e in essays:
        e.pop('password', None)
    atomic_write_json('essays.json', essays)

    # Regenerate HTML (password gate or normal)
    _sync_essay_html(target, essays=essays)
    _generate_feeds()

    return jsonify({"password_set": bool(new_password)})


@app.route('/api/essays/<slug>/content', methods=['GET'])
def get_essay_content(slug):
    essays = load_json('essays.json')
    target = next((e for e in essays if e['slug'] == slug), None)
    # 优先读 .md 文件
    md_file = os.path.join(MD_DIR, f"{slug}.md")
    if os.path.exists(md_file):
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        # Decrypt if essay is password-protected
        if target and has_essay_password(slug):
            try:
                password = get_essay_password(slug)
                content = _decrypt_content(content, password)
            except (ValueError, UnicodeDecodeError):
                return jsonify({"error": "解密失败，密码可能已变更或数据损坏"}), 500
        return jsonify({"content": content, "format": "markdown"})

    # Fallback: 从 HTML 注释提取（兼容旧格式）
    html_file = os.path.join(ESSAYS_DIR, f"{slug}.html")
    if not os.path.exists(html_file):
        return jsonify({"error": "Not found"}), 404
    with open(html_file, 'r', encoding='utf-8') as f:
        full_html = f.read()
    md_match = re.search(r'<!-- RAW_MD\n(.*)\nRAW_MD -->', full_html, flags=re.DOTALL)
    if md_match:
        return jsonify({"content": md_match.group(1), "format": "markdown"})
    return jsonify({"content": "", "format": "markdown"})

@app.route('/api/essays/<slug>/content', methods=['PUT'])
@require_json
def update_essay_content(slug):
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
    _sync_essay_html(target_essay, raw_md_memory=md_content, essays=essays)
    _generate_feeds()

    return jsonify({"status": "success", "message": f"{slug}.html updated"})

@app.route('/api/essays/upload-image', methods=['POST'])
def upload_essay_image():
    try:
        file = request.files.get('file')
        ext, _img = validate_image_upload(file)
    except UploadValidationError as exc:
        return upload_error_response(exc)

    filename = f"{uuid.uuid4().hex[:8]}.{ext}"
    slug = request.form.get('slug', '') or request.args.get('slug', '')
    if slug:
        essays = load_json('essays.json')
        essay = next((e for e in essays if e.get('slug') == slug), None)
        folder = essay.get('title', slug) if essay else slug
        folder = folder.replace('/', '_').replace('\\', '_')
        img_dir = os.path.realpath(os.path.join(IMAGES_DIR, 'essays', folder))
        essays_img_dir = os.path.realpath(os.path.join(IMAGES_DIR, 'essays'))
        if not img_dir.startswith(essays_img_dir + os.sep):
            return jsonify({"error": "Invalid title"}), 400
        url = f"/images/essays/{folder}/{filename}"
    else:
        img_dir = os.path.join(IMAGES_DIR, 'essays')
        url = f"/images/essays/{filename}"
    os.makedirs(img_dir, exist_ok=True)
    file.save(os.path.join(img_dir, filename))
    return jsonify({"url": url, "status": "uploaded"}), 201

@app.route('/api/essays/<slug>/html', methods=['GET', 'POST'])
def preview_essay_html(slug):
    """Preview Markdown to HTML (no save). `slug` from URL path - required by Flask routing."""
    if request.method == 'POST':
        if not isinstance(request.json, dict):
            return jsonify({"error": "Expected a JSON object"}), 400
        md_content = request.json.get('md', '')
    else:
        md_content = request.args.get('md', '')
    html_content = render_markdown(md_content)
    html_content += '\n<p class=\"essay-updated\">Last edited at ' + datetime.now().strftime('%Y-%m-%d %H:%M') + '</p>'
    return jsonify({"html": html_content})
