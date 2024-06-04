import asyncio
import websockets
import pika
import os
from urllib.parse import urlparse, parse_qs
from pymongo import MongoClient
from bson.json_util import dumps
from collections import defaultdict
from threading import Thread
import uuid

# Configuración de MongoDB y RabbitMQ
mongo_client = MongoClient(os.getenv('MONGODB_CONNECTION_STRING', 'mongodb://localhost:27017/'))
db = mongo_client['location_db']
clients_collection = db['clients']
locations_collection = db['locations']

rabbitmq_connection_string = os.getenv('RABBITMQ_CONNECTION_STRING', 'amqp://guest:guest@localhost:5672/')
rabbit_connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_connection_string))
rabbit_channel = rabbit_connection.channel()

connections = {}

def get_active_connections(client_id):
    active_connections = []
    client = clients_collection.find_one({'client_id': client_id, 'connections.status': 'active'}, {'_id': 0, 'connections': 1})
    if client:
        for connection in client['connections']:
            if connection['status'] == 'active':
                active_connections.append(connection['id'])
    return active_connections

def create_rabbit_queue(client_id):
    queue_name = f'location_updates_{client_id}'
    rabbit_channel.queue_declare(queue=queue_name, durable=True)
    return queue_name

def subscribe_client_to_rabbit(client_id, queue_name):
    def on_message_callback(ch, method, properties, body):
        asyncio.run_coroutine_threadsafe(rabbitmq_callback(ch, method, properties, body), asyncio.get_event_loop())

    rabbit_channel.basic_consume(queue=queue_name, on_message_callback=on_message_callback, auto_ack=True)
    print(f"Cliente {client_id} suscrito a la cola {queue_name}.")

async def handle_connection(websocket, path):
    try:
        query_params = urlparse(path).query
        client_id = parse_qs(query_params).get('client_id', [None])[0]
        if not client_id:
            await websocket.send("Error: No se proporcionó el parámetro client_id en la URL.")
            return

        connection_id = str(uuid.uuid4())
        connections[connection_id] = websocket
        queue_name = create_rabbit_queue(client_id)
        subscribe_client_to_rabbit(client_id, queue_name)

        clients_collection.update_one(
            {'client_id': client_id},
            {'$setOnInsert': {'client_id': client_id, 'active': True, 'connections': []}},
            upsert=True
        )

        clients_collection.update_one(
            {'client_id': client_id},
            {'$push': {'connections': {'id': connection_id, 'status': 'active'}}}
        )

        print(f"Cliente {client_id} conectado.")
        print("Conexiones activas:", get_active_connections(client_id))

        async for message in websocket:
            if message == "locations":
                last_location = locations_collection.find_one({'ClientId': client_id}, sort=[("_id", -1)])
                if last_location:
                    active_connections = get_active_connections(client_id)
                    for conn_id in active_connections:
                        if conn_id in connections:
                            await connections[conn_id].send(dumps(last_location))
                        else:
                            print(f"Connection with id {conn_id} not found or not active")
                            clients_collection.update_one(
                                {'client_id': client_id},
                                {'$pull': {'connections': {'id': conn_id}}}
                            )
                else:
                    await websocket.send("No location data available for this client")
            else:
                await websocket.send("Error: Operación no soportada.")
    except websockets.exceptions.ConnectionClosedOK:
        clients_collection.update_one(
            {'client_id': client_id},
            {'$pull': {'connections': {'id': connection_id}}}
        )
    finally:
        connections.pop(connection_id, None)

async def rabbitmq_callback(ch, method, properties, body):
    message = body.decode('utf-8')
    print(f"Mensaje recibido de RabbitMQ: {message}")

    client_id = message

    last_location = locations_collection.find_one({'ClientId': client_id}, sort=[("_id", -1)])

    if last_location:
        active_connections = get_active_connections(client_id)
        for conn_id in active_connections:
            if conn_id in connections:
                await connections[conn_id].send(dumps(last_location))
    else:
        print("No se encontró ubicación para el cliente.")

def start_rabbitmq_consumer():
    print("Iniciando consumidor RabbitMQ en hilo separado.")
    rabbit_channel.start_consuming()

start_server = websockets.serve(handle_connection, "localhost", 8765)

print("Servidor de websockets iniciado.")
rabbitmq_thread = Thread(target=start_rabbitmq_consumer, daemon=True)
rabbitmq_thread.start()

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
