import pika
import os
from pymongo import MongoClient
from pydantic import BaseModel
from datetime import datetime
import json
from fastapi import FastAPI

app = FastAPI()

# Conexión a la base de datos MongoDB
mongo_str_conn = os.getenv('MONGODB_STR_CONN', 'mongodb://localhost:27017/')
client = MongoClient(mongo_str_conn)
db = client['location_db']
collection = db['locations']

# Conexión a RabbitMQ
rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
connection = pika.BlockingConnection(pika.ConnectionParameters(rabbitmq_host))
channel = connection.channel()
channel.queue_declare(queue='location_updates')

class Location(BaseModel):
    latitude: float
    longitude: float

def emit_to_rabbit(location_data):
    message = {
        "latitude": location_data["latitude"],
        "longitude": location_data["longitude"],
        "timestamp": location_data["timestamp"]
    }
    channel.basic_publish(exchange='',
                          routing_key='location_updates',
                          body=json.dumps(message))

@app.post("/locations")
async def save_location(location: Location):
    location_data = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timestamp": datetime.now().isoformat()
    }
    collection.insert_one(location_data)
    emit_to_rabbit(location_data)
    return {"message": "Location saved successfully"}

@app.get("/emit_location_updates")
async def emit_location_updates():
    # Obtener la última ubicación
    last_location_data = collection.find_one(sort=[("_id", -1)])
    if last_location_data:
        emit_to_rabbit(last_location_data)
    return {"message": "Location update emitted successfully"}
