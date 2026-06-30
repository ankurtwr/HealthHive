from flask_login import UserMixin
from db import query_one, execute
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin):
    """
    Flask-Login requires: is_authenticated, is_active, is_anonymous, get_id()
    UserMixin provides all four — we just need to store the user data.
    """
    def __init__(self, id, username, email, password_hash, **kwargs):
        self.id            = id
        self.username      = username
        self.email         = email
        self.password_hash = password_hash
        self.accepted_terms = kwargs.get('accepted_terms', 0)
        self.accepted_terms_at = kwargs.get('accepted_terms_at')
        self.is_guest      = kwargs.get('is_guest', 0)

    def accept_terms(self):
        execute("UPDATE users SET accepted_terms = 1, accepted_terms_at = NOW() WHERE id = %s", (self.id,))
        self.accepted_terms = 1
        

   

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

    @classmethod
    def create_guest(cls):
        """Create a temporary guest user with random credentials."""
        import uuid
        guest_id = uuid.uuid4().hex[:8]
        username = f"guest_{guest_id}"
        email = f"{username}@guest.healthhive.local"
        hashed = generate_password_hash(uuid.uuid4().hex)
        
        user_id = execute(
            "INSERT INTO users (username, email, password_hash, is_guest, accepted_terms) VALUES (%s, %s, %s, 1, 1)",
            (username, email, hashed)
        )
        return cls(user_id, username, email, hashed, is_guest=1, accepted_terms=1)

    @classmethod
    def cleanup_guest(cls, user_id):
        """Remove all guest user data permanently."""
        # Delete reports
        execute("DELETE FROM user_reports WHERE user_id = %s", (user_id,))
        # Delete prescriptions
        execute("DELETE FROM user_prescriptions WHERE user_id = %s", (user_id,))
        # Delete saved medicines
        execute("DELETE FROM user_medicines WHERE user_id = %s", (user_id,))
        # Delete reminders
        execute("DELETE FROM medicine_reminders WHERE user_id = %s", (user_id,))
        # Delete search history
        execute("DELETE FROM search_history WHERE user_id = %s", (user_id,))
        # Delete the user record itself
        execute("DELETE FROM users WHERE id = %s AND is_guest = 1", (user_id,))

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)