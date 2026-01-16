import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime
from app.database import get_db
from app.models import Node
from app.schemas import NodeResponse
from app.meshtastic_client import meshtastic_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nodes", tags=["nodes"])


def sanitize_for_json(obj):
    """Recursively convert objects to JSON-serializable types."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    # Handle protobuf or other objects
    if hasattr(obj, '__dict__'):
        return sanitize_for_json(vars(obj))
    # Fallback to string
    return str(obj)


@router.get("", response_model=List[NodeResponse])
async def get_nodes(db: AsyncSession = Depends(get_db)):
    """Get all known nodes from database."""
    result = await db.execute(select(Node).order_by(Node.last_heard.desc()))
    nodes = result.scalars().all()
    return nodes


@router.get("/live")
async def get_live_nodes():
    """Get nodes directly from the connected Meshtastic device."""
    if not meshtastic_client.connected:
        raise HTTPException(status_code=503, detail="Not connected to device")

    try:
        nodes = meshtastic_client.get_nodes()
        logger.info(f"Returning {len(nodes)} nodes")
        # Sanitize the data to ensure JSON serialization works
        sanitized = sanitize_for_json(nodes)
        return JSONResponse(content=sanitized)
    except Exception as e:
        logger.error(f"Error getting nodes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{node_id}", response_model=NodeResponse)
async def get_node(node_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific node by ID."""
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.post("/sync")
async def sync_nodes(db: AsyncSession = Depends(get_db)):
    """Sync nodes from device to database."""
    if not meshtastic_client.connected:
        raise HTTPException(status_code=503, detail="Not connected to device")

    nodes = meshtastic_client.get_nodes()
    synced_count = 0

    for node_id, node_data in nodes.items():
        user = node_data.get("user", {})
        position = node_data.get("position", {})
        device_metrics = node_data.get("deviceMetrics", {})
        last_heard = node_data.get("lastHeard")

        # Check if node exists
        result = await db.execute(select(Node).where(Node.id == node_id))
        existing = result.scalar_one_or_none()

        node_values = {
            "id": node_id,
            "num": node_data.get("num"),
            "long_name": user.get("longName"),
            "short_name": user.get("shortName"),
            "mac_addr": user.get("macaddr"),
            "hw_model": user.get("hwModel"),
            "role": user.get("role"),
            "latitude": position.get("latitude"),
            "longitude": position.get("longitude"),
            "altitude": position.get("altitude"),
            "battery_level": device_metrics.get("batteryLevel"),
            "voltage": device_metrics.get("voltage"),
            "snr": node_data.get("snr"),
            "hops_away": node_data.get("hopsAway"),
            "last_heard": datetime.fromtimestamp(last_heard) if last_heard else None,
            "is_favorite": node_data.get("isFavorite", False)
        }

        if existing:
            for key, value in node_values.items():
                if value is not None:
                    setattr(existing, key, value)
        else:
            db.add(Node(**node_values))

        synced_count += 1

    await db.commit()
    return {"synced": synced_count}
