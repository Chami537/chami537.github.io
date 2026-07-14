"""Essay collection, creation, and tag-order routes."""

import re

from flask import jsonify, request

from backend.crud import require_json
from backend.data import has_essay_password, set_essay_password as store_password
from backend.ssg import _calc_read_time, _generate_feeds, _parse_date, _sync_essay_html
from backend.routes import essay_context


@essay_context.bp.route('/api/tags/order', methods=['GET'])
def get_tag_order():
    return jsonify(essay_context.ESSAY_REPOSITORY.read_tag_order())


@essay_context.bp.route('/api/tags/order', methods=['PUT'])
@require_json
def save_tag_order():
    order = request.json.get('order', [])
    if not isinstance(order, list):
        return jsonify({"error": "order must be a list"}), 400
    essay_context.ESSAY_REPOSITORY.save_tag_order(order)
    _generate_feeds()
    return jsonify({"status": "saved"})


@essay_context.bp.route('/api/essays', methods=['GET'])
def list_essays():
    return jsonify(essay_context.ESSAY_SERVICE.list_for_admin(_parse_date, has_essay_password))


@essay_context.bp.route('/api/essays', methods=['POST'])
@require_json
def create_essay():
    essays = essay_context.ESSAY_REPOSITORY.list()
    item = request.json
    error, status = _validate_new_essay(item, essays)
    if error:
        return jsonify({"error": error}), status
    slug = item['slug']
    body_md = _prepare_new_essay(item, slug)
    essays.append(item)
    essay_context.ESSAY_REPOSITORY.save(essays)
    _sync_created_essay(item, body_md, essays)
    return jsonify(item), 201


def _validate_new_essay(item, essays):
    slug = item.get('slug', '')
    if not slug or not re.match(r'^[a-z0-9-]+$', slug):
        return "slug 只能包含小写字母、数字和连字符", 400
    if any(essay['slug'] == slug for essay in essays):
        return 'slug 已存在', 409
    return None, None


def _prepare_new_essay(item, slug):
    password = item.pop('password', '')
    if password:
        store_password(slug, password)
    body_md = item.get('body', '')
    item['readTime'] = _calc_read_time(body_md or item.get('content', ''))
    return body_md


def _sync_created_essay(item, body_md, essays):
    _sync_essay_html(item, raw_md_memory=body_md if body_md else None, essays=essays)
    if len(essays) > 1:
        _sync_essay_html(essays[-2], essays=essays)
    _generate_feeds()
