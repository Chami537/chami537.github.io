"""Essay metadata, deletion, and pinning routes."""

import os
import re
import shutil

from flask import jsonify, request

from backend.crud import require_json
from backend.data import (
    ESSAYS_DIR,
    IMAGES_DIR,
    MD_DIR,
    delete_essay_password,
    rename_essay_password,
)
from backend.essay_navigation import parse_tags
from backend.routes import essay_context


@essay_context.bp.route('/api/essays/<slug>', methods=['PUT'])
@require_json
def update_essay_meta(slug):
    essays = essay_context.ESSAY_REPOSITORY.list()
    target = next((essay for essay in essays if essay['slug'] == slug), None)
    if not target:
        return jsonify({"error": "Not found"}), 404

    new_slug = request.json.get('slug', slug)
    error = _validate_meta_slug(slug, new_slug, essays)
    if error:
        return jsonify({"error": error}), 409 if error == 'slug 已存在' else 400

    _apply_meta_updates(target, request.json, new_slug)
    try:
        rename_essay_password(slug, new_slug)
        essay_context.ESSAY_REPOSITORY.save(essays)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409
    except Exception:
        rename_essay_password(new_slug, slug)
        raise
    _rename_essay_sources(slug, new_slug)
    _sync_related_essays(target, slug, essays)
    essay_context.ESSAY_WORKFLOW.regenerate_feeds()
    return jsonify(target)


def _validate_meta_slug(old_slug, new_slug, essays):
    if not new_slug or not re.match(r'^[a-z0-9-]+$', new_slug):
        return 'slug 只能包含小写字母、数字和连字符'
    if new_slug != old_slug and any(essay['slug'] == new_slug for essay in essays):
        return 'slug 已存在'
    return None


def _apply_meta_updates(essay, updates, new_slug):
    essay.update(updates)
    essay.pop('password', None)
    essay['slug'] = new_slug


def _rename_essay_sources(old_slug, new_slug):
    if new_slug == old_slug:
        return
    for directory in (ESSAYS_DIR, MD_DIR):
        suffix = 'html' if directory == ESSAYS_DIR else 'md'
        old_path = os.path.join(directory, f'{old_slug}.{suffix}')
        new_path = os.path.join(directory, f'{new_slug}.{suffix}')
        if os.path.exists(old_path):
            os.replace(old_path, new_path)


def _sync_related_essays(updated, old_slug, essays):
    essay_context.ESSAY_WORKFLOW.sync(updated, essays=essays)
    tags = parse_tags(updated.get('tag', ''), updated)
    for essay in essays:
        if essay['slug'] != old_slug and (not tags or tags & parse_tags(essay.get('tag', ''), essay)):
            essay_context.ESSAY_WORKFLOW.sync(essay, essays=essays)


@essay_context.bp.route('/api/essays/<slug>', methods=['DELETE'])
def delete_essay(slug):
    essays = essay_context.ESSAY_REPOSITORY.list()
    target = next((essay for essay in essays if essay['slug'] == slug), None)
    if not target:
        return jsonify({"error": "Not found"}), 404
    title_folder = _essay_title_folder(target['title'])
    if title_folder is None:
        return jsonify({"error": "Invalid title"}), 400
    essays = [essay for essay in essays if essay['slug'] != slug]
    essay_context.ESSAY_REPOSITORY.save(essays)
    delete_essay_password(slug)
    _remove_essay_files(slug, title_folder)
    _sync_after_essay_delete(target, essays)
    return jsonify({"status": "deleted"})


def _essay_title_folder(title):
    title_folder = title.replace('/', '_').replace('\\', '_')
    if '..' in title_folder.split(os.sep):
        return None
    return title_folder


def _remove_essay_files(slug, title_folder):
    for directory, suffix in ((ESSAYS_DIR, 'html'), (MD_DIR, 'md')):
        path = os.path.join(directory, f'{slug}.{suffix}')
        if os.path.exists(path):
            os.remove(path)
    image_dir = os.path.join(IMAGES_DIR, 'essays', title_folder)
    essays_image_dir = os.path.realpath(os.path.join(IMAGES_DIR, 'essays'))
    if os.path.realpath(image_dir).startswith(essays_image_dir + os.sep) and os.path.exists(image_dir):
        shutil.rmtree(image_dir)


def _sync_after_essay_delete(deleted, essays):
    deleted_tags = parse_tags(deleted.get('tag', ''), deleted)
    for essay in essays:
        if not deleted_tags or deleted_tags & parse_tags(essay.get('tag', ''), essay):
            essay_context.ESSAY_WORKFLOW.sync(essay, essays=essays)
    essay_context.ESSAY_WORKFLOW.regenerate_feeds()


@essay_context.bp.route('/api/essays/<slug>/pin', methods=['POST'])
def toggle_pin(slug):
    essays = essay_context.ESSAY_REPOSITORY.list()
    for essay in essays:
        essay.setdefault('pinned', False)

    target = next((essay for essay in essays if essay['slug'] == slug), None)
    if not target:
        return jsonify({"error": "Not found"}), 404

    if not target.get('pinned'):
        pinned_count = sum(1 for essay in essays if essay.get('pinned'))
        if pinned_count >= 5:
            return jsonify({"error": "最多置顶 5 篇文章"}), 400
        target['pinned'] = True
    else:
        target['pinned'] = False

    essay_context.ESSAY_REPOSITORY.save(essays)
    essay_context.ESSAY_WORKFLOW.regenerate_feeds()
    pinned_count = sum(1 for essay in essays if essay.get('pinned'))
    return jsonify({"pinned": target['pinned'], "count": pinned_count})
