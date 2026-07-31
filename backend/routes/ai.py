"""Authenticated AI editorial assistance for essay drafts."""

import re

from flask import Blueprint, jsonify, request

from backend.ai_service import AIServiceError, assist_essay
from backend.crud import require_json
from backend.data import has_essay_password
from backend.writing_style import load_style_reference


bp = Blueprint('ai', __name__)
_SLUG_PATTERN = re.compile(r'^[a-z0-9-]+$')
_STYLE_TASKS = {'summary', 'polish', 'review', 'title', 'continue'}


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

    style_reference = (
        load_style_reference(slug, current_tags=data.get('existing_tags', []))
        if data.get('task') in _STYLE_TASKS
        else {'samples': [], 'count': 0}
    )
    try:
        response = assist_essay(
            task=data.get('task'),
            content=data.get('content'),
            title=data.get('title', ''),
            existing_tags=data.get('existing_tags', []),
            style_samples=style_reference['samples'],
            polish_mode=data.get('polish_mode', 'light'),
            instruction=data.get('instruction', ''),
            surrounding_context=data.get('surrounding_context'),
        )
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    except AIServiceError as error:
        return jsonify({'error': str(error)}), 503
    return jsonify({
        'task': data['task'],
        **response,
        'style_reference_count': style_reference['count'],
    })
