from flask_login import current_user

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed

from wtforms import StringField, EmailField, PasswordField, SubmitField, BooleanField, ValidationError, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo

from harithmapos.models import User
import harithmapos.config as config


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New password", validators=[DataRequired(), Length(min=8, message='Use at least 8 characters.')])
    confirm_password = PasswordField("Confirm password", validators=[DataRequired(), EqualTo('password', message='The two passwords do not match.')])
    submit = SubmitField('Set new password')


class RequestPasswordResetFrom(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField('Send reset link')


class UserUpdateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=50)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    image = FileField('Profile picture', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Use a JPG or PNG image.')])
    ui_theme = SelectField('Theme', choices=config.UI_THEME_FORM_LIST)
    submit = SubmitField('Save account')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Another user already has this email.')


class UserRegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=50)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, message='Use at least 8 characters.')])
    confirm_password = PasswordField("Confirm password", validators=[DataRequired(), EqualTo('password', message='The two passwords do not match.')])
    submit = SubmitField('Add user')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('A user with this email already exists.')


class UserLoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Keep me signed in")
    submit = SubmitField('Sign in')
