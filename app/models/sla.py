"""
app/models/sla.py - SLA (Service Level Agreement) models
Tracks SLA definitions, metrics, and breach detection
"""

from datetime import datetime, timedelta
from app.extensions import db


class SLADefinition(db.Model):
    """Define SLA targets for different categories and priorities."""
    
    __tablename__ = 'sla_definition'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Category and priority combination this SLA applies to
    category = db.Column(db.String(50), nullable=False, index=True)
    priority = db.Column(db.String(20), nullable=False, index=True)
    
    # SLA response times in hours
    response_time_hours = db.Column(db.Integer, default=4)  # Time to first response
    resolution_time_hours = db.Column(db.Integer, default=24)  # Time to resolution
    
    # Whether this SLA is active
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('category', 'priority', name='unique_category_priority'),
        db.Index('idx_sla_definition_active', 'is_active'),
    )
    
    def __repr__(self):
        return f'<SLADefinition {self.category} {self.priority}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'priority': self.priority,
            'response_time_hours': self.response_time_hours,
            'resolution_time_hours': self.resolution_time_hours,
            'is_active': self.is_active,
        }
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()


class SLAMetric(db.Model):
    """Track SLA metrics and breaches for each service request."""
    
    __tablename__ = 'sla_metric'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Reference to service request
    service_request_id = db.Column(
        db.Integer,
        db.ForeignKey('service_request.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    service_request = db.relationship('ServiceRequest', backref='sla_metrics')
    
    # SLA definition applied
    sla_definition_id = db.Column(
        db.Integer,
        db.ForeignKey('sla_definition.id', ondelete='SET NULL'),
        nullable=True
    )
    sla_definition = db.relationship('SLADefinition')
    
    # Time tracking (when status changed)
    status_changed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    status = db.Column(db.String(50), nullable=False)  # The status at this point
    
    # Response SLA tracking
    first_response_at = db.Column(db.DateTime, nullable=True)  # When first response occurred
    response_sla_met = db.Column(db.Boolean, nullable=True)  # Whether response SLA was met
    response_breach_at = db.Column(db.DateTime, nullable=True)  # When response SLA was breached
    
    # Resolution SLA tracking
    resolution_target_at = db.Column(db.DateTime, nullable=True)  # Target resolution time
    resolution_sla_met = db.Column(db.Boolean, nullable=True)  # Whether resolution SLA was met
    resolution_breach_at = db.Column(db.DateTime, nullable=True)  # When resolution SLA was breached
    
    # Metrics
    time_in_status_minutes = db.Column(db.Integer, default=0)  # Minutes spent in this status
    total_time_minutes = db.Column(db.Integer, default=0)  # Total time from creation
    
    # Breach tracking
    is_breached = db.Column(db.Boolean, default=False, index=True)
    breach_type = db.Column(db.String(50), nullable=True)  # 'response' or 'resolution'
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_sla_metric_breached', 'is_breached'),
        db.Index('idx_sla_metric_service_request', 'service_request_id'),
        db.Index('idx_sla_metric_status_changed', 'status_changed_at'),
    )
    
    def __repr__(self):
        return f'<SLAMetric Request {self.service_request_id} Status {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'service_request_id': self.service_request_id,
            'status': self.status,
            'status_changed_at': self.status_changed_at.isoformat() if self.status_changed_at else None,
            'response_sla_met': self.response_sla_met,
            'resolution_sla_met': self.resolution_sla_met,
            'is_breached': self.is_breached,
            'breach_type': self.breach_type,
            'time_in_status_minutes': self.time_in_status_minutes,
            'total_time_minutes': self.total_time_minutes,
        }
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()


class SLAExemption(db.Model):
    """Track SLA exemptions (e.g., blocked by customer, scheduled maintenance)."""
    
    __tablename__ = 'sla_exemption'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Reference to service request
    service_request_id = db.Column(
        db.Integer,
        db.ForeignKey('service_request.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    service_request = db.relationship('ServiceRequest', backref='sla_exemptions')
    
    # Exemption details
    reason = db.Column(db.String(500), nullable=False)  # Why exemption was granted
    exemption_type = db.Column(db.String(50), nullable=False)  # 'response', 'resolution', 'both'
    
    # Duration
    start_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    end_at = db.Column(db.DateTime, nullable=True)  # NULL = indefinite
    
    # Who granted the exemption
    granted_by_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='SET NULL'),
        nullable=True
    )
    granted_by = db.relationship('User')
    
    # Approval/documentation
    approved = db.Column(db.Boolean, default=False)
    approved_by_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='SET NULL'),
        nullable=True
    )
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_sla_exemption_service_request', 'service_request_id'),
        db.Index('idx_sla_exemption_active', 'end_at'),
    )
    
    def __repr__(self):
        return f'<SLAExemption Request {self.service_request_id}>'
    
    def is_active(self):
        """Check if exemption is currently active."""
        now = datetime.utcnow()
        return self.start_at <= now and (self.end_at is None or now < self.end_at)
    
    def to_dict(self):
        return {
            'id': self.id,
            'service_request_id': self.service_request_id,
            'reason': self.reason,
            'exemption_type': self.exemption_type,
            'start_at': self.start_at.isoformat() if self.start_at else None,
            'end_at': self.end_at.isoformat() if self.end_at else None,
            'is_active': self.is_active(),
            'approved': self.approved,
        }
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
