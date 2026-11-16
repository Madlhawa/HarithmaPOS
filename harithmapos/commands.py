"""Command-line tasks: flask <command>."""
import click
from flask.cli import with_appcontext

from harithmapos import bcrypt, config, db


@click.command("create-user")
@click.option('--name', prompt='Name', help='The name of the user.')
@click.option('--email', prompt='Email', help='The email of the user.')
@click.option('--password', prompt='Password', hide_input=True, confirmation_prompt=True, help='The password of the user.')
@click.option('--role', type=click.Choice([config.ROLE_OWNER, config.ROLE_STAFF]), default=config.ROLE_OWNER,
              show_default=True, help='owner can do everything; staff runs the counter.')
@with_appcontext
def create_user(name, email, password, role):
    """Create a user (the first owner of a new install)."""
    from harithmapos.models import User
    if User.query.filter_by(email=email).first():
        raise click.ClickException(f"A user with the email {email} already exists.")
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    db.session.add(User(name=name, email=email, password=hashed_password, role=role))
    db.session.commit()
    click.echo(f"{name} can now sign in as {role}.")


def register_commands(app):
    app.cli.add_command(create_user)
