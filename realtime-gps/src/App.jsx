import React, { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Marker, GoogleMap, LoadScript } from '@react-google-maps/api'; // Import necessary components

const libraries = ['places']; // Include the Places library for user location

const WebSocketComponent = () => {
  const [location, setLocation] = useState(null);
  const [connected, setConnected] = useState(false);
  const [ws, setWs] = useState(null);
  const [map, setMap] = useState(null); // State to hold the Google Map instance
  const clientId = '665e1ba99b644c691227e15b'; // Asignar el clientId de manera implícita

  const handleMapLoad = (mapInstance) => {
    setMap(mapInstance);
  };

  useEffect(() => {
    const socket = new WebSocket(`ws://localhost:8765?client_id=${clientId}`);
    setWs(socket);

    socket.onopen = () => {
      setConnected(true);
      console.log('connection established');
      sendLocation(); // Solicitar la ubicación automáticamente al conectarse
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.location) {
        setLocation(data.location);
      } else {
        console.log(data);
      }
    };

    socket.onclose = () => {
      setConnected(false);
      console.log('WebSocket connection closed');
    };

    return () => {
      socket.close();
    };
  }, []);

  useEffect(() => {
    // This effect will execute whenever `location` changes or `map` is initialized
    if (location && map) {
      const { latitude, longitude } = location;
      const center = { lat: latitude, lng: longitude }; // Create a LatLng object

      map.setCenter(center); // Update map center based on received location
      map.setZoom(15); // Set an appropriate zoom level
    }
  }, [location, map]);

  const sendLocation = () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send('locations');
    }
  };



  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}> {/* Center the content vertically and horizontally */}
      <h1>Mapa de Ubicacion en tiempo Real</h1>
      {connected ? (
        <LoadScript
          googleMapsApiKey="" // Replace with your API key
          libraries={libraries}
        >
          <GoogleMap
            mapContainerStyle={{ width: '800px', height: '400px' }} // Adjust size as needed
            zoom={15}
            center={{ lat: 10.9749, lng: -74.7066 }} // Initial center (replace with default location if needed)
            onLoad={handleMapLoad}
          >
            {location && (
              <Marker
                position={{ lat: location.latitude, lng: location.longitude }}
              />
            )}
          </GoogleMap>
        </LoadScript>
      ) : (
        <p>Connecting to WebSocket...</p>
      )}
      {location && (
        <div>
          <h2>Current Location:</h2>
          <pre>{JSON.stringify(location, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};

export default WebSocketComponent;
