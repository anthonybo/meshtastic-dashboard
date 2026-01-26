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
        self._intentional_disconnect = False  # Track if user requested disconnect
        self._reconnect_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay = 5  # seconds
        self._last_error: Optional[str] = None  # Store last connection error
        self._close_failed = False  # Track if last close had issues
        self._device_address: Optional[str] = None  # Store BLE address for cleanup
        self._last_scan_result: Optional[dict] = None  # Store last BLE scan results

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

    async def _force_ble_cleanup(self, address: Optional[str] = None) -> bool:
        """Force cleanup of BLE connection using bleak directly.

        This is used when the normal close() times out and we need to
        forcibly release the BLE connection.
        """
        from bleak import BleakClient, BleakScanner

        target_address = address or self._device_address
        if not target_address:
            logger.info("[BLE] No device address stored for cleanup")
            return False

        logger.info(f"[BLE] Attempting force cleanup for {target_address}")

        try:
            # Try to connect and immediately disconnect to reset the connection state
            client = BleakClient(target_address)
            try:
                # Check if we can connect (with short timeout)
                connected = await asyncio.wait_for(client.connect(), timeout=5.0)
                if connected:
                    logger.info("[BLE] Connected to orphaned device, disconnecting...")
                    await client.disconnect()
                    logger.info("[BLE] Force disconnect successful")
                    return True
            except asyncio.TimeoutError:
                logger.warning("[BLE] Force connect timed out")
            except Exception as e:
                logger.debug(f"[BLE] Force connect failed (expected if device gone): {e}")
            finally:
                try:
                    if client.is_connected:
                        await client.disconnect()
                except Exception:
                    pass
            return False
        except Exception as e:
            logger.error(f"[BLE] Force cleanup error: {e}")
            return False

    async def _scan_for_device(self) -> Optional[str]:
        """Scan for the Meshtastic device and return its address."""
        device_name = self.settings.meshtastic_device_name
        logger.info(f"[BLE] Scanning for device: {device_name}")

        try:
            scan_result = await self.scan_ble_devices()

            # Look for our configured device
            for device in scan_result.get("meshtastic_devices", []):
                if device["name"] == device_name:
                    logger.info(f"[BLE] Found device at address: {device['address']}")
                    return device["address"]

            # Not found - log what we did find
            meshtastic_count = len(scan_result.get("meshtastic_devices", []))
            other_count = len(scan_result.get("other_devices", []))
            logger.warning(f"[BLE] Device '{device_name}' not found. "
                          f"Found {meshtastic_count} Meshtastic device(s), {other_count} other device(s)")
            return None
        except Exception as e:
            logger.error(f"[BLE] Scan error: {e}")
            return None

    async def scan_ble_devices(self, timeout: float = 10.0) -> dict:
        """Scan for all BLE devices and categorize them.

        Returns a dict with:
        - meshtastic_devices: List of Meshtastic devices found
        - other_devices: List of other named BLE devices
        - configured_device: The device name from config
        - configured_device_found: Whether the configured device was found
        """
        from bleak import BleakScanner

        logger.info(f"[BLE] Starting BLE scan (timeout={timeout}s)...")

        result = {
            "meshtastic_devices": [],
            "other_devices": [],
            "configured_device": self.settings.meshtastic_device_name,
            "configured_device_found": False,
            "scan_duration": timeout
        }

        try:
            devices = await asyncio.wait_for(
                BleakScanner.discover(timeout=timeout),
                timeout=timeout + 2  # Extra buffer for the discover call
            )

            for device in devices:
                if not device.name:
                    continue  # Skip unnamed devices

                device_info = {
                    "name": device.name,
                    "address": device.address,
                    "rssi": device.rssi if hasattr(device, 'rssi') else None
                }

                if "Meshtastic" in device.name:
                    result["meshtastic_devices"].append(device_info)
                    if device.name == self.settings.meshtastic_device_name:
                        result["configured_device_found"] = True
                else:
                    result["other_devices"].append(device_info)

            # Sort Meshtastic devices by name, others by RSSI (strongest first)
            result["meshtastic_devices"].sort(key=lambda d: d["name"])
            result["other_devices"].sort(key=lambda d: d.get("rssi") or -999, reverse=True)

            # Limit other devices to top 10 by signal strength
            result["other_devices"] = result["other_devices"][:10]

            logger.info(f"[BLE] Scan complete: {len(result['meshtastic_devices'])} Meshtastic, "
                       f"{len(result['other_devices'])} other devices")

        except asyncio.TimeoutError:
            logger.warning("[BLE] Scan timed out")
            result["error"] = "Scan timed out"
        except Exception as e:
            logger.error(f"[BLE] Scan error: {e}")
            result["error"] = str(e)

        return result

    async def reset_ble(self) -> dict:
        """Reset BLE connection state. Use when connection is stuck."""
        logger.info("[BLE] Starting BLE reset...")

        result = {
            "success": False,
            "message": "",
            "device_found": False
        }

        # First, ensure we're marked as disconnected
        self._intentional_disconnect = True
        self._connected = False

        # Unsubscribe from events
        try:
            pub.unsubscribe(self._on_receive, "meshtastic.receive")
            pub.unsubscribe(self._on_connection, "meshtastic.connection.established")
            pub.unsubscribe(self._on_disconnect, "meshtastic.connection.lost")
        except Exception:
            pass

        # Try to close interface if we have one
        if self.interface:
            try:
                # Get the bleak client address before closing
                if hasattr(self.interface, 'bleak_client') and self.interface.bleak_client:
                    self._device_address = self.interface.bleak_client.address
                    logger.info(f"[BLE] Stored device address: {self._device_address}")
            except Exception:
                pass

            self.interface = None
            self._my_info = None
            self._metadata = None
            self._nodes = {}

        # Try force cleanup if we have an address
        if self._device_address:
            cleanup_success = await self._force_ble_cleanup()
            if cleanup_success:
                result["message"] = "Force cleanup successful"

        # Scan to see if device is now visible
        await asyncio.sleep(2)  # Give BLE time to settle
        found_address = await self._scan_for_device()

        if found_address:
            result["success"] = True
            result["device_found"] = True
            result["message"] = f"Device found at {found_address}"
            self._device_address = found_address
            self._close_failed = False
        else:
            result["message"] = "Device not found after reset. BLE may still be held by system. Try restarting the server."
            self._close_failed = True

        self._schedule_event("connection", {"connected": False, "reset": True})

        return result

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
            to_id = packet.get("toId", "unknown")

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
            elif portnum == "ROUTING_APP":
                self._handle_routing(packet)
            elif portnum == "NEIGHBORINFO_APP":
                self._handle_neighborinfo(packet)
            elif portnum == "WAYPOINT_APP":
                self._handle_waypoint(packet)
            elif portnum == "ADMIN_APP":
                self._handle_admin(packet)
            elif portnum == "RANGE_TEST_APP":
                self._handle_range_test(packet)
            elif portnum == "STORE_FORWARD_APP":
                self._handle_store_forward(packet)
            elif portnum == "DETECTION_SENSOR_APP":
                self._handle_detection_sensor(packet)
            elif portnum == "PAXCOUNTER_APP":
                self._handle_paxcounter(packet)
            else:
                # Forward any unhandled packet types to the console for visibility
                self._handle_unknown_packet(packet, portnum)
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
        """Handle telemetry updates - device, environment, air quality, and power metrics."""
        decoded = packet.get("decoded", {})
        telemetry = decoded.get("telemetry", {})
        from_id = packet.get("fromId")

        # Device metrics (battery, utilization, uptime)
        device_metrics = telemetry.get("deviceMetrics", {})
        if device_metrics:
            self._schedule_event("telemetry", {
                "node_id": from_id,
                "type": "device",
                "battery_level": device_metrics.get("batteryLevel"),
                "voltage": device_metrics.get("voltage"),
                "channel_utilization": device_metrics.get("channelUtilization"),
                "air_util_tx": device_metrics.get("airUtilTx"),
                "uptime_seconds": device_metrics.get("uptimeSeconds"),
                "timestamp": datetime.now().isoformat()
            })

        # Environment metrics (temperature, humidity, pressure)
        environment_metrics = telemetry.get("environmentMetrics", {})
        if environment_metrics:
            self._schedule_event("telemetry", {
                "node_id": from_id,
                "type": "environment",
                "temperature": environment_metrics.get("temperature"),
                "relative_humidity": environment_metrics.get("relativeHumidity"),
                "barometric_pressure": environment_metrics.get("barometricPressure"),
                "gas_resistance": environment_metrics.get("gasResistance"),
                "iaq": environment_metrics.get("iaq"),
                "distance": environment_metrics.get("distance"),
                "lux": environment_metrics.get("lux"),
                "white_lux": environment_metrics.get("whiteLux"),
                "ir_lux": environment_metrics.get("irLux"),
                "uv_lux": environment_metrics.get("uvLux"),
                "wind_direction": environment_metrics.get("windDirection"),
                "wind_speed": environment_metrics.get("windSpeed"),
                "weight": environment_metrics.get("weight"),
                "timestamp": datetime.now().isoformat()
            })

        # Air quality metrics
        air_quality_metrics = telemetry.get("airQualityMetrics", {})
        if air_quality_metrics:
            self._schedule_event("telemetry", {
                "node_id": from_id,
                "type": "air_quality",
                "pm10": air_quality_metrics.get("pm10Standard"),
                "pm25": air_quality_metrics.get("pm25Standard"),
                "pm100": air_quality_metrics.get("pm100Standard"),
                "pm10_env": air_quality_metrics.get("pm10Environmental"),
                "pm25_env": air_quality_metrics.get("pm25Environmental"),
                "pm100_env": air_quality_metrics.get("pm100Environmental"),
                "co2": air_quality_metrics.get("co2"),
                "timestamp": datetime.now().isoformat()
            })

        # Power metrics
        power_metrics = telemetry.get("powerMetrics", {})
        if power_metrics:
            self._schedule_event("telemetry", {
                "node_id": from_id,
                "type": "power",
                "ch1_voltage": power_metrics.get("ch1Voltage"),
                "ch1_current": power_metrics.get("ch1Current"),
                "ch2_voltage": power_metrics.get("ch2Voltage"),
                "ch2_current": power_metrics.get("ch2Current"),
                "ch3_voltage": power_metrics.get("ch3Voltage"),
                "ch3_current": power_metrics.get("ch3Current"),
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

    def _handle_routing(self, packet):
        """Handle routing/ACK packets."""
        decoded = packet.get("decoded", {})
        routing = decoded.get("routing", {})
        from_id = packet.get("fromId")
        to_id = packet.get("toId")
        request_id = packet.get("requestId")

        error_reason = routing.get("errorReason", "NONE")

        self._schedule_event("routing", {
            "from_node_id": from_id,
            "to_node_id": to_id,
            "request_id": request_id,
            "error_reason": error_reason,
            "raw": routing,
            "timestamp": datetime.now().isoformat()
        })

    def _handle_neighborinfo(self, packet):
        """Handle neighbor info packets - shows mesh topology."""
        decoded = packet.get("decoded", {})
        neighborinfo = decoded.get("neighborinfo", {})
        from_id = packet.get("fromId")

        neighbors = neighborinfo.get("neighbors", [])
        node_broadcast_interval_secs = neighborinfo.get("nodeBroadcastIntervalSecs")

        # Format neighbor data
        formatted_neighbors = []
        for neighbor in neighbors:
            formatted_neighbors.append({
                "node_id": f"!{neighbor.get('nodeId', 0):08x}" if isinstance(neighbor.get('nodeId'), int) else neighbor.get('nodeId'),
                "snr": neighbor.get("snr"),
            })

        logger.info(f"NeighborInfo from {from_id}: {len(formatted_neighbors)} neighbors")

        self._schedule_event("neighborinfo", {
            "from_node_id": from_id,
            "neighbors": formatted_neighbors,
            "node_broadcast_interval_secs": node_broadcast_interval_secs,
            "timestamp": datetime.now().isoformat()
        })

    def _handle_waypoint(self, packet):
        """Handle waypoint packets."""
        decoded = packet.get("decoded", {})
        waypoint = decoded.get("waypoint", {})
        from_id = packet.get("fromId")

        self._schedule_event("waypoint", {
            "from_node_id": from_id,
            "id": waypoint.get("id"),
            "name": waypoint.get("name"),
            "description": waypoint.get("description"),
            "latitude": waypoint.get("latitudeI", 0) / 1e7 if waypoint.get("latitudeI") else None,
            "longitude": waypoint.get("longitudeI", 0) / 1e7 if waypoint.get("longitudeI") else None,
            "expire": waypoint.get("expire"),
            "icon": waypoint.get("icon"),
            "timestamp": datetime.now().isoformat()
        })

    def _handle_admin(self, packet):
        """Handle admin packets."""
        decoded = packet.get("decoded", {})
        from_id = packet.get("fromId")

        self._schedule_event("admin", {
            "from_node_id": from_id,
            "raw": decoded,
            "timestamp": datetime.now().isoformat()
        })

    def _handle_range_test(self, packet):
        """Handle range test packets."""
        decoded = packet.get("decoded", {})
        from_id = packet.get("fromId")

        self._schedule_event("range_test", {
            "from_node_id": from_id,
            "payload": decoded.get("payload"),
            "timestamp": datetime.now().isoformat()
        })

    def _handle_store_forward(self, packet):
        """Handle store and forward packets."""
        decoded = packet.get("decoded", {})
        from_id = packet.get("fromId")

        self._schedule_event("store_forward", {
            "from_node_id": from_id,
            "raw": decoded,
            "timestamp": datetime.now().isoformat()
        })

    def _handle_detection_sensor(self, packet):
        """Handle detection sensor packets."""
        decoded = packet.get("decoded", {})
        from_id = packet.get("fromId")

        self._schedule_event("detection_sensor", {
            "from_node_id": from_id,
            "raw": decoded,
            "timestamp": datetime.now().isoformat()
        })

    def _handle_paxcounter(self, packet):
        """Handle paxcounter (people counter) packets."""
        decoded = packet.get("decoded", {})
        paxcounter = decoded.get("paxcounter", {})
        from_id = packet.get("fromId")

        self._schedule_event("paxcounter", {
            "from_node_id": from_id,
            "wifi": paxcounter.get("wifi"),
            "ble": paxcounter.get("ble"),
            "uptime": paxcounter.get("uptime"),
            "timestamp": datetime.now().isoformat()
        })

    def _handle_unknown_packet(self, packet, portnum):
        """Handle any unrecognized packet types - forward to console for visibility."""
        decoded = packet.get("decoded", {})
        from_id = packet.get("fromId", "unknown")
        to_id = packet.get("toId", "unknown")

        logger.info(f"Unknown packet type '{portnum}' from {from_id}")

        # Forward the raw packet data so users can see what's available
        self._schedule_event("raw_packet", {
            "portnum": portnum,
            "from_node_id": from_id,
            "to_node_id": to_id,
            "decoded": decoded,
            "rx_time": packet.get("rxTime"),
            "rx_snr": packet.get("rxSnr"),
            "rx_rssi": packet.get("rxRssi"),
            "hop_limit": packet.get("hopLimit"),
            "hop_start": packet.get("hopStart"),
            "timestamp": datetime.now().isoformat()
        })

    def _on_connection(self, interface, topic=pub.AUTO_TOPIC):
        """Handle connection events from BLE library."""
        # Just log here - don't broadcast yet, connect() will do that after interface is ready
        logger.info("BLE connection established callback received")

    def _on_disconnect(self, interface, topic=pub.AUTO_TOPIC):
        """Handle disconnection events."""
        was_connected = self._connected
        self._connected = False

        if self._intentional_disconnect:
            logger.info("[CONN] Disconnected from Meshtastic device (user requested)")
            self._schedule_event("connection", {"connected": False})
        else:
            logger.warning("[CONN] Unexpected disconnection from Meshtastic device")
            self._schedule_event("connection", {"connected": False, "unexpected": True})

            # Trigger auto-reconnect if we were previously connected
            if was_connected and self._main_loop:
                logger.info("[CONN] Scheduling auto-reconnect...")
                self._main_loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(self._auto_reconnect())
                )

    async def _auto_reconnect(self):
        """Attempt to automatically reconnect after unexpected disconnection."""
        if self._intentional_disconnect:
            logger.info("[CONN] Skipping auto-reconnect (intentional disconnect)")
            return

        # Cancel any existing reconnect task
        if self._reconnect_task and not self._reconnect_task.done():
            return  # Already reconnecting

        self._reconnect_attempts = 0

        while self._reconnect_attempts < self._max_reconnect_attempts:
            if self._intentional_disconnect or self._connected:
                logger.info("[CONN] Auto-reconnect cancelled")
                return

            self._reconnect_attempts += 1
            delay = self._reconnect_delay * self._reconnect_attempts  # Exponential backoff

            logger.info(f"[CONN] Auto-reconnect attempt {self._reconnect_attempts}/{self._max_reconnect_attempts} in {delay}s...")
            self._schedule_event("connection", {
                "connected": False,
                "reconnecting": True,
                "attempt": self._reconnect_attempts,
                "max_attempts": self._max_reconnect_attempts
            })

            await asyncio.sleep(delay)

            if self._intentional_disconnect or self._connected:
                return

            try:
                success = await self._connect_internal()
                if success:
                    logger.info("[CONN] Auto-reconnect successful!")
                    self._reconnect_attempts = 0
                    return
            except Exception as e:
                logger.error(f"[CONN] Auto-reconnect attempt {self._reconnect_attempts} failed: {e}")

        logger.error(f"[CONN] Auto-reconnect failed after {self._max_reconnect_attempts} attempts")
        self._schedule_event("connection", {
            "connected": False,
            "reconnect_failed": True
        })

    async def _connect_internal(self) -> bool:
        """Internal connect logic without lock (for reconnect use)."""
        try:
            # Clean up old subscriptions first
            try:
                pub.unsubscribe(self._on_receive, "meshtastic.receive")
                pub.unsubscribe(self._on_connection, "meshtastic.connection.established")
                pub.unsubscribe(self._on_disconnect, "meshtastic.connection.lost")
            except Exception:
                pass

            # Store the main event loop for thread-safe callbacks
            self._main_loop = asyncio.get_event_loop()

            logger.info(f"[CONN] Connecting to {self.settings.meshtastic_device_name}...")

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

            # Store the device address for future cleanup
            try:
                if hasattr(self.interface, 'bleak_client') and self.interface.bleak_client:
                    self._device_address = self.interface.bleak_client.address
                    logger.info(f"[CONN] Stored device address: {self._device_address}")
            except Exception as e:
                logger.debug(f"[CONN] Could not store device address: {e}")

            self._my_info = self.interface.myInfo
            self._metadata = self.interface.metadata
            self._nodes = self.interface.nodes
            self._connected = True
            self._intentional_disconnect = False  # Reset on successful connect
            self._close_failed = False  # Clear any previous close failures

            logger.info(f"[CONN] Connected! My node num: {self.my_node_num}")

            # Broadcast connection status now that everything is ready
            self._schedule_event("connection", self.get_connection_status())

            return True

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[CONN] Failed to connect: {error_msg}")
            self._connected = False

            # If device not found, do a scan and provide better error message
            if "not found" in error_msg.lower() or "no meshtastic" in error_msg.lower():
                logger.info("[CONN] Device not found, scanning to show available devices...")
                try:
                    scan_result = await self.scan_ble_devices()
                    self._last_scan_result = scan_result
                    self._last_error = self._format_device_not_found_error(scan_result)
                except Exception as scan_err:
                    logger.error(f"[CONN] Scan failed: {scan_err}")
                    self._last_error = error_msg
            else:
                self._last_error = error_msg

            return False

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @property
    def last_scan_result(self) -> Optional[dict]:
        return self._last_scan_result

    def _format_device_not_found_error(self, scan_result: dict) -> str:
        """Format a helpful error message when device is not found."""
        configured = scan_result.get("configured_device", "Unknown")
        meshtastic_devices = scan_result.get("meshtastic_devices", [])

        if meshtastic_devices:
            device_names = [d["name"] for d in meshtastic_devices]
            return (f"Device '{configured}' not found. "
                   f"Found {len(meshtastic_devices)} other Meshtastic device(s): {', '.join(device_names)}. "
                   f"Check your MESHTASTIC_DEVICE_NAME setting.")
        else:
            return (f"Device '{configured}' not found and no Meshtastic devices visible. "
                   f"Make sure the device is powered on and BLE is enabled. "
                   f"Try Reset BLE or restart the server.")

    async def connect(self) -> bool:
        """Connect to the Meshtastic device via BLE."""
        async with self._lock:
            if self.connected:
                return True

            # If previous close failed, try to clean up BLE first
            if self._close_failed:
                logger.info("[CONN] Previous disconnect had issues, attempting BLE cleanup...")

                # First, try force cleanup if we have a device address
                if self._device_address:
                    await self._force_ble_cleanup()
                    await asyncio.sleep(2)  # Give BLE time to settle

                # Check if device is now visible
                found = await self._scan_for_device()
                if not found:
                    logger.warning("[CONN] Device still not visible after cleanup")
                    # Get scan results to show user what's available
                    scan_result = await self.scan_ble_devices()
                    self._last_scan_result = scan_result
                    self._last_error = self._format_device_not_found_error(scan_result)
                    return False

                self._close_failed = False

            # User is requesting connection, so clear intentional disconnect flag
            self._intentional_disconnect = False
            return await self._connect_internal()

    async def disconnect(self):
        """Disconnect from the Meshtastic device."""
        logger.info("[CONN] User-requested disconnect")

        # Set flag BEFORE disconnecting to prevent auto-reconnect
        self._intentional_disconnect = True
        self._close_failed = False  # Track if close had issues

        async with self._lock:
            # Unsubscribe from events FIRST to prevent callbacks during close
            try:
                pub.unsubscribe(self._on_receive, "meshtastic.receive")
                pub.unsubscribe(self._on_connection, "meshtastic.connection.established")
                pub.unsubscribe(self._on_disconnect, "meshtastic.connection.lost")
            except Exception:
                pass

            if not self.interface:
                logger.info("[CONN] No active interface to disconnect")
                self._connected = False
                return

            if self.interface:
                interface_to_close = self.interface

                # Store the device address before closing for potential cleanup
                try:
                    if hasattr(interface_to_close, 'bleak_client') and interface_to_close.bleak_client:
                        self._device_address = interface_to_close.bleak_client.address
                        logger.info(f"[CONN] Stored device address for cleanup: {self._device_address}")
                except Exception:
                    pass

                # Clear our reference immediately to prevent race conditions
                self.interface = None
                self._connected = False
                self._my_info = None
                self._metadata = None
                self._nodes = {}

                try:
                    logger.info("Closing BLE interface...")
                    # Close with timeout to prevent hanging
                    loop = asyncio.get_event_loop()
                    await asyncio.wait_for(
                        loop.run_in_executor(None, interface_to_close.close),
                        timeout=5.0
                    )
                    logger.info("BLE interface closed successfully")
                except asyncio.TimeoutError:
                    logger.warning("BLE close timed out - attempting force cleanup...")
                    self._close_failed = True

                    # Try force cleanup using bleak directly
                    if self._device_address:
                        cleanup_success = await self._force_ble_cleanup()
                        if cleanup_success:
                            logger.info("Force BLE cleanup successful")
                            self._close_failed = False
                        else:
                            logger.warning("Force cleanup failed - device may need server restart")
                            self._last_error = "BLE close timed out - try Reset BLE or restart server"
                    else:
                        self._last_error = "BLE close timed out - device may need time to release"

                except Exception as e:
                    logger.error(f"Error disconnecting: {e}")
                    self._close_failed = True
                finally:
                    # Emit disconnection event BEFORE clearing main_loop
                    self._schedule_event("connection", self.get_connection_status())
                    self._main_loop = None

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
