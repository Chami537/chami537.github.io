"""Persistence boundary for essay metadata and tag ordering."""


class EssayRepository:
    """Store-backed essay access without exposing file names to routes."""

    def __init__(self, store):
        self.store = store

    def list(self):
        return self.store.read('essays.json')

    def save(self, essays):
        self.store.write('essays.json', essays)

    def read_tag_order(self):
        return self.store.read('tags_order.json')

    def save_tag_order(self, order):
        self.store.write('tags_order.json', order)
