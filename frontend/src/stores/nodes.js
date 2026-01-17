import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

// Status thresholds in milliseconds
// Per Meshtastic docs: "online" = heard in last 2 hours (used by firmware for mesh scaling)
const ONLINE_THRESHOLD = 2 * 60 * 60 * 1000   // 2 hours - matches Meshtastic "online" definition
const RECENT_THRESHOLD = 24 * 60 * 60 * 1000  // 24 hours - seen today

export const useNodesStore = defineStore('nodes', () => {
  const nodes = ref({})
  const loading = ref(false)
  const error = ref(null)
  const pollInterval = ref(null)
  const lastPollTime = ref(null)

  // Traceroute state
  const tracerouteInProgress = ref(false)
  const tracerouteTarget = ref(null)
  const tracerouteResult = ref(null)
  const tracerouteError = ref(null)
  let tracerouteTimeout = null // Timeout handle for traceroute

  // Get node status based on last_heard
  // isConnectedDevice flag indicates this is the device we're directly connected to
  function getNodeStatus(node, isConnectedDevice = false) {
    // If this is our connected device, it's always online
    if (isConnectedDevice) return 'online'

    if (!node || !node.last_heard) return 'unknown'

    const lastHeard = new Date(node.last_heard).getTime()
    const now = Date.now()
    const diff = now - lastHeard

    if (diff <= ONLINE_THRESHOLD) return 'online'
    if (diff <= RECENT_THRESHOLD) return 'recent'
    return 'offline'
  }

  // Helper to check if a node is our connected device
  function isMyNode(node, myNodeNum) {
    if (!node || !myNodeNum) return false
    const myNodeId = `!${myNodeNum.toString(16).padStart(8, '0')}`
    return node.id === myNodeId
  }

  // Check if node is online
  function isNodeOnline(node) {
    return getNodeStatus(node) === 'online'
  }

  // Get status color class
  function getStatusColor(node) {
    const status = getNodeStatus(node)
    switch (status) {
      case 'online': return 'bg-green-500'
      case 'recent': return 'bg-yellow-500'
      case 'offline': return 'bg-gray-500'
      default: return 'bg-gray-400'
    }
  }

  // Get status text
  function getStatusText(node) {
    const status = getNodeStatus(node)
    switch (status) {
      case 'online': return 'Online'
      case 'recent': return 'Seen today'
      case 'offline': return 'Offline'
      default: return 'Unknown'
    }
  }

  const nodeList = computed(() => {
    return Object.values(nodes.value).sort((a, b) => {
      // Sort by online status first, then by last_heard
      const aStatus = getNodeStatus(a)
      const bStatus = getNodeStatus(b)
      const statusOrder = { online: 0, recent: 1, offline: 2, unknown: 3 }

      if (statusOrder[aStatus] !== statusOrder[bStatus]) {
        return statusOrder[aStatus] - statusOrder[bStatus]
      }

      // Then sort by last_heard descending
      const aTime = a.last_heard ? new Date(a.last_heard).getTime() : 0
      const bTime = b.last_heard ? new Date(b.last_heard).getTime() : 0
      return bTime - aTime
    })
  })

  // Count nodes by status
  const onlineCount = computed(() => nodeList.value.filter(n => getNodeStatus(n) === 'online').length)
  const recentCount = computed(() => nodeList.value.filter(n => getNodeStatus(n) === 'recent').length)
  const offlineCount = computed(() => nodeList.value.filter(n => getNodeStatus(n) === 'offline').length)
  const unknownCount = computed(() => nodeList.value.filter(n => getNodeStatus(n) === 'unknown').length)

  const nodesWithPosition = computed(() => {
    return nodeList.value.filter(n => n.latitude && n.longitude)
  })

  const nodeCount = computed(() => Object.keys(nodes.value).length)

  async function fetchNodes() {
    // Only show loading state if we have no data yet (initial load)
    const isInitialLoad = Object.keys(nodes.value).length === 0
    if (isInitialLoad) {
      loading.value = true
    }
    error.value = null
    try {
      const response = await axios.get('/api/nodes/live')
      // Transform from object to our format
      const statusBreakdown = { online: [], recent: [], offline: [], unknown: [] }
      const newNodes = {}

      for (const [id, data] of Object.entries(response.data)) {
        const transformed = transformNode(id, data)
        newNodes[id] = transformed

        const status = getNodeStatus(transformed)
        statusBreakdown[status].push({
          name: transformed.long_name || transformed.short_name || id.slice(-8),
          lastHeard: data.lastHeard,
          lastHeardFormatted: transformed.last_heard
        })
      }

      // Batch update: merge new data into existing nodes to preserve reactivity
      // Update existing nodes and add new ones
      for (const [id, node] of Object.entries(newNodes)) {
        if (nodes.value[id]) {
          // Update existing node properties without replacing the object
          Object.assign(nodes.value[id], node)
        } else {
          nodes.value[id] = node
        }
      }

      // Detailed debug logging
      console.log(`[nodes] === Node Status Breakdown ===`)
      console.log(`[nodes] Total: ${Object.keys(nodes.value).length}`)
      console.log(`[nodes] Online (${statusBreakdown.online.length}):`, statusBreakdown.online.map(n => `${n.name} (${n.lastHeard})`).join(', '))
      console.log(`[nodes] Recent (${statusBreakdown.recent.length}):`, statusBreakdown.recent.map(n => n.name).join(', '))
      console.log(`[nodes] Offline (${statusBreakdown.offline.length}):`, statusBreakdown.offline.map(n => n.name).join(', '))
      console.log(`[nodes] Unknown (${statusBreakdown.unknown.length}):`, statusBreakdown.unknown.map(n => n.name).join(', '))
      console.log(`[nodes] Counts: Online=${onlineCount.value}, Recent=${recentCount.value}, Offline=${offlineCount.value}, Unknown=${unknownCount.value}`)
    } catch (err) {
      error.value = err.message
      console.error('Failed to fetch nodes:', err)
    } finally {
      if (isInitialLoad) {
        loading.value = false
      }
    }
  }

  async function syncNodes() {
    try {
      await axios.post('/api/nodes/sync')
      await fetchNodes()
    } catch (err) {
      console.error('Failed to sync nodes:', err)
    }
  }

  function transformNode(id, data) {
    const user = data.user || {}
    const position = data.position || {}
    const deviceMetrics = data.deviceMetrics || {}

    return {
      id,
      num: data.num,
      long_name: user.longName,
      short_name: user.shortName,
      hw_model: user.hwModel,
      role: user.role,
      latitude: position.latitude,
      longitude: position.longitude,
      altitude: position.altitude,
      battery_level: deviceMetrics.batteryLevel,
      voltage: deviceMetrics.voltage,
      channel_utilization: deviceMetrics.channelUtilization,
      air_util_tx: deviceMetrics.airUtilTx,
      uptime_seconds: deviceMetrics.uptimeSeconds,
      snr: data.snr,
      hops_away: data.hopsAway,
      // Handle lastHeard: 0 is falsy but valid (epoch), null/undefined means no data
      last_heard: data.lastHeard != null ? new Date(data.lastHeard * 1000).toISOString() : null,
      is_favorite: data.isFavorite || false
    }
  }

  function updateNode(data) {
    const id = data.id
    if (nodes.value[id]) {
      nodes.value[id] = { ...nodes.value[id], ...data }
    } else {
      nodes.value[id] = data
    }
  }

  function updateTelemetry(data) {
    const id = data.node_id
    if (nodes.value[id]) {
      if (data.battery_level != null) nodes.value[id].battery_level = data.battery_level
      if (data.voltage != null) nodes.value[id].voltage = data.voltage
      if (data.channel_utilization != null) nodes.value[id].channel_utilization = data.channel_utilization
      if (data.air_util_tx != null) nodes.value[id].air_util_tx = data.air_util_tx
      if (data.uptime_seconds != null) nodes.value[id].uptime_seconds = data.uptime_seconds
    }
  }

  function updatePosition(data) {
    const id = data.node_id
    if (nodes.value[id]) {
      nodes.value[id].latitude = data.latitude
      nodes.value[id].longitude = data.longitude
      nodes.value[id].altitude = data.altitude
    }
  }

  function getNode(id) {
    return nodes.value[id]
  }

  // Start polling for node updates
  function startPolling(intervalMs = 30000) {
    if (pollInterval.value) {
      console.log('[nodes] Polling already active')
      return
    }

    console.log('[nodes] Starting polling every', intervalMs / 1000, 'seconds')
    pollInterval.value = setInterval(async () => {
      try {
        await fetchNodes()
        lastPollTime.value = new Date().toISOString()
        console.log('[nodes] Polled nodes, count:', nodeCount.value)
      } catch (err) {
        console.error('[nodes] Poll failed:', err)
      }
    }, intervalMs)
  }

  // Stop polling
  function stopPolling() {
    if (pollInterval.value) {
      clearInterval(pollInterval.value)
      pollInterval.value = null
      console.log('[nodes] Stopped polling')
    }
  }

  // Send traceroute request to a node
  async function sendTraceroute(nodeId, hopLimit = 3, channel = 0) {
    // Clear any existing timeout
    if (tracerouteTimeout) {
      clearTimeout(tracerouteTimeout)
      tracerouteTimeout = null
    }

    tracerouteInProgress.value = true
    tracerouteTarget.value = nodeId
    tracerouteResult.value = null
    tracerouteError.value = null

    try {
      const response = await axios.post(`/api/nodes/${encodeURIComponent(nodeId)}/traceroute`, null, {
        params: { hop_limit: hopLimit, channel }
      })
      console.log('[nodes] Traceroute request sent:', response.data)

      // Set a 30-second timeout for the response
      tracerouteTimeout = setTimeout(() => {
        if (tracerouteInProgress.value && tracerouteTarget.value === nodeId) {
          console.log('[nodes] Traceroute timed out for:', nodeId)
          tracerouteError.value = 'Traceroute timed out - node may be offline or unreachable'
          tracerouteInProgress.value = false
        }
      }, 30000) // 30 seconds

      return true
    } catch (err) {
      console.error('[nodes] Failed to send traceroute:', err)
      tracerouteError.value = err.message
      tracerouteInProgress.value = false
      return false
    }
  }

  // Handle traceroute response from WebSocket
  function handleTracerouteResponse(data) {
    console.log('[nodes] Traceroute response received:', data)

    // Clear the timeout since we got a response
    if (tracerouteTimeout) {
      clearTimeout(tracerouteTimeout)
      tracerouteTimeout = null
    }

    tracerouteResult.value = {
      from: data.from_node_id,
      to: data.to_node_id,
      route: data.route || [],
      routeBack: data.route_back || [],
      snrTowards: data.snr_towards || [],
      snrBack: data.snr_back || [],
      timestamp: data.timestamp
    }
    tracerouteInProgress.value = false
  }

  // Handle traceroute error from WebSocket (routing error, timeout, etc.)
  function handleTracerouteError(data) {
    console.log('[nodes] Traceroute error received:', data)

    // Clear the timeout
    if (tracerouteTimeout) {
      clearTimeout(tracerouteTimeout)
      tracerouteTimeout = null
    }

    // Map Meshtastic error codes to user-friendly messages
    const errorMessages = {
      'NO_ROUTE': 'No route to destination - node may be offline',
      'TIMEOUT': 'Request timed out - node did not respond',
      'NO_RESPONSE': 'No response from node',
      'MAX_RETRANSMIT': 'Maximum retransmits exceeded - node unreachable',
      'GOT_NAK': 'Received NAK - node rejected request',
      'NO_CHANNEL': 'No channel available'
    }

    const errorCode = data.error || 'UNKNOWN'
    tracerouteError.value = errorMessages[errorCode] || `Traceroute failed: ${errorCode}`
    tracerouteInProgress.value = false
  }

  // Clear traceroute results
  function clearTraceroute() {
    if (tracerouteTimeout) {
      clearTimeout(tracerouteTimeout)
      tracerouteTimeout = null
    }
    tracerouteInProgress.value = false
    tracerouteTarget.value = null
    tracerouteResult.value = null
    tracerouteError.value = null
  }

  return {
    nodes,
    nodeList,
    nodesWithPosition,
    nodeCount,
    onlineCount,
    recentCount,
    offlineCount,
    unknownCount,
    loading,
    error,
    lastPollTime,
    // Traceroute
    tracerouteInProgress,
    tracerouteTarget,
    tracerouteResult,
    tracerouteError,
    // Methods
    fetchNodes,
    syncNodes,
    updateNode,
    updateTelemetry,
    updatePosition,
    getNode,
    getNodeStatus,
    isNodeOnline,
    isMyNode,
    getStatusColor,
    getStatusText,
    startPolling,
    stopPolling,
    sendTraceroute,
    handleTracerouteResponse,
    handleTracerouteError,
    clearTraceroute
  }
})
