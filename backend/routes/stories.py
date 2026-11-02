"""HTTP boundary for the personal stories shelf."""

import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request

from backend.crud import require_json
from backend.data import BASE_DIR
from backend.repositories import repository_for
from backend.story_service import StoryError, delete_story, reorder_stories, save_story
from backend.upload_utils import (
    UploadValidationError, save_upload_atomically, upload_error_response, validate_image_upload,
)

bp = Blueprint('stories', __name__)


@bp.errorhandler(StoryError)
def story_error(error):
    return jsonify({'error': str(error)}), error.status


@bp.get('/api/stories')
def list_stories():
    return jsonify(repository_for('stories.json').list())


@bp.post('/api/stories')
@require_json
def create_story():
    return jsonify(save_story(request.json)), 201


@bp.put('/api/stories/<int:story_id>')
@require_json
def update_story(story_id):
    return jsonify(save_story(request.json, story_id))


@bp.delete('/api/stories/<int:story_id>')
def remove_story(story_id):
    delete_story(story_id)
    return jsonify({'status': 'deleted'})


@bp.put('/api/stories/order')
@require_json
def order_stories():
    reorder_stories(request.json.get('order'))
    return jsonify({'status': 'saved'})


@bp.post('/api/stories/upload-cover')
def upload_cover():
    try:
        file = request.files.get('file')
        extension, image = validate_image_upload(file)
        root = Path(BASE_DIR).resolve()
        destination = (root / 'images' / 'stories' / f'{uuid.uuid4().hex}.{extension}').resolve()
        if not destination.is_relative_to(root / 'images' / 'stories'):
            raise UploadValidationError('封面目录不合法')
        try:
            save_upload_atomically(file, str(destination))
        finally:
            image.close()
    except UploadValidationError as error:
        return upload_error_response(error)
    return jsonify({'cover': destination.relative_to(root).as_posix()}), 201
