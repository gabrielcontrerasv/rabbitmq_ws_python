import pika
import os
from pymongo import MongoClient

def create_and_consume_queue(client_id):
    rabbitmq_conn_str = os.getenv('RABBITMQ_CONNECTION_STRING', 'amqp://guest:guest@localhost:5672/')
    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_conn_str))
    channel = connection.channel()

    queue_name = f'location_updates_{client_id}'
    channel.queue_declare(queue=queue_name, durable=True)
    print(f"Queue '{queue_name}' created and subscribed.")

    mongodb_conn_str = os.getenv('MONGODB_CONNECTION_STRING', 'mongodb://localhost:27017/')
    client = MongoClient(mongodb_conn_str)
    db = client['location_db']
    collection = db['locations']

    def callback(ch, method, properties, body):
        message = body.decode('utf-8')
        if message == 'locations':
            last_location = collection.find_one({'ClientId': client_id}, sort=[('timestamp', -1)])
            if last_location:
                print(last_location)
            else:
                print(f"No locations found for {client_id}")
        else:
            print(f"Message received in {queue_name}: {message}")

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
    print(f"Waiting for messages in queue '{queue_name}'...")
    channel.start_consuming()

#client_id = '665e1ba99b644c691227e15b'
#create_and_consume_queue(client_id)
