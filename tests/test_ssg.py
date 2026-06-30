"""Tests for SSG functions and EXIF helpers."""
import os
import json
import pytest
from PIL import Image
from backend.ssg import (
    _extract_exif, _extract_gps, _calc_read_time, _parse_date,
    _parse_tags, _find_adjacent_siblings, _extract_first_image,
)
from backend.data import load_json


# ── _calc_read_time ──

def test_calc_read_time_empty():
    assert _calc_read_time('') == 1
    assert _calc_read_time(None) == 1

def test_calc_read_time_english():
    # 300 words → 1.5 char equiv per word = 450 → ~2 min
    words = 'hello ' * 300
    assert _calc_read_time(words) >= 1

def test_calc_read_time_chinese():
    # 300 chars → 1 min
    text = '测试' * 150
    assert _calc_read_time(text) == 1


# ── _parse_date ──

def test_parse_date_full():
    assert 'Jun' in _parse_date('2026-06-25 14:30')

def test_parse_date_month():
    assert _parse_date('2026-06') == 'Jun 2026'

def test_parse_date_invalid():
    assert _parse_date('') == ''
    assert _parse_date(None) == ''


# ── _parse_tags ──

def test_parse_tags_simple():
    assert _parse_tags('生活, 摄影') == {'生活', '摄影'}

def test_parse_tags_pinned():
    result = _parse_tags('随笔', {'pinned': True})
    assert '置顶' in result

def test_parse_tags_empty():
    assert _parse_tags('') == set()
    assert _parse_tags(None) == set()


# ── _extract_first_image ──

def test_extract_first_image_markdown():
    md = 'text ![alt](https://example.com/img.jpg) more'
    assert _extract_first_image(md) == 'https://example.com/img.jpg'

def test_extract_first_image_none():
    assert 'avatar.jpg' in _extract_first_image(None)
    assert 'avatar.jpg' in _extract_first_image('')


# ── _find_adjacent_siblings ──

def test_find_adjacent_siblings():
    essays = [
        {'slug': 'a'}, {'slug': 'b'}, {'slug': 'c'}, {'slug': 'd'}
    ]
    # Find siblings around index 1 (b) in [a, c]
    prev_sib, next_sib = _find_adjacent_siblings(essays, 1, [essays[0], essays[2]])
    assert prev_sib['slug'] == 'a'
    assert next_sib['slug'] == 'c'

def test_find_adjacent_siblings_edges():
    essays = [{'slug': 'a'}, {'slug': 'b'}, {'slug': 'c'}]
    # First element, only next sibling
    prev_sib, next_sib = _find_adjacent_siblings(essays, 0, essays)
    assert prev_sib is None
    assert next_sib['slug'] == 'b'


# ── _extract_gps ──

def test_extract_gps_none():
    assert _extract_gps(None) is None
    assert _extract_gps({}) is None


# ── _extract_exif with real image ──

def test_extract_exif_no_exif():
    import io
    # Create a minimal JPEG (binary) — Image.new() doesn't support _getexif()
    buf = io.BytesIO()
    Image.new('RGB', (10, 10), color='red').save(buf, 'JPEG')
    buf.seek(0)
    img = Image.open(buf)
    result = _extract_exif(img)
    assert result == {}
