"""Small domain-facing repository over the shared JSON store."""

class JsonRepository:
    """Read and write one JSON resource without exposing storage details."""

    def __init__(self, filename, store):
        self.filename = filename
        self.store = store

    def list(self):
        return self.store.read(self.filename)

    def save(self, value):
        self.store.write(self.filename, value)
