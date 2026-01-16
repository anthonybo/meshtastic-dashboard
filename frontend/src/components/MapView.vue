<template>
  <div class="h-full w-full rounded-lg overflow-hidden border border-gray-700 relative">
    <div ref="mapContainer" class="h-full w-full"></div>
    <!-- My Device Button -->
    <button
      v-if="myNodeWithPosition"
      @click="zoomToMyDevice"
      class="absolute top-3 right-3 z-[1000] flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 border border-mesh-500 text-white text-sm rounded-lg shadow-lg transition-colors"
      title="Zoom to my device"
    >
      <svg class="w-4 h-4 text-mesh-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
      </svg>
      My Device
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNodesStore } from '../stores/nodes'
import { useConnectionStore } from '../stores/connection'
import { useMessagesStore } from '../stores/messages'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const route = useRoute()
const router = useRouter()
const nodesStore = useNodesStore()
const connectionStore = useConnectionStore()
const messagesStore = useMessagesStore()
const mapContainer = ref(null)
let map = null
let markers = {}
let initialBoundsFit = false // Track if we've done the initial fitBounds

// Get my node's ID
const myNodeId = computed(() => {
  if (!connectionStore.myNodeNum) return null
  return `!${connectionStore.myNodeNum.toString(16).padStart(8, '0')}`
})

// Check if my node has a position
const myNodeWithPosition = computed(() => {
  if (!myNodeId.value) return null
  return nodesStore.nodesWithPosition.find(n => n.id === myNodeId.value)
})

// Check if a node is my device
function isMyDevice(node) {
  return node.id === myNodeId.value
}

// Zoom to my device
function zoomToMyDevice() {
  const myNode = myNodeWithPosition.value
  if (myNode && map) {
    map.setView([myNode.latitude, myNode.longitude], 15)
    if (markers[myNode.id]) {
      markers[myNode.id].openPopup()
    }
  }
}

// Handle message button click from popup
function handlePopupMessageClick(nodeId) {
  messagesStore.setSelectedConversation(nodeId)
  router.push('/messages')
}

// Setup popup click handler
function setupPopupClickHandler() {
  document.addEventListener('click', (e) => {
    const messageBtn = e.target.closest('.popup-message-btn')
    if (messageBtn) {
      const nodeId = messageBtn.dataset.nodeId
      if (nodeId) {
        handlePopupMessageClick(nodeId)
      }
    }
  })
}

onMounted(() => {
  initMap()
  setupPopupClickHandler()
})

onUnmounted(() => {
  if (map) {
    map.remove()
  }
  // Reset state for next mount
  map = null
  markers = {}
  initialBoundsFit = false
})

watch(() => nodesStore.nodesWithPosition, updateMarkers, { deep: true })

// Watch for route query changes to focus on a node
watch(() => route.query, (query) => {
  if (query.node && query.lat && query.lng) {
    focusOnNode(query.node, parseFloat(query.lat), parseFloat(query.lng))
  }
}, { immediate: true })

function initMap() {
  if (!mapContainer.value) return

  // Check if we have a specific node to focus on
  const query = route.query
  const hasTarget = query.lat && query.lng
  const initialCenter = hasTarget
    ? [parseFloat(query.lat), parseFloat(query.lng)]
    : [34.6, -112.4]
  const initialZoom = hasTarget ? 14 : 10

  map = L.map(mapContainer.value, {
    center: initialCenter,
    zoom: initialZoom,
    zoomControl: true
  })

  // Stadia Alidade Smooth Dark - cleaner dark theme with visible labels
  L.tileLayer('https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 20
  }).addTo(map)

  updateMarkers()

  // Focus on target node after markers are created
  if (query.node && hasTarget) {
    setTimeout(() => {
      focusOnNode(query.node, parseFloat(query.lat), parseFloat(query.lng))
    }, 100)
  }
}

function updateMarkers() {
  if (!map) return

  const nodes = nodesStore.nodesWithPosition

  // Remove old markers that are no longer in the list
  Object.keys(markers).forEach(id => {
    if (!nodes.find(n => n.id === id)) {
      map.removeLayer(markers[id])
      delete markers[id]
    }
  })

  // Add or update markers
  nodes.forEach(node => {
    const position = [node.latitude, node.longitude]

    if (markers[node.id]) {
      // Update position and icon (for status changes)
      markers[node.id].setLatLng(position)
      markers[node.id].setIcon(createNodeIcon(node))
      markers[node.id].setPopupContent(createPopupContent(node))
    } else {
      // Create new marker
      const icon = createNodeIcon(node)
      const marker = L.marker(position, { icon }).addTo(map)
      marker.bindPopup(createPopupContent(node))
      markers[node.id] = marker
    }
  })

  // Fit bounds to all markers only on initial load (not during updates)
  // This prevents the map from jumping around when the user has zoomed/panned
  if (!initialBoundsFit && nodes.length > 0 && Object.keys(markers).length > 0) {
    const group = L.featureGroup(Object.values(markers))
    map.fitBounds(group.getBounds().pad(0.1))
    initialBoundsFit = true
  }
}

function createNodeIcon(node) {
  const isMine = isMyDevice(node)
  const color = isMine ? '#06b6d4' : getNodeColor(node) // cyan for my device
  const borderColor = isMine ? '#0891b2' : getNodeBorderColor(node)
  const statusColor = isMine ? '#22c55e' : getStatusColor(node) // Always green for connected device
  const displayName = node.short_name || node.id?.slice(-4) || '??'
  const status = isMine ? 'online' : nodesStore.getNodeStatus(node)
  const pulseClass = status === 'online' ? 'status-pulse' : ''
  // Add a special ring for my device
  const myDeviceRing = isMine ? 'box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.5), 0 4px 12px rgba(0, 0, 0, 0.4);' : 'box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);'

  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div class="node-marker">
        <div class="node-marker-circle" style="background: ${color}; border-color: ${borderColor}; ${myDeviceRing}">
          <span class="node-marker-text">${displayName}</span>
        </div>
        <div class="node-marker-arrow" style="border-top-color: ${color};"></div>
        <div class="node-status-dot ${pulseClass}" style="background: ${statusColor};"></div>
        ${isMine ? '<div class="my-device-label">ME</div>' : ''}
      </div>
    `,
    iconSize: [44, 52],
    iconAnchor: [22, 52],
    popupAnchor: [0, -52]
  })
}

function createPopupContent(node) {
  const isMine = isMyDevice(node)
  const statusText = isMine ? 'Connected' : nodesStore.getStatusText(node)
  const statusColor = isMine ? '#22c55e' : getStatusColor(node)

  // Message button (only for other nodes, not my device)
  const messageButton = !isMine ? `
    <div class="node-popup-actions">
      <button class="popup-message-btn" data-node-id="${node.id}">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
        </svg>
        Send Message
      </button>
    </div>
  ` : ''

  return `
    <div class="node-popup">
      <div class="node-popup-header">
        <div class="node-popup-name">${node.long_name || 'Unknown Node'}${isMine ? ' <span style="color: #06b6d4; font-size: 11px;">(This Device)</span>' : ''}</div>
        <div class="node-popup-status" style="background: ${statusColor}20; border: 1px solid ${statusColor};">
          <span class="node-popup-status-dot" style="background: ${statusColor};"></span>
          ${statusText}
        </div>
      </div>
      <div class="node-popup-id">${node.id}</div>
      ${node.hw_model ? `<div class="node-popup-detail"><span class="label">Model:</span> ${node.hw_model}</div>` : ''}
      ${node.battery_level ? `<div class="node-popup-detail"><span class="label">Battery:</span> ${node.battery_level}%</div>` : ''}
      ${node.altitude ? `<div class="node-popup-detail"><span class="label">Altitude:</span> ${node.altitude}m</div>` : ''}
      ${!isMine && node.hops_away !== null && node.hops_away !== undefined ? `<div class="node-popup-detail"><span class="label">Hops:</span> ${node.hops_away === 0 ? 'Direct' : node.hops_away}</div>` : ''}
      ${isMine ? '<div class="node-popup-detail"><span class="label">Status:</span> <span style="color: #22c55e;">Active</span></div>' : (node.last_heard ? `<div class="node-popup-detail"><span class="label">Last heard:</span> ${formatLastHeard(node.last_heard)}</div>` : '')}
      ${messageButton}
    </div>
  `
}

function getNodeColor(node) {
  // Color based on hops - return hex colors
  if (node.hops_away === 0) return '#22c55e' // green-500
  if (node.hops_away <= 2) return '#eab308' // yellow-500
  if (node.hops_away <= 4) return '#f97316' // orange-500
  return '#ef4444' // red-500
}

function getNodeBorderColor(node) {
  // Darker border color
  if (node.hops_away === 0) return '#16a34a' // green-600
  if (node.hops_away <= 2) return '#ca8a04' // yellow-600
  if (node.hops_away <= 4) return '#ea580c' // orange-600
  return '#dc2626' // red-600
}

function getStatusColor(node) {
  const status = nodesStore.getNodeStatus(node)
  switch (status) {
    case 'online': return '#22c55e'  // green-500
    case 'recent': return '#eab308'  // yellow-500
    case 'offline': return '#6b7280' // gray-500
    default: return '#9ca3af'        // gray-400
  }
}

function formatLastHeard(timestamp) {
  if (!timestamp) return 'Unknown'
  const date = new Date(timestamp)
  const now = new Date()
  const diff = (now - date) / 1000

  if (diff < 60) return 'Just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return date.toLocaleDateString()
}

function focusOnNode(nodeId, lat, lng) {
  if (!map) return

  // Center map on the node with a good zoom level
  map.setView([lat, lng], 14)

  // Open the popup for this node if marker exists
  if (markers[nodeId]) {
    markers[nodeId].openPopup()
  }
}
</script>

<style>
/* Marker styles */
.custom-marker {
  background: transparent !important;
  border: none !important;
}

.node-marker {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.node-marker-circle {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 3px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.node-marker-text {
  color: white;
  font-size: 11px;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
  text-align: center;
  line-height: 1.1;
  max-width: 36px;
  overflow: hidden;
}

.node-marker-arrow {
  width: 0;
  height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 10px solid;
  margin-top: -2px;
}

.node-status-dot {
  position: absolute;
  top: 0;
  right: 0;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #1e293b;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.node-status-dot.status-pulse {
  animation: statusPulse 2s ease-in-out infinite;
}

@keyframes statusPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.1); }
}

/* My device label */
.my-device-label {
  position: absolute;
  top: -8px;
  left: 50%;
  transform: translateX(-50%);
  background: #06b6d4;
  color: white;
  font-size: 9px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 4px;
  border: 1px solid #0891b2;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

/* Popup styles - dark theme */
.leaflet-popup-content-wrapper {
  background: #1e293b;
  color: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
  border: 1px solid #334155;
  padding: 0;
}

.leaflet-popup-tip {
  background: #1e293b;
  border-left: 1px solid #334155;
  border-bottom: 1px solid #334155;
}

.leaflet-popup-content {
  margin: 0;
  min-width: 180px;
}

.node-popup {
  padding: 12px 16px;
}

.node-popup-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.node-popup-name {
  font-size: 16px;
  font-weight: 700;
  color: #f1f5f9;
}

.node-popup-status {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  color: #f1f5f9;
}

.node-popup-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.node-popup-id {
  font-size: 11px;
  color: #94a3b8;
  font-family: monospace;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #334155;
}

.node-popup-detail {
  font-size: 13px;
  color: #e2e8f0;
  margin-bottom: 4px;
}

.node-popup-detail .label {
  color: #94a3b8;
  font-weight: 500;
}

.node-popup-detail:last-child {
  margin-bottom: 0;
}

/* Popup actions */
.node-popup-actions {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #334155;
}

.popup-message-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.popup-message-btn:hover {
  background: #2563eb;
}

.popup-message-btn svg {
  flex-shrink: 0;
}

/* Close button */
.leaflet-popup-close-button {
  color: #94a3b8 !important;
  font-size: 20px !important;
  padding: 8px !important;
}

.leaflet-popup-close-button:hover {
  color: #f1f5f9 !important;
}
</style>
