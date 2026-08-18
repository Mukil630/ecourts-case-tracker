import os
import sys
import time
import threading
import requests
from typing import Optional, Union
from flask import Flask, send_from_directory
from flask_cors import CORS

from app.config import Config, get_config
from app.db.database import init_db
from app.api import register_blueprints
from app.services.sync_service import sync_worker

# Ensure UTF-8 output across standard streams
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def _keep_alive_loop(external_url: str):
    """Keeps cloud host awake 24/7 by periodically pinging the public healthz endpoint."""
    time.sleep(20)
    while True:
        try:
            target = f"{external_url.rstrip('/')}/healthz"
            requests.get(target, timeout=15)
        except Exception:
            pass
        time.sleep(480)  # Ping every 8 minutes

def create_app(config: Optional[Union[Config, str]] = None, start_background_tasks: bool = True) -> Flask:
    """Application factory for the eCourts Case Tracker & WhatsApp Dispatcher."""
    app = Flask(
        __name__,
        static_folder=str(Config.STATIC_DIR),
        template_folder=str(Config.TEMPLATES_DIR)
    )

    # 1. Load Configuration
    if isinstance(config, str):
        cfg = get_config(config)
    elif config is not None:
        cfg = config
    else:
        cfg = get_config()

    app.config.from_object(cfg)

    # 2. Setup CORS
    CORS(app)

    # 3. Initialize SQLite Database Schema (Clean Slate)
    init_db(db_path=app.config.get("DB_PATH"), auto_seed=False)

    # 4. Register API Blueprints
    register_blueprints(app)

    # 5. Serve Root & Static Frontend
    @app.route("/")
    def index():
        return send_from_directory(str(Config.STATIC_DIR), "index.html")

    @app.route("/static/<path:path>")
    def serve_static(path):
        return send_from_directory(str(Config.STATIC_DIR), path)

    # 6. Start Background Workers (Only for production/development, not unit tests)
    if start_background_tasks and not app.config.get("TESTING", False):
        # Start Auto Sync Poller
        if app.config.get("SYNC_INTERVAL_SECONDS", 0) > 0 and not sync_worker.running:
            sync_worker.start()

        # Start Render Keep-Alive Daemon
        if app.config.get("KEEP_ALIVE_ENABLED", False):
            ext_url = app.config.get("RENDER_EXTERNAL_URL", "https://ecourts-case-tracker.onrender.com")
            keep_alive_thread = threading.Thread(
                target=_keep_alive_loop,
                args=(ext_url,),
                daemon=True
            )
            keep_alive_thread.start()

    return app
