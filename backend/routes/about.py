import os

from flask import request, jsonify

from backend.app import app
from backend.data import load_json, atomic_write_json, BASE_DIR
from backend.crud import require_json
from backend.upload_utils import UploadValidationError, upload_error_response, validate_image_upload


@app.route('/api/about', methods=['GET'])
def get_about():
    return jsonify(load_json('about.json'))

@app.route('/api/about/upload-avatar', methods=['POST'])
def upload_avatar():
    try:
        file = request.files.get('file')
        ext, _img = validate_image_upload(file)
    except UploadValidationError as exc:
        return upload_error_response(exc)
    # Clean up old avatar files with different extensions
    for old_ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        if old_ext != ext:
            old_path = os.path.join(BASE_DIR, 'images', 'avatar.' + old_ext)
            if os.path.exists(old_path):
                os.remove(old_path)
    filename = 'avatar.' + ext
    filepath = os.path.join(BASE_DIR, 'images', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)
    return jsonify({"url": "images/" + filename}), 201

@app.route('/api/about', methods=['PUT'])
@require_json
def update_about():
    atomic_write_json('about.json', request.json)
    return jsonify({"status": "updated"})
