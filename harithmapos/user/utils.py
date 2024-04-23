
from flask import url_for, current_app
from flask_mail import Message

import os
import secrets
from PIL import Image

from harithmapos import mail


def save_image(form_image):
    random_hex = secrets.token_hex(8)
    _, file_extention = os.path.splitext(form_image.filename)
    image_file_name = random_hex + file_extention
    image_path = os.path.join(current_app.root_path, 'static/user_images', image_file_name)

    output_size = (125,125)
    i = Image.open(form_image)
    i.thumbnail(output_size)
    i.save(image_path)

    return image_file_name

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',sender=current_app.config['MAIL_USERNAME'],recipients=[user.email])
    msg.body = f'''To reset your password please visit:
{url_for('user_blueprint.reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email.
'''
    mail.send(msg)