import io
import os
import re
import tempfile
from PIL import Image
from flask import Blueprint, request, jsonify
from google import genai
from db import query_all

# Cross-platform Tesseract path:
# On Linux EC2: set TESSERACT_CMD=/usr/bin/tesseract in .env
# On Windows locally: set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe in .env
import pytesseract
tesseract_cmd = os.getenv("TESSERACT_CMD", "/usr/bin/tesseract")
pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

image_search_bp = Blueprint('image_search', __name__, url_prefix='/api/image_search')

def find_matching_medicine_from_text(ocr_text):
    if not ocr_text:
        return "Unknown"
    
    ocr_lower = ocr_text.lower()
    
    # Query all medicine brand names and salts from database
    medicines = query_all("SELECT id, brand_name, salt_composition FROM medicines")
    
    best_match = None
    best_score = 0
    
    # 1. Match Brand Name
    for med in medicines:
        brand = med['brand_name'].lower()
        # Extract the brand name word (e.g. "dolo" from "dolo 650")
        brand_words = brand.split()
        brand_base = brand_words[0] if brand_words else brand
        
        # If the base brand name word is in the OCR text
        if brand_base in ocr_lower:
            score = 100
            # If the strength/other words (e.g. "650" or "500") are also in the OCR text, increase score
            for word in brand_words[1:]:
                if word in ocr_lower:
                    score += 50
            
            if score > best_score:
                best_score = score
                best_match = med
                
    if best_match:
        return best_match['brand_name']
        
    # 2. Match Salt Composition
    for med in medicines:
        salt = med['salt_composition'].lower()
        # Split salt into clean alphanumeric words longer than 3 chars
        salt_words = [w for w in re.split(r'[^a-zA-Z0-9]', salt) if len(w) > 3]
        
        matched_words = 0
        for word in salt_words:
            if word in ocr_lower:
                matched_words += 1
                
        if matched_words > 0:
            score = matched_words * 30
            if score > best_score:
                best_score = score
                best_match = med
                
    if best_match:
        return best_match['brand_name']
        
    # 3. Fallback to extracting the longest/most relevant alphanumeric word
    words = re.findall(r'[a-zA-Z]{4,}', ocr_text)
    ignore_words = {
        'tablet', 'tablets', 'capsule', 'capsules', 'batch', 'manufactured', 
        'expiry', 'date', 'price', 'mfg', 'exp', 'mg', 'ml', 'ip', 'bp', 'usp', 
        'composition', 'dosage', 'keep', 'reach', 'children', 'prescription'
    }
    filtered_words = [w for w in words if w.lower() not in ignore_words]
    
    if filtered_words:
        return filtered_words[0].title()
        
    return "Unknown"

@image_search_bp.route('/', methods=['POST'])
def search_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        try:
            # Check for API key
            api_key = os.getenv("GEMINI_API_KEY")
            
            if api_key:
                # Use Gemini API
                print("[Image Search] Using Gemini API for recognition...")
                in_memory_file = file.read()
                img = Image.open(io.BytesIO(in_memory_file))
                
                client = genai.Client(api_key=api_key)
                prompt = "Extract the primary medicine brand name visible in this image. Output ONLY the name of the medicine, nothing else. If you cannot read it or it is not a medicine, output exactly 'Unknown'."
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[img, prompt]
                )
                
                extracted_text = response.text.strip()
                if "Unknown" in extracted_text or not extracted_text:
                    return jsonify({
                        'success': False,
                        'message': 'Could not confidently match a medicine name from the image.'
                    })
                
                matched_medicine = find_matching_medicine_from_text(extracted_text)
                return jsonify({
                    'success': True,
                    'extracted_text': extracted_text,
                    'matched_medicine': matched_medicine
                })
            
            else:
                # Fallback: use pytesseract (cross-platform — works on Linux EC2 and Windows)
                print(f"[Image Search] No GEMINI_API_KEY found. Using pytesseract OCR (cmd: {tesseract_cmd})...")
                
                file.seek(0)
                img = Image.open(io.BytesIO(file.read()))
                
                # Run Tesseract OCR
                extracted_text = pytesseract.image_to_string(img).strip()
                
                if not extracted_text:
                    return jsonify({
                        'success': False,
                        'message': 'Could not extract any text from the image.'
                    })
                
                print(f"[Image Search] OCR Extracted: {extracted_text}")
                matched_medicine = find_matching_medicine_from_text(extracted_text)
                print(f"[Image Search] Matched Medicine: {matched_medicine}")
                
                if matched_medicine == "Unknown":
                    return jsonify({
                        'success': False,
                        'message': f"OCR read: '{extracted_text}', but it doesn't match any medicine."
                    })
                
                return jsonify({
                    'success': True,
                    'extracted_text': extracted_text,
                    'matched_medicine': matched_medicine
                })
                
        except Exception as e:
            print(f"[Image Search] Error: {e}")
            return jsonify({'error': str(e)}), 500
