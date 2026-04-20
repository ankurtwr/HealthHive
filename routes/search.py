from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required
from forms import SearchForm
from medicine_service import search_medicine, get_suggestions

search_bp = Blueprint('search', __name__)


@search_bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    form   = SearchForm()
    result = None

    if request.method == 'GET' and request.args.get('query'):
        query_str = request.args.get('query', '').strip()
        if query_str:
            result = search_medicine(query_str)
            form.query.data = query_str

    elif form.validate_on_submit():
        result = search_medicine(form.query.data)

    return render_template('search/search.html', form=form, result=result)


@search_bp.route('/autocomplete')
@login_required
def autocomplete():
    """
    AJAX endpoint — called by JS as the user types.
    Returns JSON list of matching brand names.
    """
    prefix = request.args.get('query', '').strip()
    suggestions = get_suggestions(prefix)
    names = [s['brand_name'] for s in suggestions]
    return jsonify(names)