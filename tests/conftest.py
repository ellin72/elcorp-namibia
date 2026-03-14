"""Shared pytest fixtures."""

import os
import pytest

os.environ["FLASK_ENV"] = "testing"
os.environ["ENCRYPTION_KEY"] = "dGVzdC1lbmNyeXB0aW9uLWtleS0zMmJ5dGU="

from app import create_app
from app.extensions import db as _db
from app.services.identity_service import seed_roles


@pytest.fixture(scope="session")
def app():
    """Create the Flask application for the whole test session."""
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        seed_roles()
        yield app
        _db.drop_all()


@pytest.fixture(autouse=True)
def _clean_tables(app):
    """Roll back any changes after each test."""
    with app.app_context():
        yield
        _db.session.rollback()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def auth_headers(client):
    """Register a user and return Authorization headers."""
    resp = client.post("/api/v1/auth/signup", json={
        "email": "test@elcorp.na",
        "password": "Test1234!",
        "first_name": "Test",
        "last_name": "User",
    })
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(client, db):
    """Register an admin user and return headers."""
    from app.models.user import User, Role

    resp = client.post("/api/v1/auth/signup", json={
        "email": "admin@elcorp.na",
        "password": "Admin1234!",
        "first_name": "Admin",
        "last_name": "User",
    })
    data = resp.get_json()
    user = db.session.get(User, data["user"]["id"])
    admin_role = Role.query.filter_by(name="admin").first()
    staff_role = Role.query.filter_by(name="staff").first()
    user.roles.append(admin_role)
    user.roles.append(staff_role)
    db.session.commit()

    # Re-login to get token with admin role
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin@elcorp.na",
        "password": "Admin1234!",
    })
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
