"""
Input validators - Reusable validation functions for common patterns.
"""

import re
from typing import Tuple


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email format.
    Returns (is_valid, error_message).
    """
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not email or len(email) > 254:
        return False, "Email must be between 1 and 254 characters"
    if not re.match(email_regex, email):
        return False, "Invalid email format"
    return True, ""


def validate_phone(phone: str, country_code: str = "NA") -> Tuple[bool, str]:
    """
    Validate phone number for a country.
    Returns (is_valid, error_message).
    """
    if country_code == "NA":  # Namibia
        phone_regex = r"^(\+264|0)[0-9]{8}$"
        normalized = phone.replace(" ", "").replace("-", "")
        if not re.match(phone_regex, normalized):
            return False, "Invalid Namibian phone number (format: +264 or 0 + 8 digits)"
        return True, ""
    return False, f"Unsupported country code: {country_code}"


def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validate username.
    Allowed: alphanumeric, dots, hyphens, underscores.
    Returns (is_valid, error_message).
    """
    if not username or len(username) < 3 or len(username) > 32:
        return False, "Username must be between 3 and 32 characters"

    username_regex = r"^[a-zA-Z0-9._-]+$"
    if not re.match(username_regex, username):
        return False, "Username can only contain letters, numbers, dots, hyphens, and underscores"

    return True, ""


def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate URL format.
    Returns (is_valid, error_message).
    """
    url_regex = r"^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$"
    if not url or len(url) > 2048:
        return False, "URL must be between 1 and 2048 characters"
    if not re.match(url_regex, url):
        return False, "Invalid URL format"
    return True, ""
