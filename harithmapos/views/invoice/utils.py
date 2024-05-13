import pika
import harithmapos.config as config

def get_id(id_name_string):
    return int(id_name_string.split('|')[0].strip())

def send_print_invoice(invoice_id, queue):
    credentials = pika.PlainCredentials(config.RABBIT_MQ_USERNAME, config.RABBIT_MQ_PASSWORD)
    parameters = pika.ConnectionParameters(host=config.RABBIT_MQ_HOST, credentials=credentials)
    connection = pika.BlockingConnection(parameters)

    channel = connection.channel()

    channel.queue_declare(queue=queue)

    channel.basic_publish(exchange='', routing_key=queue, body=invoice_id)
    connection.close()