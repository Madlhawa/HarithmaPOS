from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, PasswordField, SubmitField, BooleanField, TelField, IntegerField, ValidationError
from wtforms.validators import DataRequired, Length, Email, EqualTo
from harithmapos.models import User

class RegistrationForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=20)])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(),Length(min=6)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(),EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('User with this email already exists.')

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(),Length(min=6)])
    remember = BooleanField("Remember Me")
    submit = SubmitField('Login')

class CustomerForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=20)])
    contact = TelField("Contact", validators=[Length(min=9, max=9)])
    address = StringField("Address")
    email = EmailField("Email")

class VehicalForm(FlaskForm):
    number = StringField("Number*", validators=[DataRequired(), Length(min=7, max=8)])
    make = StringField("Make")
    model = StringField("Model")
    year = IntegerField("Year")
    owner_id = IntegerField("Owner ID", validators=[DataRequired()])