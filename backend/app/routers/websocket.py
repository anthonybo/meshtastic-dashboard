import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
from app.meshtastic_client import meshtastic_client
from app.database import async_session
from app.models import Message, Telemetry, Position

logger = logging.getLogger(__name__)

router = APIRouter()

# Connected WebSocket clients
connected_clients: Set[WebSocket] = set()


async def broadcast(message: dict):
    """Broadcast a message to all connected WebSocket clients."""
    if not connected_clients:
        return

    data = json.dumps(message)
    disconnected = set()

    for client in connected_clients:
        try:
            await client.send_text(data)
        except Exception as e:
            logger.error(f"Error sending to client: {e}")
            disconnected.add(client)

    for client in disconnected:
        connected_clients.discard(client)


async def handle_meshtastic_event(event_type: str, data: dict):
    """Handle events from the Meshtastic client and broadcast to WebSockets."""
    from sqlalchemy import select, and_, desc

    # Broadcast to connected clients
    await broadcast({"type": event_type, "data": data})

    # Store incoming messages in database
    if event_type == "message":
        async with async_session() as db:
            try:
                msg = Message(
                    from_node_id=data.get("from_node_id"),
                    to_node_id=data.get("to_node_id"),
                    channel=data.get("channel", 0),
                    text=data.get("text", ""),
                    is_outgoing=False
                )
                db.add(msg)
                await db.commit()
            except Exception as e:
                logger.error(f"Error storing message: {e}")
                await db.rollback()

    # Handle ACK/NAK - update message in database
    elif event_type == "ack":
        async with async_session() as db:
            try:
                # Find the most recent outgoing message to this node with this text
                to_node = data.get("to_node_id")
                text = data.get("text")
                success = data.get("success", True)
                error = data.get("error")

                if to_node and text:
                    result = await db.execute(
                        select(Message)
                        .where(and_(
                            Message.to_node_id == to_node,
                            Message.text == text,
                            Message.is_outgoing == True,
                            Message.ack_received == False,
                            Message.ack_failed == False
                        ))
                        .order_by(desc(Message.timestamp))
                        .limit(1)
                    )
                    msg = result.scalar_one_or_none()
                    if msg:
                        if success:
                            msg.ack_received = True
                            logger.info(f"Marked message as ACK'd: {text[:30]}...")
                        else:
                            msg.ack_failed = True
                            msg.ack_error = error
                            logger.warning(f"Marked message as failed: {text[:30]}... ({error})")
                        await db.commit()
            except Exception as e:
                logger.error(f"Error updating ACK status: {e}")
                await db.rollback()


# Register the event handler
meshtastic_client.add_event_callback(handle_meshtastic_event)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info(f"WebSocket client connected. Total: {len(connected_clients)}")

    # Send current connection status
    status = meshtastic_client.get_connection_status()
    await websocket.send_text(json.dumps({"type": "connection", "data": status}))

    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()

            try:
                msg = json.loads(data)
                msg_type = msg.get("type")

                if msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

                elif msg_type == "send_message":
                    text = msg.get("text", "")
                    destination = msg.get("destination")
                    channel = msg.get("channel", 0)

                    if meshtastic_client.connected:
                        success = await meshtastic_client.send_message(text, destination, channel)
                        await websocket.send_text(json.dumps({
                            "type": "message_sent",
                            "data": {"success": success, "text": text}
                        }))

                elif msg_type == "traceroute":
                    destination = msg.get("destination")
                    hop_limit = msg.get("hop_limit", 3)
                    channel = msg.get("channel", 0)

                    if meshtastic_client.connected and destination:
                        success = await meshtastic_client.send_traceroute(
                            destination=destination,
                            hop_limit=hop_limit,
                            channel=channel
                        )
                        await websocket.send_text(json.dumps({
                            "type": "traceroute_sent",
                            "data": {
                                "success": success,
                                "destination": destination
                            }
                        }))

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        connected_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(connected_clients)}")
