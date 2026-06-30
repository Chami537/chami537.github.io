"""Test fixtures for the Chami CMS."""
import json
import os
import pytest
import tempfile

from backend.app import app
from backend.data import DATA_DIR


@pytest.fixture
def client():
    """Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def data_backup():
    """Backup and restore data/ directory around each test."""
    backup = {}
    for name in os.listdir(DATA_DIR):
        if name.endswith('.json'):
            path = os.path.join(DATA_DIR, name)
            with open(path, 'r', encoding='utf-8') as f:
                backup[name] = f.read()

    yield

    for name, content in backup.items():
        path = os.path.join(DATA_DIR, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
