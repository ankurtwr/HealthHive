from flask_login import UserMixin
from db import query_one, execute
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin):
    """
    Flask-Login requires: is_authenticated, is_active, is_anonymous, get_id()
    UserMixin provides all four — we just need to store the user data.
    """
    def __init__(self, id, username, email, password_hash,**kwargs):
        self.id            = id
        self.username      = username
        self.email         = email
        self.password_hash = password_hash
        

   

    @classmethod
    def get_by_id(cls, user_id):
        row = query_one("SELECT * FROM users WHERE id = %s", (user_id,))
        return cls(**row) if row else None

    @classmethod
    def get_by_email(cls, email):
        row = query_one("SELECT * FROM users WHERE email = %s", (email,))
        return cls(**row) if row else None

    @classmethod
    def get_by_username(cls, username):
        row = query_one("SELECT * FROM users WHERE username = %s", (username,))
        return cls(**row) if row else None

    @classmethod
    def create(cls, username, email, password):
        hashed = generate_password_hash(password)
        user_id = execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, hashed)
        )
        return cls(user_id, username, email, hashed)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)