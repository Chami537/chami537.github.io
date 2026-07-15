"""Static asset cache-busting for generated HTML entry points."""

import os
import re


_ASSET_REFERENCE_RE = re.compile(
    r'(?P<prefix>\b(?:href|src)\s*=\s*)'
    r'(?P<quote>["\'])'
    r'(?P<path>assets/(?:css|js)/[^?"\']+)'
    r'(?:\?v=\d+)?'
    r'(?P=quote)',
)


def cache_bust_assets(base_dir):
    """Version every local CSS/JS asset actually referenced by each entry page."""
    for html_filename in ('index.html', 'admin.html'):
        html_path = os.path.join(base_dir, html_filename)
        if not os.path.exists(html_path):
            continue
        with open(html_path, 'r', encoding='utf-8') as handle:
            html = handle.read()

        referenced = {match.group('path') for match in _ASSET_REFERENCE_RE.finditer(html)}
        existing = {
            path: os.path.join(base_dir, path)
            for path in referenced
            if os.path.exists(os.path.join(base_dir, path))
        }
        if not existing:
            continue
        timestamp = max(int(os.path.getmtime(path)) for path in existing.values())

        def add_version(match):
            path = match.group('path')
            if path not in existing:
                return match.group(0)
            return (
                f"{match.group('prefix')}{match.group('quote')}"
                f"{path}?v={timestamp}{match.group('quote')}"
            )

        updated = _ASSET_REFERENCE_RE.sub(add_version, html)
        with open(html_path, 'w', encoding='utf-8') as handle:
            handle.write(updated)
