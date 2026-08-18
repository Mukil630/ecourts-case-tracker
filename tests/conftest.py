import pytest
import os
import tempfile
from app import create_app
from app.config import TestingConfig
from app.db.database import init_db
from app.db.seed_data import import_karur_sample_data

@pytest.fixture
def app():
    """Creates a fresh test application instance with an isolated SQLite database."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    test_cfg = TestingConfig()
    test_cfg.DB_PATH = db_path

    app = create_app(test_cfg, start_background_tasks=False)
    app.config["DB_PATH"] = db_path

    with app.app_context():
        init_db(db_path=db_path, auto_seed=True)

    yield app

    # Cleanup temporary test database
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass

@pytest.fixture
def client(app):
    """Provides test client for making HTTP requests."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Provides test CLI runner."""
    return app.test_cli_runner()
