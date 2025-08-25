# conftest.py
import os
import random
import itertools
import pytest
from app import create_app, db
from app.models import User  # adjust if Role is in a separate file
from app.models import Role  # update this path to the actual module where Role is defined



# os.environ.setdefault("PASSWORD_RESET_TOKEN_EXPIRES", "3600")


# -------------------------
# App fixture
# -------------------------
@pytest.fixture(scope="session")
def app():
    """
    Create a Flask app instance configured for testing.
    """
    os.environ["FLASK_ENV"] = "testing"

    # Create the app
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_ENABLED=False
    )

    # Set up the database schema
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

# -------------------------
# Client fixture
# -------------------------
@pytest.fixture(scope="session")
def client(app):
    """
    Flask test client for sending requests to the app.
    """
    return app.test_client()

# -------------------------
# Session fixture
# -------------------------
@pytest.fixture(scope="function")
def session(app):
    """
    Creates a new database session for a test and rolls back after.
    """
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()

        # Bind the session to the connection
        db.session.bind = connection

        yield db.session

        transaction.rollback()
        connection.close()
        db.session.remove()

# -------------------------
# Role fixture
# -------------------------
@pytest.fixture
def admin_role(session):
    """
    Creates an admin role for testing.
    """
    role = Role(name="admin")
    session.add(role)
    session.commit()
    return role

# -------------------------
# User fixture
# -------------------------
@pytest.fixture
def admin_user(session, admin_role):
    """
    Creates a default admin user with the admin role.
    """
    user = User(
        username="admin",
        email="admin@example.com"
    )
    if hasattr(user, "set_password"):
        user.set_password("password123")

    # If your User model has a roles relationship
    if hasattr(user, "roles"):
        user.roles.append(admin_role)

    session.add(user)
    session.commit()
    return user

# 1a. Single-user fixture with unique email & phone

@pytest.fixture
def user(app):
    """
    Creates one user per test with unique username, email, and phone.
    """
    # Generate a random 6-digit suffix to avoid any collisions
    suffix   = random.randint(100000, 999999)
    username = f"testuser{suffix}"
    email    = f"{username}@example.com"
    phone    = str(random.randint(600_000_0000, 799_999_9999))

    u = User(
        username  = username,
        email     = email,
        full_name = "Test User",
        phone     = phone
    )
    u.set_password("password123")
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def user_factory(app):
    """
    Factory that emits users with unique credentials each call.
    """
    def _create(**kwargs):
        suffix   = random.randint(100000, 999999)
        defaults = {
            'username':  f"user{suffix}",
            'email':     f"user{suffix}@example.com",
            'full_name': f"Test User {suffix}",
            'password':  "password123",
            'phone':     str(random.randint(600_000_0000, 799_999_9999))
        }
        defaults.update(kwargs)

        u = User(
            username  = defaults['username'],
            email     = defaults['email'],
            full_name = defaults['full_name'],
            phone     = defaults['phone']
        )
        u.set_password(defaults['password'])
        db.session.add(u)
        db.session.commit()
        return u

    return _create

# -----------------------------------------
# End of conftest.py
