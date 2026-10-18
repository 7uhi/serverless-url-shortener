import pytest
from backend.app import Application
from backend.storage import SQLiteStore


@pytest.fixture
def store(tmp_path):
    return SQLiteStore(tmp_path / 'test.sqlite3')


@pytest.fixture
def app(store):
    return Application(store, 'https://short.example.com', clock=lambda: 1700000000)
