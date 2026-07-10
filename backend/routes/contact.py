from flask import request, jsonify

from backend.app import app
from backend.data import atomic_write_json
from backend.crud import list_all, create_item, update_item_by_id, delete_item_by_id, require_json


@app.route('/api/contact', methods=['GET'])
def list_contact():
    return list_all('contact.json')


@app.route('/api/contact', methods=['PUT'])
def update_contact():
    if not isinstance(request.json, list):
        return jsonify({"error": "Expected a JSON array"}), 400
    atomic_write_json('contact.json', request.json)
    return jsonify({"status": "updated"})


@app.route('/api/contact', methods=['POST'])
@require_json
def add_contact():
    return create_item('contact.json', request.json, auto_id=True)


@app.route('/api/contact/<int:id>', methods=['PUT'])
@require_json
def update_contact_item(id):
    return update_item_by_id('contact.json', id, request.json)


@app.route('/api/contact/<int:id>', methods=['DELETE'])
def delete_contact(id):
    return delete_item_by_id('contact.json', id)
