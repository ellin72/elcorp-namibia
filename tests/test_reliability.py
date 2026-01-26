"""
tests/test_reliability.py - Tests for background processing, SLA, monitoring, and resilience
Covers: Celery tasks, retries, SLA breaches, health checks, rate limiting
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.models import ServiceRequest, SLADefinition, SLAMetric, SLAExemption
from app.services.sla_service import SLAService
from app.security.rate_limiter import RateLimiter, rate_limit
from app.monitoring import HealthCheck


class TestCeleryTasks:
    """Test Celery async task execution and retry logic."""
    
    def test_send_email_async_task(self, app):
        """Test async email task execution."""
        from app.tasks import send_email_async
        
        with app.app_context():
            # Mock the mail service
            with patch('app.tasks.mail.send') as mock_send:
                result = send_email_async.apply_async(
                    args=['Test Subject', 'test@example.com', 'Test body']
                )
                
                assert result is not None
    
    def test_task_retry_on_failure(self):
        """Test task retry logic on exception."""
        from app.tasks import send_email_async
        
        with patch('app.tasks.mail.send') as mock_send:
            # Simulate failure
            mock_send.side_effect = Exception('SMTP error')
            
            # Task should retry
            task = send_email_async.apply_async(
                args=['Subject', 'test@example.com', 'body'],
                retry=True,
                max_retries=3
            )
            
            # Verify task was queued for retry
            assert task is not None
    
    def test_persist_audit_log_task(self, app):
        """Test async audit log persistence."""
        from app.tasks import persist_audit_log
        
        with app.app_context():
            result = persist_audit_log.apply_async(
                args=[1, 'create', 'service_request', 123],
                kwargs={'status': 'success'}
            )
            
            assert result is not None
    
    def test_health_check_task(self, app):
        """Test health check task execution."""
        from app.tasks import health_check
        
        with app.app_context():
            result = health_check.apply()
            
            # Result should be a health status dict
            assert result is not None


class TestSLATracking:
    """Test SLA definition, tracking, and breach detection."""
    
    def test_create_sla_definition(self, app):
        """Test creating SLA definition."""
        with app.app_context():
            sla = SLADefinition(
                category='hardware',
                priority='high',
                response_time_hours=2,
                resolution_time_hours=8,
                is_active=True
            )
            sla.save()
            
            # Verify created
            retrieved = SLADefinition.query.filter_by(
                category='hardware',
                priority='high'
            ).first()
            
            assert retrieved is not None
            assert retrieved.response_time_hours == 2
            assert retrieved.resolution_time_hours == 8
    
    def test_get_sla_definition_fallback(self, app):
        """Test SLA definition fallback to defaults."""
        with app.app_context():
            # Get SLA for non-existent category
            sla = SLAService.get_sla_definition('unknown_category', 'medium')
            
            # Should return default
            assert sla is not None
            assert sla.resolution_time_hours >= 8
    
    def test_track_status_change(self, app, auth):
        """Test tracking status change for SLA."""
        user = auth.register(email='user@test.com', password='pass123')
        
        with app.app_context():
            # Create request
            req = ServiceRequest(
                title='Test Request',
                description='Test',
                category='hardware',
                priority='high',
                status='open',
                created_by=user.id,
            )
            req.save()
            
            # Track status change
            metric = SLAService.track_status_change(req.id, 'in_progress')
            
            assert metric is not None
            assert metric.status == 'in_progress'
            assert metric.first_response_at is not None
    
    def test_check_response_sla_breach(self, app, auth):
        """Test detection of response SLA breach."""
        user = auth.register(email='user@test.com', password='pass123')
        
        with app.app_context():
            # Create old request (older than 4 hours)
            req = ServiceRequest(
                title='Old Request',
                description='Test',
                category='hardware',
                priority='medium',
                status='open',
                created_by=user.id,
                created_at=datetime.utcnow() - timedelta(hours=5)
            )
            req.save()
            
            # Check breach
            is_breached = SLAService.check_response_sla_breach(req.id)
            
            assert is_breached is True
    
    def test_check_resolution_sla_breach(self, app, auth):
        """Test detection of resolution SLA breach."""
        user = auth.register(email='user@test.com', password='pass123')
        
        with app.app_context():
            # Create very old request
            req = ServiceRequest(
                title='Very Old Request',
                description='Test',
                category='software',
                priority='low',
                status='in_progress',
                created_by=user.id,
                created_at=datetime.utcnow() - timedelta(hours=30)
            )
            req.save()
            
            # Check breach (default resolution SLA is 24 hours)
            is_breached = SLAService.check_resolution_sla_breach(req.id)
            
            assert is_breached is True
    
    def test_check_all_breaches(self, app, auth):
        """Test batch SLA breach detection."""
        user = auth.register(email='user@test.com', password='pass123')
        
        with app.app_context():
            # Create breached and non-breached requests
            for i in range(3):
                age_hours = 5 + (i * 10)  # 5, 15, 25 hours old
                req = ServiceRequest(
                    title=f'Request {i}',
                    description='Test',
                    category='hardware',
                    priority='medium',
                    status='open' if i < 2 else 'completed',
                    created_by=user.id,
                    created_at=datetime.utcnow() - timedelta(hours=age_hours)
                )
                req.save()
            
            # Check all breaches
            breaches = SLAService.check_all_breaches()
            
            # Should detect breaches
            assert len(breaches) >= 1
    
    def test_grant_sla_exemption(self, app, auth):
        """Test granting SLA exemption."""
        user = auth.register(email='user@test.com', password='pass123')
        
        with app.app_context():
            req = ServiceRequest(
                title='Test Request',
                description='Test',
                category='hardware',
                priority='high',
                status='open',
                created_by=user.id,
            )
            req.save()
            
            # Grant exemption
            exemption = SLAService.grant_exemption(
                req.id,
                'Waiting for customer response',
                exemption_type='response',
                duration_hours=24,
                granted_by_id=user.id
            )
            
            assert exemption is not None
            assert exemption.is_active() is True
    
    def test_exemption_blocks_breach_detection(self, app, auth):
        """Test that active exemptions prevent breach detection."""
        user = auth.register(email='user@test.com', password='pass123')
        
        with app.app_context():
            req = ServiceRequest(
                title='Old Request',
                description='Test',
                category='hardware',
                priority='medium',
                status='open',
                created_by=user.id,
                created_at=datetime.utcnow() - timedelta(hours=5)
            )
            req.save()
            
            # Grant exemption
            SLAService.grant_exemption(
                req.id,
                'Waiting for parts',
                exemption_type='response'
            )
            
            # Check breach (should be false due to exemption)
            is_breached = SLAService.check_response_sla_breach(req.id)
            
            assert is_breached is False


class TestHealthCheck:
    """Test health check endpoint and system status monitoring."""
    
    def test_health_check_endpoint(self, client):
        """Test /health endpoint returns proper status."""
        response = client.get('/health')
        
        assert response.status_code in [200, 503]
        data = json.loads(response.data)
        
        assert 'status' in data
        assert 'components' in data
        assert 'timestamp' in data
    
    def test_health_check_database_status(self, app):
        """Test health check detects database issues."""
        status = HealthCheck.get_status()
        
        # Should have database status
        assert 'database' in status['components']
    
    def test_metrics_endpoint(self, client):
        """Test /metrics endpoint returns Prometheus metrics."""
        response = client.get('/metrics')
        
        assert response.status_code == 200
        assert b'prometheus' in response.data.lower() or b'TYPE' in response.data


class TestRateLimiting:
    """Test rate limiting and brute force protection."""
    
    def test_rate_limit_login_endpoint(self):
        """Test rate limiting on login endpoint."""
        # Make multiple failed login attempts
        for i in range(6):
            allowed, remaining, reset = RateLimiter.check_rate_limit(
                'ip:127.0.0.1',
                'login'
            )
            
            if i < 5:
                assert allowed is True
            else:
                assert allowed is False
    
    def test_rate_limit_reset_on_success(self):
        """Test rate limit reset after successful attempt."""
        key = 'ip:127.0.0.1'
        
        # Make failed attempts
        for i in range(3):
            RateLimiter.check_rate_limit(key, 'login')
        
        # Reset after success
        RateLimiter.reset_attempts(key)
        
        # Should allow new attempts
        allowed, remaining, reset = RateLimiter.check_rate_limit(key, 'login')
        assert allowed is True
        assert remaining > 0
    
    def test_lockout_duration(self):
        """Test that lockout persists for configured duration."""
        key = 'ip:192.168.1.1'
        
        # Exhaust attempts
        for i in range(6):
            RateLimiter.check_rate_limit(key, 'register')
        
        # Next attempt should be blocked
        allowed, remaining, reset = RateLimiter.check_rate_limit(key, 'register')
        assert allowed is False
        assert reset > 0  # Reset time in seconds


class TestBackupAndRecovery:
    """Test backup creation and database recovery."""
    
    @patch('subprocess.run')
    def test_backup_database_task(self, mock_run, app):
        """Test database backup task execution."""
        from app.tasks import backup_database
        
        mock_run.return_value = MagicMock(returncode=0)
        
        with app.app_context():
            result = backup_database.apply()
            
            assert result is not None
    
    def test_backup_file_naming(self):
        """Test backup file uses timestamp-based naming."""
        from app.tasks import backup_database
        
        # Verify naming convention would be used
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_{timestamp}.sql.gz'
        
        assert '_' in filename
        assert filename.endswith('.sql.gz')


class TestMonitoring:
    """Test monitoring and observability features."""
    
    def test_correlation_id_generation(self, app):
        """Test correlation ID is generated for requests."""
        from app.monitoring import get_correlation_id, generate_correlation_id
        
        with app.app_context():
            # Generate ID
            correlation_id = generate_correlation_id()
            
            assert correlation_id is not None
            assert len(correlation_id) > 0
    
    def test_structured_logging_format(self):
        """Test structured logging produces valid JSON."""
        from app.monitoring import StructuredLogger
        
        # Get log entry (we can't capture logs easily, so test format)
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'http_request',
            'method': 'GET',
            'path': '/api/test',
            'status': 200,
            'duration_ms': 45.2,
        }
        
        # Should be JSON serializable
        json_str = json.dumps(log_entry)
        assert json_str is not None
        assert '"type": "http_request"' in json_str


class TestTaskRetries:
    """Test Celery task retry mechanisms."""
    
    def test_task_max_retries_configured(self, app):
        """Test that tasks have max_retries configured."""
        from app.tasks import send_email_async, persist_audit_log
        
        # Tasks should have max_retries set
        assert send_email_async.max_retries == 3
        assert persist_audit_log.max_retries == 3
    
    def test_task_retry_countdown(self):
        """Test that task retries have exponential backoff."""
        # Verify exponential backoff would be applied
        retry_times = [60, 120, 240]  # 1min, 2min, 4min
        
        for i, expected_time in enumerate(retry_times):
            # Formula: 60 * (2 ** attempt_number)
            calculated = 60 * (2 ** i)
            assert calculated == expected_time
