"""Tag parsing and adjacent-navigation helpers for essays."""

import html as html_mod
import re


def parse_tags(tag_str, essay=None):
    tags = set(t.strip() for t in re.split(r'[,，]', tag_str) if t.strip()) if tag_str else set()
    if essay and essay.get('pinned'):
        tags.add('置顶')
    return tags


def find_adjacent_siblings(essays, idx, siblings):
    prev_sib, next_sib = None, None
    for i in range(idx - 1, -1, -1):
        if essays[i] in siblings:
            prev_sib = essays[i]
            break
    for i in range(idx + 1, len(essays)):
        if essays[i] in siblings:
            next_sib = essays[i]
            break
    return prev_sib, next_sib


def build_nav(essays, current_slug):
    current = next((e for e in essays if e['slug'] == current_slug), None)
    current_tags = parse_tags(current.get('tag', ''), current) if current else set()
    if current_tags:
        siblings = [e for e in essays if e['slug'] != current_slug and parse_tags(e.get('tag', ''), e) & current_tags]
    else:
        siblings = [e for e in essays if e['slug'] != current_slug]
    idx = next((i for i, e in enumerate(essays) if e['slug'] == current_slug), -1)
    prev_sib, next_sib = find_adjacent_siblings(essays, idx, siblings)

    prev_nav = '<div></div>'
    next_nav = '<div></div>'
    if prev_sib:
        prev_nav = f'''<a href="{prev_sib['slug']}.html" class="prev-link">
      <span class="prev-label">上一篇</span>
      <div class="prev-title">
        <span class="prev-arr">←</span>
        <span>{html_mod.escape(prev_sib['title'])}</span>
      </div>
    </a>'''
    if next_sib:
        next_nav = f'''<a href="{next_sib['slug']}.html" class="next-link">
      <span class="next-label">下一篇</span>
      <div class="next-title">
        <span>{html_mod.escape(next_sib['title'])}</span>
        <span class="next-arr">→</span>
      </div>
    </a>'''
    return prev_nav, next_nav
