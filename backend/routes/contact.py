from flask import request, jsonify

from backend.app import app
from backend.data import load_json, atomic_write_json


@app.route('/api/contact', methods=['GET'])
def list_contact():
    return jsonify(load_json('contact.json'))

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
    contacts = load_json('contact.json')
    contacts.append(request.json)
    atomic_write_json('contact.json', contacts)
    return jsonify(request.json), 201

@app.route('/api/contact/<int:index>', methods=['PUT'])
def update_contact_item(index):
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    contacts = load_json('contact.json')
    if index < 0 or index >= len(contacts):
        return jsonify({"error": "Index out of range"}), 404
    contacts[index].update(request.json)
    atomic_write_json('contact.json', contacts)
    return jsonify(contacts[index])

@app.route('/api/contact/<int:index>', methods=['DELETE'])
def delete_contact(index):
    contacts = load_json('contact.json')
    if index < 0 or index >= len(contacts):
        return jsonify({"error": "Index out of range"}), 404
    contacts.pop(index)
    atomic_write_json('contact.json', contacts)
    return jsonify({"status": "deleted"})
