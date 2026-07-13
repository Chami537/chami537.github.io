"""Small, dependency-free JSON store used by the CMS data layer."""

import json
import os
import time


class DataCorruptionError(ValueError):
    """Raised when an existing JSON data file cannot be decoded."""


class JsonStore:
    """Read and atomically replace JSON files within one data directory."""

    def __init__(self, data_dir):
        self.data_dir = os.path.abspath(data_dir)

    def _path(self, filename):
        return os.path.join(self.data_dir, filename)

    def read(self, filename, default=None):
        path = self._path(filename)
        if not os.path.exists(path):
            return [] if default is None else default
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                return json.load(handle)
        except json.JSONDecodeError as exc:
            raise DataCorruptionError(f'Invalid JSON data: {path}') from exc

    def write(self, filename, data):
        path = self._path(filename)
        temp_path = path + '.tmp'
        try:
            with open(temp_path, 'w', encoding='utf-8') as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
            for attempt in range(5):
                try:
                    os.replace(temp_path, path)
                    break
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.05 * (attempt + 1))
        except Exception:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise
