# forms.py  — All WTForms definitions with validation
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, SubmitField
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, ValidationError
)
from models import User


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message='Username is required.'),
        Length(min=3, max=80, message='Username must be 3–80 characters.'),
    ])
    email = EmailField('Email', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Enter a valid email address.'),
        Length(max=150),
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.'),
        Length(min=6, message='Password must be at least 6 characters.'),
    ])
    confirm = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password.'),
        EqualTo('password', message='Passwords must match.'),
    ])
    submit = SubmitField('Create Account')

    # Custom validators — called automatically by WTForms if named validate_<fieldname>
    def validate_username(self, field):
        if User.get_by_username(field.data):
            raise ValidationError('That username is already taken.')

    def validate_email(self, field):
        if User.get_by_email(field.data):
            raise ValidationError('An account with that email already exists.')


class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Enter a valid email address.'),
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.'),
    ])
    submit = SubmitField('Sign In')


class SearchForm(FlaskForm):
    """
    Used both in the navbar (GET) and the search page.
    CSRF is disabled for the GET search — safe because it reads only.
    """
    query = StringField('Search', validators=[
        DataRequired(message='Please enter a medicine name.'),
        Length(min=2, max=200, message='Search must be 2–200 characters.'),
    ])
    submit = SubmitField('Search')