"""Shared Markdown rendering configuration."""

import html as html_mod
import re

from markdown import markdown as md_to_html
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from markdown.util import HTML_PLACEHOLDER_RE, STX, ETX

from backend.image_utils import image_dimensions, local_image_path


MARKDOWN_EXTENSIONS = [
    'extra',
    'fenced_code',
    'sane_lists',
    'pymdownx.arithmatex',
    'pymdownx.tilde',
    'pymdownx.tasklist',
]

MARKDOWN_EXTENSION_CONFIGS = {
    'pymdownx.arithmatex': {'generic': True},
    'pymdownx.tasklist': {'custom_checkbox': True},
}

_HREF_RE = re.compile(r'(?i)(href\s*=\s*)(["\'])(.*?)\2', re.DOTALL)
_SCRIPTABLE_SCHEMES = frozenset({'javascript', 'vbscript', 'data'})
_WIKILINK_RE = re.compile(r'\[\[([^\[\]]+)\]\]')
_WIKILINK_LINK_RE = re.compile(r'<a href="([^"]+)" title="wikilink">')
# ECMAScript's \s differs from Python's for BOM, NEL and control separators.
_ANCHOR_SPACE = '\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff'


def heading_id(value):
    """Match essayHeadingId in essay-toc.js, preserving established TOC URLs."""
    slug = re.sub('[^a-z0-9_\u3400-\u9fff' + _ANCHOR_SPACE + '-]', '', str(value or '').lower())
    slug = re.sub('[' + _ANCHOR_SPACE + '_-]+', '-', slug).strip('-')
    return 'heading-' + (slug or 'section')


def heading_ids(texts, existing_ids=None, reserved=()):
    """Deterministic IDs, including repeated headings and explicit Markdown IDs."""
    existing_ids = existing_ids or [''] * len(texts)
    provided = set(filter(None, existing_ids))
    used = set(reserved)
    result = []
    for text, existing in zip(texts, existing_ids):
        base = existing or heading_id(text)
        value, suffix = base, 2
        while value in used or (not existing and value in provided):
            value = f'{base}-{suffix}'
            suffix += 1
        result.append(value)
        used.add(value)
    return result


_ESCAPED_CHAR_RE = re.compile(re.escape(STX) + r'(\d+)' + re.escape(ETX))


def _heading_text(element, md):
    """Plain heading text as a browser would expose it.

    This treeprocessor runs before the unescape treeprocessor, so raw
    itertext still contains html-stash placeholders (entities / raw HTML)
    and STX<char-code>ETX backslash-escape sequences. Restore both before
    deriving the ID, so SSG output matches wikilinks and the client TOC.
    """
    text = ''.join(element.itertext())
    stash = getattr(md, 'htmlStash', None)
    blocks = getattr(stash, 'rawHtmlBlocks', []) if stash is not None else []

    def _restore(match):
        index = int(match.group(1))
        if 0 <= index < len(blocks):
            item = blocks[index]
            return item[0] if isinstance(item, tuple) else str(item)
        return match.group(0)

    text = HTML_PLACEHOLDER_RE.sub(_restore, text)
    text = _ESCAPED_CHAR_RE.sub(lambda m: chr(int(m.group(1))), text)
    return html_mod.unescape(text)


class _EssayTreeprocessor(Treeprocessor):
    def __init__(self, md, base_dir):
        super().__init__(md)
        self.base_dir = base_dir

    def run(self, root):
        headings = [element for element in root.iter() if element.tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')]
        ids = heading_ids(
            [_heading_text(element, self.md) for element in headings],
            [element.get('id', '') for element in headings],
            [element.get('id') for element in root.iter() if element not in headings and element.get('id')],
        )
        for element, value in zip(headings, ids):
            element.set('id', value)
        for index, image in enumerate(root.iter('img')):
            path = local_image_path(image.get('src', ''), self.base_dir)
            dimensions = image_dimensions(path) if path else None
            if dimensions:
                image.set('width', str(dimensions[0]))
                image.set('height', str(dimensions[1]))
            if index:
                image.set('loading', 'lazy')


class _EssayExtension(Extension):
    def __init__(self, base_dir):
        self.base_dir = base_dir
        super().__init__()

    def extendMarkdown(self, md):
        # Run after inline text and attr_list have been expanded.
        md.treeprocessors.register(_EssayTreeprocessor(md, self.base_dir), 'essay_metadata', 5)


def _expand_wikilinks(md_content, essay_links):
    lookup = {}
    for essay in essay_links or []:
        if not isinstance(essay, dict) or not essay.get('slug'):
            continue
        title = str(essay.get('title', '')).strip()
        if title:
            lookup[title.casefold()] = str(essay['slug'])

    def replace(match):
        target = match.group(1).strip()
        parts = target.split('|', 1)
        destination = parts[0].strip()
        label = parts[1].strip() if len(parts) == 2 and parts[1].strip() else destination
        note, separator, heading = destination.partition('#')
        slug = lookup.get(note.strip().casefold())
        if not slug and note.strip():
            return match.group(0)
        href = f'{slug}.html' if slug else ''
        if separator and heading.strip():
            href += '#' + heading_id(heading)
        return f'[{label}]({href} "wikilink")'

    return _WIKILINK_RE.sub(replace, md_content)


def _escape_html_outside_fenced_code(md_content):
    parts = re.split(r'(```[\s\S]*?```)', md_content)
    escaped = []
    for part in parts:
        if part.startswith('```') and part.endswith('```'):
            escaped.append(part)
        else:
            inline_parts = re.split(r'(`+[^`\n]+?`+)', part)
            escaped.extend(
                inline if inline.startswith('`') and inline.endswith('`')
                else inline.replace('<', '&lt;')
                for inline in inline_parts
            )
    return ''.join(escaped)


def _sanitize_href(match):
    value = html_mod.unescape(match.group(3))
    canonical = ''.join(
        char for char in value
        if ord(char) > 0x20 and ord(char) != 0x7f
    )
    scheme = canonical.split(':', 1)[0].lower() if ':' in canonical else ''
    if scheme in _SCRIPTABLE_SCHEMES:
        return f'{match.group(1)}{match.group(2)}#blocked:{match.group(2)}'
    return match.group(0)


def render_markdown(md_content, essay_links=None, base_dir=None):
    if base_dir is None:
        from backend.data import BASE_DIR
        base_dir = BASE_DIR
    md_content = _expand_wikilinks(md_content, essay_links)
    rendered = md_to_html(
        _escape_html_outside_fenced_code(md_content),
        extensions=[*MARKDOWN_EXTENSIONS, _EssayExtension(base_dir)],
        extension_configs=MARKDOWN_EXTENSION_CONFIGS,
    )
    rendered = _WIKILINK_LINK_RE.sub(r'<a class="essay-wikilink" href="\1">', rendered)
    # Markdown's URL parser permits scriptable schemes; neutralize them before
    # the HTML is inserted into public pages or the admin preview.
    return _HREF_RE.sub(_sanitize_href, rendered)
