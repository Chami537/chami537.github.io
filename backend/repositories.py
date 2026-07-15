"""Application composition for JSON repositories backed by the project store."""

from backend.data import STORE
from backend.photo_repository import PhotoRepository
from backend.storage import JsonRepository


PHOTO_REPOSITORY = PhotoRepository(STORE)


def repository_for(filename):
    return JsonRepository(filename, STORE)
