from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from config import Config
from models import User


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

    app.register_blueprint(auth_bp)    
    app.register_blueprint(main_bp)   
    app.register_blueprint(search_bp)  # /search    /autocomplete
    app.register_blueprint(prices_bp)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)