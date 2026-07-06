import os

from PIL import Image
from flask import request, jsonify

from backend.app import app
from backend.data import load_json, atomic_write_json, BASE_DIR, get_image_ext
from backend.crud import require_json


@app.route('/api/about', methods=['GET'])
def get_about():
    return jsonify(load_json('about.json'))

@app.route('/api/about/upload-avatar', methods=['POST'])
def upload_avatar():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({"error": "No filename"}), 400
    ext = get_image_ext(file.filename)
    if not ext:
        return jsonify({"error": "不支持的文件类型"}), 400
    try:
        img = Image.open(file.stream)
        img.verify()
        file.stream.seek(0)
    except Exception:
        return jsonify({"error": "Invalid or corrupted image file"}), 400
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
