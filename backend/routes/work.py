from flask import request, jsonify

from backend.app import app
from backend.crud import list_all, create_item, update_item_by_id, delete_item_by_id


@app.route('/api/work', methods=['GET'])
def list_work():
    return list_all('work.json')


@app.route('/api/work', methods=['POST'])
def create_work():
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    return create_item('work.json', request.json, auto_id=True)


@app.route('/api/work/<int:id>', methods=['PUT'])
def update_work(id):
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    return update_item_by_id('work.json', id, request.json)


@app.route('/api/work/<int:id>', methods=['DELETE'])
def delete_work(id):
    return delete_item_by_id('work.json', id)
