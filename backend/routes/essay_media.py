"""Essay image upload and Markdown preview routes."""

import os
import uuid
from datetime import datetime

from flask import jsonify, request

from backend.markdown_utils import render_markdown
from backend.routes import essay_context
from backend.ssg import IMAGES_DIR
from backend.upload_utils import UploadValidationError, upload_error_response, validate_image_upload


@essay_context.bp.route('/api/essays/upload-image', methods=['POST'])
def upload_essay_image():
    try:
        file = request.files.get('file')
        extension, _image = validate_image_upload(file)
    except UploadValidationError as error:
        return upload_error_response(error)

    filename = f'{uuid.uuid4().hex[:8]}.{extension}'
    slug = request.form.get('slug', '') or request.args.get('slug', '')
    if slug:
        essays = essay_context.ESSAY_REPOSITORY.list()
        essay = next((item for item in essays if item.get('slug') == slug), None)
        folder = essay.get('title', slug) if essay else slug
        folder = folder.replace('/', '_').replace('\\', '_')
        image_dir = os.path.realpath(os.path.join(IMAGES_DIR, 'essays', folder))
        essays_image_dir = os.path.realpath(os.path.join(IMAGES_DIR, 'essays'))
        if not image_dir.startswith(essays_image_dir + os.sep):
            return jsonify({"error": "Invalid title"}), 400
        url = f'/images/essays/{folder}/{filename}'
    else:
        image_dir = os.path.join(IMAGES_DIR, 'essays')
        url = f'/images/essays/{filename}'
    os.makedirs(image_dir, exist_ok=True)
    file.save(os.path.join(image_dir, filename))
    return jsonify({"url": url, "status": "uploaded"}), 201


@essay_context.bp.route('/api/essays/<slug>/html', methods=['GET', 'POST'])
def preview_essay_html(slug):
    """Preview Markdown to HTML without saving it."""
    if request.method == 'POST':
        if not isinstance(request.json, dict):
            return jsonify({"error": "Expected a JSON object"}), 400
        markdown = request.json.get('md', '')
    else:
        markdown = request.args.get('md', '')
    html = render_markdown(markdown)
    html += '\n<p class="essay-updated">Last edited at ' + datetime.now().strftime('%Y-%m-%d %H:%M') + '</p>'
    return jsonify({"html": html})
