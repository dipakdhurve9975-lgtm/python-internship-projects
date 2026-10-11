"""Hosted demo entry point. Use exactly one Gunicorn worker for shared rooms."""
from app import create_app

app, socketio = create_app()
