from flask import Blueprint, jsonify

bp = Blueprint('stack', __name__)
from backend.repositories import repository_for
from backend.crud import json_body


@bp.route('/api/stack', methods=['GET'])
def get_stack():
    return jsonify(repository_for('stack.json').list())

@bp.route('/api/stack', methods=['PUT'])
def update_stack():
    data = json_body()
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        return jsonify({"error": "Expected a JSON array of strings"}), 400
    repository_for('stack.json').save(data)
    return jsonify({"status": "updated"})
