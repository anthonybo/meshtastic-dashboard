import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.database import get_db, async_session
from app.models import Message
from app.schemas import MessageCreate, MessageResponse
from app.meshtastic_client import meshtastic_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/messages", tags=["messages"])


class BroadcastToAllRequest(BaseModel):
    text: str
    delay_seconds: float = 1.0  # Delay between messages to not overwhelm the mesh


@router.get("", response_model=List[MessageResponse])
async def get_messages(
    limit: int = 100,
    offset: int = 0,
    channel: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get message history."""
    query = select(Message).order_by(Message.timestamp.desc())

    if channel is not None:
        query = query.where(Message.channel == channel)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    messages = result.scalars().all()
    return messages


@router.post("", response_model=MessageResponse)
async def send_message(message: MessageCreate, db: AsyncSession = Depends(get_db)):
    """Send a text message via Meshtastic."""
    if not meshtastic_client.connected:
        raise HTTPException(status_code=503, detail="Not connected to device")

    logger.info(f"Sending message: text='{message.text}', to={message.to_node_id}, channel={message.channel}")

    # Send via Meshtastic
    try:
        success = await meshtastic_client.send_message(
            text=message.text,
            destination=message.to_node_id,
            channel=message.channel
        )
    except Exception as e:
        logger.error(f"Exception sending message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

    if not success:
        logger.error("send_message returned False")
        raise HTTPException(status_code=500, detail="Failed to send message")

    # Store in database
    my_node_id = f"!{meshtastic_client.my_node_num:08x}" if meshtastic_client.my_node_num else None
    db_message = Message(
        from_node_id=my_node_id,
        to_node_id=message.to_node_id,
        channel=message.channel,
        text=message.text,
        is_outgoing=True
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)

    return db_message


@router.get("/channels")
async def get_channels():
    """Get available channels from the device."""
    if not meshtastic_client.connected:
        raise HTTPException(status_code=503, detail="Not connected to device")

    interface = meshtastic_client.interface
    if not interface or not interface.localNode:
        return []

    channels = []
    for i, ch in enumerate(interface.localNode.channels):
        if ch.role != 0:  # DISABLED
            channels.append({
                "index": i,
                "name": ch.settings.name or f"Channel {i}",
                "role": ch.role
            })

    return channels


@router.post("/broadcast-all")
async def broadcast_to_all_nodes(request: BroadcastToAllRequest):
    """Send a direct message to every known node individually."""
    from app.routers.websocket import broadcast

    if not meshtastic_client.connected:
        raise HTTPException(status_code=503, detail="Not connected to device")

    nodes = meshtastic_client.get_nodes()
    if not nodes:
        raise HTTPException(status_code=404, detail="No nodes found")

    my_node_num = meshtastic_client.my_node_num
    my_node_id = f"!{my_node_num:08x}" if my_node_num else None

    sent_count = 0
    failed_count = 0
    skipped_count = 0
    total_to_send = len([n for n in nodes.keys() if n != my_node_id])
    current = 0

    # Notify start
    await broadcast({
        "type": "broadcast_progress",
        "data": {
            "status": "started",
            "total": total_to_send,
            "current": 0,
            "sent": 0,
            "failed": 0
        }
    })

    for node_id, node_data in nodes.items():
        # Skip our own node
        if node_id == my_node_id:
            skipped_count += 1
            continue

        current += 1
        user = node_data.get("user", {}) if isinstance(node_data, dict) else {}
        node_name = user.get("longName") or user.get("shortName") or node_id[-8:]

        # Notify progress
        await broadcast({
            "type": "broadcast_progress",
            "data": {
                "status": "sending",
                "total": total_to_send,
                "current": current,
                "sent": sent_count,
                "failed": failed_count,
                "current_node": node_name,
                "current_node_id": node_id
            }
        })

        try:
            # Send DM to this node
            success = await meshtastic_client.send_message(
                text=request.text,
                destination=node_id,
                channel=0
            )

            if success:
                sent_count += 1
                # Store in database (separate try/catch so DB errors don't affect send count)
                try:
                    async with async_session() as db:
                        db_message = Message(
                            from_node_id=my_node_id,
                            to_node_id=node_id,
                            channel=0,
                            text=request.text,
                            is_outgoing=True
                        )
                        db.add(db_message)
                        await db.commit()
                except Exception as db_error:
                    logger.warning(f"Failed to save message to DB for {node_id}: {db_error}")
                    # Message was sent, just not saved - don't count as failed
            else:
                failed_count += 1

            # Delay between messages to not overwhelm the mesh
            if request.delay_seconds > 0:
                await asyncio.sleep(request.delay_seconds)

        except Exception as e:
            logger.error(f"Error sending to {node_id}: {e}")
            failed_count += 1

    # Notify completion
    await broadcast({
        "type": "broadcast_progress",
        "data": {
            "status": "completed",
            "total": total_to_send,
            "current": total_to_send,
            "sent": sent_count,
            "failed": failed_count
        }
    })

    return {
        "total_nodes": len(nodes),
        "sent": sent_count,
        "failed": failed_count,
        "skipped": skipped_count
    }
