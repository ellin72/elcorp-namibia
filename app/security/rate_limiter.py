"""
app/security/rate_limiter.py - Rate limiting and abuse detection
Protects against brute force attacks and API abuse
"""

import logging
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict

from flask import request, g
from functools import wraps

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with IP-based tracking and adaptive blocking."""
    
    # Storage: {key: {'attempts': int, 'last_attempt': datetime, 'blocked_until': datetime}}
    _storage = defaultdict(lambda: {'attempts': 0, 'last_attempt': None, 'blocked_until': None})
    
    # Configuration
    CONFIG = {
        'login': {'max_attempts': 5, 'window_minutes': 15, 'lockout_minutes': 30},
        'register': {'max_attempts': 3, 'window_minutes': 60, 'lockout_minutes': 60},
        'password_reset': {'max_attempts': 5, 'window_minutes': 60, 'lockout_minutes': 60},
        'api': {'max_requests': 100, 'window_minutes': 1, 'lockout_minutes': 5},
    }
    
    @staticmethod
    def get_client_key(include_user=False):
        """Get unique key for current client (IP + User ID)."""
        ip = request.remote_addr or 'unknown'
        key = f"ip:{ip}"
        
        if include_user and hasattr(g, 'user') and g.user:
            key = f"user:{g.user.id}"
        
        return key
    
    @staticmethod
    def check_rate_limit(key, config_key):
        """
        Check if rate limit is exceeded.
        
        Returns:
            (allowed: bool, remaining: int, reset_in_seconds: int)
        """
        config = RateLimiter.CONFIG.get(config_key, {})
        max_attempts = config.get('max_attempts', 10)
        window_minutes = config.get('window_minutes', 1)
        lockout_minutes = config.get('lockout_minutes', 15)
        
        now = datetime.utcnow()
        entry = RateLimiter._storage[key]
        
        # Check if currently blocked
        if entry['blocked_until'] and now < entry['blocked_until']:
            reset_seconds = int((entry['blocked_until'] - now).total_seconds())
            logger.warning(f'Rate limit: {key} blocked until {entry["blocked_until"]}')
            return False, 0, reset_seconds
        
        # Reset if window expired
        if entry['last_attempt'] and (now - entry['last_attempt']).total_seconds() > (window_minutes * 60):
            entry['attempts'] = 0
            entry['last_attempt'] = None
            entry['blocked_until'] = None
        
        # Check if limit exceeded
        if entry['attempts'] >= max_attempts:
            entry['blocked_until'] = now + timedelta(minutes=lockout_minutes)
            logger.warning(f'Rate limit exceeded for {key}, blocking until {entry["blocked_until"]}')
            reset_seconds = lockout_minutes * 60
            return False, 0, reset_seconds
        
        # Increment attempt
        entry['attempts'] += 1
        entry['last_attempt'] = now
        
        remaining = max(0, max_attempts - entry['attempts'])
        reset_seconds = window_minutes * 60
        
        return True, remaining, reset_seconds
    
    @staticmethod
    def record_attempt(key):
        """Record failed attempt for client."""
        RateLimiter._storage[key]['last_attempt'] = datetime.utcnow()
    
    @staticmethod
    def reset_attempts(key):
        """Reset attempts for client (on success)."""
        RateLimiter._storage[key] = {'attempts': 0, 'last_attempt': None, 'blocked_until': None}
    
    @staticmethod
    def is_ip_blocked(ip):
        """Check if IP is currently blocked."""
        key = f"ip:{ip}"
        entry = RateLimiter._storage.get(key, {})
        blocked_until = entry.get('blocked_until')
        
        if blocked_until and datetime.utcnow() < blocked_until:
            return True
        return False


def rate_limit(config_key='api'):
    """
    Decorator to apply rate limiting to a route.
    
    Args:
        config_key: Configuration key ('login', 'register', 'password_reset', 'api')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            key = RateLimiter.get_client_key(include_user=(config_key == 'api'))
            allowed, remaining, reset_seconds = RateLimiter.check_rate_limit(key, config_key)
            
            if not allowed:
                logger.warning(f'Rate limit exceeded: {key} for {config_key}')
                from flask import jsonify
                return jsonify({
                    'status': 'error',
                    'message': 'Too many requests. Please try again later.',
                    'retry_after': reset_seconds,
                }), 429
            
            # Try to execute function
            try:
                response = f(*args, **kwargs)
                # On success, reset attempts
                RateLimiter.reset_attempts(key)
                return response
            except Exception as e:
                # On failure, increment attempt
                RateLimiter.record_attempt(key)
                raise
        
        return decorated_function
    return decorator


# ==================== BRUTE FORCE DETECTION ====================

class BruteForceDetector:
    """Detect and alert on brute force patterns."""
    
    # Track failed attempts by IP
    _failed_attempts = defaultdict(lambda: [])
    
    @staticmethod
    def record_failed_attempt(ip, attempt_type='login'):
        """Record a failed attempt."""
        now = datetime.utcnow()
        attempts = BruteForceDetector._failed_attempts[ip]
        
        # Keep only last 10 attempts
        attempts.append({'type': attempt_type, 'timestamp': now})
        if len(attempts) > 10:
            attempts.pop(0)
        
        # Check for pattern
        BruteForceDetector._check_pattern(ip, attempts)
    
    @staticmethod
    def _check_pattern(ip, attempts):
        """Check for brute force patterns."""
        if len(attempts) < 5:
            return
        
        # Check if 5+ failed attempts in last 5 minutes
        recent = [a for a in attempts if (datetime.utcnow() - a['timestamp']).total_seconds() < 300]
        
        if len(recent) >= 5:
            logger.error(f'BRUTE FORCE DETECTED: {ip} - {len(recent)} failed attempts in 5 minutes')
            # TODO: Send alert to admin, potentially block IP
            BruteForceDetector._send_alert(ip, recent)
    
    @staticmethod
    def _send_alert(ip, attempts):
        """Send alert to administrators."""
        from app.tasks import send_email_async
        
        # TODO: Get admin emails from config/database
        admin_email = 'admin@example.com'
        
        subject = f'SECURITY ALERT: Brute force attempt from {ip}'
        body = f'''
        Brute force attack detected!
        
        IP Address: {ip}
        Attempts: {len(attempts)}
        Time Window: Last 5 minutes
        
        Recommended Action:
        - Block IP temporarily
        - Review logs for other suspicious activity
        - Monitor for additional attacks
        '''
        
        # Queue email task
        send_email_async.delay(subject, admin_email, body)
    
    @staticmethod
    def clear_attempts(ip):
        """Clear attempt history for IP."""
        if ip in BruteForceDetector._failed_attempts:
            del BruteForceDetector._failed_attempts[ip]
