"""
Password hashing - Secure password hashing and validation.
"""

import bcrypt
from ..domain.exceptions import ValidationException


class PasswordHasher:
    """
    Secure password hashing using bcrypt.
    Passwords are hashed with salt and cannot be reversed.
    """

    # Bcrypt complexity factor (higher = slower, more secure, but slower login)
    # 12 is recommended for production (takes ~100ms per hash)
    ROUNDS = 12

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password securely using bcrypt.
        """
        if not password or len(password) < 8:
            raise ValidationException("Password must be at least 8 characters", field="password")

        salt = bcrypt.gensalt(rounds=PasswordHasher.ROUNDS)
        return bcrypt.hashpw(password.encode(), salt).decode()

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify a password against a bcrypt hash.
        """
        return bcrypt.checkpw(password.encode(), password_hash.encode())

    @staticmethod
    def validate_password_strength(password: str) -> None:
        """
        Validate password meets complexity requirements.
        """
        if len(password) < 8:
            raise ValidationException(
                "Password must be at least 8 characters", field="password"
            )

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        if not (has_upper and has_lower and has_digit):
            raise ValidationException(
                "Password must contain uppercase, lowercase, and digits",
                field="password",
            )

        # Optional: require special character
        # if not has_special:
        #     raise ValidationException(
        #         "Password must contain special characters",
        #         field="password"
        #     )
