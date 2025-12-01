import os
import click
from harithmapos import create_app, db, bcrypt
from harithmapos.models import User

app = create_app()

@app.cli.command("create-user")
@click.option('--name', prompt='Name', help='The name of the user.')
@click.option('--email', prompt='Email', help='The email of the user.')
@click.option('--password', prompt='Password', hide_input=True, confirmation_prompt=True, help='The password of the user.')
def create_user(name, email, password):
    """Create a new user."""
    try:
        from utils.database import safe_insert_with_sequence_check
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = safe_insert_with_sequence_check(
            User,
            name=name,
            email=email,
            password=hashed_password
        )
        print(f"User {name} created successfully!")
    except Exception as e:
        print(f"Error creating user: {e}")

if __name__ == "__main__":
    # Only run in debug mode if explicitly set via environment variable
    # In production, use gunicorn: gunicorn --config gunicorn_config.py app:app
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='127.0.0.1', port=5000)