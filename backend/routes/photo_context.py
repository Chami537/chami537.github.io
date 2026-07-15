"""Shared Blueprint, paths, and persistence seams for photo routes."""

from flask import Blueprint

from backend.data import BASE_DIR, IMAGES_DIR
from backend.repositories import PHOTO_REPOSITORY, repository_for


bp = Blueprint('photos', __name__)
PHOTO_STORIES_REPOSITORY = repository_for('photo_stories.json')
PHOTO_SIZES = (('lg', 1920), ('md', 800), ('sm', 400))
