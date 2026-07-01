"""Flask application for the Chami CMS — app creation + static file serving."""

import os
from flask import Flask, send_from_directory

from backend.data import BASE_DIR, DATA_DIR, ESSAYS_DIR, IMAGES_DIR

app = Flask(__name__)


# ── Admin UI ──
@app.route('/')
def admin_panel():
    return send_from_directory(BASE_DIR, 'admin.html')


# ── Static file serving (for index.html preview) ──
@app.route('/data/<path:filename>')
def serve_data(filename):
    return send_from_directory(DATA_DIR, filename)


@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory(IMAGES_DIR, filename)


@app.route('/index.html')
def serve_index():
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/essays/<path:filename>')
def serve_essay(filename):
    return send_from_directory(ESSAYS_DIR, filename)


@app.route('/music/<path:filename>')
def serve_music(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'music'), filename)


@app.route('/tracks/<path:filename>')
def serve_tracks(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'tracks'), filename)


# Routes for root-level generated files (rss, sitemap, archive, map, CSS, JS)
_ROOTS = ['rss.xml', 'sitemap.xml', 'archive.html', 'map.html', 'index.css', 'index.js', 'admin.css', 'admin.js']
for _f in _ROOTS:
    _ep = f'serve_{_f.replace(".", "_")}'
    app.add_url_rule(f'/{_f}', _ep, lambda _f=_f: send_from_directory(BASE_DIR, _f))


# Register all /api/* routes (side-effect imports — must come after app creation)
from backend import routes       # noqa: E402,F401
from backend import photo_api   # noqa: E402,F401  — photo tags/date/gps PUT routes
