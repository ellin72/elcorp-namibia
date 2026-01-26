"""
app/services/sla_service.py - SLA checking and breach detection
Monitors service request SLA compliance and tracks violations
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

from app.models import ServiceRequest, SLADefinition, SLAMetric, SLAExemption, db

logger = logging.getLogger(__name__)


class SLAService:
    """Service for SLA tracking, monitoring, and breach detection."""
    
    @staticmethod
    def get_sla_definition(category, priority):
        """
        Get SLA definition for a category/priority combination.
        
        Falls back to default SLA if specific one doesn't exist.
        """
        sla = SLADefinition.query.filter_by(
            category=category,
            priority=priority,
            is_active=True
        ).first()
        
        if not sla:
            # Return default SLA for priority
            sla = SLADefinition.query.filter_by(
                category='default',
                priority=priority,
                is_active=True
            ).first()
        
        if not sla:
            # Return absolute default (24 hour resolution)
            return SLADefinition(
                category='default',
                priority='medium',
                response_time_hours=4,
                resolution_time_hours=24,
            )
        
        return sla
    
    @staticmethod
    def track_status_change(request_id, new_status):
        """
        Track status change for SLA monitoring.
        
        Called whenever service request status changes.
        """
        try:
            req = ServiceRequest.query.get(request_id)
            if not req:
                logger.warning(f'ServiceRequest {request_id} not found')
                return None
            
            # Get applicable SLA
            sla_def = SLAService.get_sla_definition(req.category, req.priority)
            
            # Create SLA metric record
            metric = SLAMetric(
                service_request_id=request_id,
                sla_definition_id=sla_def.id,
                status_changed_at=datetime.utcnow(),
                status=new_status,
            )
            
            # Calculate SLA targets
            if new_status == 'open':
                # Response SLA starts now
                metric.response_sla_met = False
                metric.resolution_sla_met = False
            
            elif new_status == 'in_progress':
                # Set response SLA as met if first response happened on time
                metric.first_response_at = datetime.utcnow()
                response_deadline = req.created_at + timedelta(hours=sla_def.response_time_hours)
                metric.response_sla_met = datetime.utcnow() <= response_deadline
                
                # Resolution SLA target
                metric.resolution_target_at = req.created_at + timedelta(hours=sla_def.resolution_time_hours)
                metric.resolution_sla_met = False
            
            elif new_status == 'completed':
                # Check resolution SLA
                resolution_deadline = req.created_at + timedelta(hours=sla_def.resolution_time_hours)
                metric.resolution_sla_met = datetime.utcnow() <= resolution_deadline
                
                if not metric.resolution_sla_met:
                    metric.is_breached = True
                    metric.breach_type = 'resolution'
                    metric.resolution_breach_at = datetime.utcnow()
            
            db.session.add(metric)
            db.session.commit()
            
            logger.info(f'SLA metric tracked for request {request_id}: {new_status}')
            return metric
        except Exception as e:
            logger.error(f'Error tracking SLA status change: {str(e)}')
            return None
    
    @staticmethod
    def check_response_sla_breach(request_id):
        """
        Check if request has breached response SLA.
        
        Response SLA = time from creation to first response (in_progress)
        """
        try:
            req = ServiceRequest.query.get(request_id)
            if not req or req.status == 'completed':
                return False
            
            # Check for active exemptions
            if SLAService.has_active_exemption(request_id, 'response'):
                return False
            
            # Get SLA definition
            sla_def = SLAService.get_sla_definition(req.category, req.priority)
            
            # Calculate deadline
            response_deadline = req.created_at + timedelta(hours=sla_def.response_time_hours)
            
            # Check if breached
            if req.status == 'open' and datetime.utcnow() > response_deadline:
                return True
            
            return False
        except Exception as e:
            logger.error(f'Error checking response SLA: {str(e)}')
            return False
    
    @staticmethod
    def check_resolution_sla_breach(request_id):
        """
        Check if request has breached resolution SLA.
        
        Resolution SLA = time from creation to completion
        """
        try:
            req = ServiceRequest.query.get(request_id)
            if not req:
                return False
            
            # Completed requests don't breach
            if req.status == 'completed':
                return False
            
            # Check for active exemptions
            if SLAService.has_active_exemption(request_id, 'resolution'):
                return False
            
            # Get SLA definition
            sla_def = SLAService.get_sla_definition(req.category, req.priority)
            
            # Calculate deadline
            resolution_deadline = req.created_at + timedelta(hours=sla_def.resolution_time_hours)
            
            # Check if breached
            if datetime.utcnow() > resolution_deadline:
                return True
            
            return False
        except Exception as e:
            logger.error(f'Error checking resolution SLA: {str(e)}')
            return False
    
    @staticmethod
    def check_all_breaches():
        """
        Check all open/in-progress requests for SLA breaches.
        
        Returns list of breached requests.
        """
        try:
            breaches = []
            
            # Find all open/in-progress requests
            requests = ServiceRequest.query.filter(
                ServiceRequest.status.in_(['open', 'in_progress'])
            ).all()
            
            for req in requests:
                breach_info = {
                    'request_id': req.id,
                    'title': req.title,
                    'category': req.category,
                    'priority': req.priority,
                    'status': req.status,
                    'created_at': req.created_at,
                    'breaches': []
                }
                
                # Check response breach
                if SLAService.check_response_sla_breach(req.id):
                    sla_def = SLAService.get_sla_definition(req.category, req.priority)
                    deadline = req.created_at + timedelta(hours=sla_def.response_time_hours)
                    hours_overdue = (datetime.utcnow() - deadline).total_seconds() / 3600
                    
                    breach_info['breaches'].append({
                        'type': 'response',
                        'deadline': deadline,
                        'hours_overdue': hours_overdue,
                    })
                
                # Check resolution breach
                if SLAService.check_resolution_sla_breach(req.id):
                    sla_def = SLAService.get_sla_definition(req.category, req.priority)
                    deadline = req.created_at + timedelta(hours=sla_def.resolution_time_hours)
                    hours_overdue = (datetime.utcnow() - deadline).total_seconds() / 3600
                    
                    breach_info['breaches'].append({
                        'type': 'resolution',
                        'deadline': deadline,
                        'hours_overdue': hours_overdue,
                    })
                
                if breach_info['breaches']:
                    breaches.append(breach_info)
            
            logger.info(f'SLA breach check completed: {len(breaches)} breaches found')
            return breaches
        except Exception as e:
            logger.error(f'Error checking all SLA breaches: {str(e)}')
            return []
    
    @staticmethod
    def has_active_exemption(request_id, exemption_type):
        """
        Check if request has active SLA exemption.
        
        Args:
            request_id: Service request ID
            exemption_type: 'response', 'resolution', or 'both'
        
        Returns:
            True if active exemption exists
        """
        try:
            now = datetime.utcnow()
            
            exemption = SLAExemption.query.filter(
                and_(
                    SLAExemption.service_request_id == request_id,
                    SLAExemption.start_at <= now,
                    or_(
                        SLAExemption.end_at.is_(None),
                        SLAExemption.end_at > now
                    ),
                    or_(
                        SLAExemption.exemption_type == 'both',
                        SLAExemption.exemption_type == exemption_type
                    )
                )
            ).first()
            
            return exemption is not None
        except Exception as e:
            logger.error(f'Error checking exemption: {str(e)}')
            return False
    
    @staticmethod
    def grant_exemption(request_id, reason, exemption_type='both', duration_hours=None, granted_by_id=None):
        """
        Grant SLA exemption for a request.
        
        Args:
            request_id: Service request ID
            reason: Reason for exemption
            exemption_type: 'response', 'resolution', or 'both'
            duration_hours: Duration of exemption (None = indefinite)
            granted_by_id: User ID who granted exemption
        
        Returns:
            SLAExemption object
        """
        try:
            exemption = SLAExemption(
                service_request_id=request_id,
                reason=reason,
                exemption_type=exemption_type,
                start_at=datetime.utcnow(),
                granted_by_id=granted_by_id,
            )
            
            if duration_hours:
                exemption.end_at = datetime.utcnow() + timedelta(hours=duration_hours)
            
            db.session.add(exemption)
            db.session.commit()
            
            logger.info(f'SLA exemption granted for request {request_id}: {reason}')
            return exemption
        except Exception as e:
            logger.error(f'Error granting exemption: {str(e)}')
            return None
    
    @staticmethod
    def get_sla_metrics_for_request(request_id):
        """Get all SLA metrics for a request."""
        try:
            metrics = SLAMetric.query.filter_by(service_request_id=request_id).all()
            return [m.to_dict() for m in metrics]
        except Exception as e:
            logger.error(f'Error retrieving SLA metrics: {str(e)}')
            return []
    
    @staticmethod
    def get_breach_statistics(days=30):
        """
        Get SLA breach statistics for the last N days.
        
        Returns dict with breach counts and trends.
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Total breaches
            total_breaches = SLAMetric.query.filter(
                and_(
                    SLAMetric.is_breached == True,
                    SLAMetric.created_at >= cutoff_date
                )
            ).count()
            
            # Breaches by type
            response_breaches = SLAMetric.query.filter(
                and_(
                    SLAMetric.breach_type == 'response',
                    SLAMetric.created_at >= cutoff_date
                )
            ).count()
            
            resolution_breaches = SLAMetric.query.filter(
                and_(
                    SLAMetric.breach_type == 'resolution',
                    SLAMetric.created_at >= cutoff_date
                )
            ).count()
            
            # Breaches by priority
            breaches_by_priority = db.session.query(
                ServiceRequest.priority,
                db.func.count(SLAMetric.id)
            ).join(SLAMetric).filter(
                and_(
                    SLAMetric.is_breached == True,
                    SLAMetric.created_at >= cutoff_date
                )
            ).group_by(ServiceRequest.priority).all()
            
            return {
                'total_breaches': total_breaches,
                'response_breaches': response_breaches,
                'resolution_breaches': resolution_breaches,
                'breaches_by_priority': {p: count for p, count in breaches_by_priority},
                'period_days': days,
            }
        except Exception as e:
            logger.error(f'Error getting breach statistics: {str(e)}')
            return {}
