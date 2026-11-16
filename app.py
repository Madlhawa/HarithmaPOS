import os

from harithmapos import create_app

app = create_app()


if __name__ == "__main__":
    # Only run in debug mode if explicitly set via environment variable
    # In production, use gunicorn: gunicorn --config gunicorn_config.py app:app
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='127.0.0.1', port=5000)