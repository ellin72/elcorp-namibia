"""
Value objects - Immutable objects that represent domain concepts.
Value objects are compared by value, not identity.
"""

import re
from dataclasses import dataclass
from typing import NewType

from .exceptions import ValidationException

# Type aliases for strong typing
UserId = NewType("UserId", str)
RoleId = NewType("RoleId", str)
ServiceRequestId = NewType("ServiceRequestId", str)


@dataclass(frozen=True)
class Email:
    """Email value object with validation."""

    value: str

    def __post_init__(self):
        """Validate email format."""
        # Email regex from HTML5 spec (simplified)
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_regex, self.value):
            raise ValidationException(f"Invalid email format: {self.value}", field="email")

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if not isinstance(other, Email):
            return False
        return self.value.lower() == other.value.lower()

    def __hash__(self) -> int:
        return hash(self.value.lower())


@dataclass(frozen=True)
class PhoneNumber:
    """Phone number value object with validation."""

    value: str
    country_code: str = "NA"  # Namibia

    def __post_init__(self):
        """Validate phone number format."""
        # Namibia phone number pattern: +264 or 0 followed by 8 digits
        phone_regex = r"^(\+264|0)[0-9]{8}$"
        normalized = self.value.replace(" ", "").replace("-", "")
        if not re.match(phone_regex, normalized):
            raise ValidationException(
                f"Invalid phone number for {self.country_code}: {self.value}", field="phone"
            )

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if not isinstance(other, PhoneNumber):
            return False
        return self.normalize() == other.normalize()

    def __hash__(self) -> int:
        return hash(self.normalize())

    def normalize(self) -> str:
        """Return normalized phone number format."""
        normalized = self.value.replace(" ", "").replace("-", "")
        if normalized.startswith("0"):
            normalized = "+264" + normalized[1:]
        return normalized


@dataclass(frozen=True)
class WalletAddress:
    """Blockchain wallet address value object."""

    value: str
    blockchain: str = "ethereum"

    def __post_init__(self):
        """Validate wallet address format."""
        if self.blockchain == "ethereum":
            if not re.match(r"^0x[a-fA-F0-9]{40}$", self.value):
                raise ValidationException(
                    f"Invalid Ethereum wallet address: {self.value}", field="wallet_address"
                )
        elif self.blockchain == "solana":
            if not re.match(r"^[1-9A-HJ-NP-Z]{43,44}$", self.value):
                raise ValidationException(
                    f"Invalid Solana wallet address: {self.value}", field="wallet_address"
                )

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if not isinstance(other, WalletAddress):
            return False
        return self.value.lower() == other.value.lower() and self.blockchain == other.blockchain

    def __hash__(self) -> int:
        return hash((self.value.lower(), self.blockchain))


@dataclass(frozen=True)
class Money:
    """Money value object with amount and currency."""

    amount: float
    currency: str = "NAD"  # Namibian Dollar

    def __post_init__(self):
        """Validate money amount."""
        if self.amount < 0:
            raise ValidationException(f"Amount cannot be negative: {self.amount}", field="amount")

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency

    def __hash__(self) -> int:
        return hash((self.amount, self.currency))

    def add(self, other: "Money") -> "Money":
        """Add two money objects (must have same currency)."""
        if self.currency != other.currency:
            raise ValidationException(
                f"Cannot add different currencies: {self.currency} and {other.currency}"
            )
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: "Money") -> "Money":
        """Subtract two money objects (must have same currency)."""
        if self.currency != other.currency:
            raise ValidationException(
                f"Cannot subtract different currencies: {self.currency} and {other.currency}"
            )
        return Money(self.amount - other.amount, self.currency)
