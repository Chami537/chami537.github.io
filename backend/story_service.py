"""Validation and atomic mutations for the public personal stories shelf."""

import re
from datetime import date
from pathlib import Path

from backend.data import BASE_DIR, has_essay_password
from backend.repositories import repository_for


class StoryError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def public_essay_slugs(essays, has_password=has_essay_password):
    return {
        e['slug'] for e in essays if isinstance(e, dict) and e.get('slug')
        and not e.get('hidden') and not e.get('password_protected')
        and not e.get('password') and not has_password(e['slug'])
    }


def validate_story(payload, root=BASE_DIR, allowed_essays=None):
    if not isinstance(payload, dict):
        raise StoryError('应提交作品对象')
    item = {}
    for field, limit, required in (
        ('title', 120, True), ('creator', 120, False),
        ('recommendation', 1000, True), ('cover', 300, False),
        ('finished_on', 10, False), ('essay_slug', 120, False),
    ):
        value = payload.get(field, '')
        if not isinstance(value, str):
            raise StoryError(f'{field} 应为文本')
        value = value.strip()
        if (required and not value) or len(value) > limit:
            raise StoryError(f'{field} 长度应为 {1 if required else 0}–{limit} 字')
        item[field] = value
    if payload.get('type') not in ('movie', 'series', 'novel'):
        raise StoryError('请选择电影、电视剧或小说')
    item['type'] = payload['type']
    for field in ('favorite', 'featured'):
        value = payload.get(field, False)
        if not isinstance(value, bool):
            raise StoryError(f'{field} 应为布尔值')
        item[field] = value
    rating = payload.get('rating')
    if rating is not None and (
        type(rating) not in (int, float) or not 1 <= rating <= 5 or rating * 2 != int(rating * 2)
    ):
        raise StoryError('评分应为 1–5 分，允许半分')
    item['rating'] = rating
    if item['finished_on']:
        try:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', item['finished_on']):
                raise ValueError
            date.fromisoformat(item['finished_on'])
        except ValueError as exc:
            raise StoryError('看完日期应为合法 YYYY-MM-DD') from exc
    if item['cover']:
        cover = item['cover']
        base = Path(root).resolve()
        path = (base / cover).resolve()
        cover_root = (base / 'images' / 'stories').resolve()
        if (not cover.startswith('images/stories/') or '\\' in cover
                or not path.is_relative_to(cover_root) or not path.is_relative_to(base)
                or path.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp', '.gif')
                or not path.is_file()):
            raise StoryError('封面必须是 images/stories/ 下存在的图片')
    if item['essay_slug'] and allowed_essays is not None and item['essay_slug'] not in allowed_essays:
        raise StoryError('关联随笔必须为公开且未加密的文章')
    return item


def save_story(payload, story_id=None):
    allowed = public_essay_slugs(repository_for('essays.json').list())
    item = validate_story(payload, allowed_essays=allowed)
    repository = repository_for('stories.json')
    with repository.locked():
        stories = repository.list()
        if story_id is not None and not any(s['id'] == story_id for s in stories):
            raise StoryError('作品不存在', 404)
        item['id'] = story_id if story_id is not None else max((s['id'] for s in stories), default=0) + 1
        if story_id is None:
            stories.append(item)
        else:
            stories = [item if s['id'] == story_id else s for s in stories]
        repository.save(stories)
    return item


def delete_story(story_id):
    repository = repository_for('stories.json')
    with repository.locked():
        stories = repository.list()
        remaining = [s for s in stories if s['id'] != story_id]
        if len(remaining) == len(stories):
            raise StoryError('作品不存在', 404)
        repository.save(remaining)


def reorder_stories(order):
    repository = repository_for('stories.json')
    with repository.locked():
        stories = repository.list()
        if (not isinstance(order, list) or any(type(i) is not int for i in order)
                or len(order) != len(stories) or len(set(order)) != len(order)
                or set(order) != {s['id'] for s in stories}):
            raise StoryError('排序必须包含所有作品 ID，且不得重复；请刷新后重试')
        by_id = {s['id']: s for s in stories}
        repository.save([by_id[i] for i in order])
