import os
import uuid

from flask import request, jsonify

from backend.app import app
from backend.data import load_json, atomic_write_json, BASE_DIR


@app.route('/api/music', methods=['GET'])
def list_music():
    return jsonify(load_json('music.json'))

@app.route('/api/music', methods=['POST'])
def create_music():
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    music = load_json('music.json')
    item = request.json
    item['id'] = max((m['id'] for m in music), default=0) + 1
    music.append(item)
    atomic_write_json('music.json', music)
    return jsonify(item), 201

@app.route('/api/music/<int:id>', methods=['PUT'])
def update_music(id):
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    music = load_json('music.json')
    for i, m in enumerate(music):
        if m['id'] == id:
            music[i].update(request.json)
            music[i]['id'] = id
            atomic_write_json('music.json', music)
            return jsonify(music[i])
    return jsonify({"error": "Not found"}), 404

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
    music = load_json('music.json')
    for m in music:
        if m['id'] == id:
            fn = m.get('filename', '')
            if fn:
                mp3_path = os.path.join(BASE_DIR, 'music', os.path.basename(fn))
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
    music = [m for m in music if m['id'] != id]
    atomic_write_json('music.json', music)
    return jsonify({"status": "deleted"})
