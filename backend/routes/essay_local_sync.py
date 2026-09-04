"""Routes for detecting and publishing local Markdown edits."""

import os
import re
import hashlib
import shutil
from difflib import SequenceMatcher
from datetime import datetime

from flask import jsonify, request
from PIL import Image

from backend.crud import require_json
from backend.data import ALLOWED_IMAGE_EXTENSIONS, ESSAYS_DIR, IMAGES_DIR, MD_DIR, has_essay_password
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


def _obsidian_source_for(essay, project_content=None):
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
    if project_content:
        best = (0, None)
        for entry in candidates:
            try:
                with open(entry.path, 'r', encoding='utf-8') as file:
                    candidate = file.read()
            except (OSError, UnicodeDecodeError):
                continue
            score = SequenceMatcher(None, project_content, candidate).ratio()
            if score > best[0]:
                best = (score, entry.path)
        if best[0] >= 0.75:
            return best[1]
    return None


def _find_obsidian_image(name, note_path):
    """Resolve an Obsidian embed to a file inside the configured vault."""
    clean = (name or '').split('|', 1)[0].strip().replace('\\', '/')
    if not clean or clean.startswith('/') or '..' in clean.split('/'):
        return None
    note_dir = os.path.dirname(note_path)
    direct = os.path.realpath(os.path.join(note_dir, clean))
    vault_root = os.path.realpath(OBSIDIAN_DIR or '')
    if not direct.startswith(vault_root + os.sep):
        return None
    if os.path.isfile(direct):
        return direct
    basename = os.path.basename(clean)
    for root, _dirs, files in os.walk(vault_root):
        if basename in files:
            return os.path.join(root, basename)
    return None


def _safe_image_name(name):
    base, ext = os.path.splitext(os.path.basename(name))
    base = re.sub(r'[^0-9A-Za-z\u3400-\u9fff_-]+', '-', base).strip('-') or 'image'
    ext = ext.lower()
    return base[:80] + ext


def _materialize_obsidian_images(content, note_path, essay):
    """Copy embedded Obsidian images into public essay assets and rewrite links."""
    if not OBSIDIAN_DIR or not content:
        return content
    pattern = re.compile(r'!\[\[([^\]]+)\]\]')
    folder = re.sub(r'[/\\]+', '_', essay.get('title', essay['slug'])).strip() or essay['slug']
    image_dir = os.path.realpath(os.path.join(IMAGES_DIR, 'essays', folder))
    root = os.path.realpath(os.path.join(IMAGES_DIR, 'essays'))
    if not image_dir.startswith(root + os.sep):
        raise ValueError('Invalid essay image directory')
    changed = False

    def replace(match):
        nonlocal changed
        source = _find_obsidian_image(match.group(1), note_path)
        if not source or os.path.splitext(source)[1].lower().lstrip('.') not in ALLOWED_IMAGE_EXTENSIONS:
            return match.group(0)
        try:
            with Image.open(source) as image:
                image.verify()
            os.makedirs(image_dir, exist_ok=True)
            filename = _safe_image_name(match.group(1))
            destination = os.path.join(image_dir, filename)
            if os.path.exists(destination):
                with open(source, 'rb') as file:
                    source_digest = hashlib.sha256(file.read()).hexdigest()
                with open(destination, 'rb') as file:
                    destination_digest = hashlib.sha256(file.read()).hexdigest()
                if source_digest != destination_digest:
                    filename = os.path.splitext(filename)[0] + '-' + source_digest[:8] + os.path.splitext(filename)[1]
                    destination = os.path.join(image_dir, filename)
            if not os.path.exists(destination):
                shutil.copy2(source, destination)
            changed = True
            url = '/images/essays/{}/{}'.format(folder, filename)
            return '![{}]({})'.format(os.path.splitext(filename)[0], url)
        except (OSError, ValueError):
            return match.group(0)

    result = pattern.sub(replace, content)
    return result if changed else content


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
            obsidian_path = _obsidian_source_for(essay, content)
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
            obsidian_path = _obsidian_source_for(target, content)
            source_mtime = os.path.getmtime(md_file)
            if obsidian_path:
                try:
                    source_mtime = os.path.getmtime(obsidian_path)
                    with open(obsidian_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                except (OSError, UnicodeDecodeError):
                    pass
            if obsidian_path and obsidian_path != md_file:
                content = _materialize_obsidian_images(content, obsidian_path, target)
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
