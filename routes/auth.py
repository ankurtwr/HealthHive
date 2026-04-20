from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from forms import RegisterForm, LoginForm
from models import User


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
   
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegisterForm()

    if form.validate_on_submit():          
        user = User.create(
            username = form.username.data,
            email    = form.email.data,
            password = form.password.data,
        )
        login_user(user)                   
        flash('Account created! Welcome to MedCompare.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.get_by_email(form.email.data)

        if user and user.check_password(form.password.data):
            login_user(user)              
            flash(f'Welcome back, {user.username}!', 'success')
            # it will redirect the user to go where he wants to go (dashboard)
            next_page = url_for('main.dashboard')
            return redirect(next_page)
        else:
            flash('Incorrect email or password.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()                          # will end the session 
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))