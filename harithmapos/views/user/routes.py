import logging
import os

from flask_login import login_user, logout_user, login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort

from harithmapos import db, bcrypt, config
from harithmapos.models import User
from harithmapos.activity import record_login
from harithmapos.timeutils import utcnow
from harithmapos.views.utils import save_image, send_reset_email, is_safe_redirect_target
from harithmapos.views.user.forms import (
    UserRegisterForm, UserLoginForm, UserUpdateForm, RequestPasswordResetFrom, ResetPasswordForm,
    UserAdminForm,
)
from harithmapos.permissions import owner_required

from utils.database import safe_insert_with_sequence_check

logger = logging.getLogger(__name__)

user_blueprint = Blueprint('user_blueprint', __name__)


@user_blueprint.route("/app/register", methods=['GET', 'POST'])
@owner_required
def register():
    """Add another user. Only an owner can do this."""
    form = UserRegisterForm()
    if form.validate_on_submit():
        try:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            safe_insert_with_sequence_check(
                User,
                name=form.name.data,
                email=form.email.data,
                password=hashed_password,
                role=form.role.data,
            )
            flash(f"{form.name.data} can now sign in.", category='success')
            return redirect(url_for('user_blueprint.users'))
        except Exception:
            logger.exception("Could not create user")
            flash("The user could not be created. Please try again.", category='danger')
    return render_template('user/register.html', title='Add user', form=form)


@user_blueprint.route("/app", methods=['GET', 'POST'])
@user_blueprint.route("/app/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_blueprint.dashboard'))
    form = UserLoginForm()
    if form.validate_on_submit():
        typed_email = form.email.data.strip()
        user = User.query.filter_by(email=typed_email).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            if not user.is_active:
                record_login('switched_off', user)
                flash('This account has been switched off. Ask an owner to switch it back on.', category='warning')
                return render_template('user/login.html', title='Sign in', form=form)
            login_user(user, remember=form.remember.data)
            record_login('ok', user)
            next_page = request.args.get('next')
            if is_safe_redirect_target(next_page):
                return redirect(next_page)
            return redirect(url_for('dashboard_blueprint.dashboard'))
        record_login('bad_password' if user else 'unknown_email', user, email=typed_email)
        flash('That email and password do not match. Please try again.', category='danger')
    return render_template('user/login.html', title='Sign in', form=form)


@user_blueprint.route("/app/users", methods=['GET'])
@owner_required
def users():
    all_users = User.query.order_by(User.active.desc(), User.name).all()
    return render_template('user/users.html', title='Users', users=all_users)


def _other_active_owners(user):
    return User.query.filter(
        User.role == config.ROLE_OWNER, User.active.is_(True), User.id != user.id).count()


@user_blueprint.route("/app/users/<int:user_id>", methods=['GET', 'POST'])
@owner_required
def update_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    form = UserAdminForm(user)
    if form.validate_on_submit():
        stays_owner = form.role.data == config.ROLE_OWNER and form.active.data
        if user.is_owner and user.is_active and not stays_owner and not _other_active_owners(user):
            flash("There must always be at least one owner who can sign in. "
                  "Make someone else an owner first.", category='warning')
        elif user.id == current_user.id and not form.active.data:
            flash("You cannot switch off your own account.", category='warning')
        else:
            user.name = form.name.data
            user.email = form.email.data
            user.role = form.role.data
            user.active = form.active.data
            if form.password.data:
                user.password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user.update_dttm = utcnow()
            db.session.commit()
            flash(f"{user.name} saved.", category='success')
            if not current_user.is_owner:
                # They just made themselves counter staff, so the Users page is closed to them now.
                return redirect(url_for('dashboard_blueprint.dashboard'))
            return redirect(url_for('user_blueprint.users'))
    elif request.method == 'GET':
        form.name.data = user.name
        form.email.data = user.email
        form.role.data = user.role
        form.active.data = user.active
    return render_template('user/update.html', title=f"User: {user.name}", form=form, user=user)


@user_blueprint.route("/app/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UserUpdateForm()
    if form.validate_on_submit():
        if form.image.data:
            old_image = current_user.image
            current_user.image = save_image(form.image.data)
            if old_image and old_image != 'default.jpg':
                try:
                    os.remove(os.path.join(current_app.root_path, 'static', 'images', 'user_images', old_image))
                except OSError:
                    pass
        current_user.email = form.email.data
        current_user.name = form.name.data
        current_user.ui_theme = form.ui_theme.data
        current_user.update_dttm = utcnow()
        db.session.commit()
        flash('Account saved.', category='success')
        return redirect(url_for('user_blueprint.account'))
    elif request.method == 'GET':
        form.name.data = current_user.name
        form.email.data = current_user.email
        form.ui_theme.data = current_user.ui_theme
    image_path = url_for('static', filename=f'images/user_images/{current_user.image}')
    return render_template('user/account.html', title='Account', user_image_file=image_path, form=form)


@user_blueprint.route("/app/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_blueprint.dashboard'))
    form = RequestPasswordResetFrom()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip()).first()
        if user:
            try:
                send_reset_email(user)
            except Exception:
                logger.exception("Could not send password reset email")
        # Same answer whether or not the address exists, so the form
        # cannot be used to find out who has an account.
        flash('If that email belongs to an account, a reset link is on its way. It works for 30 minutes.',
              category='info')
        return redirect(url_for('user_blueprint.login'))
    return render_template('user/reset_request.html', title='Reset password', form=form)


@user_blueprint.route("/app/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_blueprint.dashboard'))
    user = User.verify_reset_token(token)
    if not user:
        flash('That reset link is invalid or has expired. Request a new one.', category='warning')
        return redirect(url_for('user_blueprint.reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        user.update_dttm = utcnow()
        db.session.commit()
        flash('Password changed. Sign in with the new one.', category='success')
        return redirect(url_for('user_blueprint.login'))
    return render_template('user/reset_token.html', title='Set a new password', form=form)


@user_blueprint.route("/app/logout", methods=['GET', 'POST'])
@login_required
def logout():
    record_login('logout', current_user._get_current_object())
    logout_user()
    return redirect(url_for('user_blueprint.login'))
