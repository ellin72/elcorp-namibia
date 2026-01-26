"""
app/services/analytics_service.py - Analytics and aggregation queries for dashboards

Provides efficient queries for dashboard metrics with proper indexing.
"""
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import func, and_, or_, desc
from app.extensions import db
from app.models import ServiceRequest, ServiceRequestHistory, User, Role


def count_service_requests_by_status():
    """
    Count service requests grouped by status.
    
    Returns:
        dict: {status: count, ...}
        Example: {'draft': 5, 'submitted': 10, 'in_review': 3, 'approved': 2, 'completed': 45}
    """
    results = db.session.query(
        ServiceRequest.status,
        func.count(ServiceRequest.id).label('count')
    ).group_by(ServiceRequest.status).all()
    
    return {status: count for status, count in results}


def count_service_requests_by_category():
    """
    Count service requests grouped by category.
    
    Returns:
        dict: {category: count, ...}
        Example: {'support': 20, 'compliance': 15, 'inquiry': 10, ...}
    """
    results = db.session.query(
        ServiceRequest.category,
        func.count(ServiceRequest.id).label('count')
    ).group_by(ServiceRequest.category).all()
    
    return {category: count for category, count in results}


def count_service_requests_by_priority():
    """
    Count service requests grouped by priority.
    
    Returns:
        dict: {priority: count, ...}
        Example: {'low': 5, 'normal': 20, 'high': 10, 'urgent': 2}
    """
    results = db.session.query(
        ServiceRequest.priority,
        func.count(ServiceRequest.id).label('count')
    ).group_by(ServiceRequest.priority).all()
    
    return {priority: count for priority, count in results}


def get_total_requests():
    """Get total count of all service requests."""
    return db.session.query(func.count(ServiceRequest.id)).scalar() or 0


def get_unassigned_requests():
    """Get count of unassigned service requests."""
    return db.session.query(func.count(ServiceRequest.id)).filter(
        ServiceRequest.assigned_to.is_(None)
    ).scalar() or 0


def get_overdue_requests():
    """
    Get count of requests that are overdue (submitted > 5 days ago).
    Overdue = Submitted status and created more than 5 days ago.
    """
    threshold = datetime.utcnow() - timedelta(days=5)
    return db.session.query(func.count(ServiceRequest.id)).filter(
        and_(
            ServiceRequest.status == ServiceRequest.STATUS_SUBMITTED,
            ServiceRequest.created_at < threshold
        )
    ).scalar() or 0


def avg_resolution_time(days=30):
    """
    Calculate average resolution time for completed requests in past N days.
    Resolution time = completed_at - created_at
    
    Args:
        days: Number of past days to analyze (default 30)
    
    Returns:
        dict: {avg_days: float, completed_count: int}
    """
    threshold = datetime.utcnow() - timedelta(days=days)
    
    completed_requests = db.session.query(ServiceRequest).filter(
        and_(
            ServiceRequest.status == ServiceRequest.STATUS_COMPLETED,
            ServiceRequest.created_at >= threshold
        )
    ).all()
    
    if not completed_requests:
        return {'avg_days': 0, 'completed_count': 0}
    
    total_duration = timedelta()
    for req in completed_requests:
        duration = req.updated_at - req.created_at
        total_duration += duration
    
    avg_duration = total_duration / len(completed_requests)
    avg_days = avg_duration.total_seconds() / (24 * 3600)
    
    return {
        'avg_days': round(avg_days, 2),
        'completed_count': len(completed_requests)
    }


def requests_created_per_day(days=30):
    """
    Get count of requests created per day for past N days.
    
    Args:
        days: Number of past days to analyze (default 30)
    
    Returns:
        list: [{date: '2026-01-26', count: 5}, ...]
    """
    threshold = datetime.utcnow() - timedelta(days=days)
    
    results = db.session.query(
        func.date(ServiceRequest.created_at).label('date'),
        func.count(ServiceRequest.id).label('count')
    ).filter(
        ServiceRequest.created_at >= threshold
    ).group_by(
        func.date(ServiceRequest.created_at)
    ).order_by(
        func.date(ServiceRequest.created_at)
    ).all()
    
    return [{'date': str(date), 'count': count} for date, count in results]


def requests_completed_per_day(days=30):
    """
    Get count of requests completed per day for past N days.
    
    Args:
        days: Number of past days to analyze (default 30)
    
    Returns:
        list: [{date: '2026-01-26', count: 5}, ...]
    """
    threshold = datetime.utcnow() - timedelta(days=days)
    
    results = db.session.query(
        func.date(ServiceRequest.updated_at).label('date'),
        func.count(ServiceRequest.id).label('count')
    ).filter(
        and_(
            ServiceRequest.status == ServiceRequest.STATUS_COMPLETED,
            ServiceRequest.updated_at >= threshold
        )
    ).group_by(
        func.date(ServiceRequest.updated_at)
    ).order_by(
        func.date(ServiceRequest.updated_at)
    ).all()
    
    return [{'date': str(date), 'count': count} for date, count in results]


def staff_workload_distribution():
    """
    Get current workload distribution across all staff members.
    
    Returns:
        list: [{staff_id: 123, staff_name: 'John', assigned_count: 5, 
                in_review_count: 2, completed_count: 10}, ...]
    """
    staff_role = db.session.query(Role).filter_by(name='staff').first()
    
    if not staff_role:
        return []
    
    staff_members = db.session.query(User).filter_by(role_id=staff_role.id).all()
    
    workload = []
    for staff in staff_members:
        assigned_count = db.session.query(func.count(ServiceRequest.id)).filter(
            and_(
                ServiceRequest.assigned_to == staff.id,
                ServiceRequest.status.in_([
                    ServiceRequest.STATUS_SUBMITTED,
                    ServiceRequest.STATUS_IN_REVIEW
                ])
            )
        ).scalar() or 0
        
        in_review_count = db.session.query(func.count(ServiceRequest.id)).filter(
            and_(
                ServiceRequest.assigned_to == staff.id,
                ServiceRequest.status == ServiceRequest.STATUS_IN_REVIEW
            )
        ).scalar() or 0
        
        completed_count = db.session.query(func.count(ServiceRequest.id)).filter(
            and_(
                ServiceRequest.assigned_to == staff.id,
                ServiceRequest.status == ServiceRequest.STATUS_COMPLETED
            )
        ).scalar() or 0
        
        workload.append({
            'staff_id': staff.id,
            'staff_name': staff.full_name,
            'assigned_count': assigned_count,
            'in_review_count': in_review_count,
            'completed_count': completed_count,
            'total_count': assigned_count + completed_count
        })
    
    return sorted(workload, key=lambda x: x['total_count'], reverse=True)


def get_category_trends(days=30):
    """
    Get request count by category per day for past N days.
    Useful for visualizing category trends.
    
    Args:
        days: Number of past days to analyze (default 30)
    
    Returns:
        list: [{category: 'support', date: '2026-01-26', count: 3}, ...]
    """
    threshold = datetime.utcnow() - timedelta(days=days)
    
    results = db.session.query(
        ServiceRequest.category,
        func.date(ServiceRequest.created_at).label('date'),
        func.count(ServiceRequest.id).label('count')
    ).filter(
        ServiceRequest.created_at >= threshold
    ).group_by(
        ServiceRequest.category,
        func.date(ServiceRequest.created_at)
    ).order_by(
        func.date(ServiceRequest.created_at)
    ).all()
    
    return [
        {'category': category, 'date': str(date), 'count': count}
        for category, date, count in results
    ]


def get_status_transition_stats(days=30):
    """
    Get statistics on status transitions for requests modified in past N days.
    
    Args:
        days: Number of past days to analyze (default 30)
    
    Returns:
        dict: {from_status: {to_status: count, ...}, ...}
    """
    threshold = datetime.utcnow() - timedelta(days=days)
    
    transitions = db.session.query(
        ServiceRequestHistory.old_status,
        ServiceRequestHistory.new_status,
        func.count(ServiceRequestHistory.id).label('count')
    ).filter(
        and_(
            ServiceRequestHistory.timestamp >= threshold,
            ServiceRequestHistory.action == 'status_changed'
        )
    ).group_by(
        ServiceRequestHistory.old_status,
        ServiceRequestHistory.new_status
    ).all()
    
    result = {}
    for old_status, new_status, count in transitions:
        if old_status not in result:
            result[old_status] = {}
        result[old_status][new_status] = count
    
    return result


def get_approval_rate(days=30):
    """
    Get approval and rejection rate for requests modified in past N days.
    
    Args:
        days: Number of past days to analyze (default 30)
    
    Returns:
        dict: {approved: count, rejected: count, approval_rate: percentage}
    """
    threshold = datetime.utcnow() - timedelta(days=days)
    
    approved = db.session.query(func.count(ServiceRequest.id)).filter(
        and_(
            ServiceRequest.status == ServiceRequest.STATUS_APPROVED,
            ServiceRequest.updated_at >= threshold
        )
    ).scalar() or 0
    
    rejected = db.session.query(func.count(ServiceRequest.id)).filter(
        and_(
            ServiceRequest.status == ServiceRequest.STATUS_REJECTED,
            ServiceRequest.updated_at >= threshold
        )
    ).scalar() or 0
    
    total = approved + rejected
    approval_rate = (approved / total * 100) if total > 0 else 0
    
    return {
        'approved': approved,
        'rejected': rejected,
        'total': total,
        'approval_rate': round(approval_rate, 2)
    }


def get_requests_with_filters(filters=None, page=1, per_page=20):
    """
    Get service requests with advanced filtering.
    
    Args:
        filters: dict with optional keys:
            - status: str or list
            - priority: str or list
            - category: str or list
            - assigned_to: int (user_id)
            - created_by: int (user_id)
            - date_from: datetime
            - date_to: datetime
        page: Page number for pagination
        per_page: Items per page
    
    Returns:
        tuple: (requests, total_count, total_pages)
    """
    filters = filters or {}
    query = ServiceRequest.query
    
    # Status filter
    if 'status' in filters:
        statuses = filters['status']
        if isinstance(statuses, str):
            statuses = [statuses]
        query = query.filter(ServiceRequest.status.in_(statuses))
    
    # Priority filter
    if 'priority' in filters:
        priorities = filters['priority']
        if isinstance(priorities, str):
            priorities = [priorities]
        query = query.filter(ServiceRequest.priority.in_(priorities))
    
    # Category filter
    if 'category' in filters:
        categories = filters['category']
        if isinstance(categories, str):
            categories = [categories]
        query = query.filter(ServiceRequest.category.in_(categories))
    
    # Assigned to filter
    if 'assigned_to' in filters:
        query = query.filter(ServiceRequest.assigned_to == filters['assigned_to'])
    
    # Created by filter
    if 'created_by' in filters:
        query = query.filter(ServiceRequest.created_by == filters['created_by'])
    
    # Date range filter
    if 'date_from' in filters and filters['date_from']:
        query = query.filter(ServiceRequest.created_at >= filters['date_from'])
    
    if 'date_to' in filters and filters['date_to']:
        query = query.filter(ServiceRequest.created_at <= filters['date_to'])
    
    # Get total count before pagination
    total_count = query.count()
    total_pages = (total_count + per_page - 1) // per_page
    
    # Apply pagination
    requests = query.order_by(desc(ServiceRequest.created_at)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()
    
    return requests, total_count, total_pages


def get_dashboard_summary():
    """
    Get comprehensive dashboard summary with all key metrics.
    
    Returns:
        dict: Summary of all important metrics
    """
    return {
        'total_requests': get_total_requests(),
        'by_status': count_service_requests_by_status(),
        'by_category': count_service_requests_by_category(),
        'by_priority': count_service_requests_by_priority(),
        'unassigned_count': get_unassigned_requests(),
        'overdue_count': get_overdue_requests(),
        'resolution_time': avg_resolution_time(30),
        'approval_rate': get_approval_rate(30),
        'workload_distribution': staff_workload_distribution(),
    }
