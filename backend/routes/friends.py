from flask import request, jsonify

from backend.app import app
from backend.crud import list_all, create_item, update_item_by_id, delete_item_by_id, require_json


@app.route('/api/friends', methods=['GET'])
def list_friends():
    return list_all('friends.json')


@app.route('/api/friends', methods=['POST'])
@require_json
def add_friend():
    return create_item('friends.json', request.json, auto_id=True)


@app.route('/api/friends/<int:id>', methods=['PUT'])
@require_json
def update_friend(id):
    return update_item_by_id('friends.json', id, request.json)


@app.route('/api/friends/<int:id>', methods=['DELETE'])
def delete_friend(id):
    return delete_item_by_id('friends.json', id)
