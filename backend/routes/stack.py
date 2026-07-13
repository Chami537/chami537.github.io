from flask import Blueprint, request, jsonify

bp = Blueprint('stack', __name__)
from backend.storage import repository_for


@bp.route('/api/stack', methods=['GET'])
def get_stack():
    return jsonify(repository_for('stack.json').list())

@bp.route('/api/stack', methods=['PUT'])
def update_stack():
    if not isinstance(request.json, list):
        return jsonify({"error": "Expected a JSON array of strings"}), 400
    repository_for('stack.json').save(request.json)
    return jsonify({"status": "updated"})
