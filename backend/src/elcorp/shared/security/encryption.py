"""
Field encryption - Encrypt sensitive data at rest using Fernet symmetric encryption.
"""

from cryptography.fernet import Fernet
import base64
import os
from typing import Optional


class FieldEncryption:
    """
    Encrypt and decrypt sensitive fields at rest.
    Uses Fernet (symmetric encryption with AES).
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption with a key.
        If no key provided, loads from ENCRYPTION_KEY environment variable.
        """
        if encryption_key is None:
            encryption_key = os.getenv(
                "ENCRYPTION_KEY",
                base64.urlsafe_b64encode(os.urandom(32)).decode(),
            )
        self.cipher_suite = Fernet(encryption_key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.
        """
        ciphertext = self.cipher_suite.encrypt(plaintext.encode())
        return ciphertext.decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a ciphertext string.
        """
        plaintext = self.cipher_suite.decrypt(ciphertext.encode())
        return plaintext.decode()

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key for use with this class.
        Store this securely (e.g., in environment variables or secrets manager).
        """
        return base64.urlsafe_b64encode(os.urandom(32)).decode()
