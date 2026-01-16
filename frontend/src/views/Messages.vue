<template>
  <div class="h-[calc(100vh-6rem)] flex flex-col">
    <!-- Compact Header -->
    <header class="mb-4 flex-shrink-0">
      <h1 class="text-2xl font-bold text-white">Messages</h1>
      <p class="text-gray-400 text-sm">Send and receive messages across the mesh network</p>
    </header>

    <!-- Main Content - Takes remaining space -->
    <div class="flex-1 flex gap-4 min-h-0">
      <!-- Chat Panel - Takes most of the space -->
      <div class="flex-1 min-w-0 h-full">
        <MessagePanel class="h-full" />
      </div>

      <!-- Right Sidebar - Fixed width, scrollable -->
      <div class="w-72 flex-shrink-0 flex flex-col min-h-0">
        <div class="flex-1 overflow-y-auto space-y-4">
          <!-- Message All Nodes -->
          <div class="bg-gray-800 rounded-lg p-3 border border-gray-700">
            <h3 class="text-sm font-semibold text-white mb-2 flex items-center gap-2">
              <svg class="w-4 h-4 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              Message All Nodes
            </h3>

            <div class="space-y-2">
              <textarea
                v-model="massMessageText"
                placeholder="Hello! Anyone active?"
                rows="2"
                :disabled="!connectionStore.connected || sendingToAll"
                class="w-full px-2 py-1.5 text-sm text-white bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-mesh-500 disabled:opacity-50 resize-none"
              ></textarea>

              <button
                @click="sendToAllNodes"
                :disabled="!massMessageText.trim() || !connectionStore.connected || sendingToAll"
                class="w-full flex items-center justify-center gap-2 px-3 py-1.5 text-xs font-medium text-white bg-orange-600 rounded-lg hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <svg v-if="sendingToAll" class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                <svg v-else class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0"/>
                </svg>
                {{ sendingToAll ? 'Sending...' : `Send to ${nodesStore.nodeCount} Nodes` }}
              </button>

              <!-- Progress -->
              <div v-if="broadcastProgress" class="space-y-1">
                <div class="flex items-center justify-between text-xs">
                  <span class="text-gray-400">{{ broadcastProgress.current }} / {{ broadcastProgress.total }}</span>
                  <span class="text-green-400">✓ {{ broadcastProgress.sent }}</span>
                </div>
                <div class="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    class="h-full bg-orange-500 transition-all duration-300"
                    :style="{ width: `${(broadcastProgress.current / broadcastProgress.total) * 100}%` }"
                  ></div>
                </div>
              </div>

              <!-- Result -->
              <div v-else-if="massMessageResult" class="text-xs p-2 rounded-lg bg-green-900/50 border border-green-700">
                <span class="text-green-300">Sent: {{ massMessageResult.sent }} | Failed: {{ massMessageResult.failed }}</span>
              </div>
            </div>
          </div>

          <!-- Quick Stats -->
          <div class="bg-gray-800 rounded-lg p-3 border border-gray-700">
            <h3 class="text-sm font-semibold text-white mb-2">Statistics</h3>
            <div class="grid grid-cols-3 gap-2 text-center">
              <div>
                <div class="text-lg font-bold text-white">{{ messagesStore.messages.length }}</div>
                <div class="text-xs text-gray-400">Total</div>
              </div>
              <div>
                <div class="text-lg font-bold text-mesh-400">{{ sentCount }}</div>
                <div class="text-xs text-gray-400">Sent</div>
              </div>
              <div>
                <div class="text-lg font-bold text-blue-400">{{ receivedCount }}</div>
                <div class="text-xs text-gray-400">Received</div>
              </div>
            </div>
          </div>

          <!-- Channels -->
          <div class="bg-gray-800 rounded-lg p-3 border border-gray-700">
            <h3 class="text-sm font-semibold text-white mb-2">Channels</h3>
            <div v-if="messagesStore.channels.length === 0" class="text-gray-500 text-xs">
              Connect to see channels
            </div>
            <div v-else class="space-y-1">
              <div
                v-for="channel in messagesStore.channels"
                :key="channel.index"
                class="flex items-center justify-between px-2 py-1 rounded bg-gray-700 text-xs"
              >
                <span class="text-white">{{ channel.name || `Ch ${channel.index}` }}</span>
                <span class="text-gray-400">{{ getChannelRole(channel.role) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { useMessagesStore } from '../stores/messages'
import { useConnectionStore } from '../stores/connection'
import { useNodesStore } from '../stores/nodes'
import MessagePanel from '../components/MessagePanel.vue'

const messagesStore = useMessagesStore()
const connectionStore = useConnectionStore()
const nodesStore = useNodesStore()

const massMessageText = ref('')
const sendingToAll = ref(false)
const massMessageResult = ref(null)
const broadcastProgress = ref(null)

const sentCount = computed(() => messagesStore.messages.filter(m => m.is_outgoing).length)
const receivedCount = computed(() => messagesStore.messages.filter(m => !m.is_outgoing).length)

onMounted(() => {
  messagesStore.fetchMessages()
  messagesStore.fetchChannels()
  window.addEventListener('broadcast-progress', handleBroadcastProgress)
})

onUnmounted(() => {
  window.removeEventListener('broadcast-progress', handleBroadcastProgress)
})

function handleBroadcastProgress(event) {
  broadcastProgress.value = event.detail
  if (event.detail.status === 'completed') {
    setTimeout(() => {
      broadcastProgress.value = null
    }, 500)
  }
}

async function sendToAllNodes() {
  if (!massMessageText.value.trim()) return

  sendingToAll.value = true
  massMessageResult.value = null

  try {
    const response = await axios.post('/api/messages/broadcast-all', {
      text: massMessageText.value.trim(),
      delay_seconds: 0.5
    })

    massMessageResult.value = response.data
    massMessageText.value = ''
    await messagesStore.fetchMessages()
  } catch (error) {
    console.error('Failed to send to all nodes:', error)
    massMessageResult.value = {
      sent: 0,
      failed: nodesStore.nodeCount,
      skipped: 0
    }
  } finally {
    sendingToAll.value = false
  }
}

function getChannelRole(role) {
  const roles = { 0: 'Disabled', 1: 'Primary', 2: 'Secondary' }
  return roles[role] || 'Unknown'
}
</script>
