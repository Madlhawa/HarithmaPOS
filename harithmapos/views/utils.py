import json
import pika
import requests
from decimal import Decimal
import harithmapos.config as config

from flask import url_for, current_app
from flask_mail import Message

import os
import secrets
from PIL import Image

from harithmapos import mail

def get_id(id_name_string):
    return int(id_name_string.split('|')[0].strip())

def send_print_invoice(message, queue):
    # pass
    credentials = pika.PlainCredentials(config.RABBIT_MQ_USERNAME, config.RABBIT_MQ_PASSWORD)
    parameters = pika.ConnectionParameters(host=config.RABBIT_MQ_HOST, credentials=credentials)
    connection = pika.BlockingConnection(parameters)

    channel = connection.channel()

    channel.queue_declare(queue=queue)

    channel.basic_publish(exchange='', routing_key=queue, body=message)
    connection.close()

# Define a custom JSON encoder that handles Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)
    
def send_sms(recipient, message):
    # pass
    # Prepare the payload
    payload = {
        "user_id": config.NOTIFYLK_USER_ID,
        "api_key": config.NOTIFYLK_API_KEY,
        "sender_id": config.NOTIFYLK_SENDER_ID,
        "to": f"94{recipient}",
        "message": message
    }

    # Send the GET request
    response = requests.get(config.NOTIFYLK_API_URL, params=payload)

    # Check the response
    if response.status_code == 200:
        print("Response:", response.json())
    else:
        print(f"Failed to send SMS. HTTP Status Code: {response.status_code}")
        print("Response:", response.text)

def save_image(form_image):
    random_hex = secrets.token_hex(8)
    _, file_extention = os.path.splitext(form_image.filename)
    image_file_name = random_hex + file_extention
    image_path = os.path.join(current_app.root_path, 'static/images/user_images', image_file_name)

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