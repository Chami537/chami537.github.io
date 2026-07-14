"""Essay password and Markdown content routes."""

import os
import re
from datetime import datetime

from flask import jsonify, request

from backend.crud import require_json
from backend.data import get_essay_password, has_essay_password, set_essay_password as store_password
from backend.routes import essay_context
from backend.ssg import (
    ESSAYS_DIR,
    MD_DIR,
    _calc_read_time,
    _decrypt_content,
    _encrypt_content,
    _generate_feeds,
    _sync_essay_html,
)


def _rewrite_encrypted_essay(md_file, old_password, new_password):
    """Decrypt an existing Markdown file and encrypt it with a new password."""
    if not os.path.exists(md_file) or not old_password:
        return None
    with open(md_file, 'r', encoding='utf-8') as file:
        raw_md = file.read()
    try:
        raw_md = _decrypt_content(raw_md, old_password)
    except (ValueError, UnicodeDecodeError):
        return "旧密码错误，无法重新加密内容"
    with open(md_file, 'w', encoding='utf-8') as file:
        file.write(_encrypt_content(raw_md, new_password))
    return None


def _decrypt_essay_file(md_file, password):
    """Decrypt an essay Markdown file in place before removing its password."""
    if not os.path.exists(md_file) or not password:
        return None
    with open(md_file, 'r', encoding='utf-8') as file:
        raw_md = file.read()
    try:
        raw_md = _decrypt_content(raw_md, password)
    except (ValueError, UnicodeDecodeError):
        return "旧密码错误，无法解密内容"
    with open(md_file, 'w', encoding='utf-8') as file:
        file.write(raw_md)
    return None


def _strip_essay_passwords(essays):
    """Remove transient password fields before persisting essay metadata."""
    for essay in essays:
        essay.pop('password', None)


@essay_context.bp.route('/api/essays/<slug>/password', methods=['POST'])
@require_json
def set_essay_password(slug):
    essays = essay_context.ESSAY_REPOSITORY.list()
    target = next((essay for essay in essays if essay['slug'] == slug), None)
    if not target:
        return jsonify({"error": "Not found"}), 404

    new_password = request.json.get('password', '')
    error = _change_essay_password(slug, new_password)
    if error:
        return jsonify({"error": error}), 400
    _persist_password_state(slug, new_password, essays)
    _sync_essay_html(target, essays=essays)
    _generate_feeds()
    return jsonify({"password_set": bool(new_password)})


def _change_essay_password(slug, new_password):
    old_password = get_essay_password(slug)
    md_file = os.path.join(MD_DIR, f'{slug}.md')
    if new_password:
        return _rewrite_encrypted_essay(md_file, old_password, new_password)
    return _decrypt_essay_file(md_file, old_password)


def _persist_password_state(slug, password, essays):
    store_password(slug, password)
    _strip_essay_passwords(essays)
    essay_context.ESSAY_REPOSITORY.save(essays)


@essay_context.bp.route('/api/essays/<slug>/content', methods=['GET'])
def get_essay_content(slug):
    essays = essay_context.ESSAY_REPOSITORY.list()
    target = next((essay for essay in essays if essay['slug'] == slug), None)
    md_file = os.path.join(MD_DIR, f'{slug}.md')
    if os.path.exists(md_file):
        with open(md_file, 'r', encoding='utf-8') as file:
            content = file.read()
        if target and has_essay_password(slug):
            try:
                content = _decrypt_content(content, get_essay_password(slug))
            except (ValueError, UnicodeDecodeError):
                return jsonify({"error": "解密失败，密码可能已变更或数据损坏"}), 500
        return jsonify({"content": content, "format": "markdown"})

    html_file = os.path.join(ESSAYS_DIR, f'{slug}.html')
    if not os.path.exists(html_file):
        return jsonify({"error": "Not found"}), 404
    with open(html_file, 'r', encoding='utf-8') as file:
        full_html = file.read()
    match = re.search(r'<!-- RAW_MD\n(.*)\nRAW_MD -->', full_html, flags=re.DOTALL)
    if match:
        return jsonify({"content": match.group(1), "format": "markdown"})
    return jsonify({"content": "", "format": "markdown"})


@essay_context.bp.route('/api/essays/<slug>/content', methods=['PUT'])
@require_json
def update_essay_content(slug):
    md_content = request.json.get('content', '')
    read_time = _calc_read_time(md_content)
    essays = essay_context.ESSAY_REPOSITORY.list()
    target = None
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    for essay in essays:
        if essay['slug'] == slug:
            essay['readTime'] = read_time
            essay['date'] = now
            target = essay
            essay_context.ESSAY_REPOSITORY.save(essays)
            break

    if not target:
        return jsonify({"error": "Essay not found"}), 404

    _sync_essay_html(target, raw_md_memory=md_content, essays=essays)
    _generate_feeds()
    return jsonify({"status": "success", "message": f"{slug}.html updated"})
