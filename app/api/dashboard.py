"""
app/api/dashboard.py - Dashboard and analytics endpoints

Provides admin and staff dashboards with analytics and trends.
"""
import logging
from datetime import datetime, timedelta
from flask import request, current_app, Blueprint
from flask_login import login_required, current_user
from sqlalchemy import func, and_, or_

from app.extensions import db
from app.models import ServiceRequest, User, Role
from app.security import require_role, require_admin
from app.services.analytics_service import (
    get_dashboard_summary, count_service_requests_by_status,
    count_service_requests_by_category, count_service_requests_by_priority,
    get_unassigned_requests, get_overdue_requests, avg_resolution_time,
    requests_created_per_day, requests_completed_per_day,
    staff_workload_distribution, get_category_trends,
    get_status_transition_stats, get_approval_rate,
    get_requests_with_filters
)
from app.api.utils import (
    api_response, api_error, get_pagination_params, paginate_query,
    validate_request_json
)

bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')
logger = logging.getLogger("app.dashboard")


# ============================================================================
# Admin Dashboard Endpoints
# ============================================================================

@bp.route("/admin/summary", methods=["GET"])
@login_required
@require_admin
def admin_dashboard_summary():
    """
    Get comprehensive admin dashboard summary.
    
    Returns:
        - total_requests: Total count
        - by_status: Breakdown by status
        - by_category: Breakdown by category
        - by_priority: Breakdown by priority
        - unassigned_count: Number of unassigned requests
        - overdue_count: Number of overdue requests (>5 days)
        - resolution_time: Average time to complete
        - approval_rate: Approval vs rejection percentage
        - workload_distribution: Staff workload
    """
    try:
        summary = get_dashboard_summary()
        
        return api_response(data=summary, message="Dashboard summary retrieved")
    
    except Exception as e:
        logger.error(f"Error retrieving admin dashboard summary: {str(e)}")
        return api_error("Failed to retrieve dashboard summary", 500)


@bp.route("/admin/trends", methods=["GET"])
@login_required
@require_admin
def admin_dashboard_trends():
    """
    Get trends data for admin dashboard.
    
    Query parameters:
        - days: Number of days to analyze (default 30, max 365)
    
    Returns:
        - created_per_day: Requests created per day
        - completed_per_day: Requests completed per day
        - category_trends: Requests by category per day
        - status_transitions: Status transition statistics
        - approval_rate: Approval rate over period
    """
    try:
        days = request.args.get('days', 30, type=int)
        days = min(max(days, 1), 365)  # Clamp between 1 and 365
        
        return api_response(data={
            'created_per_day': requests_created_per_day(days),
            'completed_per_day': requests_completed_per_day(days),
            'category_trends': get_category_trends(days),
            'status_transitions': get_status_transition_stats(days),
            'approval_rate': get_approval_rate(days),
            'period_days': days
        }, message="Trends data retrieved")
    
    except Exception as e:
        logger.error(f"Error retrieving admin dashboard trends: {str(e)}")
        return api_error("Failed to retrieve trends data", 500)


@bp.route("/admin/workload", methods=["GET"])
@login_required
@require_admin
def admin_dashboard_workload():
    """
    Get detailed staff workload distribution and performance.
    
    Query parameters:
        - sort_by: 'total' (default), 'assigned', 'in_review', 'completed'
    
    Returns:
        - workload_distribution: Staff members with their workload
        - unassigned_count: Total unassigned requests
        - pending_count: Total pending (not completed) requests
        - by_status: Breakdown by status
    """
    try:
        sort_by = request.args.get('sort_by', 'total').lower()
        
        workload = staff_workload_distribution()
        
        # Sort workload based on parameter
        if sort_by == 'assigned':
            workload = sorted(workload, key=lambda x: x['assigned_count'], reverse=True)
        elif sort_by == 'in_review':
            workload = sorted(workload, key=lambda x: x['in_review_count'], reverse=True)
        elif sort_by == 'completed':
            workload = sorted(workload, key=lambda x: x['completed_count'], reverse=True)
        else:
            workload = sorted(workload, key=lambda x: x['total_count'], reverse=True)
        
        # Get additional metrics
        unassigned = get_unassigned_requests()
        pending = db.session.query(func.count(ServiceRequest.id)).filter(
            ServiceRequest.status.in_([
                ServiceRequest.STATUS_SUBMITTED,
                ServiceRequest.STATUS_IN_REVIEW
            ])
        ).scalar() or 0
        
        return api_response(data={
            'workload_distribution': workload,
            'unassigned_count': unassigned,
            'pending_count': pending,
            'by_status': count_service_requests_by_status(),
            'sort_by': sort_by
        }, message="Workload data retrieved")
    
    except Exception as e:
        logger.error(f"Error retrieving admin dashboard workload: {str(e)}")
        return api_error("Failed to retrieve workload data", 500)


@bp.route("/admin/sla-breaches", methods=["GET"])
@login_required
@require_admin
def admin_sla_breaches():
    """
    Get requests that breach SLA (Service Level Agreement).
    SLA: Submitted requests should be resolved within 7 days.
    
    Query parameters:
        - page: Page number (default 1)
        - per_page: Items per page (default 20, max 100)
    
    Returns:
        - breaches: List of breached requests with age
        - total: Total count of breached requests
        - pagination: Pagination info
    """
    try:
        page, per_page = get_pagination_params(
            default_per_page=current_app.config.get("API_ITEMS_PER_PAGE", 20)
        )
        
        # SLA threshold: 7 days
        threshold = datetime.utcnow() - timedelta(days=7)
        
        query = ServiceRequest.query.filter(
            and_(
                ServiceRequest.status.in_([
                    ServiceRequest.STATUS_SUBMITTED,
                    ServiceRequest.STATUS_IN_REVIEW
                ]),
                ServiceRequest.created_at < threshold
            )
        ).order_by(ServiceRequest.created_at)
        
        requests_list, pagination_info = paginate_query(query, page, per_page)
        
        breaches = []
        for req in requests_list:
            age = (datetime.utcnow() - req.created_at).days
            breaches.append({
                'id': req.id,
                'title': req.title,
                'category': req.category,
                'priority': req.priority,
                'status': req.status,
                'created_at': req.created_at.isoformat(),
                'days_since_created': age,
                'sla_days': 7,
                'days_overdue': age - 7,
                'assigned_to': req.assigned_to,
                'assignee_name': req.assignee.full_name if req.assignee else None
            })
        
        return api_response(data=breaches, paginate=pagination_info)
    
    except Exception as e:
        logger.error(f"Error retrieving SLA breaches: {str(e)}")
        return api_error("Failed to retrieve SLA breaches", 500)


# ============================================================================
# Staff Dashboard Endpoints
# ============================================================================

@bp.route("/staff/summary", methods=["GET"])
@login_required
@require_role('staff', 'admin')
def staff_dashboard_summary():
    """
    Get staff member's personal dashboard summary.
    Staff can only see their own data. Admin can see it for themselves.
    
    Returns:
        - assigned_count: Number of assigned requests
        - in_review_count: Requests in review
        - completed_count: Completed requests
        - by_status: Breakdown of assigned requests by status
        - by_priority: Breakdown of assigned requests by priority
        - by_category: Breakdown of assigned requests by category
    """
    try:
        staff_id = current_user.id
        
        # All assigned requests for this staff member
        assigned_query = ServiceRequest.query.filter_by(assigned_to=staff_id)
        assigned_count = assigned_query.count()
        
        # By status
        by_status = db.session.query(
            ServiceRequest.status,
            func.count(ServiceRequest.id)
        ).filter_by(assigned_to=staff_id).group_by(ServiceRequest.status).all()
        
        # By priority
        by_priority = db.session.query(
            ServiceRequest.priority,
            func.count(ServiceRequest.id)
        ).filter_by(assigned_to=staff_id).group_by(ServiceRequest.priority).all()
        
        # By category
        by_category = db.session.query(
            ServiceRequest.category,
            func.count(ServiceRequest.id)
        ).filter_by(assigned_to=staff_id).group_by(ServiceRequest.category).all()
        
        in_review_count = db.session.query(func.count(ServiceRequest.id)).filter(
            and_(
                ServiceRequest.assigned_to == staff_id,
                ServiceRequest.status == ServiceRequest.STATUS_IN_REVIEW
            )
        ).scalar() or 0
        
        completed_count = db.session.query(func.count(ServiceRequest.id)).filter(
            and_(
                ServiceRequest.assigned_to == staff_id,
                ServiceRequest.status == ServiceRequest.STATUS_COMPLETED
            )
        ).scalar() or 0
        
        return api_response(data={
            'assigned_count': assigned_count,
            'in_review_count': in_review_count,
            'completed_count': completed_count,
            'by_status': {status: count for status, count in by_status},
            'by_priority': {priority: count for priority, count in by_priority},
            'by_category': {category: count for category, count in by_category}
        }, message="Staff dashboard summary retrieved")
    
    except Exception as e:
        logger.error(f"Error retrieving staff dashboard summary: {str(e)}")
        return api_error("Failed to retrieve dashboard summary", 500)


@bp.route("/staff/my-workload", methods=["GET"])
@login_required
@require_role('staff', 'admin')
def staff_my_workload():
    """
    Get detailed workload for current staff member.
    
    Query parameters:
        - status: Filter by status (submitted, in_review)
        - priority: Filter by priority
        - sort_by: 'created' (default) or 'priority'
        - page: Page number (default 1)
        - per_page: Items per page (default 20, max 100)
    
    Returns:
        - workload: List of assigned requests
        - summary: Summary statistics
        - pagination: Pagination info
    """
    try:
        page, per_page = get_pagination_params(
            default_per_page=current_app.config.get("API_ITEMS_PER_PAGE", 20)
        )
        
        query = ServiceRequest.query.filter_by(assigned_to=current_user.id)
        
        # Status filter
        status_filter = request.args.get('status', '').strip()
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        # Priority filter
        priority_filter = request.args.get('priority', '').strip()
        if priority_filter:
            query = query.filter_by(priority=priority_filter)
        
        # Sorting
        sort_by = request.args.get('sort_by', 'created').lower()
        if sort_by == 'priority':
            # Custom sort: urgent > high > normal > low
            priority_order = {'urgent': 0, 'high': 1, 'normal': 2, 'low': 3}
            query = query.order_by(
                func.field(ServiceRequest.priority, *['urgent', 'high', 'normal', 'low'])
            )
        else:
            query = query.order_by(ServiceRequest.created_at.desc())
        
        requests_list, pagination_info = paginate_query(query, page, per_page)
        
        workload = [
            {
                'id': req.id,
                'title': req.title,
                'description': req.description[:100] + '...' if len(req.description) > 100 else req.description,
                'category': req.category,
                'priority': req.priority,
                'status': req.status,
                'created_by': req.created_by,
                'creator_name': req.creator.full_name if req.creator else None,
                'created_at': req.created_at.isoformat(),
                'days_assigned': (datetime.utcnow() - req.created_at).days
            }
            for req in requests_list
        ]
        
        # Summary
        summary = {
            'total_assigned': db.session.query(func.count(ServiceRequest.id)).filter_by(
                assigned_to=current_user.id
            ).scalar() or 0,
            'in_review': db.session.query(func.count(ServiceRequest.id)).filter(
                and_(
                    ServiceRequest.assigned_to == current_user.id,
                    ServiceRequest.status == ServiceRequest.STATUS_IN_REVIEW
                )
            ).scalar() or 0,
            'submitted': db.session.query(func.count(ServiceRequest.id)).filter(
                and_(
                    ServiceRequest.assigned_to == current_user.id,
                    ServiceRequest.status == ServiceRequest.STATUS_SUBMITTED
                )
            ).scalar() or 0
        }
        
        return api_response(data={
            'workload': workload,
            'summary': summary,
            'pagination': pagination_info,
            'sort_by': sort_by
        })
    
    except Exception as e:
        logger.error(f"Error retrieving staff workload: {str(e)}")
        return api_error("Failed to retrieve workload", 500)


@bp.route("/staff/performance", methods=["GET"])
@login_required
@require_role('staff', 'admin')
def staff_performance():
    """
    Get performance metrics for current staff member.
    
    Query parameters:
        - days: Days to analyze (default 30, max 365)
    
    Returns:
        - completed_count: Total completed in period
        - avg_resolution_time: Average days to complete
        - completion_rate: Percentage of reviewed requests completed
        - by_category: Completion breakdown by category
        - daily_trend: Completions per day
    """
    try:
        days = request.args.get('days', 30, type=int)
        days = min(max(days, 1), 365)
        
        threshold = datetime.utcnow() - timedelta(days=days)
        
        # Completed requests in period
        completed = db.session.query(ServiceRequest).filter(
            and_(
                ServiceRequest.assigned_to == current_user.id,
                ServiceRequest.status == ServiceRequest.STATUS_COMPLETED,
                ServiceRequest.updated_at >= threshold
            )
        ).all()
        
        completed_count = len(completed)
        
        # Requests in review
        in_review_count = db.session.query(func.count(ServiceRequest.id)).filter(
            and_(
                ServiceRequest.assigned_to == current_user.id,
                ServiceRequest.status == ServiceRequest.STATUS_IN_REVIEW
            )
        ).scalar() or 0
        
        # Completion rate
        all_reviewed = completed_count + in_review_count
        completion_rate = (completed_count / all_reviewed * 100) if all_reviewed > 0 else 0
        
        # By category
        by_category = db.session.query(
            ServiceRequest.category,
            func.count(ServiceRequest.id)
        ).filter(
            and_(
                ServiceRequest.assigned_to == current_user.id,
                ServiceRequest.status == ServiceRequest.STATUS_COMPLETED,
                ServiceRequest.updated_at >= threshold
            )
        ).group_by(ServiceRequest.category).all()
        
        # Resolution time for completed
        avg_resolution = avg_resolution_time(days)
        
        # Daily trend
        daily_trend = db.session.query(
            func.date(ServiceRequest.updated_at).label('date'),
            func.count(ServiceRequest.id).label('count')
        ).filter(
            and_(
                ServiceRequest.assigned_to == current_user.id,
                ServiceRequest.status == ServiceRequest.STATUS_COMPLETED,
                ServiceRequest.updated_at >= threshold
            )
        ).group_by(
            func.date(ServiceRequest.updated_at)
        ).order_by(
            func.date(ServiceRequest.updated_at)
        ).all()
        
        return api_response(data={
            'completed_count': completed_count,
            'in_review_count': in_review_count,
            'avg_resolution_days': avg_resolution['avg_days'],
            'completion_rate': round(completion_rate, 2),
            'by_category': {cat: count for cat, count in by_category},
            'daily_trend': [{'date': str(date), 'count': count} for date, count in daily_trend],
            'period_days': days
        }, message="Performance metrics retrieved")
    
    except Exception as e:
        logger.error(f"Error retrieving staff performance: {str(e)}")
        return api_error("Failed to retrieve performance metrics", 500)


# ============================================================================
# Shared/Advanced Filtering Endpoint
# ============================================================================

@bp.route("/requests/filtered", methods=["GET"])
@login_required
def get_filtered_requests():
    """
    Get requests with advanced filtering.
    Regular users see own, staff see assigned, admin sees all.
    
    Query parameters:
        - status: Filter by status (single or comma-separated)
        - priority: Filter by priority (single or comma-separated)
        - category: Filter by category (single or comma-separated)
        - assigned_to: Filter by assignee (admin only)
        - date_from: ISO date (YYYY-MM-DD)
        - date_to: ISO date (YYYY-MM-DD)
        - sort_by: 'created' (default), 'priority', 'updated'
        - page: Page number (default 1)
        - per_page: Items per page (default 20, max 100)
    
    Returns:
        - requests: List of filtered requests
        - filters_applied: Which filters were used
        - pagination: Pagination info
    """
    try:
        page, per_page = get_pagination_params(
            default_per_page=current_app.config.get("API_ITEMS_PER_PAGE", 20)
        )
        
        # Build filters dict
        filters = {}
        
        # Status filter
        if request.args.get('status'):
            filters['status'] = request.args.get('status').split(',')
        
        # Priority filter
        if request.args.get('priority'):
            filters['priority'] = request.args.get('priority').split(',')
        
        # Category filter
        if request.args.get('category'):
            filters['category'] = request.args.get('category').split(',')
        
        # Date filters
        if request.args.get('date_from'):
            try:
                filters['date_from'] = datetime.fromisoformat(request.args.get('date_from'))
            except ValueError:
                return api_error("Invalid date_from format. Use YYYY-MM-DD", 400)
        
        if request.args.get('date_to'):
            try:
                filters['date_to'] = datetime.fromisoformat(request.args.get('date_to'))
            except ValueError:
                return api_error("Invalid date_to format. Use YYYY-MM-DD", 400)
        
        # Assigned to filter (admin only)
        if request.args.get('assigned_to'):
            is_admin = current_user.role and current_user.role.name == 'admin'
            if not is_admin:
                return api_error("Only admin can filter by assigned_to", 403)
            filters['assigned_to'] = int(request.args.get('assigned_to'))
        
        # Apply scope-based filtering
        is_admin = current_user.role and current_user.role.name == 'admin'
        is_staff = current_user.role and current_user.role.name == 'staff'
        
        if not is_admin:
            if is_staff:
                filters['assigned_to'] = current_user.id
            else:
                filters['created_by'] = current_user.id
        
        # Get filtered requests
        requests_list, total_count, total_pages = get_requests_with_filters(
            filters, page, per_page
        )
        
        # Sorting
        sort_by = request.args.get('sort_by', 'created')
        if sort_by == 'priority':
            priority_order = {'urgent': 0, 'high': 1, 'normal': 2, 'low': 3}
            requests_list = sorted(
                requests_list,
                key=lambda x: priority_order.get(x.priority, 999)
            )
        elif sort_by == 'updated':
            requests_list = sorted(requests_list, key=lambda x: x.updated_at, reverse=True)
        
        data = [
            {
                'id': req.id,
                'title': req.title,
                'category': req.category,
                'priority': req.priority,
                'status': req.status,
                'created_by': req.created_by,
                'assigned_to': req.assigned_to,
                'created_at': req.created_at.isoformat(),
                'updated_at': req.updated_at.isoformat()
            }
            for req in requests_list
        ]
        
        return api_response(data=data, paginate={
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'total_pages': total_pages
        })
    
    except Exception as e:
        logger.error(f"Error filtering requests: {str(e)}")
        return api_error("Failed to filter requests", 500)
