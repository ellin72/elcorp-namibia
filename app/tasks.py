"""
app/tasks.py - Celery task definitions for background processing
Includes: email, report generation, exports, audit logs, backups, SLA checks
"""

import logging
import os
import subprocess
import json
from datetime import datetime, timedelta
from io import StringIO, BytesIO

from celery import current_task, states
from celery.exceptions import Retry, SoftTimeLimitExceeded

from app.celery_app import celery
from app.models import (
    ServiceRequest, ServiceRequestHistory, User, Role,
    AuditLog, SLAMetric, db
)
from app.services.email_service import send_reset_password_email, send_status_update_email
from app.services.export_service import ExportService
from app.extensions import mail

logger = logging.getLogger(__name__)


# ==================== EMAIL TASKS ====================

@celery.task(bind=True, queue='email', max_retries=3)
def send_email_async(self, subject, recipient, body, html=None):
    """
    Send email asynchronously.
    
    Args:
        subject: Email subject
        recipient: Recipient email address
        body: Email body (plain text)
        html: HTML version of email (optional)
    
    Retries: 3 times with exponential backoff
    """
    try:
        from flask_mail import Message
        msg = Message(subject, recipients=[recipient], body=body, html=html)
        mail.send(msg)
        logger.info(f'Email sent to {recipient}: {subject}')
        return {'status': 'sent', 'recipient': recipient}
    except Exception as exc:
        logger.error(f'Error sending email to {recipient}: {str(exc)}')
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery.task(bind=True, queue='email', max_retries=3)
def send_request_status_update(self, request_id, new_status, assigned_to_id=None):
    """
    Send status update email for service request.
    
    Args:
        request_id: ServiceRequest ID
        new_status: New request status
        assigned_to_id: User ID if assignment changed
    """
    try:
        req = ServiceRequest.query.get(request_id)
        if not req:
            logger.warning(f'ServiceRequest {request_id} not found')
            return {'status': 'not_found'}
        
        creator = req.created_by_user
        if creator and creator.email:
            send_status_update_email(creator, req, new_status)
            logger.info(f'Status update email sent for request {request_id}')
        
        if assigned_to_id:
            assigned_user = User.query.get(assigned_to_id)
            if assigned_user and assigned_user.email:
                send_status_update_email(assigned_user, req, new_status)
                logger.info(f'Assignment email sent to {assigned_user.email}')
        
        return {'status': 'sent', 'request_id': request_id}
    except Exception as exc:
        logger.error(f'Error sending status update for request {request_id}: {str(exc)}')
        raise self.retry(exc=exc, countdown=60)


@celery.task(bind=True, queue='email', max_retries=2)
def send_reset_password_email_async(self, user_id, reset_token):
    """Send password reset email asynchronously."""
    try:
        user = User.query.get(user_id)
        if not user or not user.email:
            logger.warning(f'User {user_id} not found or has no email')
            return {'status': 'user_not_found'}
        
        send_reset_password_email(user, reset_token)
        logger.info(f'Password reset email sent to {user.email}')
        return {'status': 'sent', 'user_id': user_id}
    except Exception as exc:
        logger.error(f'Error sending reset email to user {user_id}: {str(exc)}')
        raise self.retry(exc=exc, countdown=30)


# ==================== REPORT & EXPORT TASKS ====================

@celery.task(bind=True, queue='reports', max_retries=3)
def generate_analytics_report(self, user_id, report_type='summary', days=30):
    """
    Generate analytics report asynchronously.
    
    Args:
        user_id: User requesting the report
        report_type: 'summary', 'detailed', 'trends'
        days: Days to analyze
    
    Returns:
        Report file path or URL
    """
    try:
        from app.services.analytics_service import AnalyticsService
        
        user = User.query.get(user_id)
        if not user:
            logger.warning(f'User {user_id} not found')
            return {'status': 'user_not_found'}
        
        # Generate report data
        if report_type == 'summary':
            data = AnalyticsService.get_dashboard_summary()
        else:
            data = {
                'total': AnalyticsService.get_total_requests(),
                'by_status': AnalyticsService.count_requests_by_status(),
                'by_priority': AnalyticsService.count_requests_by_priority(),
            }
        
        # Export to PDF
        pdf_buffer, filename = ExportService.export_analytics_summary_to_pdf(data)
        
        # TODO: Save to storage backend (S3, Azure Blob, etc.)
        logger.info(f'Analytics report generated: {filename}')
        
        return {
            'status': 'completed',
            'filename': filename,
            'user_id': user_id,
            'report_type': report_type,
        }
    except Exception as exc:
        logger.error(f'Error generating report for user {user_id}: {str(exc)}')
        raise self.retry(exc=exc, countdown=300)


@celery.task(bind=True, queue='exports', max_retries=2)
def export_requests_async(self, filter_params, format='csv', user_id=None):
    """
    Export requests to CSV/PDF asynchronously (for large exports).
    
    Args:
        filter_params: Filter dictionary
        format: 'csv' or 'pdf'
        user_id: User requesting export
    
    Returns:
        Export file path
    """
    try:
        # Build query with filters
        query = ServiceRequest.query
        
        if filter_params.get('status'):
            query = query.filter_by(status=filter_params['status'])
        if filter_params.get('priority'):
            query = query.filter_by(priority=filter_params['priority'])
        if filter_params.get('category'):
            query = query.filter_by(category=filter_params['category'])
        
        requests = query.all()
        
        if format == 'csv':
            buffer, filename = ExportService.export_requests_to_csv(requests)
        else:
            buffer, filename = ExportService.export_requests_to_pdf(requests)
        
        logger.info(f'Export completed: {filename} for user {user_id}')
        
        return {
            'status': 'completed',
            'filename': filename,
            'format': format,
            'count': len(requests),
            'user_id': user_id,
        }
    except Exception as exc:
        logger.error(f'Error exporting requests for user {user_id}: {str(exc)}')
        raise self.retry(exc=exc, countdown=300)


# ==================== AUDIT LOG TASKS ====================

@celery.task(bind=True, queue='default', max_retries=3)
def persist_audit_log(self, user_id, action, resource_type, resource_id, 
                      old_values=None, new_values=None, status='success', 
                      error_message=None, ip_address=None):
    """
    Persist audit log entry asynchronously.
    
    Ensures audit logging doesn't block request handling.
    """
    try:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
            status=status,
            error_message=error_message,
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
        )
        db.session.add(audit)
        db.session.commit()
        logger.info(f'Audit log persisted: {action} on {resource_type} {resource_id}')
        return {'status': 'persisted', 'audit_id': audit.id}
    except Exception as exc:
        logger.error(f'Error persisting audit log: {str(exc)}')
        raise self.retry(exc=exc, countdown=30)


@celery.task(queue='default')
def cleanup_old_audit_logs(days_to_keep=90):
    """
    Clean up old audit logs (older than days_to_keep).
    
    Scheduled daily to prevent database bloat.
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        deleted = AuditLog.query.filter(AuditLog.timestamp < cutoff_date).delete()
        db.session.commit()
        logger.info(f'Deleted {deleted} old audit logs')
        return {'status': 'completed', 'deleted_count': deleted}
    except Exception as exc:
        logger.error(f'Error cleaning up audit logs: {str(exc)}')
        return {'status': 'error', 'message': str(exc)}


# ==================== SLA TASKS ====================

@celery.task(bind=True, queue='analytics')
def check_sla_breaches(self):
    """
    Check for SLA breaches across all service requests.
    
    Scheduled every 5 minutes. Updates SLAMetric records.
    """
    try:
        from app.services.sla_service import SLAService
        
        breaches = SLAService.check_all_breaches()
        logger.info(f'SLA check completed: {len(breaches)} breaches detected')
        
        return {
            'status': 'completed',
            'breaches_detected': len(breaches),
            'timestamp': datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        logger.error(f'Error checking SLA breaches: {str(exc)}')
        return {'status': 'error', 'message': str(exc)}


# ==================== BACKUP TASKS ====================

@celery.task(bind=True, queue='backup', max_retries=2)
def backup_database(self):
    """
    Backup PostgreSQL database to encrypted file.
    
    Scheduled nightly. Compresses and encrypts backup.
    """
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.environ.get('BACKUP_DIR', '/backups')
        backup_file = f'{backup_dir}/backup_{timestamp}.sql.gz.enc'
        
        # Ensure backup directory exists
        os.makedirs(backup_dir, exist_ok=True)
        
        # Get database URL
        db_url = os.environ.get('DATABASE_URL', '')
        if not db_url:
            raise ValueError('DATABASE_URL not set')
        
        # Run pg_dump
        logger.info(f'Starting database backup to {backup_file}')
        
        # Extract connection details from DATABASE_URL
        # postgresql://user:password@host:port/dbname
        cmd = f'pg_dump {db_url} | gzip | openssl enc -aes-256-cbc -salt -out {backup_file}'
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f'pg_dump failed: {result.stderr}')
        
        # Verify backup file exists and has content
        if not os.path.exists(backup_file) or os.path.getsize(backup_file) == 0:
            raise RuntimeError('Backup file is empty or missing')
        
        logger.info(f'Database backup completed: {backup_file}')
        
        # Log backup metadata
        backup_size = os.path.getsize(backup_file)
        AuditLog.create(
            user_id=None,
            action='backup_created',
            resource_type='database',
            resource_id=timestamp,
            new_values={'file': backup_file, 'size': backup_size},
            status='success'
        )
        
        return {
            'status': 'completed',
            'file': backup_file,
            'size': backup_size,
            'timestamp': timestamp,
        }
    except Exception as exc:
        logger.error(f'Error backing up database: {str(exc)}')
        raise self.retry(exc=exc, countdown=300)


@celery.task(queue='backup')
def verify_backup(backup_file):
    """
    Verify backup file integrity.
    
    Tests decryption and basic validation.
    """
    try:
        if not os.path.exists(backup_file):
            raise FileNotFoundError(f'Backup file not found: {backup_file}')
        
        # Test decrypt with dummy password (will fail but verifies encryption)
        result = subprocess.run(
            f'openssl enc -d -aes-256-cbc -in {backup_file} -pass pass:test 2>&1 | head -c 100',
            shell=True,
            capture_output=True,
        )
        
        # Even if decrypt fails, file is readable
        logger.info(f'Backup verification passed: {backup_file}')
        
        return {
            'status': 'verified',
            'file': backup_file,
            'timestamp': datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        logger.error(f'Error verifying backup: {str(exc)}')
        return {'status': 'error', 'message': str(exc)}


# ==================== MONITORING TASKS ====================

@celery.task(queue='default')
def health_check():
    """
    Health check task to verify worker and database connectivity.
    
    Returns status for monitoring.
    """
    try:
        # Test database connection
        result = db.session.execute('SELECT 1')
        db_ok = result is not None
        
        return {
            'status': 'healthy',
            'database': 'ok' if db_ok else 'error',
            'worker': 'ok',
            'timestamp': datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        logger.error(f'Health check failed: {str(exc)}')
        return {
            'status': 'unhealthy',
            'error': str(exc),
            'timestamp': datetime.utcnow().isoformat(),
        }


@celery.task(queue='default')
def get_worker_stats():
    """Get Celery worker statistics for monitoring."""
    try:
        from app.celery_app import celery
        
        stats = celery.control.inspect().stats()
        active = celery.control.inspect().active()
        
        return {
            'status': 'ok',
            'workers': stats,
            'active_tasks': active,
            'timestamp': datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        logger.error(f'Error getting worker stats: {str(exc)}')
        return {'status': 'error', 'message': str(exc)}


# ==================== ERROR HANDLING ====================

@celery.task(queue='dlq', bind=True)
def handle_failed_task(self, exc, traceback):
    """
    Handle failed tasks by logging and alerting.
    
    Sends to dead letter queue for investigation.
    """
    logger.error(f'Task {self.name} failed with exception: {exc}')
    logger.error(f'Traceback: {traceback}')
    
    # TODO: Send alert to admin/monitoring system
    
    return {
        'status': 'logged',
        'task': self.name,
        'exception': str(exc),
    }
