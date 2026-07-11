import os
import uuid

from flask import request, jsonify

from backend.app import app
from backend.data import load_json, BASE_DIR
from backend.crud import list_all, create_item, update_item_by_id, delete_item_by_id, require_json
from backend.upload_utils import UploadValidationError, upload_error_response, validate_music_upload


@app.route('/api/music', methods=['GET'])
def list_music():
    return list_all('music.json')


@app.route('/api/music', methods=['POST'])
@require_json
def create_music():
    return create_item('music.json', request.json, auto_id=True)


@app.route('/api/music/<int:id>', methods=['PUT'])
@require_json
def update_music(id):
    return update_item_by_id('music.json', id, request.json)


@app.route('/api/music/upload', methods=['POST'])
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


@app.route('/api/music/<int:id>', methods=['DELETE'])
def delete_music(id):
    # Clean up MP3 file before deleting JSON entry
    music = load_json('music.json')
    for m in music:
        if m['id'] == id:
            fn = m.get('filename', '')
            if fn:
                mp3_path = os.path.join(BASE_DIR, 'music', os.path.basename(fn))
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
    return delete_item_by_id('music.json', id)
