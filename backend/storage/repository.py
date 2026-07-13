"""Small domain-facing repository over the shared JSON store."""

class JsonRepository:
    """Read and write one JSON resource without exposing storage details."""

    def __init__(self, filename, store=None):
        self.filename = filename
        if store is None:
            from backend.data import STORE
            store = STORE
        self.store = store

    def list(self):
        return self.store.read(self.filename)

    def save(self, value):
        self.store.write(self.filename, value)


def repository_for(filename):
    return JsonRepository(filename)
