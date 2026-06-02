"""
WSGI entry point — Gunicorn imports this file directly.
Sits at the project root so all imports resolve correctly.
"""
import sys
import os

# Ensure project root is always on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web.app import app

if __name__ == "__main__":
    app.run()
