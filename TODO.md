# Meshtastic Dashboard - Feature Roadmap

## In Progress
- [ ] **Traceroute Visualization** - See the path packets take through the mesh, visualize routing on map

## Planned Features

### Mesh Network Analysis
- [ ] **Neighbor Info** - Which nodes can directly hear which other nodes (mesh topology graph)
- [ ] **Signal Metrics** - SNR/RSSI per node to show link quality
- [ ] **Mesh Topology Graph** - Interactive visualization of node connections

### Location Features
- [ ] **Waypoints** - Create, share, and display waypoints on the map
- [ ] **Signal Strength Heatmap** - Map overlay showing coverage areas

### Extended Telemetry
- [ ] **Environment Sensors** - Temperature, humidity, barometric pressure (BME280/BME680)
- [ ] **Power Telemetry** - Solar panel voltage, current draw
- [ ] **Historical Charts** - Graph telemetry over time (battery trends, channel utilization)

### Communication
- [ ] **Range Test Module** - Test signal range with SNR/RSSI logging
- [ ] **Detection Sensor Alerts** - Motion/door sensor notifications
- [ ] **Store & Forward** - View stored messages on repeater nodes

### Device Management
- [ ] **Device Configuration** - Read/write radio settings, channels
- [ ] **Remote Admin** - Request position/telemetry from specific nodes

### User Experience
- [ ] **Browser Notifications** - Alerts for new messages, nodes going offline, low battery
- [ ] **Export Data** - Download message history, node list as CSV/JSON
- [ ] **Dark/Light Theme Toggle** - User preference for UI theme

## Completed
- [x] Real-time node discovery and status monitoring
- [x] Interactive map with node positions
- [x] Channel and direct messaging with ACK tracking
- [x] Device telemetry (battery, ChUtil, AirUtilTx, uptime)
- [x] WebSocket-based live updates
- [x] Collapsible sidebar
- [x] "My Device" identification on map
- [x] Informative tooltips for telemetry metrics

## Notes
- Test each feature thoroughly before moving to the next
- Reference Meshtastic documentation for correct implementation
- Maintain backwards compatibility with existing functionality
