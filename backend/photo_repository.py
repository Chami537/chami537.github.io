"""Single persistence owner for photo metadata."""

import threading


class PhotoRepository:
    """Serialize compound operations on the photos JSON collection."""

    def __init__(self, store, lock=None):
        self.store = store
        self.lock = lock or threading.RLock()

    def list(self):
        return self.store.read('photos.json')

    def save(self, photos):
        self.store.write('photos.json', photos)

    def find(self, filename):
        photos = self.list()
        photo = next(
            (item for item in photos if item.get('filename') == filename),
            None,
        )
        return photo, photos

    def append(self, entry):
        with self.lock:
            photos = self.list()
            photos.append(entry)
            self.save(photos)

    def update(self, filename, updater):
        with self.lock:
            photo, photos = self.find(filename)
            if photo is None:
                return None
            updater(photo)
            self.save(photos)
            return photo

    def delete(self, filename):
        with self.lock:
            photos = self.list()
            kept = [item for item in photos if item.get('filename') != filename]
            if len(kept) == len(photos):
                return False
            self.save(kept)
            return True

    def replace_preserving(self, new_data):
        with self.lock:
            existing = self.list()
            existing_filenames = {item.get('filename', '') for item in existing}
            new_filenames = {item.get('filename', '') for item in new_data}
            lost = existing_filenames - new_filenames
            if not lost:
                self.save(new_data)
            return lost
