<template>
  <!-- Collapsed view - just status dot with tooltip -->
  <div v-if="collapsed" class="flex justify-center">
    <button
      @click="collapsed ? (connectionStore.connected ? handleDisconnect() : handleConnect()) : null"
      :disabled="connecting || disconnecting"
      class="p-2 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
      :title="statusTooltip"
    >
      <span
        class="w-4 h-4 rounded-full block"
        :class="statusDotClass"
      ></span>
    </button>
  </div>

  <!-- Expanded view - full details -->
  <div v-else class="space-y-3">
    <div class="flex items-center gap-2">
      <span
        class="w-3 h-3 rounded-full"
        :class="statusDotClass"
      ></span>
      <span class="text-sm text-gray-300">
        {{ statusText }}
      </span>
    </div>

    <!-- Connecting progress -->
    <div v-if="connecting" class="space-y-2">
      <div class="flex items-center gap-2 text-xs text-yellow-400">
        <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <span>{{ connectingStatus }}</span>
      </div>
      <div class="w-full h-1 bg-gray-700 rounded-full overflow-hidden">
        <div
          class="h-full bg-yellow-500 transition-all duration-500"
          :style="{ width: `${connectingProgress}%` }"
        ></div>
      </div>
    </div>

    <div v-if="connectionStore.connected" class="text-xs text-gray-400 space-y-1">
      <p>{{ connectionStore.deviceName }}</p>
      <p v-if="connectionStore.firmwareVersion">FW: {{ connectionStore.firmwareVersion }}</p>
      <p v-if="connectionStore.hwModel">{{ connectionStore.hwModel }}</p>
    </div>

    <button
      v-if="!connectionStore.connected"
      @click="handleConnect"
      :disabled="connecting"
      class="w-full px-4 py-2 text-sm font-medium text-white bg-mesh-600 rounded-lg hover:bg-mesh-700 focus:outline-none focus:ring-2 focus:ring-mesh-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
    >
      <svg v-if="connecting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
      </svg>
      {{ connecting ? 'Connecting...' : 'Connect' }}
    </button>

    <button
      v-else
      @click="handleDisconnect"
      :disabled="disconnecting"
      class="w-full px-4 py-2 text-sm font-medium text-gray-300 bg-gray-700 rounded-lg hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
    >
      <svg v-if="disconnecting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
      </svg>
      {{ disconnecting ? 'Disconnecting...' : 'Disconnect' }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useConnectionStore } from '../stores/connection'

const props = defineProps({
  collapsed: {
    type: Boolean,
    default: false
  }
})

const connectionStore = useConnectionStore()
const connecting = ref(false)
const disconnecting = ref(false)
const connectingStatus = ref('Initializing...')
const connectingProgress = ref(0)
let progressInterval = null

const statusDotClass = computed(() => {
  if (connecting.value) return 'bg-yellow-500 animate-pulse'
  if (disconnecting.value) return 'bg-orange-500 animate-pulse'
  if (connectionStore.connected) return 'bg-green-500 animate-pulse'
  return 'bg-red-500'
})

const statusText = computed(() => {
  if (connecting.value) return 'Connecting...'
  if (disconnecting.value) return 'Disconnecting...'
  if (connectionStore.connected) return 'Connected'
  return 'Disconnected'
})

const statusTooltip = computed(() => {
  if (connecting.value) return 'Connecting... Click to cancel'
  if (disconnecting.value) return 'Disconnecting...'
  if (connectionStore.connected) {
    let tooltip = `Connected: ${connectionStore.deviceName || 'Device'}`
    if (connectionStore.hwModel) tooltip += ` (${connectionStore.hwModel})`
    tooltip += '\nClick to disconnect'
    return tooltip
  }
  return 'Disconnected - Click to connect'
})

onMounted(() => {
  connectionStore.fetchStatus()
})

onUnmounted(() => {
  if (progressInterval) clearInterval(progressInterval)
})

async function handleConnect() {
  connecting.value = true
  connectingProgress.value = 0
  connectingStatus.value = 'Scanning for BLE devices...'

  // Simulate progress during the ~20 second connection
  progressInterval = setInterval(() => {
    if (connectingProgress.value < 90) {
      connectingProgress.value += 5

      if (connectingProgress.value > 10 && connectingProgress.value < 50) {
        connectingStatus.value = 'Scanning for BLE devices...'
      } else if (connectingProgress.value >= 50 && connectingProgress.value < 70) {
        connectingStatus.value = 'Found device, connecting...'
      } else if (connectingProgress.value >= 70) {
        connectingStatus.value = 'Loading node data...'
      }
    }
  }, 1000)

  const success = await connectionStore.connect()

  clearInterval(progressInterval)
  progressInterval = null

  if (success) {
    connectingProgress.value = 100
    connectingStatus.value = 'Connected!'
  } else {
    connectingStatus.value = 'Connection failed'
  }

  setTimeout(() => {
    connecting.value = false
  }, 500)
}

async function handleDisconnect() {
  disconnecting.value = true
  try {
    await connectionStore.disconnect()
  } finally {
    disconnecting.value = false
  }
}
</script>
