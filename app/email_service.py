"""
app/email_service.py - Email notifications for service requests
"""
from flask_mail import Message
from flask import render_template, current_app
from app import mail
import logging

logger = logging.getLogger("app.email_service")


def send_service_request_submitted_email(service_request):
    """Send email notification when a service request is submitted."""
    try:
        msg = Message(
            f'[Elcorp] Service Request Submitted: {service_request.title}',
            sender=current_app.config['ADMINS'][0] if current_app.config.get('ADMINS') else 'noreply@elcorp.na',
            recipients=[service_request.creator.email]
        )
        msg.body = f"""
Dear {service_request.creator.full_name},

Your service request has been submitted successfully.

Request ID: {service_request.id}
Title: {service_request.title}
Category: {service_request.category}
Priority: {service_request.priority}
Status: submitted

We will review your request and get back to you shortly.

Best regards,
Elcorp Team
"""
        msg.html = f"""
<html>
<body>
<p>Dear {service_request.creator.full_name},</p>
<p>Your service request has been submitted successfully.</p>
<ul>
<li><strong>Request ID:</strong> {service_request.id}</li>
<li><strong>Title:</strong> {service_request.title}</li>
<li><strong>Category:</strong> {service_request.category}</li>
<li><strong>Priority:</strong> {service_request.priority}</li>
<li><strong>Status:</strong> submitted</li>
</ul>
<p>We will review your request and get back to you shortly.</p>
<p>Best regards,<br/>Elcorp Team</p>
</body>
</html>
"""
        mail.send(msg)
        logger.info(f"Submission email sent to {service_request.creator.email} for request {service_request.id}")
    except Exception as e:
        logger.error(f"Failed to send submission email: {str(e)}")
        raise


def send_service_request_status_email(service_request, old_status, new_status, notes=''):
    """Send email notification when a service request status changes."""
    try:
        recipient = service_request.creator.email
        subject_status = "Approved" if new_status == "approved" else "Rejected" if new_status == "rejected" else new_status.replace('_', ' ').title()
        
        msg = Message(
            f'[Elcorp] Service Request {subject_status}: {service_request.title}',
            sender=current_app.config['ADMINS'][0] if current_app.config.get('ADMINS') else 'noreply@elcorp.na',
            recipients=[recipient]
        )
        
        notes_text = f"Notes: {notes}" if notes else "No additional notes."
        
        msg.body = f"""
Dear {service_request.creator.full_name},

Your service request has been updated.

Request ID: {service_request.id}
Title: {service_request.title}
Previous Status: {old_status}
New Status: {new_status}
{notes_text}

Thank you for your patience. If you have any questions, please contact our support team.

Best regards,
Elcorp Team
"""
        msg.html = f"""
<html>
<body>
<p>Dear {service_request.creator.full_name},</p>
<p>Your service request has been updated.</p>
<ul>
<li><strong>Request ID:</strong> {service_request.id}</li>
<li><strong>Title:</strong> {service_request.title}</li>
<li><strong>Previous Status:</strong> {old_status}</li>
<li><strong>New Status:</strong> {new_status}</li>
</ul>
<p><strong>{notes_text}</strong></p>
<p>Thank you for your patience. If you have any questions, please contact our support team.</p>
<p>Best regards,<br/>Elcorp Team</p>
</body>
</html>
"""
        mail.send(msg)
        logger.info(f"Status email sent to {recipient} for request {service_request.id}")
    except Exception as e:
        logger.error(f"Failed to send status email: {str(e)}")
        raise


def send_service_request_assigned_email(service_request, assignee):
    """Send email notification when a service request is assigned to staff."""
    try:
        msg = Message(
            f'[Elcorp] New Service Request Assigned: {service_request.title}',
            sender=current_app.config['ADMINS'][0] if current_app.config.get('ADMINS') else 'noreply@elcorp.na',
            recipients=[assignee.email]
        )
        msg.body = f"""
Dear {assignee.full_name},

A new service request has been assigned to you.

Request ID: {service_request.id}
Title: {service_request.title}
Description: {service_request.description}
Category: {service_request.category}
Priority: {service_request.priority}
Created by: {service_request.creator.full_name}

Please review and take appropriate action.

Best regards,
Elcorp Team
"""
        msg.html = f"""
<html>
<body>
<p>Dear {assignee.full_name},</p>
<p>A new service request has been assigned to you.</p>
<ul>
<li><strong>Request ID:</strong> {service_request.id}</li>
<li><strong>Title:</strong> {service_request.title}</li>
<li><strong>Category:</strong> {service_request.category}</li>
<li><strong>Priority:</strong> {service_request.priority}</li>
<li><strong>Created by:</strong> {service_request.creator.full_name}</li>
</ul>
<p><strong>Description:</strong></p>
<p>{service_request.description}</p>
<p>Please review and take appropriate action.</p>
<p>Best regards,<br/>Elcorp Team</p>
</body>
</html>
"""
        mail.send(msg)
        logger.info(f"Assignment email sent to {assignee.email} for request {service_request.id}")
    except Exception as e:
        logger.error(f"Failed to send assignment email: {str(e)}")
        raise
