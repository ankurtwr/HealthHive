from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from medicine_service import get_search_history
from forms import SearchForm

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    # if the user is authenticated he will redirected to the dashboard 
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('main/home.html')


@main_bp.route('/dashboard')
@login_required                           
def dashboard():
    history = get_search_history(current_user.id, limit=8)
    form    = SearchForm()
    return render_template('main/dashboard.html', history=history, form=form)