"""Routes for detecting and publishing local Markdown edits."""

import os
import re
from datetime import datetime

from flask import jsonify, request

from backend.crud import require_json
from backend.data import ESSAYS_DIR, MD_DIR, has_essay_password
from backend.essay_crypto import is_encrypted_content
from backend.file_utils import atomic_write_text
from backend.routes import essay_context

OBSIDIAN_DIR = os.environ.get('OBSIDIAN_VAULT_DIR')
if not OBSIDIAN_DIR and os.path.isdir(r'E:\Obsidian Vault'):
    OBSIDIAN_DIR = r'E:\Obsidian Vault'


def _markdown_source_from_html(slug):
    html_file = os.path.join(ESSAYS_DIR, f'{slug}.html')
    if not os.path.isfile(html_file):
        return None
    try:
        with open(html_file, 'r', encoding='utf-8') as file:
            match = re.search(r'<!-- RAW_MD\n(.*)\nRAW_MD -->', file.read(), flags=re.DOTALL)
    except OSError:
        return None
    return match.group(1) if match else None


def _source_matches_generated_page(slug, content, path):
    snapshot = _markdown_source_from_html(slug)
    if snapshot is not None:
        return snapshot == content
    html_file = os.path.join(ESSAYS_DIR, f'{slug}.html')
    try:
        return os.path.getmtime(path) <= os.path.getmtime(html_file)
    except OSError:
        return False


def _normalize_name(value):
    return re.sub(r'[^0-9A-Za-z\u3400-\u9fff]', '', value or '').lower()


def _obsidian_source_for(essay):
    """Find a matching Obsidian note by title when the project source is unchanged."""
    if not OBSIDIAN_DIR or not essay.get('title'):
        return None
    title = _normalize_name(essay['title'])
    if not title:
        return None
    try:
        candidates = [entry for entry in os.scandir(OBSIDIAN_DIR)
                      if entry.is_file() and entry.name.lower().endswith('.md')]
    except OSError:
        return None
    for entry in candidates:
        name = _normalize_name(os.path.splitext(entry.name)[0])
        if all(char in name for char in title):
            return entry.path
    return None


def _local_essay_changes(essays):
    registered = {essay.get('slug'): essay for essay in essays if essay.get('slug')}
    changes = []
    try:
        filenames = sorted(name for name in os.listdir(MD_DIR) if name.lower().endswith('.md'))
    except OSError:
        filenames = []
    seen = set()
    for filename in filenames:
        slug = filename[:-3]
        seen.add(slug)
        path = os.path.join(MD_DIR, filename)
        try:
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
            mtime = os.path.getmtime(path)
        except (OSError, UnicodeDecodeError):
            continue
        essay = registered.get(slug)
        if not essay:
            changes.append({'slug': slug, 'status': 'unregistered', 'mtime': mtime})
        elif not _source_matches_generated_page(slug, content, path):
            changes.append({'slug': slug, 'title': essay.get('title', slug), 'status': 'changed',
                            'mtime': mtime, 'readTime': essay.get('readTime', 1),
                            'password_protected': has_essay_password(slug)})
        else:
            obsidian_path = _obsidian_source_for(essay)
            if obsidian_path:
                try:
                    with open(obsidian_path, 'r', encoding='utf-8') as file:
                        obsidian_content = file.read()
                    if obsidian_content != content:
                        changes.append({'slug': slug, 'title': essay.get('title', slug), 'status': 'changed',
                                        'source': 'obsidian', 'source_path': obsidian_path,
                                        'mtime': os.path.getmtime(obsidian_path),
                                        'readTime': essay.get('readTime', 1),
                                        'password_protected': has_essay_password(slug)})
                except (OSError, UnicodeDecodeError):
                    pass
    for essay in essays:
        slug = essay.get('slug')
        if slug and slug not in seen and _markdown_source_from_html(slug) is not None:
            changes.append({'slug': slug, 'title': essay.get('title', slug), 'status': 'missing_source'})
    return changes


@essay_context.bp.route('/api/essays/local-changes', methods=['GET'])
def list_local_essay_changes():
    return jsonify({'changes': _local_essay_changes(essay_context.ESSAY_REPOSITORY.list())})


@essay_context.bp.route('/api/essays/restore-local-source', methods=['POST'])
@require_json
def restore_local_essay_sources():
    slugs = request.json.get('slugs', [])
    if not isinstance(slugs, list) or any(not isinstance(slug, str) for slug in slugs):
        return jsonify({'error': 'slugs must be a list of strings'}), 400
    if any(not re.fullmatch(r'[a-z0-9-]+', slug) for slug in slugs):
        return jsonify({'error': 'invalid essay slug'}), 400
    essays = {essay.get('slug'): essay for essay in essay_context.ESSAY_REPOSITORY.list()}
    results = []
    for slug in slugs:
        if slug not in essays:
            results.append({'slug': slug, 'status': 'error', 'error': 'Essay not found'})
            continue
        source = _markdown_source_from_html(slug)
        if source is None:
            results.append({'slug': slug, 'status': 'error', 'error': 'Generated HTML has no embedded Markdown source'})
            continue
        try:
            os.makedirs(MD_DIR, exist_ok=True)
            atomic_write_text(os.path.join(MD_DIR, f'{slug}.md'), source)
            results.append({'slug': slug, 'status': 'restored'})
        except OSError as error:
            results.append({'slug': slug, 'status': 'error', 'error': str(error)})
    return jsonify({'results': results, 'restored': sum(item['status'] == 'restored' for item in results)})


@essay_context.bp.route('/api/essays/sync-local', methods=['POST'])
@require_json
def sync_local_essays():
    slugs = request.json.get('slugs', [])
    if not isinstance(slugs, list) or any(not isinstance(slug, str) for slug in slugs):
        return jsonify({'error': 'slugs must be a list of strings'}), 400
    if any(not re.fullmatch(r'[a-z0-9-]+', slug) for slug in slugs):
        return jsonify({'error': 'invalid essay slug'}), 400
    if len(set(slugs)) != len(slugs):
        return jsonify({'error': 'slugs must not contain duplicates'}), 400
    with essay_context.ESSAY_REPOSITORY.locked():
        essays = essay_context.ESSAY_REPOSITORY.list()
        by_slug = {essay.get('slug'): essay for essay in essays}
        results, changed = [], False
        for slug in slugs:
            target = by_slug.get(slug)
            md_file = os.path.join(MD_DIR, f'{slug}.md')
            if not target:
                results.append({'slug': slug, 'status': 'error', 'error': 'Essay not found'})
                continue
            try:
                with open(md_file, 'r', encoding='utf-8') as file:
                    content = file.read()
            except (OSError, UnicodeDecodeError):
                results.append({'slug': slug, 'status': 'error', 'error': 'Markdown source not found or unreadable'})
                continue
            obsidian_path = _obsidian_source_for(target)
            source_mtime = os.path.getmtime(md_file)
            if obsidian_path:
                try:
                    source_mtime = os.path.getmtime(obsidian_path)
                    with open(obsidian_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                except (OSError, UnicodeDecodeError):
                    pass
            protected = has_essay_password(slug)
            if protected and not is_encrypted_content(content):
                results.append({'slug': slug, 'status': 'error', 'error': '受保护文章的本地文件不是有效密文，已跳过'})
                continue
            if not protected and is_encrypted_content(content):
                results.append({'slug': slug, 'status': 'error', 'error': '文章未设置密码，拒绝发布密文内容'})
                continue
            try:
                target['readTime'] = essay_context.ESSAY_WORKFLOW.read_time(content) if not protected else target.get('readTime', 1)
                target['date'] = datetime.fromtimestamp(source_mtime).strftime('%Y-%m-%d %H:%M')
                if protected:
                    essay_context.ESSAY_WORKFLOW.sync(target, essays=essays)
                else:
                    essay_context.ESSAY_WORKFLOW.sync(target, raw_md_memory=content, essays=essays)
                results.append({'slug': slug, 'status': 'synced', 'readTime': target['readTime'], 'date': target['date']})
                changed = True
            except Exception as error:
                results.append({'slug': slug, 'status': 'error', 'error': str(error)})
        if changed:
            essay_context.ESSAY_REPOSITORY.save(essays)
            essay_context.ESSAY_WORKFLOW.regenerate_feeds()
    return jsonify({'results': results, 'synced': sum(item['status'] == 'synced' for item in results)})
