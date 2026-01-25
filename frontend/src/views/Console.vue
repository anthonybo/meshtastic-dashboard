<template>
  <div class="h-full flex flex-col">
    <header class="flex items-center justify-between mb-4">
      <div>
        <h1 class="text-2xl font-bold text-white">Console</h1>
        <p class="text-gray-400">Live data stream from Meshtastic device</p>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-sm text-gray-500">{{ consoleStore.filteredLogs.length }} events</span>
      </div>
    </header>

    <!-- Toolbar -->
    <div class="flex items-center gap-4 mb-4 bg-gray-800 rounded-lg p-3 border border-gray-700">
      <!-- Filter -->
      <div class="flex-1 relative">
        <input
          v-model="filterText"
          type="text"
          placeholder="Filter by type or content..."
          class="w-full px-4 py-2 pl-10 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-mesh-500"
          @input="consoleStore.setFilter(filterText)"
        />
        <svg class="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
        </svg>
      </div>

      <!-- Type filter buttons -->
      <div class="flex items-center gap-1">
        <button
          v-for="type in commonTypes"
          :key="type"
          @click="toggleTypeFilter(type)"
          class="px-2 py-1 text-xs rounded transition-colors"
          :class="filterText === type ? 'bg-mesh-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'"
        >
          {{ type }}
        </button>
      </div>

      <!-- Actions -->
      <div class="flex items-center gap-2 border-l border-gray-600 pl-4">
        <button
          @click="consoleStore.togglePause()"
          class="flex items-center gap-2 px-3 py-2 rounded-lg transition-colors"
          :class="consoleStore.pauseUpdates ? 'bg-yellow-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'"
        >
          <svg v-if="consoleStore.pauseUpdates" class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z"/>
          </svg>
          <svg v-else class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
          </svg>
          {{ consoleStore.pauseUpdates ? 'Resume' : 'Pause' }}
        </button>

        <button
          @click="consoleStore.expandAll()"
          class="px-3 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition-colors"
          title="Expand all"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>
          </svg>
        </button>

        <button
          @click="consoleStore.collapseAll()"
          class="px-3 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition-colors"
          title="Collapse all"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25"/>
          </svg>
        </button>

        <button
          @click="consoleStore.clearLogs()"
          class="px-3 py-2 bg-red-900 text-red-300 rounded-lg hover:bg-red-800 transition-colors"
        >
          Clear
        </button>
      </div>
    </div>

    <!-- Console Output -->
    <div
      ref="consoleContainer"
      class="flex-1 overflow-y-auto bg-gray-900 rounded-lg border border-gray-700 font-mono text-sm"
    >
      <div v-if="consoleStore.filteredLogs.length === 0" class="text-gray-500 text-center py-8">
        <svg class="w-12 h-12 mx-auto mb-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
        </svg>
        <p>No events to display</p>
        <p class="text-sm mt-1">Connect to your Meshtastic device to see live data</p>
      </div>

      <div v-else class="divide-y divide-gray-800">
        <div
          v-for="log in consoleStore.filteredLogs"
          :key="log.id"
          class="hover:bg-gray-800/50"
        >
          <!-- Log Header (always visible) -->
          <div
            class="flex items-center gap-3 px-4 py-2 cursor-pointer"
            @click="consoleStore.toggleExpanded(log.id)"
          >
            <!-- Expand indicator -->
            <svg
              class="w-4 h-4 text-gray-500 transition-transform flex-shrink-0"
              :class="{ 'rotate-90': log.expanded }"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/>
            </svg>

            <!-- Direction indicator -->
            <span
              class="w-6 text-center flex-shrink-0"
              :class="log.direction === 'in' ? 'text-green-500' : 'text-blue-500'"
              :title="log.direction === 'in' ? 'Received' : 'Sent'"
            >
              {{ log.direction === 'in' ? '←' : '→' }}
            </span>

            <!-- Timestamp -->
            <span class="text-gray-500 flex-shrink-0 w-24">
              {{ formatTimestamp(log.timestamp) }}
            </span>

            <!-- Type badge -->
            <span
              class="px-2 py-0.5 rounded text-xs font-medium flex-shrink-0"
              :class="getTypeBadgeClass(log.type)"
            >
              {{ log.type }}
            </span>

            <!-- Preview -->
            <span class="text-gray-300 truncate flex-1">
              {{ getPreview(log.data) }}
            </span>
          </div>

          <!-- Expanded Content -->
          <div v-if="log.expanded" class="px-4 pb-3 ml-8">
            <div class="bg-gray-950 rounded-lg p-3 overflow-x-auto">
              <JsonTree :data="log.data" :depth="0" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Status Bar -->
    <div class="mt-4 flex items-center justify-between text-xs text-gray-500">
      <div class="flex items-center gap-4">
        <span v-for="(count, type) in consoleStore.stats" :key="type" class="flex items-center gap-1">
          <span class="w-2 h-2 rounded-full" :class="getTypeColor(type)"></span>
          {{ type }}: {{ count }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <span v-if="consoleStore.pauseUpdates" class="text-yellow-500 flex items-center gap-1">
          <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
          </svg>
          Paused
        </span>
        <span>Max {{ consoleStore.maxLogs }} events</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useConsoleStore } from '../stores/console'
import JsonTree from '../components/JsonTree.vue'

const consoleStore = useConsoleStore()
const consoleContainer = ref(null)
const filterText = ref('')

const commonTypes = ['message', 'position', 'telemetry', 'node_update', 'connection']

// Scroll to bottom helper
function scrollToBottom() {
  if (consoleContainer.value) {
    consoleContainer.value.scrollTop = consoleContainer.value.scrollHeight
  }
}

// Auto-scroll to bottom
watch(() => consoleStore.logs.length, () => {
  if (!consoleStore.pauseUpdates) {
    scrollToBottom()
    setTimeout(scrollToBottom, 50)
    setTimeout(scrollToBottom, 150)
  }
}, { flush: 'post', immediate: true })

function toggleTypeFilter(type) {
  if (filterText.value === type) {
    filterText.value = ''
  } else {
    filterText.value = type
  }
  consoleStore.setFilter(filterText.value)
}

function formatTimestamp(timestamp) {
  const date = new Date(timestamp)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 })
}

function getPreview(data) {
  if (!data) return 'null'
  if (typeof data === 'string') return data

  const keys = Object.keys(data)
  if (keys.length === 0) return '{}'

  const preview = keys.slice(0, 4).map(k => {
    const v = data[k]
    if (v === null || v === undefined) return `${k}: null`
    if (typeof v === 'object') return `${k}: {...}`
    if (typeof v === 'string' && v.length > 30) return `${k}: "${v.slice(0, 30)}..."`
    return `${k}: ${JSON.stringify(v)}`
  }).join(', ')

  return `{ ${preview}${keys.length > 4 ? ', ...' : ''} }`
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
    'traceroute_error': 'bg-red-900 text-red-300',
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
