# tests/test_models.py

import pytest
import time
from datetime import datetime, timedelta
from itsdangerous import BadTimeSignature, SignatureExpired
from app.models import User

def test_get_reset_password_token_returns_string(app, user):
    """Test that get_reset_password_token returns a non-empty string."""
    # Debug: print the source of the method to ensure it's the updated one
    import inspect
    print("\n--- get_reset_password_token file:", 
          inspect.getsourcefile(user.get_reset_password_token))
    print(inspect.getsource(user.get_reset_password_token))

    token = user.get_reset_password_token()
    assert isinstance(token, str)
    assert token != ""


def test_verify_reset_password_token_valid(user_factory):
    """Test that verify_reset_password_token returns the correct user for a valid token."""
    alice = user_factory()
    bob   = user_factory()

    token = alice.get_reset_password_token()
    user  = User.verify_reset_password_token(token)
    assert user.id == alice.id

def test_verify_reset_password_token_expired(user_factory):
    """Test that verify_reset_password_token returns None for an expired token."""
    u     = user_factory()
    token = u.get_reset_password_token(expires_sec=1)

    time.sleep(2)

    expired = User.verify_reset_password_token(token)
    assert expired is None


def test_verify_reset_password_token_invalid(app):
    """Test that verify_reset_password_token returns None for an invalid token."""
    fake_token = "not-a-valid-token"
    result = User.verify_reset_password_token(fake_token)
    assert result is None


def test_invalid_expiry_config_raises_runtime_error(app, monkeypatch, user):
    """Test that an invalid PASSWORD_RESET_TOKEN_EXPIRY config raises RuntimeError."""
    # monkey-patch config to an uncastable value
    monkeypatch.setitem(app.config, "PASSWORD_RESET_TOKEN_EXPIRY", "not-an-int")
    with pytest.raises(RuntimeError) as exc:
        user.get_reset_password_token()
    assert "Invalid PASSWORD_RESET_TOKEN_EXPIRY" in str(exc.value)
    
    
def test_verify_reset_password_token_bad_signature(app, user):
    """Test that verify_reset_password_token handles BadTimeSignature."""
    token = user.get_reset_password_token()
    # Tamper with the token to make it invalid
    tampered_token = token + "tampered"
    result = User.verify_reset_password_token(tampered_token)
    assert result is None
    
def test_verify_reset_password_token_signature_expired(app, user, monkeypatch):
    """Test that verify_reset_password_token handles SignatureExpired."""
    token = user.get_reset_password_token()
    # monkey-patch config to a very short expiry
    monkeypatch.setitem(app.config, "PASSWORD_RESET_TOKEN_EXPIRY", 1)
    time.sleep(2)  # wait for token to expire
    result = User.verify_reset_password_token(token)
    assert result is None
    
def test_get_reset_password_token_with_invalid_expiry(app, user, monkeypatch):
    """Test that get_reset_password_token raises RuntimeError with invalid expiry config."""
    monkeypatch.setitem(app.config, "PASSWORD_RESET_TOKEN_EXPIRY", "invalid")
    with pytest.raises(RuntimeError) as exc:
        user.get_reset_password_token()
    assert "Invalid PASSWORD_RESET_TOKEN_EXPIRY" in str(exc.value)
    

def test_verify_valid_token(app, user, monkeypatch):
    """Test that verify_reset_password_token returns the user for a valid token."""
    app.config['PASSWORD_RESET_TOKEN_EXPIRES'] = 1
    token = user.get_reset_password_token()
    # immediately verify before expiry
    assert User.verify_reset_password_token(token).id == user.id

def test_verify_expired_token(app, user, monkeypatch, tmp_path):
    """Test that verify_reset_password_token returns None for an expired token."""
    app.config['PASSWORD_RESET_TOKEN_EXPIRES'] = 1
    token = user.get_reset_password_token()
    # fast-forward beyond expiry
    future = datetime.utcnow() + timedelta(seconds=2)
    monkeypatch.setattr('app.models.datetime.utcnow', lambda: future)
    assert User.verify_reset_password_token(token) is None

def test_verify_tampered_token(app):
    """Test that verify_reset_password_token returns None for a tampered token."""
    bad = "not-a-real-token"
    assert User.verify_reset_password_token(bad) is None
