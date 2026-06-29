"""Flask application for the Chami CMS — app creation + static file serving."""

import os
from flask import Flask, send_from_directory

from data import BASE_DIR, DATA_DIR

ESSAYS_DIR = os.path.join(BASE_DIR, 'essays')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')

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

@app.route('/rss.xml')
def serve_rss():
    return send_from_directory(BASE_DIR, 'rss.xml')

@app.route('/sitemap.xml')
def serve_sitemap():
    return send_from_directory(BASE_DIR, 'sitemap.xml')

@app.route('/archive.html')
def serve_archive():
    return send_from_directory(BASE_DIR, 'archive.html')

@app.route('/map.html')
def serve_map():
    return send_from_directory(BASE_DIR, 'map.html')


# Register all /api/* routes (side-effect import — must come after app creation)
import routes  # noqa: E402,F401
