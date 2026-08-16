"""Reversible filesystem operations for essay source artifacts."""

import os
import shutil


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


def stage_paths(paths):
    """Move existing paths aside so a multi-resource delete can be rolled back."""
    staged = []
    try:
        for path in paths:
            if not os.path.exists(path):
                continue
            temporary = path + '.deleting'
            if os.path.exists(temporary):
                raise FileExistsError(f'Staging path already exists: {temporary}')
            os.replace(path, temporary)
            staged.append((path, temporary))
    except Exception:
        restore_sources(staged)
        raise
    return staged


def purge_staged(staged):
    """Permanently remove paths previously returned by :func:`stage_paths`."""
    for _original, temporary in staged:
        if os.path.isdir(temporary):
            shutil.rmtree(temporary)
        elif os.path.exists(temporary):
            os.remove(temporary)
