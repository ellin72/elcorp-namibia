"""
app/celery_app.py - Celery configuration and task definitions
Provides async task processing with Redis broker, retry logic, and dead-letter queue
"""

import logging
import os
from celery import Celery, Task
from celery.utils.log import get_task_logger
from datetime import timedelta

logger = get_task_logger(__name__)

# Initialize Celery
celery = Celery(__name__)

# Configure Celery from environment
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

celery.conf.update(
    # Broker settings
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,  # Tasks ack after execution, not before
    task_reject_on_worker_lost=True,  # Requeue if worker dies
    worker_max_tasks_per_child=1000,  # Prevent memory leaks
    
    # Retry settings
    task_autoretry_for=(Exception,),
    task_max_retries=3,
    task_default_retry_delay=60,  # Retry after 1 minute
    
    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Include task status in results
    
    # Beat schedule (for periodic tasks)
    beat_schedule={
        'check-sla-breaches-every-5-minutes': {
            'task': 'app.tasks.check_sla_breaches',
            'schedule': timedelta(minutes=5),
        },
        'cleanup-old-audit-logs-daily': {
            'task': 'app.tasks.cleanup_old_audit_logs',
            'schedule': timedelta(hours=24),
        },
        'backup-database-nightly': {
            'task': 'app.tasks.backup_database',
            'schedule': timedelta(hours=24),  # Daily at scheduled time
        },
    },
    
    # Dead letter queue for failed tasks
    task_default_queue='default',
    task_queues={
        'default': {'exchange': 'default', 'routing_key': 'default'},
        'email': {'exchange': 'email', 'routing_key': 'email'},
        'reports': {'exchange': 'reports', 'routing_key': 'reports'},
        'exports': {'exchange': 'exports', 'routing_key': 'exports'},
        'analytics': {'exchange': 'analytics', 'routing_key': 'analytics'},
        'backup': {'exchange': 'backup', 'routing_key': 'backup'},
        'dlq': {'exchange': 'dlq', 'routing_key': 'dlq'},  # Dead letter queue
    },
)


class ContextTask(Task):
    """Task class that adds Flask app context to Celery tasks."""
    
    def __call__(self, *args, **kwargs):
        """Wrap task execution with Flask app context."""
        from app import create_app
        app = create_app()
        with app.app_context():
            return self.run(*args, **kwargs)


celery.Task = ContextTask


def init_celery(app):
    """Initialize Celery with Flask app."""
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery
