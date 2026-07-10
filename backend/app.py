"""Flask application for the Chami CMS — app creation + static file serving."""

import os
import secrets
from urllib.parse import urlparse
from flask import Flask, request, send_from_directory
from flask import jsonify, session

from backend.data import BASE_DIR, DATA_DIR, ESSAYS_DIR, IMAGES_DIR

app = Flask(__name__)
_secret = os.environ.get('FLASK_SECRET_KEY', '')
if _secret:
    app.secret_key = _secret
else:
    app.secret_key = secrets.token_hex(32)
    if not app.config.get('TESTING'):
        print('WARNING: FLASK_SECRET_KEY not set — using random key (sessions reset on restart)')

app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
app.config['SESSION_COOKIE_SECURE'] = True


# ── Auth guard: all /api/* requires login except /api/login (skipped in test mode) ──
@app.before_request
def _require_auth():
    if app.config.get('TESTING'):
        return None
    if request.path == '/api/login':
        return None
    if request.path.startswith('/api/') and not session.get('authenticated'):
        return jsonify({"error": "Unauthorized"}), 401


# ── CSRF check: reject cross-origin state-changing requests ──
@app.before_request
def _csrf_check():
    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        origin = request.headers.get('Origin', '')
        if origin:
            expected = app.config.get('SERVER_NAME') or request.host
            if urlparse(origin).netloc != expected:
                return jsonify({"error": "CSRF check failed"}), 403


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
_ROOTS = ['theme.js', 'rss.xml', 'sitemap.xml', 'archive.html', 'map.html', 'index.css', 'index.js', 'admin.css', 'admin.js', 'admin-content.js', 'admin-essays.js', 'admin-photos.js']
for _f in _ROOTS:
    _ep = f'serve_{_f.replace(".", "_")}'
    app.add_url_rule(f'/{_f}', _ep, lambda _f=_f: send_from_directory(BASE_DIR, _f))


# Register all /api/* routes (side-effect imports — must come after app creation)
from backend import routes       # noqa: E402,F401
from backend import auth         # noqa: E402,F401  — login/logout endpoints
