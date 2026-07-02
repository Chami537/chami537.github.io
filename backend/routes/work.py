from flask import request, jsonify

from backend.app import app
from backend.crud import list_all, create_item, update_item_by_id, delete_item_by_id, require_json


@app.route('/api/work', methods=['GET'])
def list_work():
    return list_all('work.json')


@app.route('/api/work', methods=['POST'])
@require_json
def create_work():
    return create_item('work.json', request.json, auto_id=True)


@app.route('/api/work/<int:id>', methods=['PUT'])
@require_json
def update_work(id):
    return update_item_by_id('work.json', id, request.json)


@app.route('/api/work/<int:id>', methods=['DELETE'])
def delete_work(id):
    return delete_item_by_id('work.json', id)
