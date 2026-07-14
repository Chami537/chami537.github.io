"""Shared Blueprint, paths, and persistence seams for photo routes."""

import threading

from flask import Blueprint

from backend.data import BASE_DIR, IMAGES_DIR
from backend.storage import repository_for


bp = Blueprint('photos', __name__)
PHOTO_STORIES_REPOSITORY = repository_for('photo_stories.json')
PHOTO_SIZES = (('lg', 1920), ('md', 800), ('sm', 400))
PHOTO_METADATA_LOCK = threading.Lock()


def load_json(name):
    """Compatibility seam backed by the repository layer."""
    return repository_for(name).list()


def atomic_write_json(name, data):
    """Compatibility seam backed by the repository layer."""
    repository_for(name).save(data)
