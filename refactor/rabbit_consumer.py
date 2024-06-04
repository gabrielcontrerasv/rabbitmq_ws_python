import pika
import os
import requests
from pymongo import MongoClient
from bson.json_util import dumps

# Configuración de MongoDB
mongodb_conn_str = os.getenv('MONGODB_CONNECTION_STRING', 'mongodb://localhost:27017/')
mongo_client = MongoClient(mongodb_conn_str)
db = mongo_client['location_db']
locations_collection = db['locations']

def create_and_consume_queue(client_id):
    rabbitmq_conn_str = os.getenv('RABBITMQ_CONNECTION_STRING', 'amqp://guest:guest@localhost:5672/')
    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_conn_str))
    channel = connection.channel()

    queue_name = f'location_updates_{client_id}'
    channel.queue_declare(queue=queue_name, durable=True)
    print(f"Queue '{queue_name}' created and subscribed.")

    def callback(ch, method, properties, body):
        message = body.decode('utf-8')
        if message == 'locations':
            last_location = locations_collection.find_one({'ClientId': client_id}, sort=[('timestamp', -1)])
            if last_location:
                send_update_to_websockets(client_id, last_location)
            else:
                print(f"No locations found for {client_id}")
        else:
            print(f"Message received in {queue_name}: {message}")

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
    print(f"Waiting for messages in queue '{queue_name}'...")
    channel.start_consuming()

def send_update_to_websockets(client_id, last_location):
    websocket_server_url = os.getenv('WEBSOCKET_SERVER_URL', 'http://localhost:8000/update')
    data = {
        'client_id': client_id,
        'location': dumps(last_location)
    }
    response = requests.post(websocket_server_url, json=data)
    if response.status_code == 200:
        print(f"Update sent to WebSocket server for client {client_id}")
    else:
        print(f"Failed to send update for client {client_id}, status code: {response.status_code}")

if __name__ == "__main__":
    import sys
    client_id = sys.argv[1]  
    create_and_consume_queue(client_id)
