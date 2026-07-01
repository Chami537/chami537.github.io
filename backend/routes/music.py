import os
import uuid

from flask import request, jsonify

from backend.app import app
from backend.data import load_json, BASE_DIR
from backend.crud import list_all, create_item, update_item_by_id, delete_item_by_id


@app.route('/api/music', methods=['GET'])
def list_music():
    return list_all('music.json')


@app.route('/api/music', methods=['POST'])
def create_music():
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    return create_item('music.json', request.json, auto_id=True)


@app.route('/api/music/<int:id>', methods=['PUT'])
def update_music(id):
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    return update_item_by_id('music.json', id, request.json)


@app.route('/api/music/upload', methods=['POST'])
def upload_music():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    if not file.filename or not file.filename.lower().endswith('.mp3'):
        return jsonify({"error": "Only .mp3 files"}), 400
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'mp3'
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
