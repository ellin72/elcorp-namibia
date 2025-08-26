# app/__init__.py
import os
import logging
from flask import Flask, render_template
from dotenv import load_dotenv
from .extensions import db, migrate, login_manager, mail, limiter, csrf


# 1. Load .env into os.environ
load_dotenv()

def create_app(test_config=None):
    """Create and configure the Flask application."""
    # project_root = os.path.dirname(__file__)

    app = Flask(
        __name__
        # instance_relative_config=False,
        # template_folder=os.path.join(project_root, 'app', 'templates'),
        # static_folder=os.path.join(project_root, 'app', 'static')
    )

    # 2. Load configuration from environment variables
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///elcorp.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        
        # Mail settings
        MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com"),
        MAIL_PORT = int(os.environ.get("MAIL_PORT", 587)),
        MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in ("true", "1", "yes"),
        MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() in ("true", "1", "yes"),
        MAIL_USERNAME = os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD = os.getenv("MAIL_PASSWORD"),
        MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", os.getenv("MAIL_USERNAME")),

        # List of admin emails (comma-separated in .env)
        ADMINS = [
            email.strip()
            for email in os.environ.get("ADMINS", "").split(",")
            if email.strip()
        ],

        # Password reset token expiry (in seconds)
        PASSWORD_RESET_TOKEN_EXPIRES = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRY", 3600))
    )
    if os.getenv("FLASK_ENV") == "production":
        app.config.update(SESSION_COOKIE_SECURE=True)

    
    # 3 Initializing extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = "auth.login"
    
    
    
    # Configure audit logger
    audit_logger = logging.getLogger("app.password_reset_audit")
    audit_logger.setLevel(logging.INFO)

    # Ensure logs/ directory exists
    logs_path = os.path.join(app.root_path, "logs")
    os.makedirs(logs_path, exist_ok=True)

    # Now safely create a FileHandler
    log_file = os.path.join(logs_path, "password_reset_audit.log")
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s"
    ))
    audit_logger.addHandler(handler)
    
##############################################################################
    # Configure logging (optional, but useful for audit/compliance)
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    def load_positive_int_env(var_name: str, default: int) -> int:
        """Load an environment variable as a positive integer with validation."""
        try:
            value = int(os.getenv(var_name, default))
        except ValueError:
            raise RuntimeError(
                f"Invalid {var_name}: must be a positive integer, got a non-integer value."
            )
        
        if value <= 0:
            raise RuntimeError(
                f"Invalid {var_name}: must be a positive integer, got {value}."
            )
        
        logger.info(f"{var_name} set to {value} (source: environment or default).")
        return value

      
    # Debug: see the raw value before anything happens
    print("DEBUG — raw env value at config load:", os.getenv("PASSWORD_RESET_TOKEN_EXPIRES"))
    

    # # Fallback to 3600 if not set
    PASSWORD_RESET_TOKEN_EXPIRES = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRES", "3600"))

    if PASSWORD_RESET_TOKEN_EXPIRES <= 0:
        raise RuntimeError("Invalid PASSWORD_RESET_TOKEN_EXPIRES: must be a positive integer")


    ##############################################################################
        
    # 4. Import and register blueprints
    from .main import bp as main_bp
    app.register_blueprint(main_bp)        # mounts "/" → main.index

    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp)        # mounts "/auth/..."

    from .vin import bp as vin_bp
    app.register_blueprint(vin_bp)         # mounts "/vin/..."
    
    from .dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp)   # mounts "/dashboard/..."
    
    # … init other extensions …
    csrf.init_app(app)

    # 6. Finally set up Flask-Admin
    from .admin import init_admin
    init_admin(app)

        
    return app
