"""Storage primitives for the file-backed CMS."""

from backend.storage.json_store import DataCorruptionError, JsonStore

__all__ = ['DataCorruptionError', 'JsonStore']
