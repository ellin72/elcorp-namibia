"""
Application entry point - main.py for running Flask app.
"""

import os
import sys
from src.elcorp.config import create_app

# Create Flask app
app = create_app(config_name=os.getenv("FLASK_ENV", "development"))


@app.shell_context_processor
def make_shell_context():
    """Add context for flask shell."""
    from src.elcorp.config import db
    return {"db": db}


if __name__ == "__main__":
    # Run development server
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=os.getenv("FLASK_ENV") == "development",
    )
