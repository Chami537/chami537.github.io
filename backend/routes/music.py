import os
import uuid

from flask import Blueprint, request, jsonify

bp = Blueprint('music', __name__)
from backend.data import BASE_DIR
from backend.storage import repository_for
from backend.crud import list_all, create_item, update_item_by_id, require_json
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
    repository = repository_for('music.json')
    music = repository.list()
    target = next((item for item in music if item.get('id') == id), None)
    if not target:
        return jsonify({"error": "Not found"}), 404

    filename = os.path.basename(target.get('filename', ''))
    shared = any(item.get('id') != id and os.path.basename(item.get('filename', '')) == filename for item in music)
    mp3_path = os.path.join(BASE_DIR, 'music', filename) if filename and not shared else ''
    staged_path = mp3_path + '.deleting' if mp3_path and os.path.exists(mp3_path) else ''
    if staged_path:
        os.replace(mp3_path, staged_path)
    try:
        repository.save([item for item in music if item.get('id') != id])
    except Exception:
        if staged_path and os.path.exists(staged_path):
            os.replace(staged_path, mp3_path)
        raise
    if staged_path and os.path.exists(staged_path):
        os.remove(staged_path)
    return jsonify({"status": "deleted"})
