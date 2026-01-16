<template>
  <div class="flex h-full max-h-full bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
    <!-- Conversations Sidebar -->
    <div class="w-56 flex-shrink-0 border-r border-gray-700 flex flex-col max-h-full">
      <!-- Channels Section -->
      <div class="flex-shrink-0">
        <div class="p-2 border-b border-gray-700 bg-gray-750">
          <h3 class="font-semibold text-gray-400 text-xs uppercase tracking-wide">Channels</h3>
        </div>

        <!-- Primary Channel (always available) -->
        <button
          @click="messagesStore.setSelectedChannel(0)"
          class="w-full flex items-center gap-2 px-2 py-2 text-left hover:bg-gray-700 transition-colors border-b border-gray-600"
          :class="messagesStore.viewMode === 'channel' && messagesStore.selectedChannel === 0 ? 'bg-gray-700' : ''"
        >
          <div class="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0"/>
            </svg>
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-white text-xs font-medium truncate">Primary</div>
            <div class="text-gray-400 text-xs truncate">Default channel</div>
          </div>
        </button>

        <!-- Other Channels from device -->
        <button
          v-for="channel in messagesStore.channels.filter(c => c.index !== 0)"
          :key="channel.index"
          @click="messagesStore.setSelectedChannel(channel.index)"
          class="w-full flex items-center gap-2 px-2 py-2 text-left hover:bg-gray-700 transition-colors border-b border-gray-600"
          :class="messagesStore.viewMode === 'channel' && messagesStore.selectedChannel === channel.index ? 'bg-gray-700' : ''"
        >
          <div class="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center flex-shrink-0">
            <span class="text-white text-xs font-bold">#{{ channel.index }}</span>
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-white text-xs font-medium truncate">{{ channel.name || `Channel ${channel.index}` }}</div>
            <div class="text-gray-400 text-xs truncate">Secondary channel</div>
          </div>
        </button>
      </div>

      <!-- Direct Messages Section -->
      <div class="flex-1 flex flex-col min-h-0">
        <div class="p-2 border-b border-gray-700 bg-gray-750 flex-shrink-0">
          <h3 class="font-semibold text-gray-400 text-xs uppercase tracking-wide">Direct Messages</h3>
        </div>

        <!-- DM Conversation List - Scrollable -->
        <div class="flex-1 overflow-y-auto min-h-0">
          <div v-if="messagesStore.conversations.length === 0" class="p-3 text-center text-gray-500 text-xs">
            No DM conversations yet
          </div>
          <button
            v-for="conv in messagesStore.conversations"
            :key="conv.nodeId"
            @click="messagesStore.setSelectedConversation(conv.nodeId)"
            class="w-full flex items-center gap-2 px-2 py-2 text-left hover:bg-gray-700 transition-colors border-b border-gray-600"
            :class="messagesStore.viewMode === 'dm' && messagesStore.selectedConversation === conv.nodeId ? 'bg-gray-700' : ''"
          >
            <div class="relative flex-shrink-0">
              <div class="w-8 h-8 rounded-full bg-mesh-600 flex items-center justify-center">
                <span class="text-white text-xs font-bold">{{ getNodeInitials(conv.nodeId) }}</span>
              </div>
              <!-- Status indicator positioned at bottom-right of avatar -->
              <div class="absolute -bottom-0.5 -right-0.5">
                <NodeStatusIndicator :node-id="conv.nodeId" size="sm" :pulse="true" />
              </div>
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex items-center justify-between">
                <span class="text-white text-xs font-medium truncate">{{ getNodeName(conv.nodeId) }}</span>
                <span class="text-gray-500 text-xs flex-shrink-0 ml-1">{{ formatTimeShort(conv.lastTimestamp) }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-gray-400 text-xs truncate flex-1">{{ conv.lastMessage }}</span>
                <!-- Status indicators -->
                <div class="flex items-center gap-1 ml-1 flex-shrink-0">
                  <!-- Pending count -->
                  <span v-if="conv.pendingCount > 0" class="flex items-center text-xs text-gray-400" title="Pending">
                    <svg class="w-3 h-3 mr-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    {{ conv.pendingCount }}
                  </span>
                  <!-- Delivered count -->
                  <span v-if="conv.deliveredCount > 0" class="flex items-center text-xs text-blue-400" title="Delivered">
                    <svg class="w-3 h-3 mr-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M2 12l5 5L18 6"/><path d="M7 12l5 5L23 6"/>
                    </svg>
                    {{ conv.deliveredCount }}
                  </span>
                  <!-- Failed count -->
                  <span v-if="conv.failedCount > 0" class="flex items-center text-xs text-red-400" title="Failed">
                    <svg class="w-3 h-3 mr-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                    {{ conv.failedCount }}
                  </span>
                </div>
              </div>
            </div>
          </button>
        </div>
      </div>
    </div>

    <!-- Chat Area -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Chat Header -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <div class="flex items-center gap-2">
          <h3 class="font-semibold text-white">
            {{ chatTitle }}
          </h3>
          <!-- Channel badge -->
          <span v-if="messagesStore.viewMode === 'channel'" class="flex items-center gap-1 px-2 py-0.5 text-xs bg-green-900 text-green-300 rounded-full">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0"/>
            </svg>
            Broadcast
          </span>
          <!-- DM badge with status -->
          <template v-else>
            <NodeStatusIndicator :node-id="messagesStore.selectedConversation" size="md" show-label />
          </template>
        </div>

        <!-- Node ID for DM -->
        <span v-if="messagesStore.viewMode === 'dm'" class="text-xs text-gray-500 font-mono">
          {{ messagesStore.selectedConversation }}
        </span>
      </div>

      <!-- Messages -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-3">
        <div v-if="messagesStore.loading" class="flex justify-center py-4">
          <svg class="w-6 h-6 text-mesh-500 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
        </div>

        <div v-else-if="displayMessages.length === 0" class="text-center py-8 text-gray-400">
          <svg class="w-12 h-12 mx-auto mb-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
          </svg>
          <p>No messages yet</p>
          <p class="text-sm mt-1">
            {{ messagesStore.viewMode === 'dm' ? 'Start a conversation!' : 'Send a broadcast message!' }}
          </p>
        </div>

        <template v-else>
          <div
            v-for="message in displayMessages"
            :key="message.id || message.timestamp"
            class="flex"
            :class="message.is_outgoing ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[80%] rounded-lg px-4 py-2"
              :class="message.is_outgoing ? 'bg-mesh-600 text-white' : 'bg-gray-700 text-white'"
            >
              <div v-if="!message.is_outgoing && messagesStore.viewMode === 'channel'" class="text-xs text-gray-400 mb-1">
                {{ getNodeName(message.from_node_id) }}
              </div>
              <p class="text-sm whitespace-pre-wrap break-words">{{ message.text }}</p>
              <div class="flex items-center justify-end gap-2 mt-1">
                <span class="text-xs opacity-60">{{ formatTime(message.timestamp) }}</span>
                <!-- Message Status Icons (only for outgoing DMs) -->
                <template v-if="message.is_outgoing && message.to_node_id">
                  <!-- Failed - Red X -->
                  <div v-if="message.ack_failed" class="flex items-center gap-1" :title="message.ack_error || 'Delivery failed'">
                    <svg class="w-3 h-3 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                  </div>
                  <!-- Delivered - Double Check -->
                  <div v-else-if="message.ack_received" class="flex items-center" title="Delivered">
                    <svg class="w-4 h-4 text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M2 12l5 5L18 6"/>
                      <path d="M7 12l5 5L23 6"/>
                    </svg>
                  </div>
                  <!-- Pending - Clock -->
                  <div v-else class="flex items-center" title="Sending...">
                    <svg class="w-3 h-3 text-gray-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                  </div>
                </template>
                <!-- Broadcast messages - Single check (sent) -->
                <template v-else-if="message.is_outgoing">
                  <svg class="w-3 h-3 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                  </svg>
                </template>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Input -->
      <div class="p-4 border-t border-gray-700">
        <form @submit.prevent="sendMessage" class="flex gap-2">
          <input
            v-model="messageText"
            type="text"
            :placeholder="inputPlaceholder"
            :disabled="!connectionStore.connected || messagesStore.sending"
            class="flex-1 px-4 py-2 text-white bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-mesh-500 disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            :disabled="!messageText.trim() || !connectionStore.connected || messagesStore.sending"
            class="px-4 py-2 text-white bg-mesh-600 rounded-lg hover:bg-mesh-700 focus:outline-none focus:ring-2 focus:ring-mesh-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <svg v-if="messagesStore.sending" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
            </svg>
          </button>
        </form>
        <p v-if="!connectionStore.connected" class="mt-2 text-xs text-red-400">
          Connect to device to send messages
        </p>
        <!-- Status Legend (only for DMs) -->
        <div v-else-if="messagesStore.viewMode === 'dm'" class="mt-2 flex items-center gap-4 text-xs text-gray-500">
          <span class="flex items-center gap-1">
            <svg class="w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            Pending
          </span>
          <span class="flex items-center gap-1">
            <svg class="w-3 h-3 text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M2 12l5 5L18 6"/><path d="M7 12l5 5L23 6"/>
            </svg>
            Delivered
          </span>
          <span class="flex items-center gap-1">
            <svg class="w-3 h-3 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
            Failed
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useMessagesStore } from '../stores/messages'
import { useConnectionStore } from '../stores/connection'
import { useNodesStore } from '../stores/nodes'
import NodeStatusIndicator from './NodeStatusIndicator.vue'

const messagesStore = useMessagesStore()
const connectionStore = useConnectionStore()
const nodesStore = useNodesStore()

const messageText = ref('')
const messagesContainer = ref(null)

const displayMessages = computed(() => {
  return [...messagesStore.conversationMessages].reverse()
})

const chatTitle = computed(() => {
  if (messagesStore.viewMode === 'dm') {
    return getNodeName(messagesStore.selectedConversation)
  }
  // Channel mode
  if (messagesStore.selectedChannel === 0) {
    return 'Primary Channel'
  }
  const channel = messagesStore.channels.find(c => c.index === messagesStore.selectedChannel)
  return channel?.name || `Channel ${messagesStore.selectedChannel}`
})

const inputPlaceholder = computed(() => {
  if (messagesStore.viewMode === 'dm') {
    const name = getNodeName(messagesStore.selectedConversation)
    return `Message ${name}...`
  }
  return `Broadcast to ${chatTitle.value}...`
})

onMounted(() => {
  messagesStore.fetchMessages()
})

watch(() => messagesStore.conversationMessages.length, () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
})

async function sendMessage() {
  if (!messageText.value.trim()) return

  const recipient = messagesStore.viewMode === 'dm' ? messagesStore.selectedConversation : null
  const channel = messagesStore.viewMode === 'channel' ? messagesStore.selectedChannel : 0
  const success = await messagesStore.sendMessage(
    messageText.value.trim(),
    recipient,
    channel
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

function formatTimeShort(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } else if (diffDays === 1) {
    return 'Yesterday'
  } else if (diffDays < 7) {
    return date.toLocaleDateString([], { weekday: 'short' })
  } else {
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
  }
}
</script>
