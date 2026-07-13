"""Static asset cache-busting for generated HTML entry points."""

import os
import re

def cache_bust_assets(base_dir):
    """Update CSS/JS query versions from the newest referenced asset mtime."""
    pages = [
        ('index.html', (
            'assets/css/index-foundation.css',
            'assets/css/index-work.css',
            'assets/css/index-photos.css',
            'assets/css/index-content.css',
            'assets/css/index-essays.css',
            'assets/css/index-polish.css',
        ), (
            'assets/js/theme.js',
            'assets/js/index-core.js',
            'assets/js/index-essays.js',
            'assets/js/index-photo-gallery.js',
            'assets/js/index-photo-map.js',
            'assets/js/index-content.js',
            'assets/js/index-lightbox.js',
            'assets/js/index.js',
        )),
        ('admin.html', (
            'assets/css/admin-foundation.css',
            'assets/css/admin-photo.css',
            'assets/css/admin-git.css',
            'assets/css/admin-essay.css',
        ), (
            'assets/js/theme.js',
            'assets/js/admin-core.js',
            'assets/js/admin-dashboard.js',
            'assets/js/admin.js',
            'assets/js/admin-work.js',
            'assets/js/admin-social.js',
            'assets/js/admin-music.js',
            'assets/js/admin-stack.js',
            'assets/js/admin-git.js',
            'assets/js/admin-essay-tags.js',
            'assets/js/admin-essay-security.js',
            'assets/js/admin-about.js',
            'assets/js/admin-essay-editor.js',
            'assets/js/admin-essays-view.js',
            'assets/js/admin-photo-editor.js',
            'assets/js/admin-photo-stories.js',
            'assets/js/admin-upload.js',
            'assets/js/admin-tabs.js',
        )),
    ]
    for html_fn, css_fns, js_fns in pages:
        html_path = os.path.join(base_dir, html_fn)
        if not os.path.exists(html_path):
            continue
        asset_paths = [os.path.join(base_dir, f) for f in css_fns + js_fns]
        existing = [p for p in asset_paths if os.path.exists(p)]
        if not existing:
            continue
        ts = max(int(os.path.getmtime(path)) for path in existing)
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
        for css_fn in css_fns:
            html = re.sub(rf'href="{re.escape(css_fn)}(\?v=\d+)?"', f'href="{css_fn}?v={ts}"', html)
        for js_fn in js_fns:
            html = re.sub(rf'src="{re.escape(js_fn)}(\?v=\d+)?"', f'src="{js_fn}?v={ts}"', html)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
