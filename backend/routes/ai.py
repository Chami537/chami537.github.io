"""Authenticated AI editorial assistance for essay drafts."""

import re

from flask import Blueprint, jsonify, request

from backend.ai_service import AIServiceError, assist_essay
from backend.crud import require_json
from backend.data import has_essay_password


bp = Blueprint('ai', __name__)
_SLUG_PATTERN = re.compile(r'^[a-z0-9-]+$')


@bp.route('/api/ai/essay-assist', methods=['POST'])
@require_json
def essay_assist():
    """Return an editorial suggestion without persisting any content."""
    data = request.json
    slug = data.get('slug')
    if type(slug) is not str or not _SLUG_PATTERN.fullmatch(slug):
        return jsonify({'error': 'slug 只能包含小写字母、数字和连字符'}), 400
    if has_essay_password(slug):
        return jsonify({'error': '密码保护文章不能发送给 AI'}), 403

    try:
        response = assist_essay(
            task=data.get('task'),
            content=data.get('content'),
            title=data.get('title', ''),
            existing_tags=data.get('existing_tags', []),
        )
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    except AIServiceError as error:
        return jsonify({'error': str(error)}), 503
    return jsonify({'task': data['task'], **response})
