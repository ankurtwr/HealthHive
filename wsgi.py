"""
wsgi.py — Gunicorn entry point for HealthHive.

Usage:
    gunicorn --workers 2 --bind unix:healthhive.sock -m 007 wsgi:app

The app.py uses the Flask application factory pattern (create_app()),
so Gunicorn cannot import 'app:app' directly — it must import from here.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
