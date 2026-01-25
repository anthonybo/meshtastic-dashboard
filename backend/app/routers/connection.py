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
        error_detail = meshtastic_client.last_error or "Failed to connect to device"
        logger.error(f"Connection failed: {error_detail}")

        # Include scan results in error response for better UX
        error_response = {"detail": error_detail}
        if meshtastic_client.last_scan_result:
            error_response["scan_result"] = meshtastic_client.last_scan_result

        raise HTTPException(status_code=503, detail=error_response)

    return {"status": "connected", **meshtastic_client.get_connection_status()}


@router.post("/disconnect")
async def disconnect_device():
    """Disconnect from the Meshtastic device."""
    logger.info("Disconnect request received")
    await meshtastic_client.disconnect()
    logger.info("Disconnect completed")

    result = {"status": "disconnected"}
    if meshtastic_client._close_failed:
        result["warning"] = "BLE close timed out. Try Reset BLE or restart the server if reconnect fails."
    return result


@router.post("/reset")
async def reset_ble():
    """Reset BLE connection state. Use when connection is stuck."""
    logger.info("BLE reset request received")
    result = await meshtastic_client.reset_ble()
    logger.info(f"BLE reset completed: {result}")
    return result


@router.get("/scan")
async def scan_ble_devices():
    """Scan for available BLE devices.

    Returns categorized list of devices with Meshtastic devices highlighted.
    """
    logger.info("BLE scan request received")
    result = await meshtastic_client.scan_ble_devices()
    logger.info(f"BLE scan completed: {len(result.get('meshtastic_devices', []))} Meshtastic devices found")
    return result
