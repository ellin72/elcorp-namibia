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
    os.environ["FLASK_ENV"] = "testing"

    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_ENABLED=False,
        PASSWORD_RESET_TOKEN_EXPIRY=3600,
    )

    # Create/drop tables once per session
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


# -------------------------
# Auto-seed roles for ALL tests
# -------------------------
@pytest.fixture(autouse=True, scope="session")
def seed_roles(app):
    """
    Ensure default roles exist before any test runs.
    """
    with app.app_context():
        base_roles = [
            ("user",     "Default regular user role"),
            ("verifier","Can verify VIN records"),
            ("staff",    "Staff member role"),
            ("admin",    "Administrator with full access"),
        ]
        for name, desc in base_roles:
            if not Role.query.filter_by(name=name).first():
                db.session.add(Role(name=name, description=desc))
        db.session.commit()


# -------------------------
# Client fixture
# -------------------------
@pytest.fixture(scope="session")
def client(app):
    """Flask test client."""
    return app.test_client()


# -------------------------
# Session fixture
# -------------------------
@pytest.fixture(scope="function")
def session(app):
    """
    Creates a transactional database session for a single test,
    rolls back at teardown.
    """
    # create a real database connection
    connection = db.engine.connect()
    transaction = connection.begin()

    # bind a session to that connection
    db.session.bind = connection

    yield db.session

    transaction.rollback()
    connection.close()
    db.session.remove()


# -------------------------
# Admin role fixture
# -------------------------
@pytest.fixture
def admin_role(session):
    """Return the pre-seeded 'admin' Role."""
    return session.query(Role).filter_by(name="admin").one()


# -------------------------
# Admin user fixture
# -------------------------
@pytest.fixture
def admin_user(session, admin_role):
    """
    Create a User with the 'admin' role.
    """
    u = User(
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        phone=str(random.randint(600_000_0000, 799_999_9999)),
        role=admin_role
    )
    u.set_password("password123")
    session.add(u)
    session.commit()
    return u


# -------------------------
# Single-user fixture
# -------------------------
@pytest.fixture
def user(session):
    """
    Create one User per test, always with the 'user' role.
    """
    suffix = random.randint(100000, 999999)
    role = session.query(Role).filter_by(name="user").one()

    u = User(
        username=f"testuser{suffix}",
        email=f"testuser{suffix}@example.com",
        full_name="Test User",
        phone=str(random.randint(600_000_0000, 799_999_9999)),
        role=role
    )
    u.set_password("password123")
    session.add(u)
    session.commit()
    return u


# -------------------------
# User-factory fixture
# -------------------------
@pytest.fixture
def user_factory(session):
    """
    Returns a callable that creates users with unique creds and a 'user' role.
    Usage:
        alice = user_factory()
        bob   = user_factory(role=verifier_role)
    """
    def _create(**kwargs):
        suffix = random.randint(100000, 999999)
        defaults = {
            "username":  f"user{suffix}",
            "email":     f"user{suffix}@example.com",
            "full_name": f"Test User {suffix}",
            "password":  "password123",
            "phone":     str(random.randint(600_000_0000, 799_999_9999)),
            "role":      session.query(Role).filter_by(name="user").one()
        }
        defaults.update(kwargs)

        u = User(
            username=defaults["username"],
            email=defaults["email"],
            full_name=defaults["full_name"],
            phone=defaults["phone"],
            role=defaults["role"]
        )
        u.set_password(defaults["password"])
        session.add(u)
        session.commit()
        return u

    return _create


# -------------------------
# Auto-push request context
# -------------------------
@pytest.fixture(autouse=True)
def push_request_context(app):
    """So current_app, url_for, request, etc. all work."""
    with app.test_request_context():
        yield



# Minimal conftest that tries to import application factory if present.
# Adjust this to match your repo's app factory name (create_app, make_app, etc.)
try:
    from app import create_app
except Exception:
    create_app = None


@pytest.fixture
def app():
    if create_app:
        app = create_app({'TESTING': True})
        yield app
    else:
        pytest.skip("No application factory found (create_app); adapt tests.")

    db.session.remove()
    db.drop_all()