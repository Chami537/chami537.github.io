"""Test fixtures for the Chami CMS."""
import os
import pytest

from backend.app import app
from backend.data import DATA_DIR


@pytest.fixture
def client():
    """Flask test client with auth bypassed (TESTING=True)."""
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def client_no_auth():
    """Flask test client with auth enforced (TESTING=False)."""
    was_testing = app.config.get('TESTING')
    app.config['TESTING'] = False
    with app.test_client() as c:
        yield c
    app.config['TESTING'] = was_testing


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
