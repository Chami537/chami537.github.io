"""Photo tags, date, and GPS metadata routes."""

import os

from flask import jsonify, request

from backend.photo_metadata import set_gps
from backend.routes import photo_context


def _find_photo(filename):
    """Return a matching photo and the full collection."""
    photos = photo_context.load_json('photos.json')
    for photo in photos:
        if photo['filename'] == filename:
            return photo, photos
    return None, photos


@photo_context.bp.route('/api/photo-tags', methods=['PUT'])
def update_photo_tags():
    data = request.json
    if not isinstance(data, dict) or 'filename' not in data or 'tags' not in data:
        return jsonify({'error': 'Expected {filename, tags}'}), 400
    photo, photos = _find_photo(data['filename'])
    if not photo:
        return jsonify({'error': 'Photo not found'}), 404
    photo['tags'] = data['tags']
    photo_context.atomic_write_json('photos.json', photos)
    return jsonify({'status': 'ok', 'tags': data['tags']})


@photo_context.bp.route('/api/photo-date', methods=['PUT'])
def update_photo_date():
    data = request.json
    if not isinstance(data, dict) or 'filename' not in data:
        return jsonify({'error': 'Expected {filename, date}'}), 400
    date = (data.get('date') or '').strip()
    photo, photos = _find_photo(data['filename'])
    if not photo:
        return jsonify({'error': 'Photo not found'}), 404
    if date:
        photo['date'] = date
    else:
        photo.pop('date', None)
    photo_context.atomic_write_json('photos.json', photos)
    return jsonify({'status': 'ok', 'date': date})


@photo_context.bp.route('/api/photo-gps', methods=['PUT'])
def update_photo_gps():
    data = request.json
    required = isinstance(data, dict) and all(key in data for key in ('filename', 'lat', 'lng'))
    if not required:
        return jsonify({'error': 'Expected {filename, lat, lng}'}), 400
    if not isinstance(data['lat'], (int, float)) or not isinstance(data['lng'], (int, float)):
        return jsonify({'error': 'lat and lng must be numbers'}), 400
    if not (-90 <= data['lat'] <= 90) or not (-180 <= data['lng'] <= 180):
        return jsonify({'error': 'lat must be -90..90, lng must be -180..180'}), 400

    lat, lng = float(data['lat']), float(data['lng'])
    photo, photos = _find_photo(data['filename'])
    if not photo:
        return jsonify({'error': 'Photo not found'}), 404
    photo.setdefault('exif', {})['gps'] = {'lat': round(lat, 6), 'lng': round(lng, 6)}
    photo_context.atomic_write_json('photos.json', photos)

    safe_name = os.path.basename(data['filename'])
    raw_path = os.path.join(photo_context.BASE_DIR, 'raw_photos', safe_name)
    if os.path.exists(raw_path):
        set_gps(safe_name, lat, lng)
    return jsonify({'status': 'ok', 'lat': lat, 'lng': lng})
