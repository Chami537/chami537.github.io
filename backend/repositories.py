"""Application composition for JSON repositories backed by the project store."""

from backend.data import STORE
from backend.storage import JsonRepository


def repository_for(filename):
    return JsonRepository(filename, STORE)
