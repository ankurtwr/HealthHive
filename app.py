from flask import Flask
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

    app.register_blueprint(auth_bp)    
    app.register_blueprint(main_bp)   
    app.register_blueprint(search_bp)  # /search    /autocomplete
    app.register_blueprint(prices_bp)
    
    # Exclude API routes from CSRF if needed, but since they might be called from JS
    # We can either pass the CSRF token in headers or exempt them. 
    # For now we'll exempt chatbot and image_search to ensure they work smoothly.
    csrf.exempt(chatbot_bp)
    csrf.exempt(image_search_bp)
    
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(image_search_bp)

    from flask import request, redirect, url_for
    from flask_login import current_user

    @app.before_request
    def check_terms_acceptance():
        if current_user and current_user.is_authenticated:
            if not getattr(current_user, 'accepted_terms', 0):
                if request.endpoint not in ['main.terms', 'auth.logout', 'static']:
                    return redirect(url_for('main.terms'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)