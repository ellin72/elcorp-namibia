# app/email.py
"""Functions to send emails, including password reset emails."""
from flask_mail import Message
from flask import render_template, current_app
from app import mail

def send_password_reset_email(user):
    """Send a password reset email to the specified user."""
    token = user.get_reset_password_token()
    msg = Message(
        '[Elcorp] Reset Your Password',
        sender=current_app.config['ADMINS'][0],
        recipients=[user.email]
    )
    msg.body = render_template(
        'email/reset_password.txt',
        user=user, token=token
    )
    msg.html = render_template(
        'email/reset_password.html',
        user=user, token=token
    )
    mail.send(msg)
