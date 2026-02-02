"""
Application factory and configuration.
Creates Flask app with all extensions initialized.
"""

import os
from flask import Flask
from datetime import timedelta

# Extension instances (created in create_app)
db = None
jwt = None
cors = None
limiter = None
celery = None


def create_app(config_name: str = "development") -> Flask:
    """
    Application factory for creating Flask app.
    
    Args:
        config_name: Configuration name ('development', 'testing', 'production')
    
    Returns:
        Configured Flask app instance
    """
    app = Flask(__name__)
    
    # Load configuration
    config = load_config(config_name)
    app.config.from_object(config)
    
    # Initialize extensions
    initialize_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app


def load_config(config_name: str) -> object:
    """Load configuration based on environment."""
    if config_name == "development":
        return DevelopmentConfig
    elif config_name == "testing":
        return TestingConfig
    elif config_name == "production":
        return ProductionConfig
    else:
        raise ValueError(f"Unknown config: {config_name}")


def initialize_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    global db, jwt, cors, limiter, celery
    
    from flask_sqlalchemy import SQLAlchemy
    from flask_jwt_extended import JWTManager
    from flask_cors import CORS
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    from celery import Celery
    
    # Database
    db = SQLAlchemy(app)
    
    # JWT
    jwt = JWTManager(app)
    
    # CORS
    cors = CORS(app, resources={
        r"/api/*": {
            "origins": app.config["CORS_ORIGINS"],
            "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Device-ID"],
            "supports_credentials": True,
        }
    })
    
    # Rate Limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
    )
    
    # Celery
    celery = Celery(app.import_name)
    celery.conf.update(app.config)


def register_blueprints(app: Flask) -> None:
    """Register API blueprints."""
    # Import here to avoid circular imports
    from src.elcorp.identity.interfaces import register_routes
    
    # Register identity routes
    register_routes(app, None, None)  # Handlers will be injected


def register_error_handlers(app: Flask) -> None:
    """Register error handlers."""
    from src.elcorp.shared.domain import DomainException
    
    @app.errorhandler(DomainException)
    def handle_domain_exception(error):
        response = error.to_dict()
        # Determine status code based on error type
        status_code = {
            "VALIDATION_ERROR": 400,
            "NOT_FOUND": 404,
            "UNAUTHORIZED": 401,
            "CONFLICT": 409,
            "INTERNAL_ERROR": 500,
        }.get(error.code, 400)
        return response, status_code
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        return {"error": "BAD_REQUEST", "message": str(error)}, 400
    
    @app.errorhandler(404)
    def handle_not_found(error):
        return {"error": "NOT_FOUND", "message": "Resource not found"}, 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        return {"error": "INTERNAL_ERROR", "message": "Internal server error"}, 500


class Config:
    """Base configuration."""
    
    # Flask
    DEBUG = False
    TESTING = False
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_ALGORITHM = "HS256"
    
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv("REDIS_URL", "memory://")
    
    # Celery
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    CELERY_TASK_SERIALIZER = "json"
    CELERY_RESULT_SERIALIZER = "json"
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_TIMEZONE = "UTC"
    
    # Security
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", None)
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Features
    ENABLE_MFA = True
    ENABLE_AUDIT_LOGGING = True
    ENABLE_DEVICE_TRACKING = True


class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True
    # Use PostgreSQL via psycopg2
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://elcorp:dev-password@postgres:5432/elcorp_dev"
    )
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = "DEBUG"


class TestingConfig(Config):
    """Testing configuration."""
    
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-secret-key"
    CORS_ORIGINS = ["http://localhost:3000"]
    # Disable rate limiting in tests
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "postgresql://elcorp:password@postgres:5432/elcorp")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-in-production")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "change-in-production")
    
    @classmethod
    def validate(cls):
        """Validate required environment variables for production."""
        if not os.getenv("DATABASE_URL"):
            raise ValueError("DATABASE_URL environment variable is required in production")
        if not os.getenv("JWT_SECRET_KEY"):
            raise ValueError("JWT_SECRET_KEY environment variable is required in production")
        if not os.getenv("ENCRYPTION_KEY"):
            raise ValueError("ENCRYPTION_KEY environment variable is required in production")
