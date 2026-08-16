"""Reversible filesystem operations for essay source artifacts."""

import os


def rename_sources(old_slug, new_slug, directories):
    """Rename existing essay artifacts and return moves for rollback."""
    if old_slug == new_slug:
        return []
    moved = []
    try:
        for directory, suffix in directories:
            old_path = os.path.join(directory, f'{old_slug}.{suffix}')
            new_path = os.path.join(directory, f'{new_slug}.{suffix}')
            if os.path.exists(old_path):
                os.replace(old_path, new_path)
                moved.append((old_path, new_path))
    except Exception:
        restore_sources(moved)
        raise
    return moved


def restore_sources(moved):
    """Restore artifacts moved by :func:`rename_sources`."""
    for old_path, new_path in reversed(moved):
        if os.path.exists(new_path):
            os.replace(new_path, old_path)
