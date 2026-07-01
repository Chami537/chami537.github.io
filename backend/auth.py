"""Simple password auth for the admin panel — local dev, session-based."""
import os

from flask import session, request, jsonify

from backend.app import app

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'chami')


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    if data.get('password') == ADMIN_PASSWORD:
        session['authenticated'] = True
        return jsonify({"status": "ok"})
    return jsonify({"error": "Wrong password"}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('authenticated', None)
    return jsonify({"status": "logged out"})
