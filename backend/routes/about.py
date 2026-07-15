import os

from flask import Blueprint, request, jsonify

bp = Blueprint('about', __name__)
from backend.data import BASE_DIR
from backend.repositories import repository_for
from backend.crud import require_json
from backend.upload_utils import UploadValidationError, upload_error_response, validate_image_upload


@bp.route('/api/about', methods=['GET'])
def get_about():
    return jsonify(repository_for('about.json').list())

@bp.route('/api/about/upload-avatar', methods=['POST'])
def upload_avatar():
    try:
        file = request.files.get('file')
        ext, _img = validate_image_upload(file)
    except UploadValidationError as exc:
        return upload_error_response(exc)
    filename = 'avatar.' + ext
    filepath = os.path.join(BASE_DIR, 'images', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    temp_path = filepath + '.uploading'
    try:
        file.save(temp_path)
        os.replace(temp_path, filepath)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
    # The replacement is durable; obsolete variants can now be removed safely.
    for old_ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        if old_ext != ext:
            old_path = os.path.join(BASE_DIR, 'images', 'avatar.' + old_ext)
            if os.path.exists(old_path):
                os.remove(old_path)
    return jsonify({"url": "images/" + filename}), 201

@bp.route('/api/about', methods=['PUT'])
@require_json
def update_about():
    repository_for('about.json').save(request.json)
    return jsonify({"status": "updated"})
