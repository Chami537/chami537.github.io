"""Simple password auth for the admin panel — local dev, session-based."""
import hmac
import os
import time

from flask import Blueprint, session, request, jsonify

bp = Blueprint('auth', __name__)

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'chami')
if 'ADMIN_PASSWORD' not in os.environ:
    print('WARNING: ADMIN_PASSWORD not set — using default. Set in .env for security.')

# Simple in-memory rate limiter: {ip: [attempt_timestamps]}
_LOGIN_ATTEMPTS = {}


@bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True)
    password = data.get('password') if isinstance(data, dict) else None
    if not isinstance(password, str):
        return jsonify({"error": "Password must be a string"}), 400

    ip = request.remote_addr or '127.0.0.1'
    now = time.time()
    window = _LOGIN_ATTEMPTS.get(ip, [])
    # Keep only attempts in the last 60 seconds
    window = [t for t in window if now - t < 60]
    if len(window) >= 10:
        return jsonify({"error": "Too many attempts, wait 60s"}), 429
    window.append(now)
    _LOGIN_ATTEMPTS[ip] = window

    if hmac.compare_digest(password, ADMIN_PASSWORD):
        session['authenticated'] = True
        _LOGIN_ATTEMPTS.pop(ip, None)
        return jsonify({"status": "ok"})
    return jsonify({"error": "Wrong password"}), 401


@bp.route('/api/logout', methods=['POST'])
def logout():
    session.pop('authenticated', None)
    return jsonify({"status": "logged out"})
