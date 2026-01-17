import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { useNodesStore } from './nodes'
import { useMessagesStore } from './messages'

export const useConnectionStore = defineStore('connection', () => {
  const connected = ref(false)
  const deviceName = ref(null)
  const myNodeNum = ref(null)
  const firmwareVersion = ref(null)
  const hwModel = ref(null)
  const ws = ref(null)
  const wsConnected = ref(false)

  const status = computed(() => ({
    connected: connected.value,
    deviceName: deviceName.value,
    myNodeNum: myNodeNum.value,
    firmwareVersion: firmwareVersion.value,
    hwModel: hwModel.value
  }))

  async function fetchStatus() {
    try {
      const wasConnected = connected.value
      const response = await axios.get('/api/connection')
      updateStatus(response.data)

      // If we just discovered we're connected, fetch the data
      if (!wasConnected && response.data.connected) {
        console.log('fetchStatus: discovered connection, fetching data...')
        const nodesStore = useNodesStore()
        const messagesStore = useMessagesStore()
        await nodesStore.fetchNodes()
        await messagesStore.fetchChannels()
      }
    } catch (error) {
      console.error('Failed to fetch connection status:', error)
    }
  }

  function updateStatus(data) {
    connected.value = data.connected
    deviceName.value = data.device_name
    myNodeNum.value = data.my_node_num
    firmwareVersion.value = data.firmware_version
    hwModel.value = data.hw_model
  }

  async function connect() {
    try {
      const response = await axios.post('/api/connection/connect')
      updateStatus(response.data)

      // Fetch nodes and messages after connecting
      const nodesStore = useNodesStore()
      const messagesStore = useMessagesStore()
      await nodesStore.fetchNodes()
      await messagesStore.fetchMessages()
      await messagesStore.fetchChannels()

      // Start polling for node updates (every 10 seconds)
      nodesStore.startPolling(10000)

      return true
    } catch (error) {
      console.error('Failed to connect:', error)
      return false
    }
  }

  async function disconnect() {
    try {
      console.log('Disconnect request initiated...')

      // Stop polling
      const nodesStore = useNodesStore()
      nodesStore.stopPolling()

      await axios.post('/api/connection/disconnect')
      console.log('Disconnect successful')
      connected.value = false
      deviceName.value = null
      myNodeNum.value = null
      firmwareVersion.value = null
      hwModel.value = null
    } catch (error) {
      console.error('Failed to disconnect:', error)
    }
  }

  function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`

    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      console.log('WebSocket connected')
      wsConnected.value = true
    }

    ws.value.onclose = () => {
      console.log('WebSocket disconnected')
      wsConnected.value = false
      // Reconnect after 3 seconds
      setTimeout(initWebSocket, 3000)
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.value.onmessage = async (event) => {
      try {
        const message = JSON.parse(event.data)
        await handleWebSocketMessage(message)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }
  }

  async function handleWebSocketMessage(message) {
    const nodesStore = useNodesStore()
    const messagesStore = useMessagesStore()

    switch (message.type) {
      case 'connection':
        const wasConnected = connected.value
        console.log('Connection status received:', message.data)
        console.log('Was connected:', wasConnected, 'Now connected:', message.data.connected)
        updateStatus(message.data)

        if (message.data.connected) {
          // Always ensure polling is running when connected
          // startPolling() is idempotent - it won't start twice
          nodesStore.startPolling(10000) // Poll every 10 seconds for near real-time updates

          // If we just learned we're connected, fetch initial data
          if (!wasConnected) {
            console.log('Fetching nodes and channels after reconnect...')
            try {
              await nodesStore.fetchNodes()
              console.log('Nodes fetched:', nodesStore.nodeCount)
              await messagesStore.fetchChannels()
              console.log('Channels fetched')
            } catch (err) {
              console.error('Error fetching data on reconnect:', err)
            }
          }
        } else {
          // Stop polling if we disconnected
          nodesStore.stopPolling()
        }
        break
      case 'message':
        messagesStore.addMessage(message.data)
        break
      case 'node_update':
        nodesStore.updateNode(message.data)
        break
      case 'telemetry':
        nodesStore.updateTelemetry(message.data)
        break
      case 'position':
        nodesStore.updatePosition(message.data)
        break
      case 'pong':
        // Heartbeat response
        break
      case 'broadcast_progress':
        // Emit event for broadcast progress - handled by Messages view
        window.dispatchEvent(new CustomEvent('broadcast-progress', { detail: message.data }))
        break
      case 'ack':
        // Update message ACK status in store
        messagesStore.markMessageAcked(message.data)
        break
      case 'traceroute':
        // Handle traceroute response
        nodesStore.handleTracerouteResponse(message.data)
        break
      case 'traceroute_error':
        // Handle traceroute error/timeout from backend
        console.log('Traceroute error:', message.data)
        nodesStore.handleTracerouteError(message.data)
        break
      case 'traceroute_sent':
        // Traceroute request was sent successfully
        console.log('Traceroute sent:', message.data)
        break
    }
  }

  function sendWebSocketMessage(type, data = {}) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type, ...data }))
    }
  }

  function closeWebSocket() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
  }

  return {
    connected,
    deviceName,
    myNodeNum,
    firmwareVersion,
    hwModel,
    wsConnected,
    status,
    fetchStatus,
    connect,
    disconnect,
    initWebSocket,
    sendWebSocketMessage,
    closeWebSocket
  }
})
