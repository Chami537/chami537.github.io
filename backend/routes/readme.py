import os

from flask import Blueprint, request, jsonify

bp = Blueprint('readme', __name__)
from backend.data import BASE_DIR
from backend.crud import require_json
from backend.file_utils import atomic_write_text


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
    atomic_write_text(readme_path, content)
    return jsonify({"status": "saved"})
