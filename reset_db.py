"""
reset_db.py — WARNING: This will DROP and recreate your database schema!

Run:
    python reset_db.py
"""

import subprocess
import uuid
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app import create_app, db
from app.models import Role, User

# DB connection config
PG_USER = "postgres"
PG_DB   = "elcorpnamibia"
PG_HOST = "localhost"

app = create_app()

def drop_and_recreate_schema():
    """Drop and recreate the public schema in PostgreSQL."""
    print("💣 Dropping & recreating schema...")
    subprocess.run([
        "psql",
        "-h", PG_HOST,
        "-U", PG_USER,
        "-d", PG_DB,
        "-c", "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    ], check=True)

def reset_migrations():
    """Reset Alembic migrations."""
    print("🗑 Removing migrations folder...")
    subprocess.run(["rm", "-rf", "migrations"], check=False)
    subprocess.run(["flask", "db", "init"], check=True)
    subprocess.run(["flask", "db", "migrate", "-m", "Initial schema"], check=True)
    subprocess.run(["flask", "db", "upgrade"], check=True)

def validate_user_fields(user: User):
    """
    Validate that required User model fields are set and correct.
    """
    assert user.full_name and len(user.full_name) <= 100, "Invalid full_name"
    assert user.username and len(user.username) <= 64, "Invalid username"
    assert user.email and len(user.email) <= 255, "Invalid email"
    assert user.phone and len(user.phone) <= 20, "Invalid phone"
    assert user.password_hash, "Password hash missing"
    assert isinstance(user.is_active, bool), "is_active must be boolean"
    assert isinstance(user.is_admin, bool), "is_admin must be boolean"
    assert isinstance(user.agreed_terms, bool), "agreed_terms must be boolean"
    assert user.wallet_address and len(user.wallet_address) <= 36, "Invalid wallet_address"
    # Optional fields are fine: organization, otp_secret, last_login, created_at

def seed_admin():
    """Create default admin user."""
    print("🌱 Seeding default admin...")
    with app.app_context():
        # Get or create admin role
        admin_role = Role.query.filter_by(name="admin").first()
        if not admin_role:
            admin_role = Role(name="admin", description="Administrator")
            db.session.add(admin_role)
            db.session.commit()

        # Remove admin role from all users
        for u in admin_role.users.all():
            u.roles.remove(admin_role)
        db.session.commit()

        # Create admin user
        admin = User(
            full_name="System Admin",
            username="admin",
            email="admin@elcorpnamibia.com",
            phone="0000000000",
            organization="Elcorp Namibia",
            is_active=True,
            is_admin=True,
            agreed_terms=True,
            wallet_address=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )
        # Set password
        from werkzeug.security import generate_password_hash
        admin.password_hash = generate_password_hash("Elcorp123!")

        # Validate required fields
        validate_user_fields(admin)

        # Attach role
        admin.roles.append(admin_role)
        db.session.add(admin)

        try:
            db.session.commit()
            print("✅ Admin user created — username: admin / password: Elcorp123!")
        except IntegrityError as e:
            db.session.rollback()
            print("❌ Failed to create admin:", e)

if __name__ == "__main__":
    drop_and_recreate_schema()
    reset_migrations()
    seed_admin()
    print("🎉 Database reset complete.")
