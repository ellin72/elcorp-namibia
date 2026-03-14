"""Alembic env.py — auto-detects models imported in app.models."""

import os
from logging.config import fileConfig

from alembic import context
from flask import current_app

from app import create_app
from app.extensions import db

# Import all models so Alembic sees them
import app.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    ini_path = config.config_file_name
    if not os.path.isabs(ini_path):
        ini_path = os.path.join(os.getcwd(), ini_path)
    if os.path.exists(ini_path):
        fileConfig(ini_path)


def get_engine():
    flask_app = current_app._get_current_object()  # type: ignore[attr-defined]
    return flask_app.extensions["migrate"].db.engine


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=db.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    flask_app = create_app()
    with flask_app.app_context():
        connectable = db.engine
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=db.metadata)
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
