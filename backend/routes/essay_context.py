"""Shared Blueprint and services for essay route modules."""

from flask import Blueprint

from backend.essay_repository import EssayRepository
from backend.essay_service import EssayService


bp = Blueprint('essays', __name__)
ESSAY_REPOSITORY = EssayRepository()
ESSAY_SERVICE = EssayService(ESSAY_REPOSITORY)
