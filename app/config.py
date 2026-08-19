import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "ecourts-secure-secret-key-2026")
    BASE_DIR = BASE_DIR
    DATA_DIR = DATA_DIR
    STATIC_DIR = STATIC_DIR
    TEMPLATES_DIR = TEMPLATES_DIR
    
    # SQLite Database Configuration: Prefer data/cases.db, with fallback/migration from root cases.db
    DEFAULT_DB_FILE = DATA_DIR / "cases.db"
    LEGACY_DB_FILE = BASE_DIR / "cases.db"
    
    # If legacy DB exists in root but not in data/, point to or migrate it
    if LEGACY_DB_FILE.exists() and not DEFAULT_DB_FILE.exists():
        DB_PATH = str(LEGACY_DB_FILE)
    else:
        DB_PATH = os.environ.get("ECOURTS_DB_PATH", str(DEFAULT_DB_FILE))

    # eCourts Partner API
    ECOURTS_API_BASE_URL = os.environ.get("ECOURTS_API_BASE_URL", "https://webapi.ecourtsindia.com")
    ECOURTS_API_KEY = os.environ.get("ECOURTS_API_KEY", "")
    
    # Meta WhatsApp Business Cloud API
    META_WA_TOKEN = os.environ.get("META_WA_TOKEN") or os.environ.get("WHATSAPP_API_TOKEN", "")
    META_PHONE_ID = os.environ.get("META_PHONE_ID") or os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    META_WABA_ID = os.environ.get("META_WABA_ID") or os.environ.get("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
    META_GRAPH_API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v21.0")

    # Cloud Keep-Alive
    RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://ecourts-case-tracker.onrender.com")
    KEEP_ALIVE_ENABLED = os.environ.get("KEEP_ALIVE_ENABLED", "true").lower() in ("true", "1", "yes")

    # Sync Poller Interval (in seconds)
    SYNC_INTERVAL_SECONDS = int(os.environ.get("SYNC_INTERVAL_SECONDS", "3600"))

    # Timezone
    TIMEZONE = "Asia/Kolkata"
    IST_OFFSET_HOURS = 5.5

    TESTING = False
    DEBUG = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    DB_PATH = ":memory:"
    SYNC_INTERVAL_SECONDS = 0
    KEEP_ALIVE_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False


def get_config(env_name: Optional[str] = None) -> Config:
    """Returns configuration object based on environment name."""
    env = env_name or os.environ.get("FLASK_ENV", "production").lower()
    if env in ("development", "dev"):
        return DevelopmentConfig()
    elif env in ("testing", "test"):
        return TestingConfig()
    return ProductionConfig()
