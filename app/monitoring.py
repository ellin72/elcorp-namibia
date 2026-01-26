"""
app/monitoring.py - Monitoring, observability, and health check endpoints
Includes: Prometheus metrics, structured logging, health checks, correlation IDs
"""

import logging
import json
import uuid
from datetime import datetime
from functools import wraps

from flask import request, jsonify, g
from prometheus_client import Counter, Histogram, Gauge, generate_latest

logger = logging.getLogger(__name__)

# ==================== PROMETHEUS METRICS ====================

# Request metrics
request_count = Counter(
    'app_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'app_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Business metrics
service_request_created = Counter(
    'service_requests_created_total',
    'Total service requests created',
    ['category', 'priority']
)

service_request_completed = Counter(
    'service_requests_completed_total',
    'Total service requests completed',
    ['category', 'priority']
)

service_request_active = Gauge(
    'service_requests_active',
    'Active (open/in-progress) service requests',
    ['category', 'priority', 'status']
)

sla_breaches = Counter(
    'sla_breaches_total',
    'Total SLA breaches',
    ['category', 'priority', 'breach_type']
)

# Celery metrics
celery_task_total = Counter(
    'celery_tasks_total',
    'Total Celery tasks executed',
    ['task_name', 'status']
)

celery_task_duration = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name']
)

# Error metrics
errors_total = Counter(
    'app_errors_total',
    'Total application errors',
    ['error_type', 'severity']
)

# Authentication metrics
auth_attempts = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['method', 'status']
)

auth_failed = Counter(
    'auth_failures_total',
    'Failed authentication attempts',
    ['method', 'reason']
)

# Database metrics
db_connection_pool_size = Gauge(
    'db_connection_pool_size',
    'Database connection pool size'
)

db_slow_queries = Counter(
    'db_slow_queries_total',
    'Total slow database queries (>1s)',
    ['query_type']
)


# ==================== STRUCTURED LOGGING ====================

class StructuredLogger:
    """Wrapper for structured JSON logging."""
    
    @staticmethod
    def log_request(method, path, status, duration, user_id=None, correlation_id=None):
        """Log HTTP request in structured format."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'http_request',
            'method': method,
            'path': path,
            'status': status,
            'duration_ms': round(duration * 1000, 2),
            'user_id': user_id,
            'correlation_id': correlation_id,
        }
        logger.info(json.dumps(log_entry))
    
    @staticmethod
    def log_task(task_name, status, duration, user_id=None, correlation_id=None, error=None):
        """Log Celery task execution in structured format."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'celery_task',
            'task_name': task_name,
            'status': status,
            'duration_ms': round(duration * 1000, 2),
            'user_id': user_id,
            'correlation_id': correlation_id,
            'error': error,
        }
        logger.info(json.dumps(log_entry))
    
    @staticmethod
    def log_error(error_type, message, user_id=None, correlation_id=None, traceback=None):
        """Log error in structured format."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'error',
            'error_type': error_type,
            'message': message,
            'user_id': user_id,
            'correlation_id': correlation_id,
            'traceback': traceback,
        }
        logger.error(json.dumps(log_entry))
    
    @staticmethod
    def log_sla_breach(request_id, breach_type, category, priority, hours_overdue):
        """Log SLA breach event."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'sla_breach',
            'request_id': request_id,
            'breach_type': breach_type,
            'category': category,
            'priority': priority,
            'hours_overdue': hours_overdue,
        }
        logger.warning(json.dumps(log_entry))


# ==================== CORRELATION ID TRACKING ====================

def generate_correlation_id():
    """Generate unique correlation ID for request tracing."""
    return str(uuid.uuid4())


def get_correlation_id():
    """Get correlation ID from request context."""
    if not hasattr(g, 'correlation_id'):
        g.correlation_id = generate_correlation_id()
    return g.correlation_id


def track_request(f):
    """
    Decorator to track request metrics and add correlation ID.
    
    Adds correlation ID to request context, logs structured entry,
    and tracks Prometheus metrics.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        import time
        
        # Generate/retrieve correlation ID
        correlation_id = request.headers.get('X-Correlation-ID') or generate_correlation_id()
        g.correlation_id = correlation_id
        
        # Get user ID if authenticated
        user_id = None
        if hasattr(g, 'user') and g.user:
            user_id = g.user.id
        
        # Execute function and time it
        start_time = time.time()
        try:
            response = f(*args, **kwargs)
            status_code = response.status_code if hasattr(response, 'status_code') else 200
        except Exception as e:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            
            # Log structured entry
            StructuredLogger.log_request(
                method=request.method,
                path=request.path,
                status=status_code,
                duration=duration,
                user_id=user_id,
                correlation_id=correlation_id,
            )
            
            # Track metrics
            request_count.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown',
                status=status_code
            ).inc()
            
            request_duration.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown'
            ).observe(duration)
        
        return response
    
    return decorated_function


# ==================== HEALTH CHECK ====================

class HealthCheck:
    """Health check status and endpoint."""
    
    @staticmethod
    def get_status():
        """Get comprehensive health status."""
        try:
            from app.extensions import db
            
            # Test database connection
            try:
                db.session.execute('SELECT 1')
                db_status = 'healthy'
            except Exception as e:
                logger.error(f'Database health check failed: {str(e)}')
                db_status = 'unhealthy'
            
            # Test Celery connectivity
            try:
                from app.celery_app import celery
                celery_status = 'healthy'
            except Exception as e:
                logger.error(f'Celery health check failed: {str(e)}')
                celery_status = 'unhealthy'
            
            # Test Redis connectivity
            try:
                import redis
                redis_client = redis.from_url(
                    os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
                )
                redis_client.ping()
                redis_status = 'healthy'
            except Exception as e:
                logger.warning(f'Redis health check failed: {str(e)}')
                redis_status = 'degraded'
            
            # Determine overall status
            if db_status == 'unhealthy':
                overall_status = 'unhealthy'
            elif redis_status == 'degraded' or celery_status == 'unhealthy':
                overall_status = 'degraded'
            else:
                overall_status = 'healthy'
            
            return {
                'status': overall_status,
                'timestamp': datetime.utcnow().isoformat(),
                'components': {
                    'database': db_status,
                    'celery': celery_status,
                    'redis': redis_status,
                },
                'version': os.environ.get('APP_VERSION', 'unknown'),
                'environment': os.environ.get('FLASK_ENV', 'unknown'),
            }
        except Exception as e:
            logger.error(f'Health check failed: {str(e)}')
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
            }
    
    @staticmethod
    def health_endpoint():
        """Flask endpoint for health checks."""
        status = HealthCheck.get_status()
        status_code = 200 if status['status'] == 'healthy' else 503 if status['status'] == 'unhealthy' else 200
        return jsonify(status), status_code


# ==================== METRICS ENDPOINT ====================

def metrics_endpoint():
    """Prometheus metrics endpoint."""
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}


# ==================== SENTRY INTEGRATION ====================

def init_sentry(app, dsn=None):
    """Initialize Sentry for error tracking."""
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        
        if not dsn:
            dsn = os.environ.get('SENTRY_DSN')
        
        if dsn:
            sentry_sdk.init(
                dsn=dsn,
                integrations=[
                    FlaskIntegration(),
                    SqlalchemyIntegration(),
                    CeleryIntegration(),
                ],
                traces_sample_rate=0.1,  # 10% of transactions
                profiles_sample_rate=0.01,  # 1% of transactions
                environment=os.environ.get('FLASK_ENV', 'production'),
                release=os.environ.get('APP_VERSION', 'unknown'),
            )
            logger.info('Sentry initialized')
        else:
            logger.warning('SENTRY_DSN not set, error tracking disabled')
    except ImportError:
        logger.warning('sentry-sdk not installed, error tracking disabled')
    except Exception as e:
        logger.error(f'Failed to initialize Sentry: {str(e)}')


# ==================== INITIALIZATION ====================

def init_monitoring(app):
    """Initialize all monitoring and observability features."""
    
    # Register health check endpoint
    app.add_url_rule('/health', 'health', HealthCheck.health_endpoint)
    app.add_url_rule('/metrics', 'metrics', metrics_endpoint)
    
    # Initialize Sentry
    init_sentry(app)
    
    logger.info('Monitoring initialized')
