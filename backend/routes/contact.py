from flask import request, jsonify

from backend.app import app
from backend.data import atomic_write_json
from backend.crud import list_all, create_item, update_item_by_index, delete_item_by_index


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
def add_contact():
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    return create_item('contact.json', request.json)


@app.route('/api/contact/<int:index>', methods=['PUT'])
def update_contact_item(index):
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    return update_item_by_index('contact.json', index, request.json)


@app.route('/api/contact/<int:index>', methods=['DELETE'])
def delete_contact(index):
    return delete_item_by_index('contact.json', index)
