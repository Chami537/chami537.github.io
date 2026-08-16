"""Photo tags, date, and GPS metadata routes."""

import os

from flask import jsonify, request

from backend.photo_metadata import set_gps
from backend.routes import photo_context

MAX_PHOTO_TAGS = 50
MAX_PHOTO_TAG_LENGTH = 80
MAX_PHOTO_DATE_LENGTH = 80


def _payload():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _filename(data):
    filename = data.get('filename') if isinstance(data, dict) else None
    if not isinstance(filename, str) or not filename.strip():
        return None
    filename = filename.strip()
    return filename if os.path.basename(filename) == filename else None


def _normalize_tags(value):
    if not isinstance(value, list) or len(value) > MAX_PHOTO_TAGS:
        return None
    normalized = []
    for tag in value:
        if not isinstance(tag, str):
            return None
        tag = tag.strip()
        if not tag or len(tag) > MAX_PHOTO_TAG_LENGTH:
            return None
        if tag not in normalized:
            normalized.append(tag)
    return normalized


def _find_photo(filename):
    """Return a matching photo and the full collection."""
    return photo_context.PHOTO_REPOSITORY.find(filename)


@photo_context.bp.route('/api/photo-tags', methods=['PUT'])
def update_photo_tags():
    data = _payload()
    filename = _filename(data)
    tags = _normalize_tags(data.get('tags') if data else None)
    if filename is None or tags is None:
        return jsonify({'error': 'Expected {filename, tags}'}), 400
    photo, _photos = _find_photo(filename)
    if not photo:
        return jsonify({'error': 'Photo not found'}), 404
    photo_context.PHOTO_REPOSITORY.update(
        filename,
        lambda item: item.update(tags=tags),
    )
    return jsonify({'status': 'ok', 'tags': tags})


@photo_context.bp.route('/api/photo-date', methods=['PUT'])
def update_photo_date():
    data = _payload()
    filename = _filename(data)
    date = data.get('date', '') if data else ''
    if filename is None or not isinstance(date, str) or len(date) > MAX_PHOTO_DATE_LENGTH:
        return jsonify({'error': 'Expected {filename, date}'}), 400
    date = date.strip()
    photo, _photos = _find_photo(filename)
    if not photo:
        return jsonify({'error': 'Photo not found'}), 404
    def set_date(item):
        if date:
            item['date'] = date
        else:
            item.pop('date', None)
    photo_context.PHOTO_REPOSITORY.update(filename, set_date)
    return jsonify({'status': 'ok', 'date': date})


@photo_context.bp.route('/api/photo-gps', methods=['PUT'])
def update_photo_gps():
    data = _payload()
    required = isinstance(data, dict) and all(key in data for key in ('filename', 'lat', 'lng'))
    if not required:
        return jsonify({'error': 'Expected {filename, lat, lng}'}), 400
    filename = _filename(data)
    if filename is None:
        return jsonify({'error': 'filename must be a safe file name'}), 400
    coordinates = data['lat'], data['lng']
    if any(type(value) not in (int, float) for value in coordinates):
        return jsonify({'error': 'lat and lng must be numbers'}), 400

    lat, lng = map(float, coordinates)
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return jsonify({'error': 'lat must be -90..90, lng must be -180..180'}), 400

    photo, _photos = _find_photo(filename)
    if not photo:
        return jsonify({'error': 'Photo not found'}), 404
    gps = {'lat': round(lat, 6), 'lng': round(lng, 6)}
    photo_context.PHOTO_REPOSITORY.update(
        filename,
        lambda item: item.setdefault('exif', {}).update(gps=gps),
    )

    safe_name = filename
    raw_path = os.path.join(photo_context.BASE_DIR, 'raw_photos', safe_name)
    if os.path.exists(raw_path):
        set_gps(safe_name, lat, lng)
    return jsonify({'status': 'ok', 'lat': lat, 'lng': lng})
