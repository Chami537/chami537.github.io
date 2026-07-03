import json
import os
import uuid

from PIL import Image
from flask import request, jsonify

from backend.app import app
from backend.data import load_json, atomic_write_json, BASE_DIR, DATA_DIR
from backend.ssg import _extract_exif, _set_gps, IMAGES_DIR

@app.route('/api/photos', methods=['GET'])
def list_photos():
    return jsonify(load_json('photos.json'))

@app.route('/api/photos', methods=['PUT'])
def reorder_photos():
    """Replace entire photo array (for reordering). Validates no entries lost."""
    if not isinstance(request.json, list):
        return jsonify({"error": "Expected a JSON array"}), 400
    new_data = request.json
    existing = load_json('photos.json')
    existing_fns = {p['filename'] for p in existing}
    new_fns = {p.get('filename', '') for p in new_data}
    lost = existing_fns - new_fns
    if lost:
        return jsonify({"error": f"Refusing to drop {len(lost)} existing photos: {', '.join(sorted(lost))}"}), 409
    atomic_write_json('photos.json', new_data)
    return jsonify({"status": "reordered"})

@app.route('/api/photos/upload', methods=['POST'])
def upload_photo():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({"error": "No filename"}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
    if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        return jsonify({"error": f"不支持的文件类型: .{ext}"}), 400
    filename = f"{uuid.uuid4().hex[:8]}.{ext}"
    try:
        img = Image.open(file.stream)
        img.verify()
        file.stream.seek(0)
        img = Image.open(file.stream)
    except Exception:
        return jsonify({"error": "Invalid or corrupted image file"}), 400

    # Extract EXIF (shared helper in ssg.py)
    exif_data = _extract_exif(img)

    # Generate thumbnails
    for size_name, max_w in [('lg', 1920), ('md', 800), ('sm', 400)]:
        thumb = img.copy()
        thumb.thumbnail((max_w, max_w), Image.LANCZOS)
        out_dir = os.path.join(IMAGES_DIR, size_name)
        os.makedirs(out_dir, exist_ok=True)
        thumb.save(os.path.join(out_dir, filename))

    # Save original to images/ and copy to raw_photos/
    img.save(os.path.join(IMAGES_DIR, filename))
    raw_dir = os.path.join(BASE_DIR, 'raw_photos')
    os.makedirs(raw_dir, exist_ok=True)
    img.save(os.path.join(raw_dir, filename))

    # Update JSON
    photos = load_json('photos.json')
    size = request.form.get('size', 'sm')
    photos.append({"filename": filename, "size": size, "exif": exif_data})
    atomic_write_json('photos.json', photos)

    return jsonify({"status": "success", "filename": filename, "exif": exif_data}), 201


@app.route('/api/photos/<filename>', methods=['DELETE'])
def delete_photo(filename):
    photos = load_json('photos.json')
    photos = [p for p in photos if p['filename'] != filename]
    atomic_write_json('photos.json', photos)
    # Remove image files (basename to prevent path traversal)
    safe_name = os.path.basename(filename)
    for subdir in ['', 'lg', 'md', 'sm']:
        path = os.path.join(IMAGES_DIR, subdir, safe_name)
        if os.path.exists(path):
            os.remove(path)
    raw_path = os.path.join(BASE_DIR, 'raw_photos', safe_name)
    if os.path.exists(raw_path):
        os.remove(raw_path)
    return jsonify({"status": "deleted"})


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
        _set_gps(safe_fn, lat, lng)
    return jsonify({"status": "ok", "lat": lat, "lng": lng})


# ── Photo stories (manually curated) ──

@app.route('/api/photo-stories', methods=['GET'])
def get_photo_stories():
    stories_path = os.path.join(DATA_DIR, 'photo_stories.json')
    if os.path.exists(stories_path):
        with open(stories_path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify([])


@app.route('/api/photo-stories', methods=['PUT'])
def save_photo_stories():
    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return jsonify({"error": "Expected a list of stories"}), 400
    atomic_write_json('photo_stories.json', data)
    return jsonify({"status": "saved", "count": len(data)})
