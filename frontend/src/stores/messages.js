import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { useConnectionStore } from './connection'

export const useMessagesStore = defineStore('messages', () => {
  const messages = ref([])
  const channels = ref([])
  const loading = ref(false)
  const sending = ref(false)
  const selectedChannel = ref(0) // Currently selected channel index for broadcast
  const dmRecipient = ref(null) // For direct messages: { id, long_name, short_name }
  const selectedConversation = ref(null) // null = channel view, node_id = DM conversation
  const viewMode = ref('channel') // 'channel' or 'dm'

  const sortedMessages = computed(() => {
    return [...messages.value].sort((a, b) => {
      return new Date(b.timestamp) - new Date(a.timestamp)
    })
  })

  const recentMessages = computed(() => {
    return sortedMessages.value.slice(0, 10)
  })

  // Get unique conversations (nodes we've messaged or received from)
  const conversations = computed(() => {
    const connectionStore = useConnectionStore()
    const myNodeId = connectionStore.myNodeNum
      ? `!${connectionStore.myNodeNum.toString(16).padStart(8, '0')}`
      : null

    const convMap = new Map()

    for (const msg of messages.value) {
      // For outgoing DMs, the conversation is with to_node_id
      // For incoming DMs, the conversation is with from_node_id
      // Skip broadcast messages (to_node_id is null or '^all')

      let otherNodeId = null

      if (msg.is_outgoing && msg.to_node_id && msg.to_node_id !== '^all') {
        otherNodeId = msg.to_node_id
      } else if (!msg.is_outgoing && msg.from_node_id && msg.from_node_id !== myNodeId) {
        otherNodeId = msg.from_node_id
      }

      if (otherNodeId && !convMap.has(otherNodeId)) {
        convMap.set(otherNodeId, {
          nodeId: otherNodeId,
          lastMessage: msg.text,
          lastTimestamp: msg.timestamp,
          unread: 0,
          pendingCount: 0,
          deliveredCount: 0,
          failedCount: 0
        })
      }

      if (otherNodeId) {
        const existing = convMap.get(otherNodeId)
        // Update last message if this one is newer
        if (new Date(msg.timestamp) > new Date(existing.lastTimestamp)) {
          existing.lastMessage = msg.text
          existing.lastTimestamp = msg.timestamp
        }
        // Count message statuses for outgoing messages
        if (msg.is_outgoing && msg.to_node_id === otherNodeId) {
          if (msg.ack_failed) {
            existing.failedCount++
          } else if (msg.ack_received) {
            existing.deliveredCount++
          } else {
            existing.pendingCount++
          }
        }
      }
    }

    // Sort by last message time
    return Array.from(convMap.values()).sort((a, b) =>
      new Date(b.lastTimestamp) - new Date(a.lastTimestamp)
    )
  })

  // Helper to check if a message is a broadcast (not a DM)
  function isBroadcastMessage(msg, myNodeId) {
    const toId = msg.to_node_id

    // No destination = broadcast
    if (!toId) return true

    // Explicit broadcast addresses
    if (toId === '^all') return true
    if (toId === '!ffffffff') return true
    if (toId === '0xffffffff') return true
    if (toId === 'broadcast') return true

    // If to_node_id equals our own node ID, it's a DM TO us, not a broadcast
    if (myNodeId && toId === myNodeId) return false

    // If it's an outgoing message with a specific destination, it's a DM
    if (msg.is_outgoing && toId) return false

    // For incoming messages, if to_node_id is set to something other than broadcast,
    // it's a DM (either to us or overheard)
    if (!msg.is_outgoing && toId && toId !== '^all' && toId !== '!ffffffff') {
      return false
    }

    return true
  }

  // Get messages for the selected conversation or channel
  const conversationMessages = computed(() => {
    const connectionStore = useConnectionStore()
    const myNodeId = connectionStore.myNodeNum
      ? `!${connectionStore.myNodeNum.toString(16).padStart(8, '0')}`
      : null

    if (viewMode.value === 'channel') {
      // Channel mode - show only broadcast messages, filter by channel
      return messages.value.filter(m =>
        isBroadcastMessage(m, myNodeId) && m.channel === selectedChannel.value
      )
    }

    // DM mode - show messages to/from the selected node
    const nodeId = selectedConversation.value
    if (!nodeId) return []

    return messages.value.filter(m => {
      if (m.is_outgoing) {
        return m.to_node_id === nodeId
      } else {
        return m.from_node_id === nodeId
      }
    })
  })

  async function fetchMessages(limit = 100, channel = null) {
    loading.value = true
    try {
      const params = { limit }
      if (channel !== null) params.channel = channel
      const response = await axios.get('/api/messages', { params })
      messages.value = response.data
    } catch (err) {
      console.error('Failed to fetch messages:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchChannels() {
    try {
      const response = await axios.get('/api/messages/channels')
      channels.value = response.data
    } catch (err) {
      console.error('Failed to fetch channels:', err)
    }
  }

  async function sendMessage(text, toNodeId = null, channel = 0) {
    sending.value = true
    try {
      const response = await axios.post('/api/messages', {
        text,
        to_node_id: toNodeId,
        channel
      })
      messages.value.unshift(response.data)
      return true
    } catch (err) {
      console.error('Failed to send message:', err)
      return false
    } finally {
      sending.value = false
    }
  }

  function addMessage(message) {
    // Add timestamp if not present
    if (!message.timestamp) {
      message.timestamp = new Date().toISOString()
    }
    messages.value.unshift(message)
  }

  function setSelectedChannel(channel) {
    selectedChannel.value = channel
    viewMode.value = 'channel'
    selectedConversation.value = null
    dmRecipient.value = null
  }

  function setDmRecipient(node) {
    dmRecipient.value = node
  }

  function clearDmRecipient() {
    dmRecipient.value = null
  }

  function setSelectedConversation(nodeId) {
    selectedConversation.value = nodeId
    viewMode.value = 'dm'
    // Also set dmRecipient for sending
    if (nodeId) {
      dmRecipient.value = { id: nodeId }
    } else {
      dmRecipient.value = null
    }
  }

  function markMessageAcked(ackData) {
    // Find the message and update its status
    const { to_node_id, text, success, error } = ackData
    const msg = messages.value.find(m =>
      m.is_outgoing &&
      m.to_node_id === to_node_id &&
      m.text === text &&
      !m.ack_received &&
      !m.ack_failed
    )
    if (msg) {
      if (success) {
        msg.ack_received = true
      } else {
        msg.ack_failed = true
        msg.ack_error = error
      }
    }
  }

  return {
    messages,
    channels,
    loading,
    sending,
    selectedChannel,
    dmRecipient,
    selectedConversation,
    viewMode,
    sortedMessages,
    recentMessages,
    conversations,
    conversationMessages,
    fetchMessages,
    fetchChannels,
    sendMessage,
    addMessage,
    setSelectedChannel,
    setDmRecipient,
    clearDmRecipient,
    setSelectedConversation,
    markMessageAcked
  }
})
