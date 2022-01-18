import asyncio
import json
import random
import string

import aioredis
from fastapi import FastAPI, WebSocket

app = FastAPI()
redis = aioredis.from_url("redis://localhost:6379")

SERVER_NAME = "".join(random.choices(string.ascii_letters, k=5))


class SocketHandler:
    def __init__(self):
        self.socket_list = list()

    def add(self, websocket: WebSocket):
        self.socket_list.append(websocket)

    async def broadcast(self, msg):
        for websocket in self.socket_list:
            await websocket.send_text(msg)


socket_handler = SocketHandler()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/message")
async def send_message(msg: str):
    await socket_handler.broadcast(msg)
    return {"message": "Message sent"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    async def handler(pubsub: aioredis.client.PubSub):
        await pubsub.subscribe("chat")
        while True:
            _message = await pubsub.get_message(ignore_subscribe_messages=True)
            if _message:
                _message = json.loads(_message['data'].decode('utf-8'))
                print(f"{_message=}")
                if _message['server'] != SERVER_NAME:
                    await websocket.send_text(_message['message'])

    await websocket.accept()
    socket_handler.add(websocket)
    await websocket.send_text("Connected")
    pubsub_client = redis.pubsub()
    asyncio.ensure_future(handler(pubsub_client))
    while True:
        message = await websocket.receive_text()
        if message:
            print(message)
            await redis.publish("chat", json.dumps(
                {
                    "server": SERVER_NAME,
                    "message": message
                }
            ))
