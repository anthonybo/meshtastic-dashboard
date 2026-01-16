import asyncio
import logging
import threading
from datetime import datetime
from typing import Callable, Optional, List
from pubsub import pub
from meshtastic.ble_interface import BLEInterface
from app.config import get_settings

logger = logging.getLogger(__name__)


class MeshtasticClient:
    def __init__(self):
        self.interface: Optional[BLEInterface] = None
        self.settings = get_settings()
        self._connected = False
        self._my_info = None
        self._metadata = None
        self._nodes = {}
        self._event_callbacks: List[Callable] = []
        self._lock = asyncio.Lock()
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def connected(self) -> bool:
        return self._connected and self.interface is not None

    @property
    def my_node_num(self) -> Optional[int]:
        if self._my_info is None:
            return None
        # myInfo is a protobuf object, access via attribute
        return getattr(self._my_info, 'my_node_num', None)

    @property
    def nodes(self) -> dict:
        return self._nodes

    def add_event_callback(self, callback: Callable):
        self._event_callbacks.append(callback)

    def remove_event_callback(self, callback: Callable):
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)

    def _schedule_event(self, event_type: str, data: dict):
        """Schedule an event to run on the main event loop (thread-safe)."""
        if self._main_loop is None:
            return

        async def emit():
            for callback in self._event_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event_type, data)
                    else:
                        callback(event_type, data)
                except Exception as e:
                    logger.error(f"Error in event callback: {e}")

        # Schedule on the main loop from any thread
        self._main_loop.call_soon_threadsafe(
            lambda: asyncio.create_task(emit())
        )

    def _on_receive(self, packet, interface):
        """Handle received packets."""
        try:
            decoded = packet.get("decoded", {})
            portnum = decoded.get("portnum")
            from_id = packet.get("fromId", "unknown")

            # Log all received packets for debugging
            logger.debug(f"Received packet from {from_id}: portnum={portnum}")

            if portnum == "TEXT_MESSAGE_APP":
                self._handle_text_message(packet)
            elif portnum == "POSITION_APP":
                self._handle_position(packet)
            elif portnum == "TELEMETRY_APP":
                self._handle_telemetry(packet)
            elif portnum == "NODEINFO_APP":
                self._handle_nodeinfo(packet)
        except Exception as e:
            logger.error(f"Error handling packet: {e}")

    def _handle_text_message(self, packet):
        """Handle incoming text messages."""
        decoded = packet.get("decoded", {})
        text = decoded.get("text", "")
        from_id = packet.get("fromId")
        to_id = packet.get("toId")
        channel = packet.get("channel", 0)

        logger.info(f"Message from {from_id}: {text}")

        self._schedule_event("message", {
            "from_node_id": from_id,
            "to_node_id": to_id,
            "channel": channel,
            "text": text,
            "timestamp": datetime.now().isoformat()
        })

    def _handle_position(self, packet):
        """Handle position updates."""
        decoded = packet.get("decoded", {})
        position = decoded.get("position", {})
        from_id = packet.get("fromId")

        if position:
            self._schedule_event("position", {
                "node_id": from_id,
                "latitude": position.get("latitude"),
                "longitude": position.get("longitude"),
                "altitude": position.get("altitude"),
                "timestamp": datetime.now().isoformat()
            })

    def _handle_telemetry(self, packet):
        """Handle telemetry updates."""
        decoded = packet.get("decoded", {})
        telemetry = decoded.get("telemetry", {})
        from_id = packet.get("fromId")
        device_metrics = telemetry.get("deviceMetrics", {})

        if device_metrics:
            self._schedule_event("telemetry", {
                "node_id": from_id,
                "battery_level": device_metrics.get("batteryLevel"),
                "voltage": device_metrics.get("voltage"),
                "channel_utilization": device_metrics.get("channelUtilization"),
                "air_util_tx": device_metrics.get("airUtilTx"),
                "uptime_seconds": device_metrics.get("uptimeSeconds"),
                "timestamp": datetime.now().isoformat()
            })

    def _handle_nodeinfo(self, packet):
        """Handle node info updates."""
        decoded = packet.get("decoded", {})
        user = decoded.get("user", {})
        from_id = packet.get("fromId")

        if user:
            self._schedule_event("node_update", {
                "id": from_id,
                "long_name": user.get("longName"),
                "short_name": user.get("shortName"),
                "hw_model": user.get("hwModel"),
                "timestamp": datetime.now().isoformat()
            })


    def _on_connection(self, interface, topic=pub.AUTO_TOPIC):
        """Handle connection events from BLE library."""
        # Just log here - don't broadcast yet, connect() will do that after interface is ready
        logger.info("BLE connection established callback received")

    def _on_disconnect(self, interface, topic=pub.AUTO_TOPIC):
        """Handle disconnection events."""
        logger.info("Disconnected from Meshtastic device")
        self._connected = False
        self._schedule_event("connection", {"connected": False})

    async def connect(self) -> bool:
        """Connect to the Meshtastic device via BLE."""
        async with self._lock:
            if self.connected:
                return True

            try:
                # Store the main event loop for thread-safe callbacks
                self._main_loop = asyncio.get_event_loop()

                logger.info(f"Connecting to {self.settings.meshtastic_device_name}...")

                # Subscribe to events
                pub.subscribe(self._on_receive, "meshtastic.receive")
                pub.subscribe(self._on_connection, "meshtastic.connection.established")
                pub.subscribe(self._on_disconnect, "meshtastic.connection.lost")

                # Connect via BLE (runs in thread pool)
                loop = asyncio.get_event_loop()
                self.interface = await loop.run_in_executor(
                    None,
                    lambda: BLEInterface(self.settings.meshtastic_device_name)
                )

                self._my_info = self.interface.myInfo
                self._metadata = self.interface.metadata
                self._nodes = self.interface.nodes
                self._connected = True

                logger.info(f"Connected! My node num: {self.my_node_num}")

                # Broadcast connection status now that everything is ready
                self._schedule_event("connection", self.get_connection_status())

                return True

            except Exception as e:
                logger.error(f"Failed to connect: {e}")
                self._connected = False
                return False

    async def disconnect(self):
        """Disconnect from the Meshtastic device."""
        logger.info("Disconnect called")
        async with self._lock:
            if not self.interface:
                logger.info("No active interface to disconnect")
                self._connected = False
                return

            if self.interface:
                try:
                    logger.info("Closing BLE interface...")
                    # Close with timeout to prevent hanging
                    loop = asyncio.get_event_loop()
                    await asyncio.wait_for(
                        loop.run_in_executor(None, self.interface.close),
                        timeout=5.0
                    )
                    logger.info("BLE interface closed successfully")
                except asyncio.TimeoutError:
                    logger.warning("BLE close timed out, forcing disconnect")
                except Exception as e:
                    logger.error(f"Error disconnecting: {e}")
                finally:
                    self.interface = None
                    self._connected = False
                    self._my_info = None
                    self._metadata = None
                    self._nodes = {}

                    # Emit disconnection event BEFORE clearing main_loop
                    self._schedule_event("connection", self.get_connection_status())

                    self._main_loop = None

                    try:
                        pub.unsubscribe(self._on_receive, "meshtastic.receive")
                        pub.unsubscribe(self._on_connection, "meshtastic.connection.established")
                        pub.unsubscribe(self._on_disconnect, "meshtastic.connection.lost")
                    except Exception:
                        pass

    def _create_ack_callback(self, destination: str, text: str):
        """Create a callback function for ACK/NAK handling."""
        def on_response(packet):
            try:
                # Check if this is an ACK or NAK
                routing = packet.get("decoded", {}).get("routing", {})
                error_reason = routing.get("errorReason")

                if error_reason is None or error_reason == "NONE":
                    logger.info(f"✓ ACK received for message to {destination} - DELIVERED")
                    self._schedule_event("ack", {
                        "to_node_id": destination,
                        "text": text,
                        "success": True,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    logger.warning(f"NAK received for message to {destination}: {error_reason}")
                    self._schedule_event("ack", {
                        "to_node_id": destination,
                        "text": text,
                        "success": False,
                        "error": str(error_reason),
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                logger.error(f"Error in ACK callback: {e}")

        return on_response

    async def send_message(self, text: str, destination: Optional[str] = None, channel: int = 0) -> bool:
        """Send a text message. Returns True if sent successfully."""
        if not self.connected:
            logger.error("Not connected to device")
            return False

        try:
            loop = asyncio.get_event_loop()

            # Create callback for ACK handling (only for DMs, not broadcasts)
            on_response = None
            if destination:
                on_response = self._create_ack_callback(destination, text)

            # sendText with onResponse callback for ACK handling
            await loop.run_in_executor(
                None,
                lambda: self.interface.sendText(
                    text,
                    destinationId=destination,
                    channelIndex=channel,
                    wantAck=destination is not None,  # Only request ACK for DMs
                    onResponse=on_response
                )
            )

            logger.info(f"Sent message to {destination or 'broadcast'}: {text}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def get_connection_status(self) -> dict:
        """Get current connection status."""
        fw_version = None
        hw_model = None

        if self._metadata:
            # metadata might be a protobuf or dict
            if hasattr(self._metadata, 'firmware_version'):
                fw_version = self._metadata.firmware_version
                hw_model = getattr(self._metadata, 'hw_model', None)
            elif isinstance(self._metadata, dict):
                fw_version = self._metadata.get("firmwareVersion")
                hw_model = self._metadata.get("hwModel")

        return {
            "connected": self.connected,
            "device_name": self.settings.meshtastic_device_name if self.connected else None,
            "my_node_num": self.my_node_num,
            "firmware_version": fw_version,
            "hw_model": str(hw_model) if hw_model else None
        }

    def get_nodes(self) -> dict:
        """Get all known nodes."""
        if not self.connected or not self.interface:
            return {}
        try:
            nodes = self.interface.nodes
            if nodes is None:
                return {}

            # Convert to JSON-serializable dict
            result = {}
            for node_id, node_data in nodes.items():
                try:
                    # node_data is already a dict from the meshtastic library
                    if isinstance(node_data, dict):
                        result[node_id] = node_data
                    else:
                        # If it's some other type, try to convert
                        result[node_id] = dict(node_data) if hasattr(node_data, '__iter__') else str(node_data)
                except Exception as e:
                    logger.warning(f"Could not convert node {node_id}: {e}")
                    continue

            return result
        except Exception as e:
            logger.error(f"Error accessing nodes: {e}", exc_info=True)
            return {}


# Singleton instance
meshtastic_client = MeshtasticClient()
