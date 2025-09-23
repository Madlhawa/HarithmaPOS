import os
from flask_login import login_user, logout_user, login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash

from harithmapos import db, bcrypt
from harithmapos.models import User
from harithmapos.views.user.utils import save_image, send_reset_email
from harithmapos.views.user.forms import UserRegisterForm, UserLoginForm, UserUpdateForm, RequestPasswordResetFrom, ResetPasswordForm

user_blueprint = Blueprint('user_blueprint', __name__)

@user_blueprint.route("/app/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_blueprint.customer'))
    form = UserRegisterForm()
    if form.validate_on_submit():
        try:
            from utils.database import safe_insert_with_sequence_check
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = safe_insert_with_sequence_check(
                User,
                name=form.name.data, 
                email=form.email.data,
                password=hashed_password
            )
            flash(f'Account has been created. Please login.',category='success')
            return redirect(url_for('user_blueprint.login'))
        except Exception as e:
            flash(f'Account creation failed: {str(e)}', category='danger')
            return redirect(url_for('user_blueprint.login'))
    return redirect(url_for('user_blueprint.login'))
    # return render_template('user/register.html', title='Register', form = form)

@user_blueprint.route("/app", methods=['GET', 'POST'])
@user_blueprint.route("/app/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_blueprint.dashboard'))
    form = UserLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard_blueprint.dashboard'))
        else:
            flash(f'Login unsuccessfull. Please check email and password.', category='danger')
    return render_template('user/login.html', title='Login', form = form)

@user_blueprint.route("/app/account", methods=['GET', 'POST'])
@login_required
def account():
    form=UserUpdateForm()
    if form.validate_on_submit():
        if form.image.data:
            if current_user.image != 'default.jpg':
                try:
                    os.remove(os.path.join('harithmapos','static', 'images', 'user_images', current_user.image))
                except:
                    pass
            image = save_image(form.image.data)
            current_user.image = image
        current_user.email = form.email.data
        current_user.name = form.name.data
        current_user.ui_theme = form.ui_theme.data
        db.session.commit()
        flash('Account has been updated.',category='success')
        return redirect(url_for('user_blueprint.account'))
    elif request.method == 'GET':
        form.name.data = current_user.name
        form.email.data = current_user.email
        form.ui_theme.data = current_user.ui_theme
    image_path = url_for('static', filename=f'images/user_images/{current_user.image}')
    print(f'{image_path = }')
    return render_template('user/account.html', title='Account', user_image_file=image_path, form=form)

@user_blueprint.route("/app/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('customer_blueprint.customer'))
    form = RequestPasswordResetFrom()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('Email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('user_blueprint.login'))
    return render_template('user/reset_request.html', title='Password Reset', form = form)

@user_blueprint.route("/app/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('customer_blueprint.customer'))
    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or expired token.', category='warning')
        return redirect(url_for('user_blueprint.reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash(f'Account password has been updated. Please login.',category='success')
        return redirect(url_for('user_blueprint.login'))
    return render_template('user/reset_token.html', title='Password Reset', form = form)

@user_blueprint.route("/app/logout", methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('user_blueprint.login'))