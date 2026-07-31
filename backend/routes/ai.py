"""Authenticated AI editorial assistance for essay drafts."""

import re
from datetime import date

from flask import Blueprint, jsonify, request

from backend.ai_service import AIServiceError, assist_admin_content, assist_essay
from backend.crud import require_json
from backend.data import has_essay_password, load_json
from backend.writing_style import (
    load_style_profile,
    load_style_reference,
    save_style_profile,
)


bp = Blueprint('ai', __name__)
_SLUG_PATTERN = re.compile(r'^[a-z0-9-]+$')
_STYLE_TASKS = {'summary', 'polish', 'review', 'title', 'continue'}
_ADMIN_COPY_TASKS = {'about', 'project', 'photo_story'}


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


@bp.route('/api/ai/admin-assist', methods=['POST'])
@require_json
def admin_assist():
    """Suggest copy for a supported admin surface without persisting it."""
    data = request.json
    if data.get('task') not in _ADMIN_COPY_TASKS:
        return jsonify({'error': '不支持的管理面板 AI 任务'}), 400
    style_profile = load_style_profile()['profile']
    try:
        response = assist_admin_content(
            task=data['task'],
            context=data.get('context'),
            style_profile=style_profile,
        )
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    except AIServiceError as error:
        return jsonify({'error': str(error)}), 503
    return jsonify({
        'task': data['task'],
        **response,
        'style_profile_used': bool(style_profile),
    })


def _public_site_audit_context():
    essays = [
        {
            key: essay.get(key, '')
            for key in ('slug', 'title', 'date', 'excerpt', 'tag')
        }
        for essay in load_json('essays.json')
        if (
            isinstance(essay, dict)
            and isinstance(essay.get('slug'), str)
            and not has_essay_password(essay['slug'])
        )
    ]
    work = [
        {
            key: item.get(key, '')
            for key in ('title', 'description', 'url', 'repo', 'tags')
        }
        for item in load_json('work.json')
        if isinstance(item, dict)
    ]
    stories = [
        {
            key: story.get(key, '')
            for key in ('name', 'date', 'caption', 'photo_count')
        }
        for story in load_json('photo_stories.json')
        if isinstance(story, dict)
    ]
    about = load_json('about.json')
    return {
        'about': about if isinstance(about, dict) else {},
        'essays': essays[:50],
        'projects': work[:30],
        'photo_stories': stories[:30],
        'counts': {
            'essays': len(essays),
            'projects': len(work),
            'photo_stories': len(stories),
        },
        'current_date': date.today().isoformat(),
        'conventions': {
            'essay_tags': '层级标签：主类、技术主题、内容类型，数量可不同',
            'essay_order': '支持置顶和人工编排，不必严格按日期',
            'photo_story_order': '人工策展顺序，不要按日期判定对错',
        },
    }


def _deterministic_content_findings(context):
    findings = []

    def add(priority, area, issue, suggestion):
        findings.append({
            'priority': priority,
            'area': area,
            'issue': issue,
            'suggestion': suggestion,
        })

    about_content = context.get('about', {}).get('content')
    if not isinstance(about_content, str) or not about_content.strip():
        add('high', 'About', '个人简介为空', '补充一段可公开的个人简介')

    seen_titles = set()
    for project in context.get('projects', []):
        title = project.get('title')
        description = project.get('description')
        label = title.strip() if isinstance(title, str) and title.strip() else '未命名项目'
        if not isinstance(title, str) or not title.strip():
            add('high', 'Work', '存在未命名项目', '为项目补充标题')
        elif title.strip().casefold() in seen_titles:
            add('medium', 'Work', f'项目标题重复：{label}', '合并重复项目或区分名称')
        else:
            seen_titles.add(title.strip().casefold())
        if not isinstance(description, str) or not description.strip():
            add('high', 'Work', f'项目“{label}”缺少描述', '补充已实现的核心功能')
            continue
        if description != description.strip():
            add('medium', 'Work', f'项目“{label}”描述存在首尾空格', '删除多余空格')
        if re.search(r'\b(?:todo|tbd|none|panel)\b', description, re.IGNORECASE):
            add('low', 'Work', f'项目“{label}”描述含有含混占位词', '改成明确的中文功能名称')

    for essay in context.get('essays', []):
        title = essay.get('title')
        excerpt = essay.get('excerpt')
        label = title.strip() if isinstance(title, str) and title.strip() else essay.get('slug', '未命名随笔')
        if not isinstance(title, str) or not title.strip():
            add('high', 'Essays', f'随笔“{label}”缺少标题', '补充公开标题')
        if not isinstance(excerpt, str) or not excerpt.strip():
            add('high', 'Essays', f'随笔“{label}”缺少摘要', '补充一句可公开摘要')

    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    return sorted(findings, key=lambda item: priority_order[item['priority']])


@bp.route('/api/ai/site-content-audit', methods=['POST'])
@require_json
def site_content_audit():
    """Review bounded public metadata; protected essay content is excluded."""
    try:
        context = _public_site_audit_context()
        response = assist_admin_content(
            task='site_audit',
            context=context,
        )
    except (OSError, TypeError, ValueError) as error:
        return jsonify({'error': str(error)}), 400
    except AIServiceError as error:
        return jsonify({'error': str(error)}), 503
    combined = _deterministic_content_findings(context)
    seen = {(item['area'], item['issue']) for item in combined}
    for finding in response['result']['findings']:
        key = (finding['area'], finding['issue'])
        if key not in seen:
            combined.append(finding)
            seen.add(key)
    response['result']['findings'] = combined[:10]
    return jsonify(response)
