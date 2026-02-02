"""
Rate limiting - Prevent brute force attacks with rate limiting.
"""

from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Dict, Tuple


class RateLimiter:
    """
    Simple in-memory rate limiter (for development).
    In production, use Redis for distributed rate limiting.
    """

    def __init__(self):
        self.attempts: Dict[str, list[datetime]] = defaultdict(list)

    def is_allowed(
        self, key: str, max_attempts: int = 5, window_seconds: int = 60
    ) -> bool:
        """
        Check if a request is allowed under rate limit.
        Removes attempts older than the time window.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window_seconds)

        # Remove old attempts outside the window
        self.attempts[key] = [
            attempt for attempt in self.attempts[key] if attempt > cutoff
        ]

        # Check if under limit
        if len(self.attempts[key]) < max_attempts:
            self.attempts[key].append(now)
            return True

        return False

    def get_remaining_attempts(
        self, key: str, max_attempts: int = 5, window_seconds: int = 60
    ) -> Tuple[int, int]:
        """
        Get remaining attempts and time until next attempt is allowed.
        Returns (remaining_attempts, seconds_until_reset)
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window_seconds)

        # Remove old attempts
        self.attempts[key] = [
            attempt for attempt in self.attempts[key] if attempt > cutoff
        ]

        remaining = max_attempts - len(self.attempts[key])
        oldest = self.attempts[key][0] if self.attempts[key] else now
        reset_at = oldest + timedelta(seconds=window_seconds)
        seconds_until_reset = max(0, int((reset_at - now).total_seconds()))

        return (max(0, remaining), seconds_until_reset)

    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        self.attempts[key] = []


# Common rate limiting patterns
class AuthRateLimiter:
    """Pre-configured rate limiters for authentication."""

    def __init__(self):
        self.limiter = RateLimiter()

    def check_login_attempt(self, identifier: str) -> bool:
        """
        Check login attempts: max 5 per 60 seconds.
        """
        return self.limiter.is_allowed(f"login:{identifier}", max_attempts=5, window_seconds=60)

    def check_registration_attempt(self, ip_address: str) -> bool:
        """
        Check registration attempts: max 3 per hour per IP.
        """
        return self.limiter.is_allowed(
            f"register:{ip_address}", max_attempts=3, window_seconds=3600
        )

    def check_password_reset_attempt(self, email: str) -> bool:
        """
        Check password reset attempts: max 3 per hour.
        """
        return self.limiter.is_allowed(
            f"reset:{email}", max_attempts=3, window_seconds=3600
        )

    def reset_user_limits(self, identifier: str) -> None:
        """Reset all rate limits for a user (after successful login)."""
        self.limiter.reset(f"login:{identifier}")
