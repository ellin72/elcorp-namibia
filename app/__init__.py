# app/__init__.py
import os
import logging
from pathlib import Path
from flask import Flask, render_template
from dotenv import load_dotenv
from .extensions import db, migrate, login_manager, mail, limiter, csrf

# 1. Load .env into os.environ
load_dotenv()

def _validate_positive_int(var_name: str, default: int) -> int:
    """Validate and return a positive integer from environment."""
    try:
        value = int(os.getenv(var_name, default))
        if value <= 0:
            raise ValueError()
        return value
    except (ValueError, TypeError):
        raise RuntimeError(
            f"Invalid {var_name}: must be a positive integer, got '{os.getenv(var_name)}'"
        )

def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        instance_relative_config=False,
        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), 'static')
    )

    # 2. Load configuration from environment variables with validation
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-key-change-in-production"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///elcorp.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("FLASK_ENV") == "production",
        
        # Mail settings
        MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
        MAIL_PORT=_validate_positive_int("MAIL_PORT", 587),
        MAIL_USE_TLS=os.getenv("MAIL_USE_TLS", "true").lower() in ("true", "1", "yes"),
        MAIL_USE_SSL=os.getenv("MAIL_USE_SSL", "false").lower() in ("true", "1", "yes"),
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
        MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER", os.getenv("MAIL_USERNAME")),

        # List of admin emails (comma-separated in .env)
        ADMINS=[
            email.strip()
            for email in os.environ.get("ADMINS", "").split(",")
            if email.strip()
        ],

        # Password reset token expiry (in seconds)
        PASSWORD_RESET_TOKEN_EXPIRY=_validate_positive_int("PASSWORD_RESET_TOKEN_EXPIRY", 3600),
        
        # Password history (number of old passwords to check)
        PASSWORD_HISTORY_COUNT=_validate_positive_int("PASSWORD_HISTORY_COUNT", 5),
        
        # Require 2FA re-authentication for sensitive operations
        REQUIRE_2FA_REAUTH=os.getenv("REQUIRE_2FA_REAUTH", "false").lower() in ("true", "1", "yes"),
        
        # API Configuration
        API_ITEMS_PER_PAGE=_validate_positive_int("API_ITEMS_PER_PAGE", 20),
        MAX_CONTENT_LENGTH=_validate_positive_int("MAX_CONTENT_LENGTH", 16777216),
    )

    
# 3. Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = "auth.login"
    
    # 4. Configure logging
    _configure_logging(app)
    
    # 5. Register blueprints
    from .main import bp as main_bp
    app.register_blueprint(main_bp)        # mounts "/" → main.index

    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp)        # mounts "/auth/..."

    from .vin import bp as vin_bp
    app.register_blueprint(vin_bp)         # mounts "/vin/..."
    
    from .dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp)   # mounts "/dashboard/..."
    
    from .api import bp as api_bp
    app.register_blueprint(api_bp)         # mounts "/api/..."
    
    # 6. Initialize other extensions
    csrf.init_app(app)

    # 7. Set up Flask-Admin
    from .admin import init_admin
    init_admin(app)

    return app


def _configure_logging(app: Flask) -> None:
    """Configure application and audit logging."""
    logs_path = Path(app.root_path) / "logs"
    logs_path.mkdir(exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    if not app.debug:
        root_logger.setLevel(logging.INFO)

    # Password reset audit logger
    audit_logger = logging.getLogger("app.password_reset_audit")
    audit_logger.setLevel(logging.INFO)

    # Ensure only one handler per logger
    if not audit_logger.handlers:
        log_file = logs_path / "password_reset_audit.log"
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        audit_logger.addHandler(handler)

    # API logger
    api_logger = logging.getLogger("app.api")
    if not api_logger.handlers:
        log_file = logs_path / "api.log"
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        api_logger.addHandler(handler)
