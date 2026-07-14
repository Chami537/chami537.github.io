"""Read-only site health API."""

from flask import Blueprint, jsonify

from backend.data import BASE_DIR, has_essay_password
from backend.site_health import run_site_health


bp = Blueprint('health', __name__)


@bp.route('/api/site-health', methods=['GET'])
def site_health():
    try:
        return jsonify(run_site_health(BASE_DIR, has_essay_password))
    except (OSError, ValueError, TypeError):
        return jsonify({'error': '无法完成站点健康检查'}), 500
