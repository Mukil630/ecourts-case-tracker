from app.api.health import health_bp
from app.api.settings import settings_bp
from app.api.cases import cases_bp
from app.api.cause_list import cause_list_bp
from app.api.whatsapp import whatsapp_bp
from app.api.telegram import telegram_bp
from app.api.ai import ai_bp
from app.api.scheduler import scheduler_bp
from app.api.leads import leads_bp

def register_blueprints(app):
    """Registers all modular application blueprints with the Flask app."""
    app.register_blueprint(health_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(cases_bp)
    app.register_blueprint(cause_list_bp)
    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(telegram_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(scheduler_bp)
    app.register_blueprint(leads_bp)

__all__ = [
    "health_bp",
    "settings_bp",
    "cases_bp",
    "cause_list_bp",
    "whatsapp_bp",
    "telegram_bp",
    "ai_bp",
    "scheduler_bp",
    "leads_bp",
    "register_blueprints",
]
