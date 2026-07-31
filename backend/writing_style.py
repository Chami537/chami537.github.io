"""Bounded public essay samples for personal writing-style prompts."""

import re
from datetime import datetime
from pathlib import Path

from backend.data import MD_DIR, has_essay_password, load_json
from backend.essay_crypto import is_encrypted_content


MAX_STYLE_ESSAYS = 4
MAX_SAMPLE_CHARS = 1_500
MAX_TOTAL_CHARS = 5_000
MIN_USEFUL_SAMPLE_CHARS = 300

_SLUG_PATTERN = re.compile(r'^[a-z0-9-]+$')
_IMAGE_LINE = re.compile(r'^\s*!\[[^\]]*\]\([^)]*\)\s*$')
_URL_LINE = re.compile(r'^\s*https?://\S+\s*$')


def _date_key(value):
    if not isinstance(value, str):
        return datetime.min
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError:
        return datetime.min


def _clean_markdown(content):
    lines = content.splitlines()
    output = []
    in_front_matter = bool(lines and lines[0].strip() == '---')
    in_fence = False

    for index, line in enumerate(lines):
        stripped = line.strip()
        if in_front_matter:
            if index and stripped == '---':
                in_front_matter = False
            continue
        if stripped.startswith(('```', '~~~')):
            in_fence = not in_fence
            continue
        if in_fence or _IMAGE_LINE.fullmatch(line) or _URL_LINE.fullmatch(line):
            continue
        if not stripped and (not output or output[-1] == ''):
            continue
        output.append(line.rstrip())

    return '\n'.join(output).strip()


def _tag_parts(value):
    if isinstance(value, str):
        return {part.strip().casefold() for part in value.split(',') if part.strip()}
    if isinstance(value, list):
        return {part.strip().casefold() for part in value if isinstance(part, str) and part.strip()}
    return set()


def load_style_reference(
    current_slug,
    *,
    current_tags=None,
    metadata_loader=None,
    password_checker=None,
    md_dir=None,
):
    """Return recent public prose samples, degrading safely when unavailable."""
    metadata_loader = metadata_loader or load_json
    password_checker = password_checker or has_essay_password
    md_dir = Path(md_dir or MD_DIR)

    try:
        essays = metadata_loader('essays.json')
    except (OSError, TypeError, ValueError):
        return {'samples': [], 'count': 0}
    if not isinstance(essays, list):
        return {'samples': [], 'count': 0}

    candidates = [
        essay for essay in essays
        if (
            isinstance(essay, dict)
            and isinstance(essay.get('slug'), str)
            and _SLUG_PATTERN.fullmatch(essay['slug'])
            and essay['slug'] != current_slug
        )
    ]
    current_tag_set = _tag_parts(current_tags)
    prepared = []
    for essay in candidates:
        slug = essay['slug']
        try:
            if password_checker(slug):
                continue
            content = (md_dir / f'{slug}.md').read_text(encoding='utf-8')
        except (OSError, TypeError, ValueError):
            continue
        if is_encrypted_content(content):
            continue

        cleaned = _clean_markdown(content)
        if not cleaned:
            continue
        prepared.append((
            len(current_tag_set & _tag_parts(essay.get('tag'))),
            _date_key(essay.get('date')),
            essay,
            cleaned,
        ))

    useful = [item for item in prepared if len(item[3]) >= MIN_USEFUL_SAMPLE_CHARS]
    if useful:
        prepared = useful
    prepared.sort(key=lambda item: (item[0], item[1]), reverse=True)

    samples = []
    remaining = MAX_TOTAL_CHARS
    for _overlap, _date, essay, cleaned in prepared:
        if len(samples) >= MAX_STYLE_ESSAYS or remaining <= 0:
            break
        cleaned = cleaned[:min(MAX_SAMPLE_CHARS, remaining)].rstrip()
        if not cleaned:
            continue
        title = essay.get('title')
        samples.append({
            'title': title.strip() if isinstance(title, str) and title.strip() else slug,
            'content': cleaned,
        })
        remaining -= len(cleaned)

    return {'samples': samples, 'count': len(samples)}
