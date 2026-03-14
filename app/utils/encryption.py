"""Field-level encryption helpers using Fernet (AES-128-CBC under the hood)."""

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    key = os.getenv("ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError("ENCRYPTION_KEY is not configured")
    # Ensure the key is valid Fernet-compatible (url-safe base64, 32 bytes)
    try:
        Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        # Derive a Fernet key from the raw key material
        raw = base64.urlsafe_b64decode(key + "==")[:32]
        key = base64.urlsafe_b64encode(raw).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value, returning a base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted value."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
