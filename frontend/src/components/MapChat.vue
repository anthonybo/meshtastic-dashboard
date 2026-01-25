<template>
  <div class="bg-gray-800 rounded-lg border border-gray-700 flex flex-col h-full overflow-hidden relative">
    <div class="p-3 border-b border-gray-700 flex-shrink-0">
      <h3 class="text-lg font-semibold text-white">Primary Channel</h3>
    </div>

    <!-- Messages -->
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto p-3 space-y-2 min-h-0"
    >
      <div v-if="messages.length === 0" class="text-center text-gray-500 text-sm py-4">
        No messages yet
      </div>
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="text-sm"
        :class="msg.is_outgoing ? 'text-right' : 'text-left'"
      >
        <div
          class="inline-block max-w-[85%] rounded-lg px-2 py-1"
          :class="msg.is_outgoing ? 'bg-mesh-600 text-white' : 'bg-gray-700 text-gray-100'"
        >
          <button
            v-if="!msg.is_outgoing"
            @click="(e) => showNodePopover(msg.from_node_id, e)"
            class="text-xs font-medium text-mesh-400 mb-0.5 hover:text-mesh-300 hover:underline cursor-pointer text-left flex items-center gap-1"
          >
            <span
              class="w-1.5 h-1.5 rounded-full flex-shrink-0"
              :class="getNodeStatusColor(msg.from_node_id)"
            ></span>
            {{ getNodeName(msg.from_node_id) }}
          </button>
          <div class="break-words text-xs">{{ msg.text }}</div>
          <div class="text-xs mt-0.5" :class="msg.is_outgoing ? 'text-mesh-200' : 'text-gray-500'">
            {{ formatTime(msg.timestamp) }}
            <span v-if="msg.is_outgoing" class="ml-1">
              <svg v-if="msg.ack_received" class="w-3 h-3 inline text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M2 12l5 5L18 6"/><path d="M7 12l5 5L23 6"/>
              </svg>
              <svg v-else class="w-3 h-3 inline text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12l5 5L20 7"/>
              </svg>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="p-2 border-t border-gray-700 flex-shrink-0">
      <form @submit.prevent="sendMessage" class="flex gap-2">
        <input
          v-model="messageText"
          type="text"
          placeholder="Broadcast message..."
          class="flex-1 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-mesh-500"
          :disabled="!connectionStore.connected"
        />
        <button
          type="submit"
          :disabled="!messageText.trim() || !connectionStore.connected"
          class="px-3 py-1 bg-mesh-600 text-white rounded text-sm hover:bg-mesh-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </form>
    </div>

    <!-- Node Info Popover -->
    <div
      v-if="popoverNode"
      ref="popoverEl"
      class="absolute z-50 bg-gray-900 border border-gray-600 rounded-lg shadow-xl w-64"
      :style="popoverStyle"
    >
      <!-- Arrow pointing down (popover above) -->
      <template v-if="popoverAbove">
        <div class="absolute -bottom-2 left-4 w-0 h-0 border-l-8 border-r-8 border-t-8 border-l-transparent border-r-transparent border-t-gray-600"></div>
        <div class="absolute -bottom-1.5 left-4 w-0 h-0 border-l-8 border-r-8 border-t-8 border-l-transparent border-r-transparent border-t-gray-900"></div>
      </template>
      <!-- Arrow pointing up (popover below) -->
      <template v-else>
        <div class="absolute -top-2 left-4 w-0 h-0 border-l-8 border-r-8 border-b-8 border-l-transparent border-r-transparent border-b-gray-600"></div>
        <div class="absolute -top-1.5 left-4 w-0 h-0 border-l-8 border-r-8 border-b-8 border-l-transparent border-r-transparent border-b-gray-900"></div>
      </template>

      <!-- Header with close -->
      <div class="flex items-center justify-between px-3 py-2 border-b border-gray-700">
        <div class="flex items-center gap-2">
          <div class="w-6 h-6 rounded-full bg-mesh-600 flex items-center justify-center flex-shrink-0">
            <span class="text-white text-xs font-bold">{{ getNodeInitials(popoverNode.id) }}</span>
          </div>
          <span class="text-white text-sm font-medium truncate">{{ popoverNode.long_name || popoverNode.short_name || 'Unknown' }}</span>
        </div>
        <button @click="closePopover" class="text-gray-400 hover:text-white">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <!-- Content -->
      <div class="p-2 space-y-1.5 text-xs">
        <!-- Status -->
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full" :class="popoverNode.statusColor"></span>
          <span class="text-gray-300">{{ popoverNode.status }}</span>
          <span class="text-gray-500">{{ formatLastHeard(popoverNode.last_heard) }}</span>
        </div>

        <!-- Info grid -->
        <div class="grid grid-cols-2 gap-1">
          <div class="bg-gray-800 rounded px-1.5 py-1">
            <div class="text-gray-500 text-[10px]">Model</div>
            <div class="text-white truncate">{{ popoverNode.hw_model || 'Unknown' }}</div>
          </div>
          <div class="bg-gray-800 rounded px-1.5 py-1">
            <div class="text-gray-500 text-[10px]">Battery</div>
            <div class="text-white">{{ popoverNode.battery_level ? `${popoverNode.battery_level}%` : 'N/A' }}</div>
          </div>
          <div v-if="popoverNode.snr != null" class="bg-gray-800 rounded px-1.5 py-1">
            <div class="text-gray-500 text-[10px]">SNR</div>
            <div class="text-white">{{ popoverNode.snr.toFixed(1) }} dB</div>
          </div>
          <div v-if="popoverNode.hops_away != null" class="bg-gray-800 rounded px-1.5 py-1">
            <div class="text-gray-500 text-[10px]">Hops</div>
            <div class="text-white">{{ popoverNode.hops_away }}</div>
          </div>
        </div>

        <!-- Location if available -->
        <div v-if="popoverNode.latitude && popoverNode.longitude" class="bg-gray-800 rounded px-1.5 py-1">
          <div class="text-gray-500 text-[10px]">Location</div>
          <div class="text-white">
            {{ popoverNode.latitude.toFixed(4) }}, {{ popoverNode.longitude.toFixed(4) }}
            <span v-if="popoverNode.altitude" class="text-gray-500">({{ popoverNode.altitude }}m)</span>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-1.5 pt-1">
          <button
            v-if="popoverNode.latitude && popoverNode.longitude"
            @click="focusOnMap(popoverNode.id)"
            class="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
            title="Focus on map"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
            Map
          </button>
          <button
            @click="openDM(popoverNode.id)"
            class="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-mesh-600 hover:bg-mesh-700 text-white rounded transition-colors"
            title="Send DM"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
            </svg>
            DM
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessagesStore } from '../stores/messages'
import { useConnectionStore } from '../stores/connection'
import { useNodesStore } from '../stores/nodes'

const emit = defineEmits(['focus-node'])

const router = useRouter()
const messagesStore = useMessagesStore()
const connectionStore = useConnectionStore()
const nodesStore = useNodesStore()

const messageText = ref('')
const messagesContainer = ref(null)
const popoverNode = ref(null)
const popoverStyle = ref({})
const popoverEl = ref(null)
const popoverAbove = ref(true)

// Get primary channel messages (channel 0 broadcasts)
const messages = computed(() => {
  return messagesStore.messages
    .filter(msg => {
      // Only show broadcast messages (primary channel)
      const toId = msg.to_node_id
      if (!toId) return true
      if (toId === '^all') return true
      if (toId === '!ffffffff') return true
      return false
    })
    .slice(-50) // Show last 50 messages
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
})

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

onMounted(async () => {
  document.addEventListener('click', handleClickOutside)
  await messagesStore.fetchMessages()
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

function handleClickOutside(e) {
  if (popoverEl.value && !popoverEl.value.contains(e.target) && !e.target.closest('button')) {
    closePopover()
  }
}

// Watch for messages changes and scroll to bottom
// Using flush: 'post' ensures it runs after DOM updates
watch(
  () => messages.value,
  () => {
    nextTick(() => {
      scrollToBottom()
      // Backup scroll after delay for initial load
      setTimeout(scrollToBottom, 50)
      setTimeout(scrollToBottom, 200)
    })
  },
  { immediate: true, flush: 'post', deep: true }
)

async function sendMessage() {
  if (!messageText.value.trim()) return

  const success = await messagesStore.sendMessage(
    messageText.value.trim(),
    null, // broadcast
    0     // primary channel
  )

  if (success) {
    messageText.value = ''
  }
}

function getNodeName(nodeId) {
  if (!nodeId) return 'Unknown'
  const node = nodesStore.getNode(nodeId)
  return node?.long_name || node?.short_name || nodeId.slice(-8)
}

function getNodeStatusColor(nodeId) {
  const node = nodesStore.getNode(nodeId)
  if (!node?.last_heard) return 'bg-gray-500'

  const lastHeard = new Date(node.last_heard)
  const now = new Date()
  const diffMins = (now - lastHeard) / 60000

  if (diffMins < 15) return 'bg-green-500'
  if (diffMins < 60) return 'bg-yellow-500'
  return 'bg-red-500'
}

function getNodeInitials(nodeId) {
  const name = getNodeName(nodeId)
  if (name.startsWith('!')) {
    return name.slice(-2).toUpperCase()
  }
  return name.slice(0, 2).toUpperCase()
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatLastHeard(timestamp) {
  if (!timestamp) return 'Never'
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`

  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`

  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}

function getNodeStatus(node) {
  if (!node?.last_heard) {
    return { status: 'Unknown', color: 'bg-gray-500' }
  }

  const lastHeard = new Date(node.last_heard)
  const now = new Date()
  const diffMins = (now - lastHeard) / 60000

  if (diffMins < 15) {
    return { status: 'Online', color: 'bg-green-500' }
  } else if (diffMins < 60) {
    return { status: 'Recent', color: 'bg-yellow-500' }
  } else {
    return { status: 'Offline', color: 'bg-red-500' }
  }
}

function showNodePopover(nodeId, event) {
  event.stopPropagation()

  const node = nodesStore.getNode(nodeId)
  const { status, color } = node ? getNodeStatus(node) : { status: 'Unknown', color: 'bg-gray-500' }

  popoverNode.value = node ? {
    ...node,
    status,
    statusColor: color
  } : {
    id: nodeId,
    status: 'Unknown',
    statusColor: 'bg-gray-500'
  }

  // Position the popover relative to the clicked element
  const rect = event.target.getBoundingClientRect()
  const containerRect = event.target.closest('.relative').getBoundingClientRect()

  // Calculate position relative to the container
  const left = rect.left - containerRect.left
  const spaceAbove = rect.top - containerRect.top
  const popoverHeight = 220 // Approximate popover height

  // Show below if not enough space above
  if (spaceAbove < popoverHeight) {
    popoverAbove.value = false
    const top = rect.bottom - containerRect.top + 8
    popoverStyle.value = {
      left: `${Math.max(8, Math.min(left, containerRect.width - 270))}px`,
      top: `${top}px`
    }
  } else {
    popoverAbove.value = true
    const bottom = containerRect.bottom - rect.top + 8
    popoverStyle.value = {
      left: `${Math.max(8, Math.min(left, containerRect.width - 270))}px`,
      bottom: `${bottom}px`
    }
  }
}

function closePopover() {
  popoverNode.value = null
}

function focusOnMap(nodeId) {
  const node = nodesStore.getNode(nodeId)
  if (node?.latitude && node?.longitude) {
    emit('focus-node', { lat: node.latitude, lng: node.longitude, nodeId })
  }
  closePopover()
}

function openDM(nodeId) {
  messagesStore.setSelectedConversation(nodeId)
  router.push('/messages')
  closePopover()
}
</script>
