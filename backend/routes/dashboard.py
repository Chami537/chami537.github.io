from datetime import datetime

from flask import Blueprint, jsonify

bp = Blueprint('dashboard', __name__)
from backend.data import has_essay_password
from backend.repositories import repository_for


def load_json(name):
    return repository_for(name).list()


_STAT_DATA_FILES = (
    'essays.json', 'photos.json', 'photo_stories.json', 'work.json',
    'music.json', 'friends.json', 'stack.json',
)
_ESSAY_MAIN_TAGS = {'随笔', '生活', '摄影', '阅读', '感悟', '技术'}


def _build_counts(essays, photos, stories, work, music, friends, stack):
    hidden = sum(1 for essay in essays if essay.get('hidden'))
    encrypted = sum(1 for essay in essays if has_essay_password(essay.get('slug', '')))
    return {
        'essays': {
            'total': len(essays),
            'public': len(essays) - hidden - encrypted,
            'encrypted': encrypted,
        },
        'photos': len(photos),
        'photo_stories': len(stories),
        'places': sum(1 for photo in photos if _has_gps(photo)),
        'work': len(work),
        'music': len(music),
        'friends': len(friends),
        'stack': len(stack),
    }


def _has_gps(photo):
    gps = (photo.get('exif') or {}).get('gps') or {}
    return 'lat' in gps and 'lng' in gps


def _essay_tag_counts(essays):
    primary = {}
    secondary = {}
    for essay in essays:
        tags = [raw_tag.strip() for raw_tag in str(essay.get('tag', '')).split(',') if raw_tag.strip()]
        is_technical = '技术' in tags
        for raw_tag in tags:
            tag = raw_tag.strip()
            bucket = secondary if is_technical and tag not in _ESSAY_MAIN_TAGS else primary
            bucket[tag] = bucket.get(tag, 0) + 1

    def sort_counts(counts):
        return [
            {'name': name, 'count': count}
            for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]

    return {'primary': sort_counts(primary), 'secondary': sort_counts(secondary)}


def _date_key(value):
    text = str(value or '').strip()
    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d', '%b %Y', '%B %Y'):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return datetime.min


def _recent_items(essays, stories):
    items = [
        {
            'type': 'essay',
            'title': essay.get('title', ''),
            'date': essay.get('date', ''),
            'url': '/essays/' + essay.get('slug', '') + '.html',
            '_date': _date_key(essay.get('date')),
        }
        for essay in essays
    ]
    items.extend(
        {
            'type': 'photo_story',
            'title': story.get('name', story.get('title', '')),
            'date': story.get('date', ''),
            'url': '/index.html#photos',
            '_date': _date_key(story.get('date')),
        }
        for story in stories
    )
    items.sort(key=lambda item: item['_date'], reverse=True)
    for item in items:
        item.pop('_date', None)
    return items[:8]


@bp.route('/api/dashboard-stats', methods=['GET'])
def dashboard_stats():
    try:
        data = {name: load_json(name) for name in _STAT_DATA_FILES}
        return jsonify({
            'counts': _build_counts(
                data['essays.json'], data['photos.json'], data['photo_stories.json'],
                data['work.json'], data['music.json'], data['friends.json'], data['stack.json'],
            ),
            'tags': _essay_tag_counts(data['essays.json']),
            'recent': _recent_items(data['essays.json'], data['photo_stories.json']),
        })
    except (OSError, ValueError, TypeError, KeyError):
        return jsonify({'error': '无法读取统计数据'}), 500
