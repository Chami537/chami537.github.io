"""Photo tag/date/GPS API — separate module to avoid Werkzeug routing conflicts."""
from flask import request, jsonify
from backend.app import app
from backend.data import load_json, atomic_write_json, BASE_DIR
import os

@app.route('/api/photo-tags', methods=['PUT'])
def update_photo_tags():
    d = request.json
    if not isinstance(d, dict) or 'filename' not in d or 'tags' not in d:
        return jsonify({"error": "Expected {filename, tags}"}), 400
    photos = load_json('photos.json')
    for p in photos:
        if p['filename'] == d['filename']:
            p['tags'] = d['tags']
            atomic_write_json('photos.json', photos)
            return jsonify({"status": "ok", "tags": d['tags']})
    return jsonify({"error": "Photo not found"}), 404

@app.route('/api/photo-date', methods=['PUT'])
def update_photo_date():
    d = request.json
    if not isinstance(d, dict) or 'filename' not in d:
        return jsonify({"error": "Expected {filename, date}"}), 400
    dv = (d.get('date') or '').strip()
    photos = load_json('photos.json')
    for p in photos:
        if p['filename'] == d['filename']:
            if dv: p['date'] = dv
            else: p.pop('date', None)
            atomic_write_json('photos.json', photos)
            return jsonify({"status": "ok", "date": dv})
    return jsonify({"error": "Photo not found"}), 404

@app.route('/api/photo-gps', methods=['PUT'])
def update_photo_gps():
    d = request.json
    if not isinstance(d, dict) or 'filename' not in d or 'lat' not in d or 'lng' not in d:
        return jsonify({"error": "Expected {filename, lat, lng}"}), 400
    lat, lng = float(d['lat']), float(d['lng'])
    photos = load_json('photos.json')
    for p in photos:
        if p['filename'] == d['filename']:
            if 'exif' not in p: p['exif'] = {}
            p['exif']['gps'] = {'lat': round(lat, 6), 'lng': round(lng, 6)}
            atomic_write_json('photos.json', photos)
            rp = os.path.join(BASE_DIR, 'raw_photos', d['filename'])
            if os.path.exists(rp):
                from backend.ssg import _set_gps
                _set_gps(d['filename'], lat, lng)
            return jsonify({"status": "ok", "lat": lat, "lng": lng})
    return jsonify({"error": "Photo not found"}), 404
