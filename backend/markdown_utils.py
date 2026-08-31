"""Shared Markdown rendering configuration."""

import html as html_mod
import re

from markdown import markdown as md_to_html


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


def _wiki_anchor(value):
    return re.sub(r'[^\w\u4e00-\u9fff -]', '', value.strip().lower()).replace(' ', '-')


def _expand_wikilinks(md_content, essay_links):
    if not essay_links:
        return md_content
    lookup = {}
    for essay in essay_links:
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
        if not slug:
            return match.group(0)
        href = f'{slug}.html'
        if separator and heading.strip():
            href += '#' + _wiki_anchor(heading)
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


def render_markdown(md_content, essay_links=None):
    md_content = _expand_wikilinks(md_content, essay_links)
    rendered = md_to_html(
        _escape_html_outside_fenced_code(md_content),
        extensions=MARKDOWN_EXTENSIONS,
        extension_configs=MARKDOWN_EXTENSION_CONFIGS,
    )
    rendered = _WIKILINK_LINK_RE.sub(r'<a class="essay-wikilink" href="\1">', rendered)
    # Markdown's URL parser permits scriptable schemes; neutralize them before
    # the HTML is inserted into public pages or the admin preview.
    return _HREF_RE.sub(_sanitize_href, rendered)
