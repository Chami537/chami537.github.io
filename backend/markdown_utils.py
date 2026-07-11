"""Shared Markdown rendering configuration."""

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


def render_markdown(md_content):
    return md_to_html(
        _escape_html_outside_fenced_code(md_content),
        extensions=MARKDOWN_EXTENSIONS,
        extension_configs=MARKDOWN_EXTENSION_CONFIGS,
    )
