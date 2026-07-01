"""Photo tag/date/GPS API — separate module to avoid Werkzeug routing conflicts."""
from flask import request, jsonify
from backend.app import app
from backend.data import load_json, atomic_write_json, BASE_DIR
import os


def _find_photo(filename):
    """Return (photo_dict, all_photos) for *filename*, or (None, all_photos)."""
    photos = load_json('photos.json')
    for p in photos:
        if p['filename'] == filename:
            return p, photos
    return None, photos


@app.route('/api/photo-tags', methods=['PUT'])
def update_photo_tags():
    d = request.json
    if not isinstance(d, dict) or 'filename' not in d or 'tags' not in d:
        return jsonify({"error": "Expected {filename, tags}"}), 400
    p, photos_lock = _find_photo(d['filename'])
    if not p:
        return jsonify({"error": "Photo not found"}), 404
    p['tags'] = d['tags']
    atomic_write_json('photos.json', photos_lock)
    return jsonify({"status": "ok", "tags": d['tags']})


@app.route('/api/photo-date', methods=['PUT'])
def update_photo_date():
    d = request.json
    if not isinstance(d, dict) or 'filename' not in d:
        return jsonify({"error": "Expected {filename, date}"}), 400
    dv = (d.get('date') or '').strip()
    p, photos_lock = _find_photo(d['filename'])
    if not p:
        return jsonify({"error": "Photo not found"}), 404
    if dv:
        p['date'] = dv
    else:
        p.pop('date', None)
    atomic_write_json('photos.json', photos_lock)
    return jsonify({"status": "ok", "date": dv})


@app.route('/api/photo-gps', methods=['PUT'])
def update_photo_gps():
    d = request.json
    if not isinstance(d, dict) or 'filename' not in d or 'lat' not in d or 'lng' not in d:
        return jsonify({"error": "Expected {filename, lat, lng}"}), 400
    if not isinstance(d['lat'], (int, float)) or not isinstance(d['lng'], (int, float)):
        return jsonify({"error": "lat and lng must be numbers"}), 400
    if not (-90 <= d['lat'] <= 90) or not (-180 <= d['lng'] <= 180):
        return jsonify({"error": "lat must be -90..90, lng must be -180..180"}), 400
    lat, lng = float(d['lat']), float(d['lng'])
    p, photos_lock = _find_photo(d['filename'])
    if not p:
        return jsonify({"error": "Photo not found"}), 404
    if 'exif' not in p:
        p['exif'] = {}
    p['exif']['gps'] = {'lat': round(lat, 6), 'lng': round(lng, 6)}
    atomic_write_json('photos.json', photos_lock)
    safe_fn = os.path.basename(d['filename'])
    rp = os.path.join(BASE_DIR, 'raw_photos', safe_fn)
    if os.path.exists(rp):
        from backend.ssg import _set_gps
        _set_gps(safe_fn, lat, lng)
    return jsonify({"status": "ok", "lat": lat, "lng": lng})
