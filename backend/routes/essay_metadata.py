"""Essay metadata, deletion, and pinning routes."""

import os
import re

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
from backend.essay_file_ops import purge_staged, rename_sources, restore_sources, stage_paths
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
    moved_sources = []
    password_renamed = False
    try:
        rename_essay_password(slug, new_slug)
        password_renamed = slug != new_slug
        moved_sources = rename_sources(
            slug, new_slug, ((ESSAYS_DIR, 'html'), (MD_DIR, 'md')),
        )
        essay_context.ESSAY_REPOSITORY.save(essays)
    except ValueError as exc:
        _rollback_essay_rename(slug, new_slug, moved_sources, password_renamed)
        return jsonify({"error": str(exc)}), 409
    except Exception:
        _rollback_essay_rename(slug, new_slug, moved_sources, password_renamed)
        raise
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
def _rollback_essay_rename(old_slug, new_slug, moved_sources, password_renamed):
    restore_sources(moved_sources)
    if password_renamed:
        rename_essay_password(new_slug, old_slug)
def _sync_related_essays(updated, old_slug, essays):
    essay_context.ESSAY_WORKFLOW.sync(updated, essays=essays)
    tags = parse_tags(updated.get('tag', ''), updated)
    for essay in essays:
        if essay['slug'] != old_slug and (not tags or tags & parse_tags(essay.get('tag', ''), essay)):
            essay_context.ESSAY_WORKFLOW.sync(essay, essays=essays)


@essay_context.bp.route('/api/essays/<slug>', methods=['DELETE'])
def delete_essay(slug):
    with essay_context.ESSAY_REPOSITORY.locked():
        original_essays = essay_context.ESSAY_REPOSITORY.list()
        target = next((essay for essay in original_essays if essay['slug'] == slug), None)
        if not target:
            return jsonify({"error": "Not found"}), 404
        title_folder = _essay_title_folder(target['title'])
        if title_folder is None:
            return jsonify({"error": "Invalid title"}), 400
        essays = [essay for essay in original_essays if essay['slug'] != slug]
        staged = stage_paths(_essay_artifact_paths(slug, title_folder))
        password_slug = f'__deleting__{slug}'
        password_staged = False
        metadata_saved = False
        try:
            password_staged = rename_essay_password(slug, password_slug)
            essay_context.ESSAY_REPOSITORY.save(essays)
            metadata_saved = True
            delete_essay_password(password_slug)
            purge_staged(staged)
        except Exception:
            if metadata_saved:
                essay_context.ESSAY_REPOSITORY.save(original_essays)
            restore_sources(staged)
            if password_staged:
                rename_essay_password(password_slug, slug)
            raise
    _sync_after_essay_delete(target, essays)
    return jsonify({"status": "deleted"})


def _essay_title_folder(title):
    title_folder = title.replace('/', '_').replace('\\', '_')
    if '..' in title_folder.split(os.sep):
        return None
    return title_folder


def _essay_artifact_paths(slug, title_folder):
    paths = [
        os.path.join(directory, f'{slug}.{suffix}')
        for directory, suffix in ((ESSAYS_DIR, 'html'), (MD_DIR, 'md'))
    ]
    image_dir = os.path.join(IMAGES_DIR, 'essays', title_folder)
    essays_image_dir = os.path.realpath(os.path.join(IMAGES_DIR, 'essays'))
    if os.path.realpath(image_dir).startswith(essays_image_dir + os.sep) and os.path.exists(image_dir):
        paths.append(image_dir)
    return paths


def _sync_after_essay_delete(deleted, essays):
    deleted_tags = parse_tags(deleted.get('tag', ''), deleted)
    for essay in essays:
        if not deleted_tags or deleted_tags & parse_tags(essay.get('tag', ''), essay):
            essay_context.ESSAY_WORKFLOW.sync(essay, essays=essays)
    essay_context.ESSAY_WORKFLOW.regenerate_feeds()


@essay_context.bp.route('/api/essays/<slug>/pin', methods=['POST'])
def toggle_pin(slug):
    with essay_context.ESSAY_REPOSITORY.locked():
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
