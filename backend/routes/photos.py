import os
import re
import uuid

from flask import Blueprint, request, jsonify
from PIL import Image

bp = Blueprint('photos', __name__)
from backend.data import BASE_DIR
from backend.storage import repository_for
from backend.ssg import _parse_date, IMAGES_DIR
from backend.photo_metadata import set_gps as _set_gps
from backend.exif_utils import extract_exif as _extract_exif, without_camera_model as _without_camera_model
from backend.upload_utils import UploadValidationError, upload_error_response, validate_image_upload

PHOTO_STORIES_REPOSITORY = repository_for('photo_stories.json')
_PHOTO_SIZES = [('lg', 1920), ('md', 800), ('sm', 400)]

# Compatibility seams for existing tests and extensions; default behavior still
# goes through the repository rather than backend.data's file implementation.
def load_json(name):
    return repository_for(name).list()


def atomic_write_json(name, data):
    repository_for(name).save(data)


def _photo_upload_payload(img):
    exif_data = _without_camera_model(_extract_exif(img))
    return exif_data, img.getexif().tobytes()


def _save_photo_variants(img, filename, exif_bytes):
    for size_name, max_width in _PHOTO_SIZES:
        thumb = img.copy()
        if thumb.mode == 'RGBA':
            thumb = thumb.convert('RGB')
        thumb.thumbnail((max_width, max_width), Image.LANCZOS)
        out_dir = os.path.join(IMAGES_DIR, size_name)
        os.makedirs(out_dir, exist_ok=True)
        thumb.save(os.path.join(out_dir, filename))

    img.save(os.path.join(IMAGES_DIR, filename), exif=exif_bytes)
    raw_dir = os.path.join(BASE_DIR, 'raw_photos')
    os.makedirs(raw_dir, exist_ok=True)
    img.save(os.path.join(raw_dir, filename), exif=exif_bytes)


def _photo_entry(filename, exif_data, size):
    entry = {'filename': filename, 'size': size, 'exif': exif_data}
    if exif_data.get('date'):
        entry['date'] = _parse_date(exif_data['date'])
    return entry

@bp.route('/api/photos', methods=['GET'])
def list_photos():
    return jsonify(load_json('photos.json'))

@bp.route('/api/photos', methods=['PUT'])
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

@bp.route('/api/photos/upload', methods=['POST'])
def upload_photo():
    try:
        file = request.files.get('file')
        ext, img = validate_image_upload(file)
    except UploadValidationError as exc:
        return upload_error_response(exc)

    filename = f"{uuid.uuid4().hex[:8]}.{ext}"

    exif_data, exif_bytes = _photo_upload_payload(img)
    _save_photo_variants(img, filename, exif_bytes)

    # Update JSON
    photos = load_json('photos.json')
    size = request.form.get('size', 'sm')
    photos.append(_photo_entry(filename, exif_data, size))
    atomic_write_json('photos.json', photos)

    return jsonify({"status": "success", "filename": filename, "exif": exif_data}), 201


@bp.route('/api/photos/<filename>', methods=['DELETE'])
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


@bp.route('/api/photo-tags', methods=['PUT'])
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


@bp.route('/api/photo-date', methods=['PUT'])
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


@bp.route('/api/photo-gps', methods=['PUT'])
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


_STORY_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,80}$')


def _clean_story_text(value, limit=240):
    return str(value or '').strip()[:limit]


def _normalize_story_photos(raw_photos, story_id, valid_filenames):
    photos = []
    for filename in raw_photos or []:
        if not isinstance(filename, str):
            return None, f"Story {story_id} has a non-string photo filename"
        safe_name = os.path.basename(filename)
        if safe_name != filename or safe_name not in valid_filenames:
            return None, f"Story {story_id} references unknown photo: {filename}"
        if safe_name not in photos:
            photos.append(safe_name)
    if not photos:
        return None, f"Story {story_id} must contain at least one photo"
    return photos, None


def _normalize_story(raw, position, valid_filenames):
    if not isinstance(raw, dict):
        return None, f"Story #{position + 1} must be an object"

    story_id = _clean_story_text(raw.get('id'), 80)
    if not story_id or not _STORY_ID_RE.match(story_id):
        return None, f"Story #{position + 1} has an invalid id"

    photos, error = _normalize_story_photos(raw.get('photos'), story_id, valid_filenames)
    if error:
        return None, error

    raw_cover = _clean_story_text(raw.get('cover'), 160)
    cover = os.path.basename(raw_cover) if raw_cover else photos[0]
    if raw_cover and cover != raw_cover:
        return None, f"Story {story_id} has an invalid cover filename"
    if cover not in photos:
        return None, f"Story {story_id} cover must be one of its photos"

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
        for photo in load_json('photos.json')
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


# ── Photo stories (manually curated) ──

@bp.route('/api/photo-stories', methods=['GET'])
def get_photo_stories():
    data = PHOTO_STORIES_REPOSITORY.list()
    if not isinstance(data, list):
        return jsonify([])
    stories, error = _normalize_photo_stories(data)
    if error:
        return jsonify(data)
    return jsonify(stories)


@bp.route('/api/photo-stories', methods=['PUT'])
def save_photo_stories():
    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return jsonify({"error": "Expected a list of stories"}), 400
    stories, error = _normalize_photo_stories(data)
    if error:
        return jsonify({"error": error}), 400
    PHOTO_STORIES_REPOSITORY.save(stories)
    return jsonify({"status": "saved", "count": len(stories), "stories": stories})
