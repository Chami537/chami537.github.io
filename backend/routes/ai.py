"""Authenticated AI editorial assistance for essay drafts."""

import re

from flask import Blueprint, jsonify, request

from backend.ai_service import AIServiceError, assist_essay
from backend.crud import require_json
from backend.data import has_essay_password
from backend.writing_style import (
    load_style_profile,
    load_style_reference,
    save_style_profile,
)


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
    style_profile = (
        load_style_profile()['profile']
        if data.get('task') in _STYLE_TASKS
        else ''
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
            style_profile=style_profile,
        )
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    except AIServiceError as error:
        return jsonify({'error': str(error)}), 503
    return jsonify({
        'task': data['task'],
        **response,
        'style_reference_count': style_reference['count'],
        'style_profile_used': bool(style_profile),
    })


@bp.route('/api/ai/writing-style', methods=['GET'])
def writing_style():
    """Return the saved, author-editable writing profile."""
    return jsonify(load_style_profile())


@bp.route('/api/ai/writing-style/analyze', methods=['POST'])
@require_json
def analyze_writing_style():
    """Suggest a new profile from bounded public samples without saving it."""
    style_reference = load_style_reference('')
    if not style_reference['samples']:
        return jsonify({'error': '没有可用的公开文章样本'}), 400
    try:
        response = assist_essay(
            task='style',
            content='总结这些公开文章的稳定作者文风',
            style_samples=style_reference['samples'],
        )
    except (ValueError, AIServiceError) as error:
        status = 400 if isinstance(error, ValueError) else 503
        return jsonify({'error': str(error)}), status
    return jsonify({
        **response,
        'style_reference_count': style_reference['count'],
    })


@bp.route('/api/ai/writing-style', methods=['PUT'])
@require_json
def update_writing_style():
    """Persist an explicitly reviewed writing profile."""
    try:
        profile = save_style_profile(request.json.get('profile'))
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    return jsonify(profile)
