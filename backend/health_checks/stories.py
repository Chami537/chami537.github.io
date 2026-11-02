"""Read-only shelf integrity checks, including local media and essay links."""

from backend.health_checks.report import check
from backend.story_service import StoryError, public_essay_slugs, validate_story


def check_stories(root, stories, essays, has_password):
    errors, warnings, ids, referenced = [], [], set(), set()
    if stories is None:
        return check('stories.shelf', '精选书架', 'warning', '数据不可用，已跳过')
    allowed = public_essay_slugs(essays or [], has_password)
    for index, item in enumerate(stories):
        label = f'stories.json[{index}]'
        try:
            validated = validate_story(item, root=root)
        except StoryError as exc:
            errors.append(f'{label}: {exc}')
            continue
        story_id = item.get('id')
        if type(story_id) is not int or story_id < 1 or story_id in ids:
            errors.append(f'{label}: ID 无效或重复')
        else:
            ids.add(story_id)
        if validated['cover']:
            referenced.add((root / validated['cover']).resolve())
        if validated['essay_slug'] and validated['essay_slug'] not in allowed:
            warnings.append(f'{label}: 关联随笔不可公开访问，书架将不显示链接')
    cover_root = root / 'images' / 'stories'
    if cover_root.is_dir() and cover_root.resolve().is_relative_to(root):
        for path in cover_root.iterdir():
            if path.is_file() and path.resolve() not in referenced and not path.name.endswith(('.uploading', '.tmp')):
                warnings.append(f'images/stories/{path.name}: 未引用封面')
    status = 'error' if errors else 'warning' if warnings else 'passed'
    return check('stories.shelf', '精选书架', status,
                 '书架存在待处理项目' if errors or warnings else '书架数据正常', errors + warnings)
