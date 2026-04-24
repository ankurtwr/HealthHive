# routes/prices.py
"""
Price comparison routes.
/prices?q=medicine_name returns live prices from all platforms as JSON.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
from price_scraper import get_live_prices

prices_bp = Blueprint('prices', __name__)


@prices_bp.route('/prices')
@login_required
def fetch_prices():
    """
    GET /prices?q=Crocin+500mg
    
    Returns JSON array of price data from all platforms:
    [
      {
        "platform": "Tata 1mg",
        "medicine_name": "Crocin 500mg Tablet",
        "price": 15.50,
        "mrp": 20.00,
        "discount": 22.5,
        "url": "https://www.1mg.com/...",
        "pack_size": "Strip of 15 tablets",
        "manufacturer": "GSK",
        "in_stock": true,
        "cached": false
      },
      ...
    ]
    """
    medicine_name = request.args.get('q', '').strip()
    
    if not medicine_name:
        return jsonify({
            'error': 'Missing medicine name',
            'message': 'Please provide ?q=medicine_name'
        }), 400
    
    try:
        # Fetch prices (uses cache if available)
        results = get_live_prices(medicine_name)
        
        return jsonify({
            'query': medicine_name,
            'count': len(results),
            'prices': results
        })
        
    except Exception as e:
        print(f"[prices route] Error: {e}")
        return jsonify({
            'error': 'Failed to fetch prices',
            'message': str(e)
        }), 500