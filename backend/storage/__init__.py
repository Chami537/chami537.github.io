"""Storage primitives for the file-backed CMS."""

from backend.storage.json_store import DataCorruptionError, JsonStore
from backend.storage.repository import JsonRepository, repository_for

__all__ = ['DataCorruptionError', 'JsonStore', 'JsonRepository', 'repository_for']
