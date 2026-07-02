import os

from flask import request, jsonify

from backend.app import app
from backend.data import BASE_DIR
from backend.crud import require_json


@app.route('/api/readme', methods=['GET'])
def get_readme():
    readme_path = os.path.join(BASE_DIR, 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = ''
    return jsonify({"content": content})

@app.route('/api/readme', methods=['PUT'])
@require_json
def save_readme():
    content = request.json.get('content', '')
    readme_path = os.path.join(BASE_DIR, 'README.md')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({"status": "saved"})
