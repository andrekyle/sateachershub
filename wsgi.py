"""
WSGI entry point for Vercel deployment
"""
from app import app

# Vercel requires the Flask app to be named 'app'
# This is the entry point for serverless functions

if __name__ == "__main__":
    app.run()
