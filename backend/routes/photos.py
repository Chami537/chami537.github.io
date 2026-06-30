import os
import uuid

from PIL import Image
from flask import request, jsonify

from backend.app import app
from backend.data import load_json, atomic_write_json, BASE_DIR
from backend.ssg import _extract_exif, IMAGES_DIR


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
