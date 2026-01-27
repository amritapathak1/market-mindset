"""
WSGI entry point for production deployment.
This file is used by Gunicorn and other WSGI servers.
"""

from app import app

# Expose the Flask server for WSGI
application = app.server

if __name__ == "__main__":
    application.run()
