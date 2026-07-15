"""Shared CRUD helpers for JSON array endpoints — index-based and id-based."""

from functools import wraps

from flask import jsonify, request

from backend.repositories import repository_for


def require_json(f):
    """Decorator: reject requests without a JSON object body."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not isinstance(request.json, dict):
            return jsonify({"error": "Expected a JSON object"}), 400
        return f(*args, **kwargs)
    return wrapper


def list_all(filename):
    return jsonify(repository_for(filename).list())


def create_item(filename, item, auto_id=False):
    repository = repository_for(filename)
    data = repository.list()
    if auto_id:
        item['id'] = max((i['id'] for i in data if isinstance(i.get('id'), int)), default=0) + 1
    data.append(item)
    repository.save(data)
    return jsonify(item), 201


def update_item_by_index(filename, index, updates):
    repository = repository_for(filename)
    data = repository.list()
    if index < 0 or index >= len(data):
        return jsonify({"error": "Index out of range"}), 404
    data[index].update(updates)
    repository.save(data)
    return jsonify(data[index])


def delete_item_by_index(filename, index):
    repository = repository_for(filename)
    data = repository.list()
    if index < 0 or index >= len(data):
        return jsonify({"error": "Index out of range"}), 404
    data.pop(index)
    repository.save(data)
    return jsonify({"status": "deleted"})


def update_item_by_id(filename, id_val, updates):
    repository = repository_for(filename)
    data = repository.list()
    for i, item in enumerate(data):
        if 'id' not in item:
            continue
        if item['id'] == id_val:
            updates['id'] = id_val
            data[i].update(updates)
            repository.save(data)
            return jsonify(data[i])
    return jsonify({"error": "Not found"}), 404


def delete_item_by_id(filename, id_val):
    repository = repository_for(filename)
    data = repository.list()
    new_data = [item for item in data if item.get('id') != id_val]
    if len(new_data) == len(data):
        return jsonify({"error": "Not found"}), 404
    repository.save(new_data)
    return jsonify({"status": "deleted"})
