"""Shared CRUD helpers for JSON array endpoints — index-based and id-based."""

from flask import jsonify

from backend.data import load_json, atomic_write_json


def list_all(filename):
    return jsonify(load_json(filename))


def create_item(filename, item, auto_id=False):
    data = load_json(filename)
    if auto_id:
        item['id'] = max((i['id'] for i in data), default=0) + 1
    data.append(item)
    atomic_write_json(filename, data)
    return jsonify(item), 201


def update_item_by_index(filename, index, updates):
    data = load_json(filename)
    if index < 0 or index >= len(data):
        return jsonify({"error": "Index out of range"}), 404
    data[index].update(updates)
    atomic_write_json(filename, data)
    return jsonify(data[index])


def delete_item_by_index(filename, index):
    data = load_json(filename)
    if index < 0 or index >= len(data):
        return jsonify({"error": "Index out of range"}), 404
    data.pop(index)
    atomic_write_json(filename, data)
    return jsonify({"status": "deleted"})


def update_item_by_id(filename, id_val, updates):
    data = load_json(filename)
    for i, item in enumerate(data):
        if item['id'] == id_val:
            updates['id'] = id_val
            data[i].update(updates)
            atomic_write_json(filename, data)
            return jsonify(data[i])
    return jsonify({"error": "Not found"}), 404


def delete_item_by_id(filename, id_val):
    data = load_json(filename)
    new_data = [item for item in data if item['id'] != id_val]
    if len(new_data) == len(data):
        return jsonify({"error": "Not found"}), 404
    atomic_write_json(filename, new_data)
    return jsonify({"status": "deleted"})
