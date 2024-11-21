import json
import pika
import requests
from decimal import Decimal
import harithmapos.config as config

def get_id(id_name_string):
    return int(id_name_string.split('|')[0].strip())

def send_print_invoice(message, queue):
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