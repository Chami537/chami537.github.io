from flask import Blueprint, request, jsonify

bp = Blueprint('stack', __name__)
from backend.data import load_json, atomic_write_json


@bp.route('/api/stack', methods=['GET'])
def get_stack():
    return jsonify(load_json('stack.json'))

@bp.route('/api/stack', methods=['PUT'])
def update_stack():
    if not isinstance(request.json, list):
        return jsonify({"error": "Expected a JSON array of strings"}), 400
    atomic_write_json('stack.json', request.json)
    return jsonify({"status": "updated"})
