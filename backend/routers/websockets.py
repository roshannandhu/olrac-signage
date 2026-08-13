import asyncio
import json
import logging
from typing import Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from .. import database, models
from ..routers.auth import ALGORITHM, get_secret_key
from ..database import get_redis

logger = logging.getLogger(__name__)

router = APIRouter()

def verify_device_token(device_id: str, token: str, db: Session) -> models.Screen:
    screen = db.query(models.Screen).filter(models.Screen.device_id == device_id).first()
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    
    if screen.device_secret_hash:
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
        try:
            payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
            sub = payload.get("sub")
            if sub != f"device:{device_id}":
                raise HTTPException(status_code=401, detail="Token device mismatch")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
            
    return screen


# The literal dashboard route must be declared before the parameterised device route
# below: Starlette matches in definition order, so "/{device_id}/ws" otherwise claims
# /dashboard/ws with device_id="dashboard", fails the device lookup, and rejects the
# handshake before the dashboard handler is ever reached.
@router.websocket("/dashboard/ws")
async def dashboard_websocket(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(database.get_db)
):
    # Verify user token
    from ..routers.auth import get_current_user_ws
    try:
        user = await get_current_user_ws(token, db)
    except HTTPException as e:
        await websocket.close(code=1008, reason=e.detail)
        return
        
    if not user.organization_id:
        await websocket.close(code=1008, reason="User has no organization")
        return

    await websocket.accept()
    
    redis = database.get_redis()
    pubsub = redis.pubsub()
    
    channel = f"dashboard:{user.organization_id}"
    await pubsub.subscribe(channel)
    logger.info(f"Dashboard WS connected for user {user.username}, subscribed to {channel}")

    async def writer():
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    await websocket.send_text(data)
        except asyncio.CancelledError:
            pass

    writer_task = asyncio.create_task(writer())
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        writer_task.cancel()
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        logger.info(f"Dashboard WS disconnected for user {user.username}")


@router.websocket("/{device_id}/ws")
async def screen_websocket(
    websocket: WebSocket,
    device_id: str,
    token: str = Query(None),
    db: Session = Depends(database.get_db)
):
    try:
        screen = verify_device_token(device_id, token, db)
    except HTTPException as e:
        await websocket.close(code=1008, reason=e.detail)
        return

    await websocket.accept()
    
    redis = database.get_redis()
    pubsub = redis.pubsub()
    
    channels = [
        f"screen:{device_id}",
    ]
    if screen.organization_id:
        channels.append(f"org:{screen.organization_id}")
    if screen.group_id:
        channels.append(f"group:{screen.group_id}")
        
    await pubsub.subscribe(*channels)
    logger.info(f"Screen {device_id} WS connected, subscribed to {channels}")

    async def reader():
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                    # Forward playback progress to dashboard channel if applicable
                    if msg.get("type") == "playback_progress" and screen.organization_id:
                        msg["device_id"] = device_id
                        msg["screen_id"] = screen.id
                        await redis.publish(f"dashboard:{screen.organization_id}", json.dumps(msg))
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            pass

    async def writer():
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    await websocket.send_text(data)
        except asyncio.CancelledError:
            pass

    reader_task = asyncio.create_task(reader())
    writer_task = asyncio.create_task(writer())

    done, pending = await asyncio.wait(
        [reader_task, writer_task],
        return_when=asyncio.FIRST_COMPLETED
    )

    for task in pending:
        task.cancel()

    await pubsub.unsubscribe(*channels)
    await pubsub.close()
    logger.info(f"Screen {device_id} WS disconnected")
