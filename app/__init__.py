# app/__init__.py
import os
from flask import Flask, render_template
from dotenv import load_dotenv
from .extensions import db, migrate, login_manager, mail, limiter


# 1. Load .env into os.environ
load_dotenv()

def create_app():
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

    
    # 4. Import and register blueprints
    from .main import bp as main_bp
    app.register_blueprint(main_bp)        # mounts "/" → main.index

    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp)        # mounts "/auth/..."

    from .vin import bp as vin_bp
    app.register_blueprint(vin_bp)         # mounts "/vin/..."

    # 6. Finally set up Flask-Admin
    from .admin import init_admin
    init_admin(app)

    # @app.route('/')
    # def index():
    #     return "Welcome to the ELCorp Namibia application!"
    
    
    return app
