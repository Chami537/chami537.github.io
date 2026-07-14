"""GPX track CRUD and uploads."""

import os
import uuid

from flask import Blueprint, jsonify, request

from backend.data import BASE_DIR
from backend.storage import repository_for
from backend.upload_utils import UploadValidationError, upload_error_response, validate_gpx_upload


bp = Blueprint('tracks', __name__)


def _repository():
    return repository_for('tracks.json')


@bp.route('/api/tracks', methods=['GET'])
def list_tracks():
    return jsonify(_repository().list())


@bp.route('/api/tracks/upload', methods=['POST'])
def upload_track():
    try:
        file = request.files.get('file')
        validate_gpx_upload(file)
    except UploadValidationError as exc:
        return upload_error_response(exc)

    filename = f'{uuid.uuid4().hex[:8]}.gpx'
    tracks_dir = os.path.join(BASE_DIR, 'tracks')
    os.makedirs(tracks_dir, exist_ok=True)
    path = os.path.join(tracks_dir, filename)
    item = {'name': os.path.splitext(file.filename)[0][:120] or filename, 'file': filename}
    try:
        file.save(path)
        repository = _repository()
        tracks = repository.list()
        tracks.append(item)
        repository.save(tracks)
    except Exception:
        if os.path.exists(path):
            os.remove(path)
        raise
    return jsonify(item), 201


@bp.route('/api/tracks/<int:index>', methods=['DELETE'])
def delete_track(index):
    repository = _repository()
    tracks = repository.list()
    if index < 0 or index >= len(tracks):
        return jsonify({'error': 'Index out of range'}), 404
    item = tracks.pop(index)
    filename = os.path.basename(str(item.get('file', '')))
    path = os.path.join(BASE_DIR, 'tracks', filename) if filename else ''
    staged = path + '.deleting' if path and os.path.exists(path) else ''
    if staged:
        os.replace(path, staged)
    try:
        repository.save(tracks)
    except Exception:
        if staged and os.path.exists(staged):
            os.replace(staged, path)
        raise
    if staged and os.path.exists(staged):
        os.remove(staged)
    return jsonify({'status': 'deleted'})
