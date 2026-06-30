"""JSON data utilities for the Chami CMS."""

import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
ESSAYS_DIR = os.path.join(BASE_DIR, 'essays')
MD_DIR = os.path.join(BASE_DIR, 'md')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')

for _d in (DATA_DIR, ESSAYS_DIR, MD_DIR, IMAGES_DIR):
    os.makedirs(_d, exist_ok=True)


def load_json(name):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"WARNING: corrupted JSON — {path}")
        return []


def atomic_write(filepath, data):
    """Atomically write JSON to *filepath*: .tmp → os.replace, prevents corruption on crash."""
    tmp_filepath = filepath + '.tmp'
    try:
        with open(tmp_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_filepath, filepath)
    except Exception:
        if os.path.exists(tmp_filepath):
            os.remove(tmp_filepath)
        raise


def atomic_write_json(filename, data):
    """Atomically write JSON to DATA_DIR/<filename>. Delegates to atomic_write()."""
    atomic_write(os.path.join(DATA_DIR, filename), data)


def decimal_to_dms(d):
    """Convert decimal degrees to (deg, min, sec) tuple.
    Always returns positive values; N/S/E/W tags carry the direction."""
    d = abs(d)
    deg = int(d)
    m = (d - deg) * 60
    min_val = int(m)
    sec = (m - min_val) * 60
    return (deg, min_val, sec)


def dms_to_decimal(value):
    """Convert EXIF DMS (deg, min, sec) tuple to decimal degrees."""
    return float(value[0]) + float(value[1]) / 60.0 + float(value[2]) / 3600.0


def format_shutter(val):
    try:
        v = float(val)
        if 0 < v < 1:
            return f"1/{int(round(1/v))}s"
        return f"{int(v)}s" if v.is_integer() else f"{v}s"
    except (ValueError, TypeError):
        return str(val)


def format_aperture(val):
    try:
        return f"f/{float(val):g}"
    except (ValueError, TypeError):
        return str(val)


def format_focal(val):
    try:
        return f"{int(float(val))}mm"
    except (ValueError, TypeError):
        return str(val)
