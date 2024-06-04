import asyncio
import websockets
from urllib.parse import urlparse, parse_qs
from pymongo import MongoClient
from bson.json_util import dumps
import uuid
import os

# Configuración de MongoDB
mongodb_conn_str = os.getenv('MONGODB_CONNECTION_STRING', 'mongodb://localhost:27017/')
mongo_client = MongoClient(mongodb_conn_str)
db = mongo_client['location_db']
clients_collection = db['clients']
locations_collection = db['locations']

connections = {}

async def handle_connection(websocket, path):
    query_params = urlparse(path).query
    client_id = parse_qs(query_params).get('client_id', [None])[0]
    if not client_id:
        await websocket.send("Error: No se proporcionó el parámetro client_id en la URL.")
        return

    connection_id = str(uuid.uuid4())
    if client_id not in connections:
        connections[client_id] = {}

    connections[client_id][connection_id] = websocket

    clients_collection.update_one(
        {'client_id': client_id},
        {'$setOnInsert': {'client_id': client_id, 'active': True, 'connections': []}},
        upsert=True
    )

    clients_collection.update_one(
        {'client_id': client_id},
        {'$push': {'connections': {'id': connection_id, 'status': 'active'}}}
    )

    print(f"Cliente {client_id} conectado. Conexión ID: {connection_id}")

    try:
        async for message in websocket:
            if message == "locations":
                last_location = locations_collection.find_one({'ClientId': client_id}, sort=[("_id", -1)])
                if last_location:
                    for conn_id, ws in connections[client_id].items():
                        if ws.open:
                            await ws.send(dumps(last_location))
                        else:
                            print(f"Connection with id {conn_id} is closed")
                            clients_collection.update_one(
                                {'client_id': client_id},
                                {'$pull': {'connections': {'id': conn_id}}}
                            )
                else:
                    await websocket.send("No location data available for this client")
            else:
                await websocket.send("Error: Operación no soportada.")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connections[client_id].pop(connection_id, None)
        clients_collection.update_one(
            {'client_id': client_id},
            {'$pull': {'connections': {'id': connection_id}}}
        )

async def send_update(client_id, location):
    if client_id in connections:
        for conn_id, websocket in connections[client_id].items():
            if websocket.open:
                await websocket.send(dumps(location))
            else:
                print(f"Connection with id {conn_id} is closed")
                clients_collection.update_one(
                    {'client_id': client_id},
                    {'$pull': {'connections': {'id': conn_id}}}
                )

async def start_websocket_server():
    start_server_ws = websockets.serve(handle_connection, "localhost", 8766)
    await start_server_ws

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_websocket_server())
    loop.run_forever()