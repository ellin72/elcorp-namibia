"""
WSGI application entry point for Flask.
Used by production application servers (Gunicorn, uWSGI, etc.)
"""

import os
import sys

# Add backend source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend", "src"))

from elcorp.config import create_app

# Create Flask application
app = create_app(config_name=os.getenv("FLASK_ENV", "development"))


# Add health check endpoint
@app.route("/api/v1/health", methods=["GET"])
def health():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "environment": os.getenv("FLASK_ENV", "development")
    }, 200


if __name__ == "__main__":
    # Only for local debugging
    app.run(debug=True, host="0.0.0.0", port=5000)
