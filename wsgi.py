from app import create_app

app = create_app()

if __name__ == "__main__":
    # Only for local debugging
    app.run(debug=True)
# This file is used to run the application with a WSGI server.
# In production, you would typically use a WSGI server like Gunicorn or uWSGI
