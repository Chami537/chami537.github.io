"""Small domain-facing repository over the shared JSON store."""

import threading


_LOCKS = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(store, filename):
    key = (id(store), filename)
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, threading.RLock())


class JsonRepository:
    """Read and write one JSON resource without exposing storage details.

    ``mutate`` serializes the full read-modify-write cycle for callers that
    update collections, preventing concurrent admin requests from losing data.
    """

    def __init__(self, filename, store):
        self.filename = filename
        self.store = store
        self._lock = _lock_for(store, filename)

    def list(self):
        return self.store.read(self.filename)

    def save(self, value):
        self.store.write(self.filename, value)

    def mutate(self, callback):
        """Apply ``callback`` under a per-store/per-file transaction lock.

        The callback receives the decoded value and must return a non-``None``
        result when the value was changed. Returning ``None`` leaves the file
        intact.
        """
        with self._lock:
            value = self.list()
            result = callback(value)
            if result is not None:
                self.save(value)
            return result
