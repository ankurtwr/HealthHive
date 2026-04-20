from db import query_one, query_all, execute
from flask_login import current_user

def search_medicine(query_str):
    query_str = query_str.strip()
    if not query_str:
        return None

    q = query_str.lower()

  
    medicine = query_one(
        "SELECT * FROM medicines WHERE LOWER(brand_name) = %s LIMIT 1", (q,)
    )

    # partial brand name match
    if not medicine:
        medicine = query_one("""
            SELECT * FROM medicines
            WHERE LOWER(brand_name) LIKE %s
            ORDER BY LENGTH(brand_name) LIMIT 1
        """, (f'%{q}%',))

    #  salt/composition match 
    if not medicine:
        medicine = query_one("""
            SELECT * FROM medicines
            WHERE LOWER(salt_composition) LIKE %s
            ORDER BY LENGTH(brand_name) LIMIT 1
        """, (f'%{q}%',))

    if not medicine:
        suggestions = query_all("""
            SELECT DISTINCT brand_name, manufacturer, salt_composition
            FROM medicines
            WHERE LOWER(brand_name) LIKE %s OR LOWER(salt_composition) LIKE %s
            LIMIT 6
        """, (f'%{q}%', f'%{q}%'))
        return {'found': False, 'query': query_str, 'suggestions': suggestions}

    # generics for the same salt (Jan Aushadhi first, then by MRP)
    generics = query_all("""
        SELECT * FROM generics
        WHERE salt_composition = %s
        ORDER BY
            CASE source WHEN 'JanAushadhi' THEN 0 ELSE 1 END,
            mrp ASC
    """, (medicine['salt_composition'],))

    # other brands with the same salt
    other_brands = query_all("""
        SELECT brand_name, manufacturer, strength
        FROM medicines
        WHERE salt_composition = %s AND id != %s
        ORDER BY brand_name
    """, (medicine['salt_composition'], medicine['id']))

    # savings calculation
    savings = None
    if generics:
        cheapest = generics[0]
        ja_options = [g for g in generics if g['source'] == 'JanAushadhi']
        savings = {
            'cheapest':       cheapest,
            'cheapest_mrp':   float(cheapest['mrp']) if cheapest['mrp'] else None,
            'total_generics': len(generics),
            'ja_options':     ja_options,
        }

    #  log search history for logged-in users
    if current_user.is_authenticated:
        execute(
            "INSERT INTO search_history (user_id, query) VALUES (%s, %s)",
            (current_user.id, query_str)
        )

    return {
        'found':        True,
        'query':        query_str,
        'medicine':     medicine,
        'generics':     generics,
        'other_brands': other_brands,
        'savings':      savings,
    }


def get_search_history(user_id, limit=10):
    return query_all("""
        SELECT query, searched_at FROM search_history
        WHERE user_id = %s
        ORDER BY searched_at DESC
        LIMIT %s
    """, (user_id, limit))


def get_suggestions(prefix):
    """Used by the search autocomplete (AJAX)."""
    if len(prefix) < 2:
        return []
    return query_all("""
        SELECT DISTINCT brand_name FROM medicines
        WHERE LOWER(brand_name) LIKE %s
        ORDER BY brand_name LIMIT 8
    """, (f'{prefix.lower()}%',))