import os

from flask import Blueprint, request, jsonify

bp = Blueprint('readme', __name__)
from backend.data import BASE_DIR
from backend.crud import require_json


@bp.route('/api/readme', methods=['GET'])
def get_readme():
    readme_path = os.path.join(BASE_DIR, 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = ''
    return jsonify({"content": content})

@bp.route('/api/readme', methods=['PUT'])
@require_json
def save_readme():
    content = request.json.get('content')
    if not isinstance(content, str):
        return jsonify({"error": "content must be a string"}), 400
    readme_path = os.path.join(BASE_DIR, 'README.md')
    temp_path = readme_path + '.tmp'
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(temp_path, readme_path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
    return jsonify({"status": "saved"})
