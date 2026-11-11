from flask_login import current_user

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed

from wtforms import StringField, EmailField, PasswordField, SubmitField, BooleanField, ValidationError, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional

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
    role = SelectField('Role', choices=config.ROLE_FORM_LIST, default=config.ROLE_STAFF)
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


class UserAdminForm(FlaskForm):
    """An owner editing someone's account: details, role, on/off and an optional new password."""
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=50)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    role = SelectField('Role', choices=config.ROLE_FORM_LIST)
    active = BooleanField('Can sign in')
    password = PasswordField("New password", validators=[Optional(), Length(min=8, message='Use at least 8 characters.')])
    confirm_password = PasswordField("Confirm new password", validators=[EqualTo('password', message='The two passwords do not match.')])
    submit = SubmitField('Save user')

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user

    def validate_email(self, email):
        other = User.query.filter(User.email == email.data, User.id != self._user.id).first()
        if other:
            raise ValidationError('Another user already has this email.')
