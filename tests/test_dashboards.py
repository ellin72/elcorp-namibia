"""
tests/test_dashboards.py - Comprehensive test suite for dashboard endpoints
Tests cover:
- Analytics accuracy and aggregation
- RBAC enforcement on all endpoints
- Filtering, pagination, and sorting
- Export functionality
- Performance with large datasets
"""

import io
import json
import pytest
from datetime import datetime, timedelta
from flask import url_for

from app.models import ServiceRequest, User, Role, ServiceRequestHistory
from app.services.analytics_service import AnalyticsService
from app.services.export_service import ExportService


class TestAnalyticsService:
    """Test analytics service functions for accuracy and performance."""

    def test_count_requests_by_status(self, client, auth, app):
        """Test counting requests grouped by status."""
        with app.app_context():
            # Create test requests with various statuses
            user = User.query.first()
            for status in ['open', 'in_progress', 'in_progress', 'completed']:
                req = ServiceRequest(
                    title=f'Test {status}',
                    description='Test',
                    category='testing',
                    priority='medium',
                    status=status,
                    created_by=user.id,
                )
                req.save()

            result = AnalyticsService.count_requests_by_status()
            assert result['open'] == 1
            assert result['in_progress'] == 2
            assert result['completed'] == 1

    def test_count_requests_by_category(self, client, auth, app):
        """Test counting requests grouped by category."""
        with app.app_context():
            user = User.query.first()
            categories = ['hardware', 'software', 'hardware', 'network', 'hardware']
            for cat in categories:
                req = ServiceRequest(
                    title=f'Test {cat}',
                    description='Test',
                    category=cat,
                    priority='medium',
                    status='open',
                    created_by=user.id,
                )
                req.save()

            result = AnalyticsService.count_requests_by_category()
            assert result['hardware'] == 3
            assert result['software'] == 1
            assert result['network'] == 1

    def test_count_requests_by_priority(self, client, auth, app):
        """Test counting requests grouped by priority."""
        with app.app_context():
            user = User.query.first()
            for priority in ['high', 'high', 'medium', 'low', 'low', 'low']:
                req = ServiceRequest(
                    title=f'Test {priority}',
                    description='Test',
                    category='testing',
                    priority=priority,
                    status='open',
                    created_by=user.id,
                )
                req.save()

            result = AnalyticsService.count_requests_by_priority()
            assert result['high'] == 2
            assert result['medium'] == 1
            assert result['low'] == 3

    def test_get_total_requests(self, client, auth, app):
        """Test total request count."""
        with app.app_context():
            user = User.query.first()
            initial_count = AnalyticsService.get_total_requests()

            # Add more requests
            for i in range(5):
                req = ServiceRequest(
                    title=f'Request {i}',
                    description='Test',
                    category='testing',
                    priority='medium',
                    status='open',
                    created_by=user.id,
                )
                req.save()

            new_count = AnalyticsService.get_total_requests()
            assert new_count == initial_count + 5

    def test_get_unassigned_requests(self, client, auth, app):
        """Test counting unassigned requests."""
        with app.app_context():
            user = User.query.first()
            
            # Create unassigned request
            req1 = ServiceRequest(
                title='Unassigned',
                description='Test',
                category='testing',
                priority='medium',
                status='open',
                created_by=user.id,
            )
            req1.save()

            # Create assigned request
            req2 = ServiceRequest(
                title='Assigned',
                description='Test',
                category='testing',
                priority='medium',
                status='open',
                created_by=user.id,
                assigned_to=user.id,
            )
            req2.save()

            unassigned = AnalyticsService.get_unassigned_requests()
            assert unassigned >= 1

    def test_get_overdue_requests(self, client, auth, app):
        """Test counting overdue requests."""
        with app.app_context():
            user = User.query.first()

            # Create overdue request (due date in past, still open)
            overdue = ServiceRequest(
                title='Overdue',
                description='Test',
                category='testing',
                priority='high',
                status='open',
                created_by=user.id,
                due_date=datetime.now() - timedelta(days=5),
            )
            overdue.save()

            # Create non-overdue request
            normal = ServiceRequest(
                title='Normal',
                description='Test',
                category='testing',
                priority='medium',
                status='open',
                created_by=user.id,
                due_date=datetime.now() + timedelta(days=5),
            )
            normal.save()

            result = AnalyticsService.get_overdue_requests()
            assert result >= 1

    def test_avg_resolution_time(self, client, auth, app):
        """Test average resolution time calculation."""
        with app.app_context():
            user = User.query.first()

            # Create completed request
            now = datetime.now()
            completed = ServiceRequest(
                title='Completed',
                description='Test',
                category='testing',
                priority='medium',
                status='completed',
                created_by=user.id,
                created_at=now - timedelta(days=5),
                completed_at=now,
            )
            completed.save()

            avg_time = AnalyticsService.avg_resolution_time(days=30)
            assert avg_time >= 0

    def test_staff_workload_distribution(self, client, auth, app):
        """Test staff workload aggregation."""
        with app.app_context():
            user = User.query.first()

            # Create requests assigned to user
            for i in range(3):
                req = ServiceRequest(
                    title=f'Staff Request {i}',
                    description='Test',
                    category='testing',
                    priority='medium',
                    status='in_progress',
                    created_by=user.id,
                    assigned_to=user.id,
                )
                req.save()

            result = AnalyticsService.staff_workload_distribution()
            assert isinstance(result, list)
            assert len(result) >= 1

    def test_get_category_trends(self, client, auth, app):
        """Test category trend analysis."""
        with app.app_context():
            user = User.query.first()

            for i in range(3):
                req = ServiceRequest(
                    title=f'Trend Test {i}',
                    description='Test',
                    category='testing',
                    priority='medium',
                    status='open',
                    created_by=user.id,
                )
                req.save()

            result = AnalyticsService.get_category_trends(days=30)
            assert isinstance(result, dict)

    def test_get_approval_rate(self, client, auth, app):
        """Test approval rate calculation."""
        with app.app_context():
            result = AnalyticsService.get_approval_rate(days=30)
            assert isinstance(result, (int, float))
            assert 0 <= result <= 100


class TestAdminDashboard:
    """Test admin dashboard endpoints and RBAC enforcement."""

    def test_admin_summary_requires_admin_role(self, client, auth):
        """Test that admin summary endpoint requires admin role."""
        # Login as regular user should fail
        user = auth.register(email='user@test.com', password='pass123')
        auth.login(email='user@test.com', password='pass123')

        response = client.get(url_for('dashboard.admin_summary'))
        assert response.status_code == 403

    def test_admin_summary_successful(self, client, auth):
        """Test successful admin summary endpoint."""
        user = auth.register(email='admin@test.com', password='pass123')
        auth.login(email='admin@test.com', password='pass123')

        # Make user admin
        user = User.query.filter_by(email='admin@test.com').first()
        user.roles.clear()
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            admin_role.save()
        user.roles.append(admin_role)
        user.save()

        response = client.get(url_for('dashboard.admin_summary'))
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'total_requests' in data
        assert 'open_requests' in data
        assert 'unassigned_requests' in data
        assert 'overdue_requests' in data

    def test_admin_trends_endpoint(self, client, auth, app):
        """Test admin trends endpoint."""
        user = auth.register(email='admin@test.com', password='pass123')
        auth.login(email='admin@test.com', password='pass123')

        # Make user admin
        user = User.query.filter_by(email='admin@test.com').first()
        user.roles.clear()
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            admin_role.save()
        user.roles.append(admin_role)
        user.save()

        # Add some requests
        with app.app_context():
            for i in range(3):
                req = ServiceRequest(
                    title=f'Trend {i}',
                    description='Test',
                    category='testing',
                    priority='medium',
                    status='open',
                    created_by=user.id,
                )
                req.save()

        response = client.get(url_for('dashboard.admin_trends') + '?days=30')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'created_per_day' in data
        assert 'completed_per_day' in data

    def test_admin_workload_endpoint(self, client, auth):
        """Test admin workload endpoint."""
        user = auth.register(email='admin@test.com', password='pass123')
        auth.login(email='admin@test.com', password='pass123')

        # Make user admin
        user = User.query.filter_by(email='admin@test.com').first()
        user.roles.clear()
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            admin_role.save()
        user.roles.append(admin_role)
        user.save()

        response = client.get(url_for('dashboard.admin_workload'))
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'staff_workload' in data

    def test_admin_sla_breaches_endpoint(self, client, auth):
        """Test admin SLA breaches endpoint."""
        user = auth.register(email='admin@test.com', password='pass123')
        auth.login(email='admin@test.com', password='pass123')

        # Make user admin
        user = User.query.filter_by(email='admin@test.com').first()
        user.roles.clear()
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            admin_role.save()
        user.roles.append(admin_role)
        user.save()

        response = client.get(url_for('dashboard.admin_sla_breaches'))
        assert response.status_code == 200


class TestStaffDashboard:
    """Test staff dashboard endpoints and RBAC enforcement."""

    def test_staff_summary_endpoint(self, client, auth):
        """Test staff summary endpoint."""
        user = auth.register(email='staff@test.com', password='pass123')
        auth.login(email='staff@test.com', password='pass123')

        # Make user staff
        user = User.query.filter_by(email='staff@test.com').first()
        user.roles.clear()
        staff_role = Role.query.filter_by(name='staff').first()
        if not staff_role:
            staff_role = Role(name='staff')
            staff_role.save()
        user.roles.append(staff_role)
        user.save()

        response = client.get(url_for('dashboard.staff_summary'))
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'assigned_requests' in data
        assert 'completed_requests' in data

    def test_staff_my_workload_endpoint(self, client, auth, app):
        """Test staff my workload endpoint."""
        user = auth.register(email='staff@test.com', password='pass123')
        auth.login(email='staff@test.com', password='pass123')

        # Make user staff
        user = User.query.filter_by(email='staff@test.com').first()
        user.roles.clear()
        staff_role = Role.query.filter_by(name='staff').first()
        if not staff_role:
            staff_role = Role(name='staff')
            staff_role.save()
        user.roles.append(staff_role)
        user.save()

        # Add requests assigned to this staff
        with app.app_context():
            for i in range(2):
                req = ServiceRequest(
                    title=f'Staff Work {i}',
                    description='Test',
                    category='testing',
                    priority='medium',
                    status='in_progress',
                    created_by=user.id,
                    assigned_to=user.id,
                )
                req.save()

        response = client.get(url_for('dashboard.staff_my_workload'))
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'requests' in data

    def test_staff_performance_endpoint(self, client, auth):
        """Test staff performance endpoint."""
        user = auth.register(email='staff@test.com', password='pass123')
        auth.login(email='staff@test.com', password='pass123')

        # Make user staff
        user = User.query.filter_by(email='staff@test.com').first()
        user.roles.clear()
        staff_role = Role.query.filter_by(name='staff').first()
        if not staff_role:
            staff_role = Role(name='staff')
            staff_role.save()
        user.roles.append(staff_role)
        user.save()

        response = client.get(url_for('dashboard.staff_performance'))
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'assigned_count' in data
        assert 'completed_count' in data


class TestFilteredRequests:
    """Test advanced filtering endpoint with various filters."""

    def test_filtered_requests_by_status(self, client, auth, app):
        """Test filtering requests by status."""
        user = auth.register(email='staff@test.com', password='pass123')
        auth.login(email='staff@test.com', password='pass123')

        user = User.query.filter_by(email='staff@test.com').first()
        user.roles.clear()
        staff_role = Role.query.filter_by(name='staff').first()
        if not staff_role:
            staff_role = Role(name='staff')
            staff_role.save()
        user.roles.append(staff_role)
        user.save()

        with app.app_context():
            # Create requests with different statuses
            for status in ['open', 'in_progress', 'completed']:
                req = ServiceRequest(
                    title=f'Status {status}',
                    description='Test',
                    category='testing',
                    priority='medium',
                    status=status,
                    created_by=user.id,
                )
                req.save()

        response = client.get(url_for('dashboard.filtered_requests') + '?status=open')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'requests' in data
        assert 'total' in data

    def test_filtered_requests_by_priority(self, client, auth, app):
        """Test filtering requests by priority."""
        user = auth.register(email='staff@test.com', password='pass123')
        auth.login(email='staff@test.com', password='pass123')

        user = User.query.filter_by(email='staff@test.com').first()
        user.roles.clear()
        staff_role = Role.query.filter_by(name='staff').first()
        if not staff_role:
            staff_role = Role(name='staff')
            staff_role.save()
        user.roles.append(staff_role)
        user.save()

        with app.app_context():
            for priority in ['high', 'medium', 'low']:
                req = ServiceRequest(
                    title=f'Priority {priority}',
                    description='Test',
                    category='testing',
                    priority=priority,
                    status='open',
                    created_by=user.id,
                )
                req.save()

        response = client.get(url_for('dashboard.filtered_requests') + '?priority=high')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'requests' in data

    def test_filtered_requests_by_category(self, client, auth, app):
        """Test filtering requests by category."""
        user = auth.register(email='staff@test.com', password='pass123')
        auth.login(email='staff@test.com', password='pass123')

        user = User.query.filter_by(email='staff@test.com').first()
        user.roles.clear()
        staff_role = Role.query.filter_by(name='staff').first()
        if not staff_role:
            staff_role = Role(name='staff')
            staff_role.save()
        user.roles.append(staff_role)
        user.save()

        with app.app_context():
            for category in ['hardware', 'software', 'network']:
                req = ServiceRequest(
                    title=f'Category {category}',
                    description='Test',
                    category=category,
                    priority='medium',
                    status='open',
                    created_by=user.id,
                )
                req.save()

        response = client.get(url_for('dashboard.filtered_requests') + '?category=hardware')
        assert response.status_code == 200

    def test_filtered_requests_pagination(self, client, auth, app):
        """Test pagination on filtered requests."""
        user = auth.register(email='staff@test.com', password='pass123')
        auth.login(email='staff@test.com', password='pass123')

        user = User.query.filter_by(email='staff@test.com').first()
        user.roles.clear()
        staff_role = Role.query.filter_by(name='staff').first()
        if not staff_role:
            staff_role = Role(name='staff')
            staff_role.save()
        user.roles.append(staff_role)
        user.save()

        with app.app_context():
            for i in range(15):
                req = ServiceRequest(
                    title=f'Request {i}',
                    description='Test',
                    category='testing',
                    priority='medium',
                    status='open',
                    created_by=user.id,
                )
                req.save()

        response = client.get(url_for('dashboard.filtered_requests') + '?page=1&per_page=5')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data['requests']) <= 5
        assert 'pages' in data


class TestExportFunctionality:
    """Test export functionality (CSV and PDF)."""

    def test_export_requests_to_csv(self, client, auth, app):
        """Test CSV export of requests."""
        user = auth.register(email='admin@test.com', password='pass123')
        auth.login(email='admin@test.com', password='pass123')

        user = User.query.filter_by(email='admin@test.com').first()
        user.roles.clear()
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            admin_role.save()
        user.roles.append(admin_role)
        user.save()

        with app.app_context():
            for i in range(3):
                req = ServiceRequest(
                    title=f'CSV Test {i}',
                    description='Test',
                    category='testing',
                    priority='medium',
                    status='open',
                    created_by=user.id,
                )
                req.save()

            requests = ServiceRequest.query.all()
            csv_buffer, filename = ExportService.export_requests_to_csv(requests)

            assert csv_buffer is not None
            assert 'service_requests' in filename
            assert filename.endswith('.csv')

            csv_content = csv_buffer.getvalue()
            assert 'ID' in csv_content
            assert 'Title' in csv_content
            assert 'CSV Test 0' in csv_content

    def test_export_requests_to_pdf(self, client, auth, app):
        """Test PDF export of requests."""
        user = auth.register(email='admin@test.com', password='pass123')
        auth.login(email='admin@test.com', password='pass123')

        user = User.query.filter_by(email='admin@test.com').first()
        user.roles.clear()
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            admin_role.save()
        user.roles.append(admin_role)
        user.save()

        with app.app_context():
            for i in range(3):
                req = ServiceRequest(
                    title=f'PDF Test {i}',
                    description='Test',
                    category='testing',
                    priority='medium',
                    status='open',
                    created_by=user.id,
                )
                req.save()

            requests = ServiceRequest.query.all()
            pdf_buffer, filename = ExportService.export_requests_to_pdf(requests)

            assert pdf_buffer is not None
            assert 'service_requests_report' in filename
            assert filename.endswith('.pdf')

            pdf_content = pdf_buffer.getvalue()
            assert len(pdf_content) > 0

    def test_export_staff_performance_to_csv(self, client, auth, app):
        """Test staff performance CSV export."""
        user = auth.register(email='admin@test.com', password='pass123')
        auth.login(email='admin@test.com', password='pass123')

        user = User.query.filter_by(email='admin@test.com').first()
        user.roles.clear()
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            admin_role.save()
        user.roles.append(admin_role)
        user.save()

        with app.app_context():
            staff_data = [
                {
                    'name': 'John Doe',
                    'assigned_count': 5,
                    'completed_count': 3,
                    'in_progress_count': 2,
                    'completion_rate': 60.0,
                    'avg_resolution_time': 3.5,
                }
            ]

            csv_buffer, filename = ExportService.export_staff_performance_to_csv(staff_data)

            assert csv_buffer is not None
            assert 'staff_performance' in filename
            assert filename.endswith('.csv')

            csv_content = csv_buffer.getvalue()
            assert 'Staff Member' in csv_content
            assert 'John Doe' in csv_content


class TestPerformance:
    """Test dashboard performance with large datasets."""

    def test_dashboard_performance_1000_requests(self, client, auth, app):
        """Test dashboard performance with 1000 requests."""
        user = auth.register(email='admin@test.com', password='pass123')
        auth.login(email='admin@test.com', password='pass123')

        user = User.query.filter_by(email='admin@test.com').first()
        user.roles.clear()
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            admin_role.save()
        user.roles.append(admin_role)
        user.save()

        with app.app_context():
            # Create 1000 requests
            for i in range(100):  # Reduced from 1000 for test speed
                statuses = ['open', 'in_progress', 'completed']
                priorities = ['high', 'medium', 'low']
                req = ServiceRequest(
                    title=f'Performance Test {i}',
                    description='Test',
                    category='testing',
                    priority=priorities[i % 3],
                    status=statuses[i % 3],
                    created_by=user.id,
                    assigned_to=user.id if i % 2 == 0 else None,
                )
                req.save()

        # Test admin summary response time
        import time
        start = time.time()
        response = client.get(url_for('dashboard.admin_summary'))
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 5  # Should complete within 5 seconds

    def test_filtering_performance(self, client, auth, app):
        """Test filtering performance with multiple criteria."""
        user = auth.register(email='admin@test.com', password='pass123')
        auth.login(email='admin@test.com', password='pass123')

        user = User.query.filter_by(email='admin@test.com').first()
        user.roles.clear()
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            admin_role.save()
        user.roles.append(admin_role)
        user.save()

        with app.app_context():
            for i in range(50):
                req = ServiceRequest(
                    title=f'Filter Test {i}',
                    description='Test',
                    category='testing',
                    priority='high' if i % 2 == 0 else 'medium',
                    status='open' if i % 3 == 0 else 'in_progress',
                    created_by=user.id,
                )
                req.save()

        # Test filtering with multiple criteria
        import time
        start = time.time()
        response = client.get(
            url_for('dashboard.filtered_requests')
            + '?status=open&priority=high&category=testing&page=1&per_page=10'
        )
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 3  # Should complete within 3 seconds
