"""
Test configuration and fixtures.
"""

import pytest
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Add backend to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def jwt_secret():
    """Provide JWT secret for tests."""
    return "test-secret-key-for-jwt-testing"


@pytest.fixture
def test_user_data():
    """Provide test user registration data."""
    return {
        "username": "john.doe",
        "email": "john@example.com",
        "phone": "+26461234567",
        "password": "SecureP@ss123",
    }


@pytest.fixture
def test_login_data():
    """Provide test login data."""
    return {
        "username": "john.doe",
        "password": "SecureP@ss123",
        "device_id": "device-123-abc",
        "device_name": "Chrome on Windows",
    }


@pytest.fixture
def mock_user_repository():
    """Provide mock user repository."""
    repo = MagicMock()
    repo.get_by_id = MagicMock(return_value=None)
    repo.get_by_email = MagicMock(return_value=None)
    repo.get_by_username = MagicMock(return_value=None)
    repo.email_exists = MagicMock(return_value=False)
    repo.username_exists = MagicMock(return_value=False)
    repo.add = MagicMock()
    repo.update = MagicMock()
    return repo


@pytest.fixture
def mock_device_token_repository():
    """Provide mock device token repository."""
    repo = MagicMock()
    repo.get_by_id = MagicMock(return_value=None)
    repo.get_by_user_and_device = MagicMock(return_value=None)
    repo.get_all_by_user = MagicMock(return_value=[])
    repo.add = MagicMock()
    repo.update = MagicMock()
    return repo
