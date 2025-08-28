# tests/test_models.py
import time
from datetime import datetime, timedelta
import pytest
from itsdangerous import BadTimeSignature, SignatureExpired
from app.models import User


@pytest.fixture(autouse=True)
def push_app_context(app):
    """Automatically push an app context for all tests in this module."""
    with app.app_context():
        yield


def test_get_reset_password_token_returns_string(user):
    """Test that get_reset_password_token returns a non-empty string."""
    import inspect
    print("\n--- get_reset_password_token file:",
          inspect.getsourcefile(user.get_reset_password_token))
    print(inspect.getsource(user.get_reset_password_token))

    token = user.get_reset_password_token()
    assert isinstance(token, str)
    assert token != ""


def test_verify_reset_password_token_valid(user_factory):
    """Should return correct user for valid token."""
    alice = user_factory()
    bob = user_factory()

    token = alice.get_reset_password_token()
    u = User.verify_reset_password_token(token)
    assert u.id == alice.id


def test_verify_reset_password_token_expired(user_factory):
    """Should return None for expired token."""
    u = user_factory()
    token = u.get_reset_password_token(expires_sec=1)
    time.sleep(2)
    expired = User.verify_reset_password_token(token)
    assert expired is None


def test_verify_reset_password_token_invalid():
    """Should return None for invalid token."""
    fake_token = "not-a-valid-token"
    result = User.verify_reset_password_token(fake_token)
    assert result is None


def test_invalid_expiry_config_raises_runtime_error(monkeypatch, user, app):
    """Invalid PASSWORD_RESET_TOKEN_EXPIRY should raise RuntimeError."""
    monkeypatch.setitem(app.config, "PASSWORD_RESET_TOKEN_EXPIRY", "not-an-int")
    with pytest.raises(RuntimeError) as exc:
        user.get_reset_password_token()
    assert "Invalid TOKEN_EXPIRY" in str(exc.value)



def test_verify_reset_password_token_bad_signature(user):
    """Should handle BadTimeSignature gracefully."""
    token = user.get_reset_password_token()
    tampered_token = token + "tampered"
    result = User.verify_reset_password_token(tampered_token)
    assert result is None


def test_verify_reset_password_token_signature_expired(user, app, monkeypatch):
    """Should handle SignatureExpired gracefully."""
    token = user.get_reset_password_token()
    monkeypatch.setitem(app.config, "PASSWORD_RESET_TOKEN_EXPIRY", 1)
    time.sleep(2)
    result = User.verify_reset_password_token(token)
    assert result is None


def test_get_reset_password_token_with_invalid_expiry(user, app, monkeypatch):
    """Invalid expiry config should raise RuntimeError."""
    monkeypatch.setitem(app.config, "PASSWORD_RESET_TOKEN_EXPIRY", "invalid")
    with pytest.raises(RuntimeError) as exc:
        user.get_reset_password_token()
    assert "Invalid TOKEN_EXPIRY" in str(exc.value)



def test_verify_valid_token(user, app):
    """Should verify valid token before expiry."""
    app.config['PASSWORD_RESET_TOKEN_EXPIRY'] = 5
    token = user.get_reset_password_token()
    assert User.verify_reset_password_token(token).id == user.id


def test_verify_expired_token(user, app, monkeypatch):
    """Should return None if token is expired."""
    app.config['PASSWORD_RESET_TOKEN_EXPIRY'] = 1
    token = user.get_reset_password_token()
    future = datetime.utcnow() + timedelta(seconds=2)
    monkeypatch.setattr('app.models.datetime', datetime)
    monkeypatch.setattr('app.models.datetime.utcnow', lambda: future)
    assert User.verify_reset_password_token(token) is None


def test_verify_tampered_token():
    """Should return None for tampered token."""
    bad = "not-a-real-token"
    assert User.verify_reset_password_token(bad) is None
