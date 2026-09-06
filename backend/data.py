"""JSON data utilities for the Chami CMS."""

import os
import json
import threading
from backend.storage import JsonStore

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
ESSAYS_DIR = os.path.join(BASE_DIR, 'essays')
MD_DIR = os.path.join(BASE_DIR, 'md')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')

# Load .env from project root (if exists)
_dotenv_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(_dotenv_path):
    load_dotenv(_dotenv_path)

# ── Password store (gitignored, local-only) ──

PASSWORD_STORE = os.path.join(DATA_DIR, 'essay_passwords.json')
_password_cache = None
_password_cache_lock = threading.RLock()


def _password_store_signature():
    try:
        stat = os.stat(PASSWORD_STORE)
    except OSError:
        return None
    return stat.st_mtime_ns, stat.st_size


def _read_password_store():
    """Read the local password store. Returns empty dict if missing or corrupted."""
    global _password_cache
    signature = _password_store_signature()
    with _password_cache_lock:
        if _password_cache is not None and _password_cache[0] == signature:
            return dict(_password_cache[1])
        if signature is None:
            value = {}
        else:
            try:
                with open(PASSWORD_STORE, 'r', encoding='utf-8') as f:
                    value = json.load(f)
            except (json.JSONDecodeError, IOError):
                value = {}
        if not isinstance(value, dict):
            value = {}
        _password_cache = (signature, value)
        return dict(value)


def _write_password_store(data):
    """Atomically write the password store."""
    tmp = PASSWORD_STORE + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, PASSWORD_STORE)
        global _password_cache
        with _password_cache_lock:
            _password_cache = (_password_store_signature(), dict(data))
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def get_essay_password(slug):
    """Get password for an essay. Checks password store first, then env var fallback."""
    store = _read_password_store()
    if slug in store:
        return store[slug]
    env_key = f'ESSAY_PASSWORD_{slug.replace("-", "_").upper()}'
    return os.environ.get(env_key, os.environ.get('ESSAY_MASTER_PASSWORD', ''))


def set_essay_password(slug, password):
    """Store a password for an essay (local, gitignored file)."""
    store = _read_password_store()
    if password:
        store[slug] = password
    else:
        store.pop(slug, None)
    _write_password_store(store)


def rename_essay_password(old_slug, new_slug):
    """Move a locally stored essay password when its slug changes."""
    if old_slug == new_slug:
        return
    store = _read_password_store()
    if old_slug not in store:
        return False
    if new_slug in store:
        raise ValueError(f'Password already exists for slug: {new_slug}')
    store[new_slug] = store.pop(old_slug)
    _write_password_store(store)
    return True


def delete_essay_password(slug):
    """Remove an orphan-prone local password entry for a deleted essay."""
    store = _read_password_store()
    if slug not in store:
        return
    store.pop(slug)
    _write_password_store(store)


def has_essay_password(slug):
    """Check if an essay has a password set."""
    return bool(get_essay_password(slug))


# Re-export EXIF utilities from exif_utils.py (backwards-compat, prefer importing from exif_utils)
from backend.exif_utils import (  # noqa: E402,F401
    ALLOWED_IMAGE_EXTENSIONS, get_image_ext,
    decimal_to_dms, dms_to_decimal,
    format_shutter, format_aperture, format_focal,
)


def _ensure_dirs():
    for _d in (DATA_DIR, ESSAYS_DIR, MD_DIR, IMAGES_DIR):
        os.makedirs(_d, exist_ok=True)


_ensure_dirs()

STORE = JsonStore(DATA_DIR)


def load_json(name):
    """Read JSON data, propagating corruption instead of hiding data loss."""
    return STORE.read(name)


def atomic_write_json(filename, data):
    """Compatibility wrapper for the shared atomic JSON store."""
    STORE.write(filename, data)
