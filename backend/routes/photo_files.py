"""Photo listing, ordering, upload, and file removal routes."""

import os
import uuid

from flask import jsonify, request
from PIL import Image

from backend.exif_utils import extract_exif, without_camera_model
from backend.routes import photo_context
from backend.ssg import _parse_date
from backend.upload_utils import UploadValidationError, upload_error_response, validate_image_upload


def _photo_upload_payload(img):
    exif_data = without_camera_model(extract_exif(img))
    return exif_data, img.getexif().tobytes()


def _photo_file_paths(filename):
    return [
        os.path.join(photo_context.IMAGES_DIR, size_name, filename)
        for size_name, _max_width in photo_context.PHOTO_SIZES
    ] + [
        os.path.join(photo_context.IMAGES_DIR, filename),
        os.path.join(photo_context.BASE_DIR, 'raw_photos', filename),
    ]


def _save_photo_variants(img, filename, exif_bytes):
    for size_name, max_width in photo_context.PHOTO_SIZES:
        thumb = img.copy()
        if thumb.mode == 'RGBA':
            thumb = thumb.convert('RGB')
        thumb.thumbnail((max_width, max_width), Image.LANCZOS)
        out_dir = os.path.join(photo_context.IMAGES_DIR, size_name)
        os.makedirs(out_dir, exist_ok=True)
        thumb.save(os.path.join(out_dir, filename))

    img.save(os.path.join(photo_context.IMAGES_DIR, filename), exif=exif_bytes)
    raw_dir = os.path.join(photo_context.BASE_DIR, 'raw_photos')
    os.makedirs(raw_dir, exist_ok=True)
    img.save(os.path.join(raw_dir, filename), exif=exif_bytes)
    return _photo_file_paths(filename)


def _cleanup_photo_files(paths):
    for path in paths:
        if os.path.exists(path):
            os.remove(path)


def _photo_entry(filename, exif_data, size):
    entry = {'filename': filename, 'size': size, 'exif': exif_data}
    if exif_data.get('date'):
        entry['date'] = _parse_date(exif_data['date'])
    return entry


def _append_photo_entry(entry):
    """Serialize the read-modify-write used by parallel browser uploads."""
    with photo_context.PHOTO_METADATA_LOCK:
        photos = photo_context.load_json('photos.json')
        photos.append(entry)
        photo_context.atomic_write_json('photos.json', photos)


@photo_context.bp.route('/api/photos', methods=['GET'])
def list_photos():
    return jsonify(photo_context.load_json('photos.json'))


@photo_context.bp.route('/api/photos', methods=['PUT'])
def reorder_photos():
    """Replace the photo array while refusing to lose existing entries."""
    if not isinstance(request.json, list):
        return jsonify({'error': 'Expected a JSON array'}), 400
    new_data = request.json
    existing = photo_context.load_json('photos.json')
    existing_fns = {photo['filename'] for photo in existing}
    new_fns = {photo.get('filename', '') for photo in new_data}
    lost = existing_fns - new_fns
    if lost:
        names = ', '.join(sorted(lost))
        return jsonify({'error': f'Refusing to drop {len(lost)} existing photos: {names}'}), 409
    photo_context.atomic_write_json('photos.json', new_data)
    return jsonify({'status': 'reordered'})


@photo_context.bp.route('/api/photos/upload', methods=['POST'])
def upload_photo():
    try:
        file = request.files.get('file')
        ext, img = validate_image_upload(file)
    except UploadValidationError as exc:
        return upload_error_response(exc)

    filename = f'{uuid.uuid4().hex[:8]}.{ext}'
    created_files = _photo_file_paths(filename)
    try:
        exif_data, exif_bytes = _photo_upload_payload(img)
        _save_photo_variants(img, filename, exif_bytes)
        size = request.form.get('size', 'sm')
        _append_photo_entry(_photo_entry(filename, exif_data, size))
    except Exception:
        _cleanup_photo_files(created_files)
        raise
    return jsonify({'status': 'success', 'filename': filename, 'exif': exif_data}), 201


@photo_context.bp.route('/api/photos/<filename>', methods=['DELETE'])
def delete_photo(filename):
    photos = photo_context.load_json('photos.json')
    photos = [photo for photo in photos if photo['filename'] != filename]
    photo_context.atomic_write_json('photos.json', photos)
    safe_name = os.path.basename(filename)
    _cleanup_photo_files(_photo_file_paths(safe_name))
    return jsonify({'status': 'deleted'})
