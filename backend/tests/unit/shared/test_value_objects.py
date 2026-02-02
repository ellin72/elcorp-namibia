"""
Unit tests for value objects.
"""

import pytest
from src.elcorp.shared.domain import (
    Email,
    PhoneNumber,
    WalletAddress,
    Money,
    ValidationException,
)


class TestEmail:
    """Test Email value object."""

    def test_valid_email_creation(self):
        """Test creating a valid email."""
        email = Email("john@example.com")
        assert str(email) == "john@example.com"

    def test_invalid_email_format(self):
        """Test that invalid email format raises exception."""
        with pytest.raises(ValidationException) as exc_info:
            Email("invalid-email")
        assert "Invalid email format" in str(exc_info.value)

    def test_email_case_insensitivity(self):
        """Test that emails are compared case-insensitively."""
        email1 = Email("John@Example.com")
        email2 = Email("john@example.com")
        assert email1 == email2

    def test_email_hash(self):
        """Test that equal emails have same hash."""
        email1 = Email("john@example.com")
        email2 = Email("john@example.com")
        assert hash(email1) == hash(email2)


class TestPhoneNumber:
    """Test PhoneNumber value object."""

    def test_valid_namibia_phone_with_country_code(self):
        """Test valid Namibian phone with country code."""
        phone = PhoneNumber("+26461234567")
        assert phone.normalize() == "+26461234567"

    def test_valid_namibia_phone_with_zero(self):
        """Test valid Namibian phone starting with 0."""
        phone = PhoneNumber("061234567")
        assert phone.normalize() == "+26461234567"

    def test_invalid_phone_format(self):
        """Test that invalid phone format raises exception."""
        with pytest.raises(ValidationException) as exc_info:
            PhoneNumber("123")
        assert "Invalid phone number" in str(exc_info.value)

    def test_phone_normalization(self):
        """Test phone number normalization."""
        phone = PhoneNumber("061-234-567")
        assert phone.normalize() == "+26461234567"


class TestWalletAddress:
    """Test WalletAddress value object."""

    def test_valid_ethereum_address(self):
        """Test valid Ethereum address."""
        address = WalletAddress("0x1234567890abcdef1234567890abcdef12345678")
        assert str(address) == "0x1234567890abcdef1234567890abcdef12345678"

    def test_invalid_ethereum_address(self):
        """Test that invalid Ethereum address raises exception."""
        with pytest.raises(ValidationException) as exc_info:
            WalletAddress("0xINVALID")
        assert "Invalid Ethereum" in str(exc_info.value)

    def test_wallet_address_case_insensitive(self):
        """Test wallet address comparison is case-insensitive."""
        addr1 = WalletAddress("0xABCDEF1234567890ABCDEF1234567890ABCDEF12")
        addr2 = WalletAddress("0xabcdef1234567890abcdef1234567890abcdef12")
        assert addr1 == addr2


class TestMoney:
    """Test Money value object."""

    def test_valid_money_creation(self):
        """Test creating money with valid amount."""
        money = Money(100.50, "NAD")
        assert money.amount == 100.50
        assert money.currency == "NAD"

    def test_negative_amount_not_allowed(self):
        """Test that negative amounts raise exception."""
        with pytest.raises(ValidationException) as exc_info:
            Money(-100, "NAD")
        assert "cannot be negative" in str(exc_info.value)

    def test_money_addition(self):
        """Test adding two money objects."""
        m1 = Money(100, "NAD")
        m2 = Money(50, "NAD")
        result = m1.add(m2)
        assert result.amount == 150
        assert result.currency == "NAD"

    def test_money_subtraction(self):
        """Test subtracting two money objects."""
        m1 = Money(100, "NAD")
        m2 = Money(30, "NAD")
        result = m1.subtract(m2)
        assert result.amount == 70
        assert result.currency == "NAD"

    def test_mixed_currency_addition_fails(self):
        """Test that adding different currencies raises exception."""
        m1 = Money(100, "NAD")
        m2 = Money(50, "USD")
        with pytest.raises(ValidationException) as exc_info:
            m1.add(m2)
        assert "different currencies" in str(exc_info.value)
