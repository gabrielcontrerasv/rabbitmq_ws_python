import asyncio
from aiohttp import web
import json
from websocket_server import send_update

async def handle_update(request):
    data = await request.json()
    client_id = data.get('client_id')
    location = json.loads(data.get('location'))
    await send_update(client_id, location)
    return web.Response(text="locations")

async def start_http_server():
    app = web.Application()
    app.router.add_post('/update', handle_update)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8010)
    await site.start()
    print("Servidor HTTP iniciado para recibir actualizaciones.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_http_server())
    loop.run_forever()