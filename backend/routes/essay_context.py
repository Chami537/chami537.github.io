"""Shared Blueprint and services for essay route modules."""

from flask import Blueprint

from backend.data import STORE
from backend.essay_repository import EssayRepository
from backend.essay_service import EssayService


bp = Blueprint('essays', __name__)
ESSAY_REPOSITORY = EssayRepository(STORE)
ESSAY_SERVICE = EssayService(ESSAY_REPOSITORY)
