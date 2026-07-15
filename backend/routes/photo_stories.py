"""Validation and persistence routes for curated photo stories."""

import os
import re

from flask import jsonify, request

from backend.routes import photo_context


STORY_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,80}$')


def _clean_story_text(value, limit=240):
    return str(value or '').strip()[:limit]


def _normalize_story_photos(raw_photos, story_id, valid_filenames):
    photos = []
    for filename in raw_photos or []:
        if not isinstance(filename, str):
            return None, f'Story {story_id} has a non-string photo filename'
        safe_name = os.path.basename(filename)
        if safe_name != filename or safe_name not in valid_filenames:
            return None, f'Story {story_id} references unknown photo: {filename}'
        if safe_name not in photos:
            photos.append(safe_name)
    if not photos:
        return None, f'Story {story_id} must contain at least one photo'
    return photos, None


def _normalize_story(raw, position, valid_filenames):
    if not isinstance(raw, dict):
        return None, f'Story #{position + 1} must be an object'
    story_id = _clean_story_text(raw.get('id'), 80)
    if not story_id or not STORY_ID_RE.match(story_id):
        return None, f'Story #{position + 1} has an invalid id'
    photos, error = _normalize_story_photos(raw.get('photos'), story_id, valid_filenames)
    if error:
        return None, error

    raw_cover = _clean_story_text(raw.get('cover'), 160)
    cover = os.path.basename(raw_cover) if raw_cover else photos[0]
    if raw_cover and cover != raw_cover:
        return None, f'Story {story_id} has an invalid cover filename'
    if cover not in photos:
        return None, f'Story {story_id} cover must be one of its photos'
    return {
        'id': story_id,
        'name': _clean_story_text(raw.get('name'), 80) or story_id,
        'date': _clean_story_text(raw.get('date'), 40),
        'caption': _clean_story_text(raw.get('caption'), 180),
        'cover': cover,
        'photos': photos,
        'photo_count': len(photos),
    }, None


def _normalize_photo_stories(data):
    """Validate and normalize manually curated photo stories."""
    valid_filenames = {
        photo.get('filename')
        for photo in photo_context.PHOTO_REPOSITORY.list()
        if photo.get('filename')
    }
    seen_ids = set()
    normalized = []
    for position, raw in enumerate(data):
        story, error = _normalize_story(raw, position, valid_filenames)
        if error:
            return None, error
        if story['id'] in seen_ids:
            return None, f"Duplicate story id: {story['id']}"
        seen_ids.add(story['id'])
        normalized.append(story)
    return normalized, None


@photo_context.bp.route('/api/photo-stories', methods=['GET'])
def get_photo_stories():
    data = photo_context.PHOTO_STORIES_REPOSITORY.list()
    if not isinstance(data, list):
        return jsonify([])
    stories, error = _normalize_photo_stories(data)
    return jsonify(data if error else stories)


@photo_context.bp.route('/api/photo-stories', methods=['PUT'])
def save_photo_stories():
    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return jsonify({'error': 'Expected a list of stories'}), 400
    stories, error = _normalize_photo_stories(data)
    if error:
        return jsonify({'error': error}), 400
    photo_context.PHOTO_STORIES_REPOSITORY.save(stories)
    return jsonify({'status': 'saved', 'count': len(stories), 'stories': stories})
