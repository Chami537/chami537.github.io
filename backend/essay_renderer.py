"""Pure HTML rendering and output helpers for generated essay pages."""

import html as html_mod
import os

from markupsafe import Markup


def render_essay_html(essay, body_data, essays, template, parse_date):
    """Render one essay page from already-prepared body and navigation data."""
    slug = essay['slug']
    prev_nav, next_nav = _navigation(essays, slug)
    tag_raw = essay.get('tag', '')
    return template.render(
        title=html_mod.escape(essay.get('title', '')),
        excerpt=html_mod.escape(essay.get('excerpt', '')),
        epigraph=html_mod.escape(essay.get('epigraph', '')),
        tag=html_mod.escape(tag_raw.replace(', ', ' · ').replace(',', ' · ')),
        date_display=html_mod.escape(parse_date(essay.get('date', ''))),
        read_time=essay.get('readTime', 1),
        body_html=Markup(body_data['body_html']),
        encrypted_body=body_data['encrypted_body'],
        password_protected=body_data['password_protected'],
        encrypted_is_md=body_data['encrypted_is_md'],
        last_edited=html_mod.escape(parse_date(essay.get('date', ''), include_time=True)),
        prev_nav=Markup(prev_nav),
        next_nav=Markup(next_nav),
        slug=slug,
        og_image=html_mod.escape(body_data['og_image']),
        build_ts=__import__('time').time_ns() // 1_000_000_000,
    )


def write_essay_html(path, html):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as output:
        output.write(html)


def _navigation(essays, slug):
    from backend.essay_navigation import build_nav
    return build_nav(essays, slug)
