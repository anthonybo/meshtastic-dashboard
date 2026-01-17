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
            elif portnum == "TRACEROUTE_APP":
                self._handle_traceroute(packet)
        except Exception as e:
            logger.error(f"Error handling packet: {e}")

    def _handle_text_message(self, packet):
        """Handle incoming text messages."""
        decoded = packet.get("decoded", {})
        text = decoded.get("text", "")
        from_id = packet.get("fromId")
        to_id = packet.get("toId")
        channel = packet.get("channel", 0)

        # Determine if this is a broadcast or DM
        is_broadcast = to_id in (None, "^all", "!ffffffff", 4294967295)
        msg_type = "BROADCAST" if is_broadcast else f"DM→{to_id}"

        logger.info(f"[MSG] Received {msg_type} from {from_id} on ch{channel}: {text[:50]}{'...' if len(text) > 50 else ''}")

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

    def _handle_traceroute(self, packet):
        """Handle traceroute response packets."""
        decoded = packet.get("decoded", {})
        traceroute = decoded.get("traceroute", {})
        from_id = packet.get("fromId")
        to_id = packet.get("toId")

        # Extract route information
        # 'route' contains the forward path node IDs
        # 'routeBack' contains the return path node IDs
        # SNR values may also be included (firmware 2.5+)
        route = traceroute.get("route", [])
        route_back = traceroute.get("routeBack", [])
        snr_towards = traceroute.get("snrTowards", [])
        snr_back = traceroute.get("snrBack", [])

        # Convert node IDs to hex format if they're integers
        def format_node_id(node_id):
            if isinstance(node_id, int):
                # Handle unknown nodes (0xFFFFFFFF)
                if node_id == 4294967295:
                    return "unknown"
                return f"!{node_id:08x}"
            return node_id

        formatted_route = [format_node_id(n) for n in route]
        formatted_route_back = [format_node_id(n) for n in route_back]

        logger.info(f"Traceroute response from {from_id}: route={formatted_route}, routeBack={formatted_route_back}")

        self._schedule_event("traceroute", {
            "from_node_id": from_id,
            "to_node_id": to_id,
            "route": formatted_route,
            "route_back": formatted_route_back,
            "snr_towards": list(snr_towards) if snr_towards else [],
            "snr_back": list(snr_back) if snr_back else [],
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
                logger.debug(f"[ACK] Response packet received for {destination}: {packet}")

                # Check if this is an ACK or NAK
                decoded = packet.get("decoded", {})
                routing = decoded.get("routing", {})
                error_reason = routing.get("errorReason")

                # Log packet details for debugging
                packet_type = packet.get("decoded", {}).get("portnum", "unknown")
                from_id = packet.get("fromId", "unknown")
                logger.debug(f"[ACK] Packet type={packet_type}, from={from_id}, routing={routing}")

                if error_reason is None or error_reason == "NONE":
                    logger.info(f"[ACK] ✓ Message to {destination} DELIVERED")
                    self._schedule_event("ack", {
                        "to_node_id": destination,
                        "text": text,
                        "success": True,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    logger.warning(f"[ACK] ✗ Message to {destination} FAILED: {error_reason}")
                    self._schedule_event("ack", {
                        "to_node_id": destination,
                        "text": text,
                        "success": False,
                        "error": str(error_reason),
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                logger.error(f"[ACK] Error in callback: {e}", exc_info=True)

        return on_response

    async def send_message(self, text: str, destination: Optional[str] = None, channel: int = 0) -> bool:
        """Send a text message. Returns True if sent successfully."""
        if not self.connected:
            logger.error("Not connected to device")
            return False

        try:
            from meshtastic import portnums_pb2

            loop = asyncio.get_event_loop()

            # For broadcasts, use "^all" instead of None
            dest_id = destination if destination else "^all"
            is_broadcast = destination is None

            # Create callback for ACK handling (only for DMs, not broadcasts)
            on_response = None
            if not is_broadcast:
                on_response = self._create_ack_callback(destination, text)

            # Use sendData directly instead of sendText to access onResponseAckPermitted
            # This is required to get ACK/NAK callbacks to fire
            text_bytes = text.encode("utf-8")

            await loop.run_in_executor(
                None,
                lambda: self.interface.sendData(
                    text_bytes,
                    destinationId=dest_id,
                    portNum=portnums_pb2.PortNum.TEXT_MESSAGE_APP,
                    channelIndex=channel,
                    wantAck=not is_broadcast,  # Only request ACK for DMs
                    wantResponse=False,
                    onResponse=on_response,
                    onResponseAckPermitted=True  # Required for ACK/NAK callbacks to fire
                )
            )

            if is_broadcast:
                logger.info(f"[MSG] Sent broadcast on channel {channel}: {text[:50]}...")
            else:
                logger.info(f"[MSG] Sent DM to {destination} (wantAck=True): {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"[MSG] Failed to send message: {e}", exc_info=True)
            return False

    def _create_traceroute_response_handler(self, destination: str):
        """Create a response handler for traceroute that sends results via WebSocket."""
        def on_response(packet):
            try:
                logger.info(f"Traceroute response received for {destination}: {packet}")
                decoded = packet.get("decoded", {})

                # Check for routing error
                routing = decoded.get("routing", {})
                error_reason = routing.get("errorReason")
                if error_reason and error_reason != "NONE":
                    logger.warning(f"Traceroute to {destination} failed: {error_reason}")
                    self._schedule_event("traceroute_error", {
                        "destination": destination,
                        "error": str(error_reason),
                        "timestamp": datetime.now().isoformat()
                    })
                    return

                # Parse traceroute data
                traceroute = decoded.get("traceroute", {})
                if traceroute:
                    from_id = packet.get("fromId")
                    to_id = packet.get("toId")
                    route = traceroute.get("route", [])
                    route_back = traceroute.get("routeBack", [])
                    snr_towards = traceroute.get("snrTowards", [])
                    snr_back = traceroute.get("snrBack", [])

                    def format_node_id(node_id):
                        if isinstance(node_id, int):
                            if node_id == 4294967295:
                                return "unknown"
                            return f"!{node_id:08x}"
                        return node_id

                    formatted_route = [format_node_id(n) for n in route]
                    formatted_route_back = [format_node_id(n) for n in route_back]

                    logger.info(f"Traceroute result: {from_id} route={formatted_route}")

                    self._schedule_event("traceroute", {
                        "from_node_id": from_id,
                        "to_node_id": to_id,
                        "route": formatted_route,
                        "route_back": formatted_route_back,
                        "snr_towards": list(snr_towards) if snr_towards else [],
                        "snr_back": list(snr_back) if snr_back else [],
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                logger.error(f"Error handling traceroute response: {e}", exc_info=True)

        return on_response

    async def _run_traceroute_async(self, destination: str, dest_int: int, hop_limit: int, channel: int):
        """Run traceroute in background. Handles response/timeout via WebSocket."""
        from meshtastic import mesh_pb2, portnums_pb2

        loop = asyncio.get_event_loop()
        try:
            # Create our own response handler
            on_response = self._create_traceroute_response_handler(destination)

            # Use sendData directly instead of sendTraceRoute so we control the callback
            r = mesh_pb2.RouteDiscovery()

            await loop.run_in_executor(
                None,
                lambda: self.interface.sendData(
                    r,
                    destinationId=dest_int,
                    portNum=portnums_pb2.PortNum.TRACEROUTE_APP,
                    wantResponse=True,
                    onResponse=on_response,
                    channelIndex=channel,
                    hopLimit=hop_limit,
                )
            )

            # Wait for the response (library's waitForTraceRoute logic)
            wait_factor = min(len(self.interface.nodes) - 1 if self.interface.nodes else 0, hop_limit)
            await loop.run_in_executor(
                None,
                lambda: self.interface.waitForTraceRoute(wait_factor)
            )

            logger.info(f"Traceroute to {destination} completed")
        except Exception as trace_err:
            # Check if it's a timeout error
            error_msg = str(trace_err).lower()
            if "timeout" in error_msg or "timed out" in error_msg:
                logger.warning(f"Traceroute to {destination} timed out")
                self._schedule_event("traceroute_error", {
                    "destination": destination,
                    "error": "TIMEOUT",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                logger.error(f"Traceroute to {destination} failed: {trace_err}")
                self._schedule_event("traceroute_error", {
                    "destination": destination,
                    "error": str(trace_err),
                    "timestamp": datetime.now().isoformat()
                })

    async def send_traceroute(self, destination: str, hop_limit: int = 3, channel: int = 0) -> bool:
        """Send a traceroute request to a destination node.

        Returns immediately after dispatching. Response comes via WebSocket.
        """
        if not self.connected:
            logger.error("Not connected to device")
            return False

        try:
            # Convert destination to int if it's a hex string like "!abcd1234"
            if isinstance(destination, str) and destination.startswith("!"):
                dest_int = int(destination[1:], 16)
            else:
                dest_int = int(destination)

            logger.info(f"Sending traceroute to {destination} (hop_limit={hop_limit}, channel={channel})")

            # Create background task - don't await it, let it run independently
            asyncio.create_task(
                self._run_traceroute_async(destination, dest_int, hop_limit, channel)
            )

            logger.info(f"Traceroute request dispatched to {destination}")
            return True

        except Exception as e:
            logger.error(f"Failed to send traceroute: {e}")
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
