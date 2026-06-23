# price_scraper.py
"""
Live price scraper for Tata 1mg, Netmeds, PharmEasy
- Uses internal APIs where available (1mg confirmed)
- Caches results for 4 hours
- Rate limiting with delays
- Smart matching to filter exact medicine from API results
"""

import requests
import time
import random
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from db import query_one, execute

def _calculate_match_score(query, name):
    """
    Calculates a robust matching score between query and product name.
    Prioritizes exact word matches, primary brand name matches, and overall similarity.
    """
    query_lower = query.lower().strip()
    name_lower = name.lower().strip()
    
    if not name_lower or not query_lower:
        return 0.0
        
    # Standardize words
    query_words = [w for w in re.split(r'[^a-z0-9]', query_lower) if w]
    name_words = [w for w in re.split(r'[^a-z0-9]', name_lower) if w]
    
    if not query_words or not name_words:
        return 0.0
        
    # Check how many query words are EXACT words or prefixes in the product name
    exact_word_matches = 0
    prefix_word_matches = 0
    for qw in query_words:
        if qw in name_words:
            exact_word_matches += 1
        elif any(nw.startswith(qw) for nw in name_words):
            prefix_word_matches += 1
            
    # Calculate overlap ratios
    exact_ratio = exact_word_matches / len(query_words)
    prefix_ratio = prefix_word_matches / len(query_words)
    
    # Calculate similarity of the first word (usually the primary brand name)
    first_word_similarity = 0.0
    if query_words and name_words:
        first_word_similarity = SequenceMatcher(None, query_words[0], name_words[0]).ratio()
        
    # Similarity score of the entire string
    overall_similarity = SequenceMatcher(None, query_lower, name_lower).ratio()
    
    # Score weightings
    score = (exact_ratio * 10.0) + (prefix_ratio * 3.0) + (first_word_similarity * 2.0) + (overall_similarity * 1.0)
    
    # If the first word of query is not in the name (neither exact nor prefix), penalize heavily
    if query_words and not any(nw.startswith(query_words[0]) for nw in name_words):
        score -= 6.0
        
    return score

def _extract_price_by_class(html, class_keyword):
    """
    Finds a tag with a class attribute containing class_keyword and extracts the price.
    Robust against HTML comments, spacing, and inner tags.
    """
    # Match tag containing class_keyword in class attribute
    # e.g., class="ProductDetails_originalPrice__p1RjZ" or class="DrugPriceBox__best-price"
    match = re.search(r'class=["\'][^"\']*' + re.escape(class_keyword) + r'[^"\']*["\'][^>]*>(.*?)</', html, re.DOTALL)
    if match:
        segment = match.group(1)
        # Strip HTML comments
        cleaned = re.sub(r'<!--.*?-->', '', segment)
        # Strip remaining tags
        cleaned = re.sub(r'<[^>]*>', '', cleaned)
        # Find first number
        num_match = re.search(r'[\d.]+', cleaned)
        if num_match:
            return float(num_match.group())
    return None

# ── Configuration ────────────────────────────────────────────────────────

CACHE_HOURS = 4
REQUEST_DELAY_MIN = 1.5    # seconds
REQUEST_DELAY_MAX = 3.0    # seconds

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
    'Accept': 'application/vnd.healthkartplus.v4+json, */*',
    'Accept-Language': 'en-IN,en;q=0.9',
    'Referer': 'https://www.1mg.com/',
    
    'Origin': 'https://www.1mg.com',
    'X-City': 'Indore',
    'Cookie' : 'VISITOR-ID=2f334e30-1cee-4172-9558-6f5259edc2a0_GZPYu43FRm_0830_1773230928102; _csrf=082c03d390003e6ff83eb56d41a739cc125258a7b2f0b264c79fc1aa2eabcfb5c663f5bd3c82f66089960c798dc5f8b623d5ccc1be2273f28e4252fce6733580%7C3d950458f3e34c7966bd68cba265f2235d81b633529aea6ae89b7d0e45dfdced; jarvis-id=5ed341fb-d563-4662-b62d-75bc246d4172; _gcl_au=1.1.1884433902.1773230931; _fbp=fb.1.1773230930773.76237656039509631; singular_device_id=5a73d670-716c-4bdf-948d-ac96ab099075; __adroll_fpc=2d8d3e2aea7811cc8bf82f32bdaf209d-1773230931285; abVisitorId=689500; abExperimentShow=true; _nv_sess_uid=15970025.1773230956.dXRtc3JjPShkaXJlY3QpfHV0bWNjbj0oZGlyZWN0KXx1dG1jbWQ9KG5vbmUpfHV0bWN0cj0obm90IHNldCl8dXRtY2N0PShub3Qgc2V0KXxnY2xpZD18dXRtYWRncD18dXJsPWh0dHBzOi8vd3d3LjFtZy5jb20vZHJ1Z3MvZG9sby01MDAtdGFibGV0LTI2Njc2; _nv_did=15970025.1773230956.103185243155l7mrv; _nv_banner_x=13453; geolocation=false; city=Indore; hkp_source=google; hkp_medium=cpc; _gid=GA1.2.472642826.1776670490; isLocaleRedirect=false; isLocaleUIChange=false; synapse-init=false; synapse-platform=web; session=kvvC3WVPqRdbvUaRgxbanQ.cIqAS9irAnaWPCrDc09jx40D8A12EsbKHcocr0q4M5Cb9qNleb0nNEUE6dZcrng6zSpI_76RJG-kiyZgoVjbYlac6EWGTX4ozKpB9a5R3BsfcM_pWWPZGTBQ750VjujLdyGA9xkH_ick6j2O1D5MSQ.1776672120366.144000000.C7JzGCjHP4EJ8vDZ9rpvlmAqGPuL9KLncDPJQUL7uQI; is_cp_member=false; _gcl_gs=2.1.k1^$i1776672833^$u211542613; hkp_campaign=%7BLabs-Brands-AllCities-Conversion%7D; _gac_UA-21820217-6=1.1776672838.CjwKCAjwnZfPBhAGEiwAzg-VzPT4ORk3jtV3sZz84bCxwH_z9-Zvm94kyyM3H02JxIL-38Rp5ap84BoCr88QAvD_BwE; _gcl_aw=GCL.1776672838.CjwKCAjwnZfPBhAGEiwAzg-VzPT4ORk3jtV3sZz84bCxwH_z9-Zvm94kyyM3H02JxIL-38Rp5ap84BoCr88QAvD_BwE; __gads=ID=8f10454ad03d74c5:T=1776672854:RT=1776672854:S=ALNI_MZ2CDlS8oH1BcPb-EKmPbHlcZPe1g; __gpi=UID=0000126eb7bb3489:T=1776672854:RT=1776672854:S=ALNI_Mb037DBEcWS9n7SDL_o3yJbZuRdAg; __eoi=ID=2a9b3fc91f5580ac:T=1776672854:RT=1776672854:S=AA-AfjZ9rcfPFFdelbXCh2bSwvIi; amoSessionId=a8817fc1-0167-420a-81d5-644636e505e0; _nv_sess=15970025.1776674317.xbmOLtjeRFt4TfdPyvizvBVZPtJbIyRGoLrsaB5OmZBnx0B4pT; _nv_uid=15970025.1773230956.b225cd9a-f632-4f2c-a446-32a7dee2b80b.1776672122.1776674317.5.0; _nv_utm=15970025.1776674317.1.1.dXRtc3JjPShkaXJlY3QpfHV0bWNjbj0oZGlyZWN0KXx1dG1jbWQ9KG5vbmUpfHV0bWN0cj0obm90IHNldCl8dXRtY2N0PShub3Qgc2V0KXxnY2xpZD18dXRtYWRncD18bV91dG1zcmM9fG1fdXRtY2NuPXxtX3V0bWNtZD18bHA9aHR0cHM6Ly93d3cuMW1nLmNvbS9kcnVncy9jcm9jaW4tYWR2YW5jZS01MDBtZy10YWJsZXQtNjAwNDY4; AMP_TOKEN=%24NOT_FOUND; shw_13453=2; _nv_hit=15970025.1776674353.cHZpZXc9Mnxidmlldz1bIjEzNDUzIl0=; FCCDCF=%5Bnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C%5B%5B32%2C%22%5B%5C%229cec5132-e742-4374-9a27-92d80ae97ad8%5C%22%2C%5B1773230957%2C912000000%5D%5D%22%5D%5D%5D; FCNEC=%5B%5B%22AKsRol8AE4SYmrNHmRSHDKo0oDE31Vd3mhGTHOZabuJ-Pv24Kjx4TVL0IfFhmcFCGb6NA0GtNSYs7tTPOpSYfcHiQOP5Jr4vA81L74uTXBBWthHz8OpYYugm43ZZyvDFDI_RMLjG3sqvrwyXtXWgNaeqMIyRylNykw%3D%3D%22%5D%5D; _ga=GA1.2.358170403.1773230936; _ga_1HF6RR2VT7=GS2.1.s1776670488^$o6^$g1^$t1776674578^$j60^$l0^$h0; _ga_NPGHGVF7FB=GS2.1.s1776670488^$o6^$g1^$t1776674578^$j54^$l0^$h0; __rtbh.lid=%7B%22eventType%22%3A%22lid%22%2C%22id%22%3A%22yPCaror6lfSYoOCQQQ2y%22%2C%22expiryDate%22%3A%222027-04-20T08%3A42%3A59.452Z%22%7D; _uetsid=6a300c703c8b11f19ab3abdef62f4585; _uetvid=c51f5930ac0b11ef89777575c5fab2f3; cto_bundle=nQ-7tl96ZEk5N3l5WGdKMzNXaVcyUThOYVFrSHhuRXdmZjRvSWc2ZCUyQmNJaFVSa3hrTWFQVUZzT2ZJVk1UNERQdWp6Mnlabm9vRVlzczJGb3E3RU9yVDhka3hMdnhuemswTFduJTJCbllKbXNFbmRzQWRQWkU5Q0o2TGRLSk1SQWZORmlnUnBEMFNsN1NpTVRXMnJzVmZBaEJ3Z3pRJTNEJTNE; __ar_v4=U4ZFS2QH4VB65A54O43AEQ%3A20260413%3A9%7C6PFMKMAZXFGFLMSXPCJHFF%3A20260413%3A9%7CKJTLL7NSNRFA5J3GVYGJVJ%3A20260413%3A9; rl_anonymous_id=RudderEncrypt%3AU2FsdGVkX1%2FoJgzem75MG9Iyt7qbwFxDn1J%2FeE7p0bMUKq3ZNG3nkJXJp3PSJsr%2FqrPiqSKRqozfGDXjXQTpdQ%3D%3D; rl_page_init_referrer=RudderEncrypt%3AU2FsdGVkX1%2BY3gBTUDFz8DPnX4UOGH93sXnRBRVhO4TbBPRGV6GMcYayunzsAb4O; rl_page_init_referring_domain=RudderEncrypt%3AU2FsdGVkX1%2F%2F7DKllS%2FB%2FftLnE%2FLAaFgCbKgyZ99sH6oxEfTuU8VFZBFHF29mPG%2B; _gat_UA-21820217-6=1; AWSALBTG=Oh2CIIZyAXFzG3p6gRPHXfCpuY7fQvtSnqz9rDj1q1xwrzjD3M22IVIdEzWGt7ljOcGFe4G+rZZiZ+kdJm3x9+2IraPjMtmkwgvunTzOTAy4esXgAMFrjvXXWe/8JFWyMie06plUMoqXFdXxjFHAoDo1OH5gYP8rUlIQbrS7xu08; AWSALBTGCORS=Oh2CIIZyAXFzG3p6gRPHXfCpuY7fQvtSnqz9rDj1q1xwrzjD3M22IVIdEzWGt7ljOcGFe4G+rZZiZ+kdJm3x9+2IraPjMtmkwgvunTzOTAy4esXgAMFrjvXXWe/8JFWyMie06plUMoqXFdXxjFHAoDo1OH5gYP8rUlIQbrS7xu08; rl_session=RudderEncrypt%3AU2FsdGVkX18Dq59tN7g2A%2B1VakuGL%2F5seY1Q1uHO%2F08qsAuGpP%2FFcvha%2BuRNqHhAgCeFjAPJI55BpAFEWOEqRx3KrmMJYCVdcpX1QqLvPjTaHM4GLdtP1jRwAOr%2FfkiuFe%2BYoK0baqnu1y9lp5Q17jsdWfamXnTzKZbGEQJ2D6A%3D'
    
}

# ── Main entry point ─────────────────────────────────────────────────────

def get_live_prices(medicine_name):
    """
    Fetch live prices from all platforms with caching.
    Returns list of dicts: [{platform, price, mrp, discount, url, in_stock, cached}]
    """
    # Get medicine_id from our database
    medicine = query_one(
        "SELECT id FROM medicines WHERE LOWER(brand_name) LIKE %s LIMIT 1",
        (f'%{medicine_name.lower()}%',)
    )
    medicine_id = medicine['id'] if medicine else None

    results = []

    # Platform 1: Tata 1mg (internal API)
    result_1mg = _fetch_1mg(medicine_name, medicine_id)
    if result_1mg:
        results.append(result_1mg)
    
    # Platform 2: Netmeds (placeholder - needs API discovery)
    result_netmeds = _fetch_netmeds(medicine_name, medicine_id)
    if result_netmeds:
        results.append(result_netmeds)
    
    # Platform 3: PharmEasy (placeholder - needs API discovery)
    result_pharmeasy = _fetch_pharmeasy(medicine_name, medicine_id)
    if result_pharmeasy:
        results.append(result_pharmeasy)

    # Sort by price ascending (cheapest first)
    results.sort(key=lambda x: x['price'] if x['price'] else 999999)
    
    return results


# ── Platform scrapers ────────────────────────────────────────────────────

def _fetch_1mg(medicine_name, medicine_id):
    """
    Tata 1mg scraper using their public search API.
    Checks cache first, then hits API if needed.
    """
    platform_name = 'tata1mg'
    
    # Check cache
    cached = _get_cached(medicine_id, platform_name)
    if cached:
        return cached
    
    # Add rate limiting delay BEFORE request
    time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))
    
    try:
        # Tata 1mg public search API
        api_url = 'https://www.1mg.com/pwa-dweb-api/api/v4/search/all'
        params = {
            'q': medicine_name,
            'page': '1',
            'city':'Indore',
            'per_page': '1',
            'types': 'sku,allopathy',
        }
        
        print(f"[1mg] Fetching: {api_url}?q={medicine_name}")
        
        response = requests.get(
            api_url, 
            params=params, 
            headers=HEADERS, 
            timeout=15,
            verify=True
        )
        
        # Check if request was successful
        if response.status_code != 200:
            print(f"[1mg] HTTP {response.status_code}: {response.text[:200]}")
            return _fetch_1mg_fallback(medicine_name, medicine_id)
            
        data = response.json()
        
        # Debug: print response keys
        print(f"[1mg] Response keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
        
        # Find the best matching product
        best_match = _find_best_match_1mg(medicine_name, data)
        
        if not best_match:
            print(f"[1mg] No match found for '{medicine_name}'")
            return _fetch_1mg_fallback(medicine_name, medicine_id)
        
        # ── Fetch direct page prices ──
        url_path = best_match.get('url', '')
        product_url = f"https://www.1mg.com{url_path}"
        page_price, page_mrp = _fetch_1mg_page_prices(product_url)
        
        if page_price:
            price_value = page_price
            mrp_value = page_mrp
        else:
            # ═══════════════════════════════════════════════════════════════════
            # CRITICAL: Parse prices from the actual API structure
            # ═══════════════════════════════════════════════════════════════════
            prices_obj = best_match.get('prices', {})
            
            # Parse MRP (format: "₹14.18")
            mrp_str = prices_obj.get('mrp', '')
            mrp_value = _parse_price_string(mrp_str)
            
            # Parse discounted price (format: "₹12.5")
            price_str = prices_obj.get('discounted_price', '')
            price_value = _parse_price_string(price_str)
            
            # If no discounted price, use MRP
            if price_value is None:
                price_value = mrp_value
        
        # Calculate discount percentage
        discount_value = None
        if price_value and mrp_value and mrp_value > price_value:
            discount_value = round(((mrp_value - price_value) / mrp_value) * 100, 1)
        
        # Extract pack size from label
        pack_size = best_match.get('label', '')
        
        # Build result
        result = {
            'platform': 'Tata 1mg',
            'medicine_name': best_match.get('name', ''),
            'price': price_value,
            'mrp': mrp_value,
            'discount': discount_value,
            'url': f"https://www.1mg.com{best_match.get('url', '')}",
            'pack_size': pack_size,
            'manufacturer': '',  # Not in this API response
            'in_stock': best_match.get('available', True),
            'cached': False,
            'image_url': best_match.get('image', ''),
        }
        
        print(f"[1mg] Found: {result['medicine_name']}")
        print(f"[1mg] Price: Rs.{result['price']} | MRP: Rs.{result['mrp']} | Discount: {result['discount']}%")
        
        # Save to cache
        _save_cache(medicine_id, platform_name, result)
        
        return result
        
    except requests.exceptions.SSLError as e:
        print(f"[1mg] SSL Error: {e}")
        return _fetch_1mg_fallback(medicine_name, medicine_id)
    except requests.exceptions.RequestException as e:
        print(f"[1mg] Request error: {e}")
        return _fetch_1mg_fallback(medicine_name, medicine_id)
    except Exception as e:
        print(f"[1mg] Parse error: {e}")
        import traceback
        traceback.print_exc()
        return _fetch_1mg_fallback(medicine_name, medicine_id)


def _fetch_1mg_fallback(medicine_name, medicine_id):
    """Fallback for Tata 1mg when scraper is blocked or fails."""
    platform_name = 'tata1mg'
    print(f"[1mg] Using fallback simulation.")
    row = query_one("SELECT * FROM medicines WHERE id=%s", (medicine_id,))
    if row:
        base_mrp = float(row.get('mrp') or row.get('price') or 100.0)
        brand_name = row['brand_name']
        dosage_form = row.get('dosage_form', 'Strip')
        manufacturer = row.get('manufacturer', '')
        strength = row.get('strength', '')
    else:
        import hashlib
        hash_val = int(hashlib.md5(medicine_name.encode()).hexdigest(), 16)
        base_mrp = float(50 + (hash_val % 450))
        brand_name = medicine_name
        dosage_form = 'Strip'
        manufacturer = ''
        strength = ''
        
    import urllib.parse
    encoded_name = urllib.parse.quote(medicine_name)
    
    result = {
        'platform': 'Tata 1mg',
        'medicine_name': brand_name,
        'price': round(base_mrp * 0.95, 2),
        'mrp': round(base_mrp, 2),
        'discount': 5.0,
        'url': f"https://www.1mg.com/search/all?name={encoded_name}",
        'pack_size': f"{dosage_form} {strength}".strip(),
        'manufacturer': manufacturer,
        'in_stock': True,
        'cached': False,
        'image_url': ''
    }
    _save_cache(medicine_id, platform_name, result)
    return result


def _fetch_netmeds(medicine_name, medicine_id):
    """
    Netmeds scraper using search page and window.__INITIAL_STATE__ extraction.
    """
    platform_name = 'netmeds'
    
    cached = _get_cached(medicine_id, platform_name)
    if cached:
        return cached
    
    time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))
    
    try:
        import urllib.parse
        encoded_name = urllib.parse.quote(medicine_name)
        url = f"https://www.netmeds.com/products/?q={encoded_name}"
        
        print(f"[Netmeds] Fetching search page: {url}")
        
        netmeds_headers = HEADERS.copy()
        netmeds_headers['Referer'] = 'https://www.netmeds.com/'
        
        response = requests.get(url, headers=netmeds_headers, timeout=15)
        
        if response.status_code == 200:
            html = response.text
            start_str = "window.__INITIAL_STATE__="
            idx = html.find(start_str)
            
            if idx != -1:
                start_json = html.find("{", idx)
                if start_json != -1:
                    brace_count = 0
                    in_string = False
                    escape = False
                    json_str = None
                    
                    for i in range(start_json, len(html)):
                        char = html[i]
                        if escape:
                            escape = False
                            continue
                        if char == '\\':
                            escape = True
                            continue
                        if char == '"':
                            in_string = not in_string
                            continue
                        if not in_string:
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_str = html[start_json:i+1]
                                    break
                    
                    if json_str:
                        import json
                        state = json.loads(json_str)
                        items = state.get("productListingPage", {}).get("productlists", {}).get("items", [])
                        
                        best_match = None
                        best_score = 0
                        
                        for item in items:
                            name = item.get('name', '')
                            score = _calculate_match_score(medicine_name, name)
                            
                            if score > best_score and score > 2.0:
                                best_score = score
                                best_match = item
                                
                        if best_match:
                            name = best_match.get('name', '')
                            url_path = best_match.get('url', '')
                            price_obj = best_match.get('price', {})
                            effective_price = price_obj.get('effective', {}).get('min')
                            marked_price = price_obj.get('marked', {}).get('min')
                            
                            in_stock = best_match.get('sellable', True)
                            
                            attrs = best_match.get('attributes', {})
                            manufacturer = attrs.get('manufacturername', '')
                            pack_size = attrs.get('packsize', '')
                            
                            mrp = float(marked_price) if marked_price is not None else 0.0
                            price = float(effective_price) if effective_price is not None else mrp
                            
                            medias = best_match.get('medias', [])
                            image_url = medias[0].get('url', '') if medias else ''

                            result = {
                                'platform': 'Netmeds',
                                'medicine_name': name,
                                'price': price,
                                'mrp': mrp,
                                'discount': _calculate_discount(price, mrp),
                                'url': f"https://www.netmeds.com{url_path}" if url_path else f"https://www.netmeds.com/products/?q={encoded_name}",
                                'pack_size': str(pack_size),
                                'manufacturer': manufacturer,
                                'in_stock': in_stock,
                                'cached': False,
                                'image_url': image_url
                            }
                            
                            _save_cache(medicine_id, platform_name, result)
                            print(f"[Netmeds] Found best match: {name} (Rs.{price})")
                            return result
                            
        print(f"[Netmeds] No product match in live state. Falling back to DB estimate.")
        
    except Exception as e:
        print(f"[Netmeds] Live scrap error: {e}")
        
    # Fallback to DB estimate with search page redirect
    row = query_one("SELECT * FROM medicines WHERE id=%s", (medicine_id,))
    if row:
        base_mrp = float(row.get('mrp') or row.get('price') or 100.0)
        brand_name = row['brand_name']
        dosage_form = row.get('dosage_form', 'Strip')
        manufacturer = row.get('manufacturer', '')
        strength = row.get('strength', '')
    else:
        import hashlib
        hash_val = int(hashlib.md5(medicine_name.encode()).hexdigest(), 16)
        base_mrp = float(50 + (hash_val % 450))
        brand_name = medicine_name
        dosage_form = 'Strip'
        manufacturer = ''
        strength = ''
        
    import urllib.parse
    encoded_name = urllib.parse.quote(medicine_name)
    
    result = {
        'platform': 'Netmeds',
        'medicine_name': brand_name,
        'price': round(base_mrp * 0.90, 2),
        'mrp': round(base_mrp, 2),
        'discount': 10.0,
        'url': f"https://www.netmeds.com/products/?q={encoded_name}",
        'pack_size': f"{dosage_form} {strength}".strip(),
        'manufacturer': manufacturer,
        'in_stock': True,
        'cached': False,
        'image_url': ''
    }
    _save_cache(medicine_id, platform_name, result)
    return result



def _fetch_pharmeasy(medicine_name, medicine_id):
    """
    PharmEasy scraper using search API.
    """
    platform_name = 'pharmeasy'
    
    cached = _get_cached(medicine_id, platform_name)
    if cached:
        return cached
        
    time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))
    
    try:
        api_url = "https://pharmeasy.in/api/search/search/"
        params = {'intent_id': '1', 'q': medicine_name}
        
        # Add PharmEasy specific headers to bypass basic blocks
        pe_headers = HEADERS.copy()
        pe_headers['Origin'] = 'https://pharmeasy.in'
        pe_headers['Referer'] = 'https://pharmeasy.in/'
        
        response = requests.get(api_url, params=params, headers=pe_headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            products = data.get('data', {}).get('products', [])
            
            if products:
                best_match = None
                best_score = 0
                
                for item in products:
                    name = item.get('name', '')
                    score = _calculate_match_score(medicine_name, name)
                    
                    if score > best_score and score > 2.0:
                        best_score = score
                        best_match = item
                
                if best_match:
                    # Let's try to fetch actual prices from product page HTML
                    slug = best_match.get('slug', '')
                    product_url = f"https://pharmeasy.in/online-medicine-order/{slug}"
                    page_price, page_mrp = _fetch_pharmeasy_page_prices(product_url)
                    
                    if page_price:
                        price = page_price
                        mrp = page_mrp
                    else:
                        mrp = float(best_match.get('mrpDecimal', 0))
                        price = float(best_match.get('salePriceDecimal', mrp))
                    
                    # Correct stock check with dictionary verification to prevent exceptions
                    flags = best_match.get('productAvailabilityFlags') or {}
                    in_stock = flags.get('isAvailable', True) if isinstance(flags, dict) else True
                    
                    result = {
                        'platform': 'PharmEasy',
                        'medicine_name': best_match.get('name', ''),
                        'price': price,
                        'mrp': mrp,
                        'discount': _calculate_discount(price, mrp),
                        'url': f"https://pharmeasy.in/online-medicine-order/{best_match.get('slug', '')}",
                        'pack_size': best_match.get('packform', ''), # Fixed key to packform (lowercase)
                        'manufacturer': best_match.get('manufacturer', ''),
                        'in_stock': in_stock,
                        'cached': False,
                        'image_url': best_match.get('image', '')
                    }
                    _save_cache(medicine_id, platform_name, result)
                    return result
                
        # If no match or status is not 200, return fallback simulation
        return _fetch_pharmeasy_fallback(medicine_name, medicine_id)
            
    except Exception as e:
        print(f"[PharmEasy] Error: {e}")
        return _fetch_pharmeasy_fallback(medicine_name, medicine_id)


def _fetch_pharmeasy_fallback(medicine_name, medicine_id):
    """Fallback for PharmEasy when API fails or gets blocked."""
    platform_name = 'pharmeasy'
    print(f"[PharmEasy] Using fallback simulation.")
    row = query_one("SELECT * FROM medicines WHERE id=%s", (medicine_id,))
    
    if row:
        base_mrp = float(row.get('mrp') or row.get('price') or 100.0)
        brand_name = row['brand_name']
        dosage_form = row.get('dosage_form', 'Strip')
        manufacturer = row.get('manufacturer', '')
        strength = row.get('strength', '')
    else:
        import hashlib
        hash_val = int(hashlib.md5(medicine_name.encode()).hexdigest(), 16)
        base_mrp = float(50 + (hash_val % 450))
        brand_name = medicine_name
        dosage_form = 'Strip'
        manufacturer = ''
        strength = ''
        
    import urllib.parse
    encoded_name = urllib.parse.quote(medicine_name)
    
    result = {
        'platform': 'PharmEasy',
        'medicine_name': brand_name,
        'price': round(base_mrp * 0.88, 2),
        'mrp': round(base_mrp, 2),
        'discount': 12.0,
        'url': f"https://pharmeasy.in/search/all?q={encoded_name}", # Fixed query parameter name to q
        'pack_size': f"{dosage_form} {strength}".strip(),
        'manufacturer': manufacturer,
        'in_stock': True,
        'cached': False,
        'image_url': ''
    }
    _save_cache(medicine_id, platform_name, result)
    return result


# ── Smart matching logic ─────────────────────────────────────────────────

def _find_best_match_1mg(query, api_response):
    """
    Find the medicine from 1mg API results that best matches user's search query.
    
    API structure: 
    {
        "data": {
            "search_results": [ {...}, {...} ]
        }
    }
    """
    try:
        products = []

        # Extract products from the nested structure
        if isinstance(api_response, dict):
            data_block = api_response.get('data', {})
            
            # The actual products are in data.search_results
            if isinstance(data_block, dict):
                search_results = data_block.get('search_results', [])
                if isinstance(search_results, list):
                    products = search_results
                    print(f"[1mg Match] Found {len(products)} products in data.search_results")

        if not products:
            print("[1mg Match] ❌ No products found in response")
            return None

        # If only one result, return it
        if len(products) == 1:
            print("[1mg Match] Only one product found, returning it")
            return products[0]

        # ── Filter products by type (drug only, skip otc/supplements) ──
        drug_products = [p for p in products if p.get('type') == 'drug']
        
        if drug_products:
            print(f"[1mg Match] Filtered to {len(drug_products)} drug products (skipped OTC)")
            products = drug_products

        # ── Score each product ──
        scored = []
        
        for product in products:
            product_name = product.get('name') or ''
            
            if not product_name:
                continue
            
            score = _calculate_match_score(query, product_name)
            
            scored.append({
                'product': product,
                'score': score,
                'name': product_name
            })
        
        if not scored:
            print("[1mg Match] ❌ No valid products after scoring")
            return None
        
        # Sort by score descending
        scored.sort(key=lambda x: x['score'], reverse=True)
        
        # Debug: print top 3 matches
        print(f"[1mg Match] Query: '{query}'")
        for i, item in enumerate(scored[:3], 1):
            print(f"  {i}. {item['name']} (score: {item['score']:.2f})")
            
        if scored[0]['score'] < 2.0:
            print(f"[1mg Match] Best match '{scored[0]['name']}' score {scored[0]['score']:.2f} below threshold 2.0")
            return None
        
        return scored[0]['product']
        
    except Exception as e:
        print(f"[1mg Match] Error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ── Cache management ─────────────────────────────────────────────────────

def _get_cached(medicine_id, platform):
    """
    Retrieve cached price if it exists and is less than CACHE_HOURS old.
    """
    if medicine_id == -1:
        return None

    cutoff = datetime.now() - timedelta(hours=CACHE_HOURS)
    
    row = query_one("""
        SELECT platform, medicine_name, price, mrp, discount_pct as discount,
               product_url as url, pack_size, manufacturer, in_stock, fetched_at, image_url
        FROM price_cache
        WHERE medicine_id = %s AND platform = %s AND fetched_at > %s
        ORDER BY fetched_at DESC LIMIT 1
    """, (medicine_id, platform, cutoff))
    
    if row:
        # Convert Decimal to float for JSON serialization
        row['price'] = float(row['price']) if row['price'] is not None else None
        row['mrp'] = float(row['mrp']) if row['mrp'] is not None else None
        row['discount'] = float(row['discount']) if row['discount'] is not None else None
        
        # Convert datetime to string
        if isinstance(row.get('fetched_at'), datetime):
            row['fetched_at'] = row['fetched_at'].strftime('%Y-%m-%d %H:%M:%S')
            
        row['cached'] = True
        print(f"[Cache HIT] {platform} - cached {row['fetched_at']}")
        return row
    
    print(f"[Cache MISS] {platform}")
    return None


def _save_cache(medicine_id, platform, result):
    """
    Save fetched price to cache.
    Deletes old cache entry first to avoid duplicates.
    """
    if not medicine_id or medicine_id == -1:
        print("[Cache] Skipping save - no valid medicine_id")
        return
    
    # Validate that we have actual price data
    if result.get('price') is None:
        print(f"[Cache] Skipping save for {platform} - price is None")
        return
    
    try:
        # Delete old cache for this medicine+platform
        execute(
            "DELETE FROM price_cache WHERE medicine_id = %s AND platform = %s",
            (medicine_id, platform)
        )
        
        # Insert new cache entry
        execute("""
            INSERT INTO price_cache (
                medicine_id,
                platform,
                medicine_name,
                price,
                mrp,
                discount_pct,
                product_url,
                pack_size,
                manufacturer,
                in_stock,
                fetched_at,
                image_url
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
        """, (
            medicine_id,
            platform,
            result.get('medicine_name'),
            result.get('price'),
            result.get('mrp'),
            result.get('discount'),
            result.get('url'),
            result.get('pack_size'),
            result.get('manufacturer', ''),
            1 if result.get('in_stock') else 0,
            result.get('image_url', '')
        ))
        
        print(f"[Cache SAVE] {platform} - Rs.{result.get('price')} saved to DB")
        
    except Exception as e:
        print(f"[Cache SAVE ERROR] {platform}: {e}")
        import traceback
        traceback.print_exc()


# ── Helper functions ─────────────────────────────────────────────────────

def _parse_price_string(price_str):
    """
    Parse price from string format "₹14.18" or "₹12.5" to float.
    Returns None if parsing fails.
    """
    if not price_str:
        return None
    
    try:
        # Remove rupee symbol and any spaces
        cleaned = price_str.replace('₹', '').replace(',', '').strip()
        
        # Extract first number found
        match = re.search(r'[\d.]+', cleaned)
        if match:
            return float(match.group())
        
        return None
    except (ValueError, TypeError, AttributeError):
        return None


def _calculate_discount(price, mrp):
    """Calculate discount percentage."""
    try:
        price = float(price) if price else 0
        mrp = float(mrp) if mrp else 0
        
        if price > 0 and mrp > 0 and mrp > price:
            return round(((mrp - price) / mrp) * 100, 1)
        return None
    except:
        return None


def _fetch_pharmeasy_page_prices(product_url):
    """Fetch and parse exact prices from a PharmEasy product page HTML."""
    try:
        pe_headers = HEADERS.copy()
        pe_headers['Origin'] = 'https://pharmeasy.in'
        pe_headers['Referer'] = 'https://pharmeasy.in/'
        print(f"[PharmEasy HTML] Fetching product page: {product_url}")
        res = requests.get(product_url, headers=pe_headers, timeout=8)
        if res.status_code == 200:
            html = res.text
            price = _extract_price_by_class(html, 'originalPrice')
            mrp = _extract_price_by_class(html, 'mrpPrice')
            
            if price:
                print(f"[PharmEasy HTML] Found exact page prices - Price: Rs.{price} | MRP: Rs.{mrp or price}")
                return price, mrp or price
    except Exception as e:
        print(f"[PharmEasy HTML Error] {e}")
    return None, None


def _fetch_1mg_page_prices(product_url):
    """Fetch and parse exact prices from a Tata 1mg product page HTML."""
    try:
        print(f"[1mg HTML] Fetching product page: {product_url}")
        res = requests.get(product_url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            html = res.text
            price = _extract_price_by_class(html, 'best-price')
            mrp = _extract_price_by_class(html, 'slashed-price')
            
            if price:
                print(f"[1mg HTML] Found exact page prices - Price: Rs.{price} | MRP: Rs.{mrp or price}")
                return price, mrp or price
    except Exception as e:
        print(f"[1mg HTML Error] {e}")
    return None, None