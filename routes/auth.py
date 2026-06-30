from flask import Blueprint, render_template, redirect, url_for, flash, session
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
        flash('Account created! Welcome to HealthHive.', 'success')
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


@auth_bp.route('/guest')
def guest_login():
    """Create a temporary guest session — no signup required."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    try:
        guest_user = User.create_guest()
        login_user(guest_user)
        session['is_guest'] = True
        session['guest_user_id'] = guest_user.id
        flash('Welcome, Guest! You can explore HealthHive freely. Your data will be erased when you leave.', 'info')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        flash(f'Could not create guest session. Please try again.', 'danger')
        return redirect(url_for('auth.login'))


@auth_bp.route('/guest/exit')
def guest_exit():
    """Explicitly end guest session and purge all data."""
    if current_user.is_authenticated and getattr(current_user, 'is_guest', False):
        user_id = current_user.id
        logout_user()
        User.cleanup_guest(user_id)
        session.pop('is_guest', None)
        session.pop('guest_user_id', None)
        flash('Guest session ended. All your data has been erased.', 'info')
    else:
        logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/logout')
@login_required
def logout():
    # If guest user, cleanup their data
    if getattr(current_user, 'is_guest', False):
        user_id = current_user.id
        logout_user()
        User.cleanup_guest(user_id)
        session.pop('is_guest', None)
        session.pop('guest_user_id', None)
        flash('Guest session ended. All your data has been erased.', 'info')
    else:
        logout_user()                          # will end the session 
        flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))