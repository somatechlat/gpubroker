"""
WebSocket Gateway for real-time price updates.
Subscribes to Redis Pub/Sub channel "price_updates" and streams messages to clients.
Heartbeat ping every 30 seconds.
"""

import asyncio
import json
import logging
import os
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

try:
    import redis.asyncio as redis
except Exception:  # pragma: no cover
    redis = None  # type: ignore

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(_redis_listener())
    try:
        yield
    finally:
        if redis_subscriber:
            try:
                await redis_subscriber.close()
            except Exception:
                pass


app = FastAPI(title="GPUBROKER WebSocket Gateway", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://:redis_dev_password_2024@redis:6379/0")
CHANNEL = os.getenv("PRICE_UPDATES_CHANNEL", "price_updates")
HEARTBEAT_SECONDS = int(os.getenv("WS_HEARTBEAT_SECONDS", "30"))


class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active.discard(websocket)

    async def broadcast(self, message: str):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
redis_subscriber = None


async def _redis_listener():
    if redis is None:
        logger.error("redis module not available; cannot start listener")
        return
    global redis_subscriber
    redis_subscriber = await redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis_subscriber.pubsub()
    await pubsub.subscribe(CHANNEL)
    logger.info("Subscribed to Redis channel %s", CHANNEL)

    async for msg in pubsub.listen():
        if msg is None:
            continue
        if msg.get("type") != "message":
            continue
        data = msg.get("data")
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        await manager.broadcast(data)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            try:
                # Receive optional messages to keep connection alive
                await asyncio.wait_for(websocket.receive_text(), timeout=HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)
        logger.warning("WebSocket error: %s", e)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "redis": bool(redis_subscriber),
        "channel": CHANNEL,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005, reload=True)
