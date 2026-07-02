from flask import request, jsonify

from backend.app import app
from backend.crud import list_all, create_item, update_item_by_index, delete_item_by_index, require_json


@app.route('/api/friends', methods=['GET'])
def list_friends():
    return list_all('friends.json')


@app.route('/api/friends', methods=['POST'])
@require_json
def add_friend():
    return create_item('friends.json', request.json)


@app.route('/api/friends/<int:index>', methods=['PUT'])
@require_json
def update_friend(index):
    return update_item_by_index('friends.json', index, request.json)


@app.route('/api/friends/<int:index>', methods=['DELETE'])
def delete_friend(index):
    return delete_item_by_index('friends.json', index)
