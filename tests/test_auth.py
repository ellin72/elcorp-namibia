"""
tests/test_auth.py - Tests for authentication functionality
"""
import pytest
import json
from app import db
from app.models import User, Role


class TestUserRegistration:
    """Test user registration."""
    
    def test_register_valid_user(self, client):
        """Test successful user registration."""
        response = client.post('/auth/register', data={
            'full_name': 'Test User',
            'username': 'testuser',
            'email': 'test@example.com',
            'phone': '1234567890',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'agree_terms': True
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Check user was created
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        assert user.username == 'testuser'
    
    def test_register_duplicate_email(self, client, app):
        """Test registration with duplicate email."""
        with app.app_context():
            user_role = Role.query.filter_by(name='user').first()
            user = User(
                username='existing',
                email='existing@example.com',
                phone='9876543210',
                full_name='Existing User',
                role=user_role,
            )
            user.set_password('pass123')
            db.session.add(user)
            db.session.commit()
        
        response = client.post('/auth/register', data={
            'full_name': 'Another User',
            'username': 'another',
            'email': 'existing@example.com',  # Duplicate
            'phone': '5555555555',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'agree_terms': True
        }, follow_redirects=True)
        
        assert b'already registered' in response.data.lower() or response.status_code == 200


class TestUserLogin:
    """Test user login."""
    
    @pytest.fixture
    def test_user(self, app):
        """Create a test user."""
        with app.app_context():
            user_role = Role.query.filter_by(name='user').first()
            user = User(
                username='loginuser',
                email='login@test.com',
                phone='1111111111',
                full_name='Login Test User',
                role=user_role,
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            return user
    
    def test_login_valid_credentials(self, client, test_user):
        """Test login with valid credentials."""
        response = client.post('/auth/login', data={
            'username': 'loginuser',
            'password': 'password123',
            'remember': False
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_login_invalid_password(self, client, test_user):
        """Test login with invalid password."""
        response = client.post('/auth/login', data={
            'username': 'loginuser',
            'password': 'wrongpassword',
            'remember': False
        }, follow_redirects=True)
        
        assert b'invalid credentials' in response.data.lower() or response.status_code == 200
    
    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user."""
        response = client.post('/auth/login', data={
            'username': 'nonexistent',
            'password': 'password123',
            'remember': False
        }, follow_redirects=True)
        
        assert b'invalid credentials' in response.data.lower() or response.status_code == 200


class TestPasswordChange:
    """Test password change functionality."""
    
    @pytest.fixture
    def auth_user(self, app):
        """Create and authenticate a user."""
        with app.app_context():
            user_role = Role.query.filter_by(name='user').first()
            user = User(
                username='passuser',
                email='pass@test.com',
                phone='2222222222',
                full_name='Password Test User',
                role=user_role,
            )
            user.set_password('oldpassword')
            db.session.add(user)
            db.session.commit()
            return user
    
    def test_change_password_valid(self, client, auth_user):
        """Test changing password with valid credentials."""
        with client:
            client.post('/auth/login', data={
                'username': 'passuser',
                'password': 'oldpassword'
            }, follow_redirects=True)
            
            response = client.post('/auth/change-password', data={
                'current_password': 'oldpassword',
                'new_password': 'newpassword123',
                'new_password_confirm': 'newpassword123'
            }, follow_redirects=True)
            
            assert response.status_code == 200
    
    def test_change_password_wrong_current(self, client, auth_user):
        """Test password change with wrong current password."""
        with client:
            client.post('/auth/login', data={
                'username': 'passuser',
                'password': 'oldpassword'
            }, follow_redirects=True)
            
            response = client.post('/auth/change-password', data={
                'current_password': 'wrongpassword',
                'new_password': 'newpassword123',
                'new_password_confirm': 'newpassword123'
            }, follow_redirects=True)
            
            assert b'incorrect' in response.data.lower() or response.status_code == 200


class TestLogout:
    """Test logout functionality."""
    
    @pytest.fixture
    def logged_in_user(self, app):
        """Create a logged-in user."""
        with app.app_context():
            user_role = Role.query.filter_by(name='user').first()
            user = User(
                username='logoutuser',
                email='logout@test.com',
                phone='3333333333',
                full_name='Logout Test User',
                role=user_role,
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            return user
    
    def test_logout(self, client, logged_in_user):
        """Test user logout."""
        with client:
            client.post('/auth/login', data={
                'username': 'logoutuser',
                'password': 'password123'
            }, follow_redirects=True)
            
            response = client.get('/auth/logout', follow_redirects=True)
            assert response.status_code == 200


class TestPasswordReset:
    """Test password reset functionality."""
    
    @pytest.fixture
    def resetable_user(self, app):
        """Create a user for password reset testing."""
        with app.app_context():
            user_role = Role.query.filter_by(name='user').first()
            user = User(
                username='resetuser',
                email='reset@test.com',
                phone='4444444444',
                full_name='Reset Test User',
                role=user_role,
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            return user
    
    def test_forgot_password_request(self, client, resetable_user):
        """Test password reset request."""
        response = client.post('/auth/forgot_password', data={
            'email': 'reset@test.com'
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_forgot_password_nonexistent_email(self, client):
        """Test password reset request with nonexistent email."""
        response = client.post('/auth/forgot_password', data={
            'email': 'nonexistent@test.com'
        }, follow_redirects=True)
        
        # Should not reveal whether email exists
        assert response.status_code == 200
