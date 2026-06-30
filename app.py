from flask import Flask, session
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from dotenv import load_dotenv
from config import Config
from models import User

load_dotenv()


csrf = CSRFProtect()
login = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    csrf.init_app(app)     
    login.init_app(app)

   
    login.login_view         = 'auth.login'
    login.login_message      = 'Please log in to access this page.'
    login.login_message_category = 'warning'

   
    @login.user_loader
    def load_user(user_id):
        return User.get_by_id(int(user_id))

 
    from routes.auth   import auth_bp
    from routes.main   import main_bp
    from routes.search import search_bp
    from routes.prices import prices_bp
    from routes.chatbot import chatbot_bp
    from routes.image_search import image_search_bp
    from routes.report_explainer import report_bp
    from routes.whatsapp_bot import whatsapp_bp

    app.register_blueprint(auth_bp)    
    app.register_blueprint(main_bp)   
    app.register_blueprint(search_bp)  # /search    /autocomplete
    app.register_blueprint(prices_bp)
    
    # Exclude API routes from CSRF since they're called via AJAX or external webhooks
    csrf.exempt(chatbot_bp)
    csrf.exempt(image_search_bp)
    csrf.exempt(report_bp)
    csrf.exempt(whatsapp_bp)
    
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(image_search_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(whatsapp_bp)

    from flask import request, redirect, url_for
    from flask_login import current_user

    @app.before_request
    def check_terms_and_guest_session():
        if current_user and current_user.is_authenticated:
            # Guest sessions: ensure cookie expires when browser closes
            if getattr(current_user, 'is_guest', False):
                session.permanent = False  # Session cookie dies on browser/tab close
                return None
            # Regular users: check terms acceptance
            if not getattr(current_user, 'accepted_terms', 0):
                if request.endpoint not in ['main.terms', 'auth.logout', 'static']:
                    return redirect(url_for('main.terms'))

    # Inject guest status into all templates
    @app.context_processor
    def inject_guest_status():
        is_guest = False
        if current_user and current_user.is_authenticated:
            is_guest = bool(getattr(current_user, 'is_guest', False))
        return dict(is_guest=is_guest)

    # Start Offline Medication Reminders Daemon
    start_reminder_daemon(app)

    return app


def start_reminder_daemon(app):
    import time
    import threading
    from datetime import datetime
    from db import query_all
    from routes.whatsapp_bot import send_whatsapp_message

    def run_loop():
        # Let the webserver start up first
        time.sleep(5)
        
        # Track already sent reminder keys for the current minute to avoid double fires
        last_checked_minute = ""
        
        while True:
            try:
                from datetime import timezone, timedelta
                ist_tz = timezone(timedelta(hours=5, minutes=30))
                now_ist = datetime.now(ist_tz)
                current_min_str = now_ist.strftime("%H:%M")
                
                # Run database queries inside Flask app context
                if current_min_str != last_checked_minute:
                    with app.app_context():
                        due_reminders = query_all("""
                            SELECT r.*, u.phone_number FROM medicine_reminders r
                            JOIN users u ON r.user_id = u.id
                            WHERE r.reminder_time = %s AND u.phone_number IS NOT NULL
                        """, (current_min_str,))
                        
                        for r in due_reminders:
                            phone = r['phone_number'].strip()
                            if not phone.startswith('whatsapp:'):
                                phone = f"whatsapp:{phone}"
                                
                            msg = (
                                f"⏰ *HealthHive Medication Reminder*\n\n"
                                f"💊 *Medicine:* {r['medicine_name']}\n"
                                f"🥄 *Dosage:* {r['dosage'] or 'N/A'}\n"
                            )
                            if r['instructions']:
                                msg += f"📝 *Note:* {r['instructions']}\n"
                            
                            msg += "\nStay healthy and take your dose on time! ⚕️"
                            
                            # Send WhatsApp message via Twilio client
                            send_whatsapp_message(phone, msg)
                            app.logger.info(f"Medication reminder sent to {phone} for {r['medicine_name']}")
                            
                    last_checked_minute = current_min_str
                    
            except Exception as e:
                # Catch all errors to prevent the daemon thread from dying
                app.logger.error(f"Error in medication reminder daemon: {e}")
                
            time.sleep(10)

    t = threading.Thread(target=run_loop, daemon=True)
    t.start()


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)