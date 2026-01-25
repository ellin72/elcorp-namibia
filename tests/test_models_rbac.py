"""
tests/test_models.py - Tests for database models
"""
import pytest
from app import db
from app.models import User, Role, UserProfile, PasswordHistory, AuditLog, Vehicle


class TestRoleModel:
    """Test Role model."""
    
    def test_create_role(self, app):
        """Test creating a role."""
        with app.app_context():
            role = Role(name="tester", description="Test role")
            db.session.add(role)
            db.session.commit()
            
            retrieved = Role.query.filter_by(name="tester").first()
            assert retrieved is not None
            assert retrieved.description == "Test role"
    
    def test_role_users_relationship(self, app):
        """Test role-users relationship."""
        with app.app_context():
            user_role = Role.query.filter_by(name="user").first()
            admin_role = Role.query.filter_by(name="admin").first()
            
            # Both roles should exist
            assert user_role is not None
            assert admin_role is not None


class TestUserModel:
    """Test User model."""
    
    def test_create_user(self, app):
        """Test creating a user."""
        with app.app_context():
            user_role = Role.query.filter_by(name="user").first()
            user = User(
                username="testuser",
                email="test@example.com",
                phone="1234567890",
                full_name="Test User",
                role=user_role
            )
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
            
            retrieved = User.query.filter_by(email="test@example.com").first()
            assert retrieved is not None
            assert retrieved.username == "testuser"
    
    def test_user_password_hashing(self, app):
        """Test that passwords are hashed correctly."""
        with app.app_context():
            user_role = Role.query.filter_by(name="user").first()
            user = User(
                username="hashtest",
                email="hash@test.com",
                phone="9876543210",
                full_name="Hash Test",
                role=user_role
            )
            password = "secretpassword"
            user.set_password(password)
            
            # Password should be hashed
            assert user.password_hash != password
            assert user.check_password(password)
            assert not user.check_password("wrongpassword")
    
    def test_user_wallet_address_generation(self, app):
        """Test automatic wallet address generation."""
        with app.app_context():
            user_role = Role.query.filter_by(name="user").first()
            user = User(
                username="walletuser",
                email="wallet@test.com",
                phone="5555555555",
                full_name="Wallet User",
                role=user_role
            )
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
            
            assert user.wallet_address is not None
            # Check it's a valid UUID format
            assert len(user.wallet_address) == 36  # UUID4 string length
    
    def test_user_has_role(self, app):
        """Test user role checking."""
        with app.app_context():
            user_role = Role.query.filter_by(name="user").first()
            admin_role = Role.query.filter_by(name="admin").first()
            
            user = User(
                username="roletest",
                email="role@test.com",
                phone="6666666666",
                full_name="Role Test",
                role=user_role
            )
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
            
            assert user.has_role("user")
            assert not user.has_role("admin")


class TestUserProfileModel:
    """Test UserProfile model."""
    
    def test_create_user_profile(self, app):
        """Test creating a user profile."""
        with app.app_context():
            user_role = Role.query.filter_by(name="user").first()
            user = User(
                username="profiletest",
                email="profile@test.com",
                phone="7777777777",
                full_name="Profile Test",
                role=user_role
            )
            user.set_password("password123")
            db.session.add(user)
            db.session.flush()
            
            profile = UserProfile(
                user_id=user.id,
                bio="Test bio",
                country="Namibia",
                city="Windhoek"
            )
            db.session.add(profile)
            db.session.commit()
            
            retrieved = UserProfile.query.filter_by(user_id=user.id).first()
            assert retrieved is not None
            assert retrieved.bio == "Test bio"
    
    def test_user_profile_relationship(self, app):
        """Test user-profile relationship."""
        with app.app_context():
            user_role = Role.query.filter_by(name="user").first()
            user = User(
                username="reltest",
                email="rel@test.com",
                phone="8888888888",
                full_name="Rel Test",
                role=user_role
            )
            user.set_password("password123")
            db.session.add(user)
            db.session.flush()
            
            profile = UserProfile(user_id=user.id)
            db.session.add(profile)
            db.session.commit()
            
            # Retrieve user and check profile relationship
            retrieved_user = User.query.get(user.id)
            assert retrieved_user.profile is not None
            assert retrieved_user.profile.user_id == user.id


class TestPasswordHistoryModel:
    """Test PasswordHistory model."""
    
    def test_create_password_history(self, app):
        """Test recording password history."""
        with app.app_context():
            user_role = Role.query.filter_by(name="user").first()
            user = User(
                username="passhistory",
                email="passhist@test.com",
                phone="9999999999",
                full_name="Pass History",
                role=user_role
            )
            user.set_password("password1")
            db.session.add(user)
            db.session.flush()
            
            history = PasswordHistory(
                user_id=user.id,
                password_hash=user.password_hash
            )
            db.session.add(history)
            db.session.commit()
            
            retrieved = PasswordHistory.query.filter_by(user_id=user.id).first()
            assert retrieved is not None


class TestAuditLogModel:
    """Test AuditLog model."""
    
    def test_create_audit_log(self, app):
        """Test creating an audit log."""
        with app.app_context():
            user_role = Role.query.filter_by(name="user").first()
            user = User(
                username="audituser",
                email="audit@test.com",
                phone="1010101010",
                full_name="Audit User",
                role=user_role
            )
            user.set_password("password123")
            db.session.add(user)
            db.session.flush()
            
            log = AuditLog(
                user_id=user.id,
                action="login",
                details={"ip": "127.0.0.1"}
            )
            db.session.add(log)
            db.session.commit()
            
            retrieved = AuditLog.query.filter_by(user_id=user.id).first()
            assert retrieved is not None
            assert retrieved.action == "login"


class TestVehicleModel:
    """Test Vehicle model."""
    
    def test_create_vehicle(self, app):
        """Test creating a vehicle."""
        with app.app_context():
            user_role = Role.query.filter_by(name="user").first()
            user = User(
                username="carowner",
                email="owner@test.com",
                phone="1111111111",
                full_name="Car Owner",
                role=user_role
            )
            user.set_password("password123")
            db.session.add(user)
            db.session.flush()
            
            vehicle = Vehicle(
                user_id=user.id,
                make="Toyota",
                model="Corolla",
                plate_number="NAB-123"
            )
            db.session.add(vehicle)
            db.session.commit()
            
            retrieved = Vehicle.query.filter_by(plate_number="NAB-123").first()
            assert retrieved is not None
            assert retrieved.make == "Toyota"
    
    def test_vehicle_user_relationship(self, app):
        """Test vehicle-user relationship."""
        with app.app_context():
            user_role = Role.query.filter_by(name="user").first()
            user = User(
                username="multicar",
                email="multicar@test.com",
                phone="2222222222",
                full_name="Multi Car",
                role=user_role
            )
            user.set_password("password123")
            db.session.add(user)
            db.session.flush()
            
            vehicle1 = Vehicle(
                user_id=user.id,
                make="BMW",
                model="X5",
                plate_number="NAB-001"
            )
            vehicle2 = Vehicle(
                user_id=user.id,
                make="Mercedes",
                model="C-Class",
                plate_number="NAB-002"
            )
            db.session.add_all([vehicle1, vehicle2])
            db.session.commit()
            
            # Check relationship
            retrieved_user = User.query.get(user.id)
            assert len(retrieved_user.vehicles) == 2
