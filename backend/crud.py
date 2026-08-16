"""Shared CRUD helpers for JSON array endpoints — index-based and id-based."""

from functools import wraps

from flask import jsonify, request

from backend.repositories import repository_for


def json_body():
    """Read a JSON body without turning malformed input into a framework 415."""
    return request.get_json(silent=True)


def require_json(f):
    """Decorator: reject requests without a JSON object body."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not isinstance(json_body(), dict):
            return jsonify({"error": "Expected a JSON object"}), 400
        return f(*args, **kwargs)
    return wrapper


def list_all(filename):
    return jsonify(repository_for(filename).list())


def create_item(filename, item, auto_id=False):
    if not isinstance(item, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    item = dict(item)
    repository = repository_for(filename)
    def append_item(data):
        if auto_id:
            item['id'] = max((i['id'] for i in data if isinstance(i.get('id'), int)), default=0) + 1
        data.append(item)
        return item
    repository.mutate(append_item)
    return jsonify(item), 201


def update_item_by_id(filename, id_val, updates):
    if not isinstance(updates, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    updates = dict(updates)
    repository = repository_for(filename)
    def update(data):
        for item in data:
            if not isinstance(item, dict):
                continue
            if item.get('id') == id_val:
                updates['id'] = id_val
                item.update(updates)
                return item
        return None
    updated = repository.mutate(update)
    return jsonify(updated) if updated is not None else (jsonify({"error": "Not found"}), 404)


def delete_item_by_id(filename, id_val):
    repository = repository_for(filename)
    def remove(data):
        for index, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            if item.get('id') == id_val:
                data.pop(index)
                return True
        return None
    deleted = repository.mutate(remove)
    return jsonify({"status": "deleted"}) if deleted else (jsonify({"error": "Not found"}), 404)
