from flask import Blueprint, request, jsonify

bp = Blueprint('friends', __name__)
from backend.crud import list_all, create_item, update_item_by_id, delete_item_by_id, require_json


@bp.route('/api/friends', methods=['GET'])
def list_friends():
    return list_all('friends.json')


@bp.route('/api/friends', methods=['POST'])
@require_json
def add_friend():
    return create_item('friends.json', request.json, auto_id=True)


@bp.route('/api/friends/<int:id>', methods=['PUT'])
@require_json
def update_friend(id):
    return update_item_by_id('friends.json', id, request.json)


@bp.route('/api/friends/<int:id>', methods=['DELETE'])
def delete_friend(id):
    return delete_item_by_id('friends.json', id)
