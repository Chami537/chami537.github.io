"""Small filesystem primitives shared by generated and edited text files."""

import os
import time


def atomic_write_text(path, content, encoding='utf-8'):
    """Replace a text file atomically and clean up interrupted writes."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    temporary = path + '.tmp'
    try:
        with open(temporary, 'w', encoding=encoding) as handle:
            handle.write(content)
        for attempt in range(5):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
    except Exception:
        if os.path.exists(temporary):
            try:
                os.remove(temporary)
            except OSError:
                pass
        raise
