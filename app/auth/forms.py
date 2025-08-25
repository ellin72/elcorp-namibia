# app/auth/forms.py
"""Forms for user authentication and account management."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, ValidationError, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp
from flask_login import current_user
# from app.models import User

class RegisterForm(FlaskForm):
    """Form for user registration with fields for full name, email, phone number, organization, role, password, and terms agreement."""
    full_name = StringField(
        "Full Name",
        validators=[DataRequired(message="Please enter your name"), Length(min=2, max=100)]
    )
    username = StringField(
        'Username',
        validators=[
            DataRequired(),
            Length(min=3, max=64),
            Regexp('^[A-Za-z0-9_]+$', message="Usernames must contain only letters, numbers, or underscores.")
        ]
    )

    email = StringField(
        "Email",
        validators=[DataRequired(message="Please enter your email"), Email()]
    )

    phone = StringField("Phone Number", validators=[DataRequired()])
    organization = StringField("Organization", validators=[])
    role = SelectField("Role", choices=[
        ("user", "Regular User"),
        ("verifier", "Verifier"),
        ("admin", "Administrator")
    ], validators=[DataRequired()])
    password = PasswordField(
        "Password", 
        validators=[DataRequired(), Length(min=6)]
    )
    confirm_password = PasswordField("Confirm Password", validators=[
        DataRequired(), EqualTo("password", message="Passwords must match.")
    ])
    agree_terms = BooleanField("I agree to the Terms and Conditions", validators=[DataRequired()])
    submit = SubmitField("Create Account")


class LoginForm(FlaskForm):
    """Form for user login with fields for username, password, remember me option, and submit button."""
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Sign in")

class TwoFactorForm(FlaskForm):
    """Form for two-factor authentication with fields for email and authentication code."""
    token = StringField("Authentication code", validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField("Verify")
    

class ChangePasswordForm(FlaskForm):
    """Form for changing the user's password with fields for current password, new password, confirmation of new password, and submit button."""
    current_password = PasswordField(
        "Current Password",
        validators=[DataRequired(message="Please enter your current password.")]
    )
    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(message="Choose a new password."),
            Length(min=8, message="Your new password must be at least 8 characters.")
        ]
    )
    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(message="Repeat your new password."),
            EqualTo(
                "new_password",
                message="New password and confirmation must match."
            )
        ]
    )
    submit = SubmitField("Change Password")

    def validate_current_password(self, field):
        """
        Ensure that the current_password field matches the logged-in user’s password.
        """
        if not current_user.check_password(field.data):
            raise ValidationError("The current password you entered is incorrect.")
        
    def validate_new_password(self, field):
        """
        Ensure that the new password is not the same as the current password.
        """
        if current_user.check_password(field.data):
            raise ValidationError("The new password must be different from the current password.")
        
    def validate_confirm_new_password(self, field):
        """
        Ensure that the confirm_new_password field matches the new_password field.
        """
        if field.data != self.new_password.data:
            raise ValidationError("The confirmation password does not match the new password.")
        
class ResetPasswordRequestForm(FlaskForm):
    """Form for requesting a password reset with fields for email and submit button."""
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Request Password Reset")
        
class ResetPasswordForm(FlaskForm):
    """Form for resetting the user's password with fields for new password, confirmation of new password, and submit button."""
    password = PasswordField('New Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password',
        validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField('Reset Password')
    