# app/utils.py
"""Utility functions for OTP generation and QR code creation."""
import pyotp
import qrcode
import io
from flask import send_file, current_app

def generate_otp_secret() -> str:
    """
    Create a new base32-encoded secret for TOTP.
    """
    return pyotp.random_base32()

def get_totp_uri(secret: str, user_email: str) -> str:
    """
    Build the provisioning URI for authenticator apps.
    """
    issuer = current_app.config.get("OTP_ISSUER_NAME", "Elcorp Namibia")
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=user_email,
        issuer_name=issuer
    )

def generate_qr_code(uri: str):
    """
    Generate a PIL Image object of the QR code for a provisioning URI.
    """
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img

def otp_qr_response(user):
    """
    Flask response: generate and return the QR-code PNG for a user's OTP.
    """
    secret = user.otp_secret
    if not secret:
        return None
    uri = get_totp_uri(secret, user.email)
    img = generate_qr_code(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")
