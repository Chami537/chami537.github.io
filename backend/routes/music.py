import os
import uuid

from flask import Blueprint, request, jsonify

bp = Blueprint('music', __name__)
from backend.data import BASE_DIR
from backend.storage import repository_for
from backend.crud import list_all, create_item, update_item_by_id, delete_item_by_id, require_json
from backend.upload_utils import UploadValidationError, upload_error_response, validate_music_upload


@bp.route('/api/music', methods=['GET'])
def list_music():
    return list_all('music.json')


@bp.route('/api/music', methods=['POST'])
@require_json
def create_music():
    return create_item('music.json', request.json, auto_id=True)


@bp.route('/api/music/<int:id>', methods=['PUT'])
@require_json
def update_music(id):
    return update_item_by_id('music.json', id, request.json)


@bp.route('/api/music/upload', methods=['POST'])
def upload_music():
    try:
        file = request.files.get('file')
        ext = validate_music_upload(file)
    except UploadValidationError as exc:
        return upload_error_response(exc)

    filename = f"{uuid.uuid4().hex[:8]}.{ext}"
    music_dir = os.path.join(BASE_DIR, 'music')
    os.makedirs(music_dir, exist_ok=True)
    file.save(os.path.join(music_dir, filename))
    return jsonify({"filename": filename, "status": "uploaded"}), 201


@bp.route('/api/music/<int:id>', methods=['DELETE'])
def delete_music(id):
    # Clean up MP3 file before deleting JSON entry
    music = repository_for('music.json').list()
    for m in music:
        if m['id'] == id:
            fn = m.get('filename', '')
            if fn:
                mp3_path = os.path.join(BASE_DIR, 'music', os.path.basename(fn))
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
    return delete_item_by_id('music.json', id)
