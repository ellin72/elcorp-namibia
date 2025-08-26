import os
import random
import pytest
from app import create_app, db
from app.models import User, Role

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
        WTF_CSRF_ENABLED=False,
        PASSWORD_RESET_TOKEN_EXPIRY=3600,  # default expiry for tests
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
# Admin user fixture
# -------------------------
@pytest.fixture
def admin_user(session, admin_role):
    """
    Creates a default admin user with the admin role.
    """
    user = User(username="admin", email="admin@example.com")
    user.set_password("password123")
    user.roles.append(admin_role)
    session.add(user)
    session.commit()
    return user

# -------------------------
# Single-user fixture
# -------------------------
@pytest.fixture
def user(app):
    """
    Creates one user per test with unique username, email, and phone.
    """
    suffix = random.randint(100000, 999999)
    username = f"testuser{suffix}"
    email = f"{username}@example.com"
    phone = str(random.randint(600_000_0000, 799_999_9999))

    u = User(
        username=username,
        email=email,
        full_name="Test User",
        phone=phone
    )
    u.set_password("password123")
    db.session.add(u)
    db.session.commit()
    return u

# -------------------------
# User factory fixture
# -------------------------
@pytest.fixture
def user_factory(app):
    """
    Factory that emits users with unique credentials each call.
    """
    def _create(**kwargs):
        suffix = random.randint(100000, 999999)
        defaults = {
            'username':  f"user{suffix}",
            'email':     f"user{suffix}@example.com",
            'full_name': f"Test User {suffix}",
            'password':  "password123",
            'phone':     str(random.randint(600_000_0000, 799_999_9999))
        }
        defaults.update(kwargs)

        u = User(
            username=defaults['username'],
            email=defaults['email'],
            full_name=defaults['full_name'],
            phone=defaults['phone']
        )
        u.set_password(defaults['password'])
        db.session.add(u)
        db.session.commit()
        return u

    return _create

# -------------------------
# Auto-push request context
# -------------------------
@pytest.fixture(autouse=True)
def push_test_request_context(app):
    """
    Automatically push a request context for every test.
    This covers both app and request globals (current_app, request, url_for, session).
    """
    with app.test_request_context():
        yield
