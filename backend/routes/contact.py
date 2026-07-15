from flask import Blueprint, request, jsonify

bp = Blueprint('contact', __name__)
from backend.repositories import repository_for
from backend.crud import list_all, create_item, update_item_by_id, delete_item_by_id, require_json


@bp.route('/api/contact', methods=['GET'])
def list_contact():
    return list_all('contact.json')


@bp.route('/api/contact', methods=['PUT'])
def update_contact():
    if not isinstance(request.json, list):
        return jsonify({"error": "Expected a JSON array"}), 400
    for item in request.json:
        if not isinstance(item.get('id'), int):
            return jsonify({"error": "Each item must have a numeric id"}), 400
    repository_for('contact.json').save(request.json)
    return jsonify({"status": "updated"})


@bp.route('/api/contact', methods=['POST'])
@require_json
def add_contact():
    return create_item('contact.json', request.json, auto_id=True)


@bp.route('/api/contact/<int:id>', methods=['PUT'])
@require_json
def update_contact_item(id):
    return update_item_by_id('contact.json', id, request.json)


@bp.route('/api/contact/<int:id>', methods=['DELETE'])
def delete_contact(id):
    return delete_item_by_id('contact.json', id)
