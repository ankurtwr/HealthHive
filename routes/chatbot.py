import os
from flask import Blueprint, request, jsonify
from google import genai
from db import query_all

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/api/chat')

@chatbot_bp.route('/', methods=['POST'])
def chat():
    data = request.json
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400
        
    user_message = data['message']
    
    # Check for API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No GEMINI_API_KEY found, using fallback chatbot.")
        return jsonify({
            'success': True,
            'response': "I am running in offline mode because no API key was provided. I can still help you! Try searching for medicines using the main search bar."
        })
    
    try:
        # Fetch a few generic medicines to provide as context
        generics = query_all("SELECT generic_name, salt_composition, mrp FROM generics LIMIT 15")
        context = "Available affordable generics in our database (partial list):\n"
        for g in generics:
            context += f"- {g['generic_name']} (Salt: {g['salt_composition']}, MRP: ₹{g['mrp']})\n"
            
        client = genai.Client(api_key=api_key)
        
        system_instruction = (
            "You are HealthHive's expert AI pharmacist and assistant. "
            "Your goal is to help users understand their medicines, provide affordable generic alternatives, "
            "explain uses, and list potential side-effects concisely and accurately. "
            "Always maintain a polite, professional, and empathetic tone. "
            "Use the provided context to recommend affordable generic options if they match the user's query. "
            f"Context: {context}"
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"System: {system_instruction}\n\nUser: {user_message}"
        )
        
        return jsonify({
            'success': True,
            'response': response.text
        })
        
    except Exception as e:
        print(f"Chatbot API Error: {e}")
        return jsonify({
            'success': False,
            'response': "I am having trouble connecting to the AI brain right now. Please try again later."
        })
