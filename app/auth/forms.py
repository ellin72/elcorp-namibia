# app/auth/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, ValidationError
from wtforms.validators import DataRequired, Email, Length, EqualTo
from flask_login import current_user
# from app.models import User

class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    submit = SubmitField("Create account")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Sign in")

class TwoFactorForm(FlaskForm):
    token = StringField("Authentication code", validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField("Verify")
    

class ChangePasswordForm(FlaskForm):
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
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Request Password Reset")
    