"""Read-only integrity checks for the local CMS workspace."""

import base64
import json
import re
from pathlib import Path
from backend.health_checks.report import (
    aggregate as _aggregate,
    check as _check,
    problem_check as _problem_check,
    unavailable as _unavailable,
)
from backend.health_checks.security import check_security


_DATA_TYPES = {
    'about.json': dict,
    'contact.json': list,
    'essays.json': list,
    'friends.json': list,
    'music.json': list,
    'photos.json': list,
    'photo_stories.json': list,
    'stack.json': list,
    'tracks.json': list,
    'work.json': list,
}
_CORE_FILES = (
    'admin.html',
    'index.html',
    'templates/essay.html',
    'assets/js/admin-api.js',
    'assets/js/admin-ui.js',
    'assets/js/admin-tabs.js',
    'assets/js/admin-health.js',
    'assets/css/admin-foundation.css',
    'assets/css/admin-health.css',
)
_SLUG_RE = re.compile(r'^[a-z0-9-]+$')
_IGNORED_MEDIA_SUFFIXES = ('.tmp', '.uploading', '.deleting')


def _load_data(root):
    loaded = {}
    details = []
    for filename, expected_type in _DATA_TYPES.items():
        path = root / 'data' / filename
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
        except FileNotFoundError:
            details.append(f'{filename}: 文件缺失')
            continue
        except (OSError, UnicodeDecodeError):
            details.append(f'{filename}: 文件无法读取')
            continue
        except json.JSONDecodeError:
            details.append(f'{filename}: JSON 无法解析')
            continue
        if not isinstance(value, expected_type):
            details.append(f'{filename}: 顶层类型应为 {expected_type.__name__}')
            continue
        loaded[filename] = value
    return loaded, _check(
        'data.json', 'JSON 数据', 'error' if details else 'passed',
        '数据文件存在问题' if details else '数据文件正常', details,
    )


def _safe_relative(root, path):
    resolved = path.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return None


def _encrypted_source(text):
    try:
        raw = base64.b64decode(text.split('\n', 1)[0], validate=True)
        return len(raw) > 17 and raw[0] == 2
    except (ValueError, TypeError):
        return False


def _valid_http_url(value):
    return not value or str(value).strip().lower().startswith(('http://', 'https://'))


def _check_essays(root, essays, has_password):
    if essays is None:
        return _unavailable('essays.sources', '随笔源文件')
    details = []
    essays_dir = root / 'essays'
    for essay in essays:
        slug = str(essay.get('slug', ''))
        if not _SLUG_RE.fullmatch(slug):
            details.append(f'{slug or "<empty>"}: slug 不合法')
            continue
        md_path = root / 'md' / f'{slug}.md'
        if not md_path.is_file():
            details.append(f'md/{slug}.md: 文件缺失')
            continue
        try:
            source = md_path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            details.append(f'md/{slug}.md: 文件无法读取')
            continue
        protected = bool(has_password(slug))
        encrypted = _encrypted_source(source)
        if protected != encrypted:
            details.append(f'md/{slug}.md: 密码状态与密文状态不一致')
        html_path = essays_dir / f'{slug}.html'
        if essays_dir.is_dir() and not html_path.is_file():
            details.append(f'essays/{slug}.html: 生成文件缺失')
        elif protected and html_path.is_file():
            try:
                html = html_path.read_text(encoding='utf-8')
            except (OSError, UnicodeDecodeError):
                details.append(f'essays/{slug}.html: 文件无法读取')
            else:
                if 'class="essay-gate"' not in html and "class='essay-gate'" not in html:
                    details.append(f'essays/{slug}.html: 缺少密码门')
    return _problem_check(
        'essays.sources', '随笔源文件', details,
        '随笔文件存在不一致' if details else '随笔源文件正常',
    ) if details else _check('essays.sources', '随笔源文件', 'passed', '随笔源文件正常')


def _photo_names(photos):
    return {str(photo.get('filename', '')) for photo in photos if photo.get('filename')}


def _check_photos(root, photos):
    if photos is None:
        return _unavailable('photos.variants', '照片文件完整性')
    details = []
    for filename in sorted(_photo_names(photos)):
        paths = [root / 'images' / size / filename for size in ('lg', 'md', 'sm')]
        for path in paths:
            if not path.is_file():
                details.append(f'{_safe_relative(root, path)}: 文件缺失')
    return _problem_check(
        'photos.variants', '照片文件完整性', details,
        '照片引用文件缺失' if details else '照片文件完整',
    ) if details else _check('photos.variants', '照片文件完整性', 'passed', '照片文件完整')


def _check_photo_stories(photos, stories):
    if photos is None or stories is None:
        return _unavailable('photos.stories', '照片故事引用')
    valid = _photo_names(photos)
    details = []
    for story in stories:
        story_id = story.get('id', '<empty>')
        story_photos = story.get('photos') or []
        for filename in story_photos + ([story.get('cover')] if story.get('cover') else []):
            if filename not in valid:
                details.append(f'{story_id}: 引用了不存在的照片 {filename}')
    return _problem_check(
        'photos.stories', '照片故事引用', details,
        '照片故事存在无效引用' if details else '照片故事引用正常',
    ) if details else _check('photos.stories', '照片故事引用', 'passed', '照片故事引用正常')


def _check_media(root, music, tracks):
    if music is None or tracks is None:
        return _unavailable('media.files', '音乐与轨迹文件')
    details = []
    for item in music:
        filename = str(item.get('filename', ''))
        if filename and not (root / 'music' / Path(filename).name).is_file():
            details.append(f'music/{Path(filename).name}: 文件缺失')
    for item in tracks:
        filename = str(item.get('file', ''))
        if filename and not (root / 'tracks' / Path(filename).name).is_file():
            details.append(f'tracks/{Path(filename).name}: 文件缺失')
    return _problem_check(
        'media.files', '音乐与轨迹文件', details,
        '媒体引用文件缺失' if details else '音乐与轨迹文件正常',
    ) if details else _check('media.files', '音乐与轨迹文件', 'passed', '音乐与轨迹文件正常')


def _check_orphans(root, photos, music, tracks):
    if photos is None or music is None or tracks is None:
        return _unavailable('media.orphans', '孤立媒体文件')
    references = {
        'images/lg': _photo_names(photos),
        'images/md': _photo_names(photos),
        'images/sm': _photo_names(photos),
        'music': {Path(str(item.get('filename', ''))).name for item in music},
        'tracks': {Path(str(item.get('file', ''))).name for item in tracks},
    }
    details = []
    for directory, names in references.items():
        folder = root / directory
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if path.is_file() and path.suffix not in _IGNORED_MEDIA_SUFFIXES and path.name not in names:
                details.append(f'{directory}/{path.name}')
    details.sort()
    return _problem_check(
        'media.orphans', '孤立媒体文件', details,
        '发现未被数据引用的媒体文件' if details else '没有孤立媒体文件', 'warning',
    ) if details else _check('media.orphans', '孤立媒体文件', 'passed', '没有孤立媒体文件')


def _check_links(data):
    if not all(name in data for name in ('work.json', 'contact.json', 'friends.json')):
        return _unavailable('links.protocols', '外链协议')
    details = []
    for filename in ('work.json', 'contact.json', 'friends.json'):
        for index, item in enumerate(data[filename]):
            url = item.get('url', '') if isinstance(item, dict) else ''
            if url and not _valid_http_url(url):
                details.append(f'{filename}[{index}]: URL 协议不安全')
    return _problem_check(
        'links.protocols', '外链协议', details,
        '存在非 HTTP(S) 外链' if details else '外链协议正常', 'warning',
    ) if details else _check('links.protocols', '外链协议', 'passed', '外链协议正常')


def _check_build_files(root):
    details = [_safe_relative(root, root / relative) for relative in _CORE_FILES if not (root / relative).is_file()]
    return _problem_check(
        'build.core', '核心构建文件', details,
        '核心文件缺失' if details else '核心构建文件正常',
    ) if details else _check('build.core', '核心构建文件', 'passed', '核心构建文件正常')


def run_site_health(base_dir, has_password):
    root = Path(base_dir).resolve()
    data, data_check = _load_data(root)
    checks = [
        data_check,
        _check_essays(root, data.get('essays.json'), has_password),
        _check_photos(root, data.get('photos.json')),
        _check_photo_stories(data.get('photos.json'), data.get('photo_stories.json')),
        _check_media(root, data.get('music.json'), data.get('tracks.json')),
        _check_orphans(root, data.get('photos.json'), data.get('music.json'), data.get('tracks.json')),
        _check_links(data),
        _check_build_files(root),
        check_security(root, data.get('essays.json'), has_password, _SLUG_RE),
    ]
    return _aggregate(checks)
