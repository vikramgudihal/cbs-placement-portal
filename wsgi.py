"""
WSGI Entrypoint for Production Deployment
Usage with Waitress (Windows/Linux):
    python waitress_server.py
Usage with Gunicorn (Linux):
    gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
"""
import os
from app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(host=host, port=port)
