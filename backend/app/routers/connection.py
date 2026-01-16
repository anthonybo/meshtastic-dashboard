import logging
from fastapi import APIRouter, HTTPException
from app.schemas import ConnectionStatus
from app.meshtastic_client import meshtastic_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/connection", tags=["connection"])


@router.get("", response_model=ConnectionStatus)
async def get_connection_status():
    """Get current BLE connection status."""
    return meshtastic_client.get_connection_status()


@router.post("/connect")
async def connect_device():
    """Connect to the Meshtastic device via BLE."""
    if meshtastic_client.connected:
        return {"status": "already_connected", **meshtastic_client.get_connection_status()}

    success = await meshtastic_client.connect()

    if not success:
        raise HTTPException(status_code=503, detail="Failed to connect to device")

    return {"status": "connected", **meshtastic_client.get_connection_status()}


@router.post("/disconnect")
async def disconnect_device():
    """Disconnect from the Meshtastic device."""
    logger.info("Disconnect request received")
    await meshtastic_client.disconnect()
    logger.info("Disconnect completed")
    return {"status": "disconnected"}
