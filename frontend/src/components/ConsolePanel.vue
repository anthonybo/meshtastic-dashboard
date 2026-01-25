<template>
  <div class="bg-gray-800 rounded-lg border border-gray-700 flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-gray-700">
      <div class="flex items-center gap-2">
        <h3 class="font-semibold text-white">Live Console</h3>
        <span class="text-xs text-gray-500">({{ consoleStore.logs.length }} events)</span>
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="consoleStore.togglePause()"
          class="p-1.5 rounded transition-colors"
          :class="consoleStore.pauseUpdates ? 'bg-yellow-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-700'"
          :title="consoleStore.pauseUpdates ? 'Resume' : 'Pause'"
        >
          <svg v-if="consoleStore.pauseUpdates" class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z"/>
          </svg>
          <svg v-else class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
          </svg>
        </button>
        <button
          @click="consoleStore.clearLogs()"
          class="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
          title="Clear"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
          </svg>
        </button>
        <router-link
          to="/console"
          class="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
          title="Open full console"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
          </svg>
        </router-link>
      </div>
    </div>

    <!-- Console Output -->
    <div ref="consoleContainer" class="flex-1 overflow-y-auto font-mono text-xs p-2 space-y-1 bg-gray-900">
      <div v-if="consoleStore.recentLogs.length === 0" class="text-gray-500 text-center py-4">
        No events yet. Connect to device to see live data.
      </div>
      <div
        v-for="log in consoleStore.recentLogs"
        :key="log.id"
        class="flex gap-2 hover:bg-gray-800 rounded px-1 py-0.5 cursor-pointer"
        @click="consoleStore.toggleExpanded(log.id)"
      >
        <!-- Direction indicator -->
        <span :class="log.direction === 'in' ? 'text-green-500' : 'text-blue-500'">
          {{ log.direction === 'in' ? '←' : '→' }}
        </span>
        <!-- Timestamp -->
        <span class="text-gray-600 flex-shrink-0">{{ formatTime(log.timestamp) }}</span>
        <!-- Type badge -->
        <span
          class="px-1.5 py-0.5 rounded text-xs flex-shrink-0"
          :class="getTypeBadgeClass(log.type)"
        >
          {{ log.type }}
        </span>
        <!-- Preview -->
        <span class="text-gray-300 truncate flex-1">
          {{ getPreview(log.data) }}
        </span>
      </div>
    </div>

    <!-- Stats bar -->
    <div class="px-3 py-2 border-t border-gray-700 flex items-center gap-3 text-xs">
      <span
        v-for="(count, type) in topStats"
        :key="type"
        class="flex items-center gap-1"
      >
        <span
          class="w-2 h-2 rounded-full"
          :class="getTypeColor(type)"
        ></span>
        <span class="text-gray-400">{{ type }}:</span>
        <span class="text-white">{{ count }}</span>
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useConsoleStore } from '../stores/console'

const consoleStore = useConsoleStore()
const consoleContainer = ref(null)

// Get top 4 most common event types
const topStats = computed(() => {
  const entries = Object.entries(consoleStore.stats)
  entries.sort((a, b) => b[1] - a[1])
  return Object.fromEntries(entries.slice(0, 4))
})

// Scroll to bottom helper
function scrollToBottom() {
  if (consoleContainer.value) {
    consoleContainer.value.scrollTop = consoleContainer.value.scrollHeight
  }
}

// Auto-scroll when new logs arrive
watch(() => consoleStore.logs.length, () => {
  if (!consoleStore.pauseUpdates) {
    scrollToBottom()
    // Backup scrolls in case DOM isn't fully rendered
    setTimeout(scrollToBottom, 50)
    setTimeout(scrollToBottom, 150)
  }
}, { flush: 'post', immediate: true })

function formatTime(timestamp) {
  const date = new Date(timestamp)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function getPreview(data) {
  if (!data) return 'null'
  if (typeof data === 'string') return data

  // Create a short preview of the object
  const keys = Object.keys(data)
  if (keys.length === 0) return '{}'

  const preview = keys.slice(0, 3).map(k => {
    const v = data[k]
    if (v === null || v === undefined) return `${k}: null`
    if (typeof v === 'object') return `${k}: {...}`
    if (typeof v === 'string' && v.length > 20) return `${k}: "${v.slice(0, 20)}..."`
    return `${k}: ${JSON.stringify(v)}`
  }).join(', ')

  return `{ ${preview}${keys.length > 3 ? ', ...' : ''} }`
}

function getTypeBadgeClass(type) {
  const classes = {
    'connection': 'bg-blue-900 text-blue-300',
    'message': 'bg-green-900 text-green-300',
    'position': 'bg-purple-900 text-purple-300',
    'telemetry': 'bg-yellow-900 text-yellow-300',
    'node_update': 'bg-cyan-900 text-cyan-300',
    'ack': 'bg-emerald-900 text-emerald-300',
    'traceroute': 'bg-orange-900 text-orange-300',
    'pong': 'bg-gray-700 text-gray-400',
    'ping': 'bg-gray-700 text-gray-400',
    'send_message': 'bg-green-900 text-green-300',
  }
  return classes[type] || 'bg-gray-700 text-gray-300'
}

function getTypeColor(type) {
  const colors = {
    'connection': 'bg-blue-500',
    'message': 'bg-green-500',
    'position': 'bg-purple-500',
    'telemetry': 'bg-yellow-500',
    'node_update': 'bg-cyan-500',
    'ack': 'bg-emerald-500',
    'traceroute': 'bg-orange-500',
  }
  return colors[type] || 'bg-gray-500'
}
</script>
