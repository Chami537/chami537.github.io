"""Persistence boundary for essay metadata and tag ordering."""

from backend.storage import JsonRepository


class EssayRepository(JsonRepository):
    """Store-backed essay access without exposing file names to routes."""

    def __init__(self, store):
        super().__init__('essays.json', store)

    def read_tag_order(self):
        return self.store.read('tags_order.json')

    def save_tag_order(self, order):
        self.store.write('tags_order.json', order)
