# app/dashboard/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, DecimalField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, Regexp
from wtforms import HiddenField

class ProfileForm(FlaskForm):
    """Form for updating user profile information."""
    full_name = StringField(
        "Full Name",
        validators=[DataRequired(), Length(2, 100)]
    )
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()]
    )
    phone = StringField(
        "Phone Number",
        validators=[Optional(), Length(7, 20)]
    )
    organization = StringField(
        "Organization",
        validators=[Optional(), Length(max=100)]
    )
    submit = SubmitField("Save Profile")

class PasswordChangeForm(FlaskForm):
    """Form for changing user password."""
    current_password = PasswordField(
        "Current Password",
        validators=[DataRequired()]
    )
    new_password = PasswordField(
        "New Password",
        validators=[DataRequired(), Length(min=6)]
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(), EqualTo("new_password")]
    )
    submit = SubmitField("Change Password")
    

class VehicleForm(FlaskForm):
    """Form for adding or editing vehicle information."""
    id = HiddenField()
    make = StringField("Make", validators=[DataRequired(), Length(max=50)])
    model = StringField("Model", validators=[DataRequired(), Length(max=50)])
    plate_number = StringField(
        "Plate Number",
        validators=[DataRequired(), Length(max=20)]
    )
    submit = SubmitField("Save Vehicle")

class SendCoinForm(FlaskForm):
    """Form for sending Elcoin to another user."""
    recipient_address = StringField(
        "Recipient Wallet Address",
        validators=[
            DataRequired(),
            Length(min=36, max=36),
            Regexp(r'^[0-9a-fA-F\-]+$', message="Invalid wallet address format")
        ]
    )
    amount = DecimalField("Amount", validators=[DataRequired()])
    submit = SubmitField("Send Elcoin")

class TwoFactorForm(FlaskForm):
    """Form for enabling/disabling two-factor authentication."""
    enable_2fa = BooleanField("Enable Two-Factor Authentication")
    submit = SubmitField("Update Security")

