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

    <!-- Auto-reconnecting progress -->
    <div v-if="connectionStore.reconnecting" class="space-y-2">
      <div class="flex items-center gap-2 text-xs text-orange-400">
        <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <span>Reconnecting ({{ connectionStore.reconnectAttempt }}/{{ connectionStore.reconnectMaxAttempts }})...</span>
      </div>
      <div class="w-full h-1 bg-gray-700 rounded-full overflow-hidden">
        <div
          class="h-full bg-orange-500 transition-all duration-500"
          :style="{ width: `${(connectionStore.reconnectAttempt / connectionStore.reconnectMaxAttempts) * 100}%` }"
        ></div>
      </div>
    </div>

    <!-- Reconnect failed -->
    <div v-if="connectionStore.reconnectFailed" class="text-xs text-red-400">
      Auto-reconnect failed. Click Connect to retry.
    </div>

    <!-- Connection error -->
    <div v-if="connectionStore.connectionError && !connecting" class="text-xs text-red-400 bg-red-900/20 rounded p-2">
      {{ connectionStore.connectionError }}
    </div>

    <!-- BLE Scan Results -->
    <div v-if="connectionStore.lastScanResult && !connectionStore.connected" class="text-xs space-y-2">
      <!-- Meshtastic devices found -->
      <div v-if="connectionStore.lastScanResult.meshtastic_devices?.length > 0" class="space-y-1">
        <p class="text-green-400 font-medium">Meshtastic Devices Found:</p>
        <div
          v-for="device in connectionStore.lastScanResult.meshtastic_devices"
          :key="device.address"
          class="flex items-center justify-between bg-green-900/20 rounded p-2 border border-green-800/50"
        >
          <div>
            <span class="text-green-300 font-mono">{{ device.name }}</span>
            <span v-if="device.name === connectionStore.lastScanResult.configured_device" class="ml-2 text-yellow-400">(configured)</span>
          </div>
          <span v-if="device.rssi" class="text-gray-500">{{ device.rssi }} dBm</span>
        </div>
      </div>

      <!-- No Meshtastic devices -->
      <div v-else class="text-yellow-400 bg-yellow-900/20 rounded p-2">
        No Meshtastic devices found. Make sure your device is powered on with BLE enabled.
      </div>

      <!-- Configured device info -->
      <div v-if="connectionStore.lastScanResult.configured_device" class="text-gray-400">
        Looking for: <span class="font-mono text-gray-300">{{ connectionStore.lastScanResult.configured_device }}</span>
        <span v-if="connectionStore.lastScanResult.configured_device_found" class="text-green-400 ml-1">✓</span>
        <span v-else class="text-red-400 ml-1">✗</span>
      </div>

      <!-- Scan button -->
      <button
        @click="handleScan"
        :disabled="connectionStore.scanning"
        class="w-full px-3 py-1.5 text-xs font-medium text-blue-300 bg-blue-800/50 rounded hover:bg-blue-700/50 disabled:opacity-50 flex items-center justify-center gap-2"
      >
        <svg v-if="connectionStore.scanning" class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <svg v-else class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
        </svg>
        {{ connectionStore.scanning ? 'Scanning...' : 'Scan for Devices' }}
      </button>
    </div>

    <!-- Disconnect warning (BLE close timeout) with Reset button -->
    <div v-if="connectionStore.disconnectWarning && !connectionStore.connected" class="text-xs text-orange-400 bg-orange-900/20 rounded p-2 space-y-2">
      <div class="flex items-center gap-2">
        <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
        </svg>
        <span>{{ connectionStore.disconnectWarning }}</span>
      </div>
      <button
        @click="handleResetBle"
        :disabled="resetting"
        class="w-full px-3 py-1.5 text-xs font-medium text-orange-300 bg-orange-800/50 rounded hover:bg-orange-700/50 disabled:opacity-50 flex items-center justify-center gap-2"
      >
        <svg v-if="resetting" class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        {{ resetting ? 'Resetting BLE...' : 'Reset BLE' }}
      </button>
    </div>

    <!-- Stale data warning -->
    <div v-if="connectionStore.isDataStale" class="text-xs text-yellow-400 bg-yellow-900/20 rounded p-2 flex items-center gap-2">
      <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
      </svg>
      <span>No data received recently. Connection may be stale.</span>
    </div>

    <div v-if="connectionStore.connected" class="text-xs text-gray-400 space-y-1">
      <p>{{ connectionStore.deviceName }}</p>
      <p v-if="connectionStore.firmwareVersion">FW: {{ connectionStore.firmwareVersion }}</p>
      <p v-if="connectionStore.hwModel">{{ connectionStore.hwModel }}</p>
    </div>

    <!-- Reconnecting state with progress -->
    <div v-if="reconnecting" class="space-y-2">
      <div class="flex items-center gap-2 text-xs text-yellow-400">
        <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <span>{{ reconnectStatus || 'Reconnecting...' }}</span>
      </div>
      <button
        disabled
        class="w-full px-4 py-2 text-sm font-medium text-white bg-mesh-600 rounded-lg disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
      >
        <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        Reconnecting...
      </button>
    </div>

    <!-- Disconnected: show Connect button -->
    <button
      v-else-if="!connectionStore.connected"
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

    <!-- Connected: show Reconnect and Disconnect buttons -->
    <div v-else class="flex gap-2">
      <button
        @click="handleReconnect"
        :disabled="reconnecting"
        class="flex-1 px-3 py-2 text-sm font-medium text-white bg-mesh-600 rounded-lg hover:bg-mesh-700 focus:outline-none focus:ring-2 focus:ring-mesh-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        <svg v-if="reconnecting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
        {{ reconnecting ? 'Reconnecting...' : 'Reconnect' }}
      </button>
      <button
        @click="handleDisconnect"
        :disabled="disconnecting || reconnecting"
        class="px-3 py-2 text-sm font-medium text-gray-300 bg-gray-700 rounded-lg hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
        title="Disconnect"
      >
        <svg v-if="disconnecting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
        </svg>
      </button>
    </div>
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
const reconnecting = ref(false)
const reconnectStatus = ref('')
const resetting = ref(false)
const connectingStatus = ref('Initializing...')
const connectingProgress = ref(0)
let progressInterval = null

const statusDotClass = computed(() => {
  if (connecting.value) return 'bg-yellow-500 animate-pulse'
  if (reconnecting.value) return 'bg-yellow-500 animate-pulse'
  if (disconnecting.value) return 'bg-orange-500 animate-pulse'
  if (connectionStore.reconnecting) return 'bg-orange-500 animate-pulse'
  if (connectionStore.connected) return 'bg-green-500 animate-pulse'
  if (connectionStore.reconnectFailed) return 'bg-red-500'
  return 'bg-red-500'
})

const statusText = computed(() => {
  if (connecting.value) return 'Connecting...'
  if (reconnecting.value) return 'Reconnecting...'
  if (disconnecting.value) return 'Disconnecting...'
  if (connectionStore.reconnecting) return `Reconnecting (${connectionStore.reconnectAttempt}/${connectionStore.reconnectMaxAttempts})...`
  if (connectionStore.connected) return 'Connected'
  if (connectionStore.reconnectFailed) return 'Reconnect Failed'
  return 'Disconnected'
})

const statusTooltip = computed(() => {
  if (connecting.value) return 'Connecting... Click to cancel'
  if (disconnecting.value) return 'Disconnecting...'
  if (connectionStore.reconnecting) {
    return `Auto-reconnecting (attempt ${connectionStore.reconnectAttempt}/${connectionStore.reconnectMaxAttempts})...`
  }
  if (connectionStore.connected) {
    let tooltip = `Connected: ${connectionStore.deviceName || 'Device'}`
    if (connectionStore.hwModel) tooltip += ` (${connectionStore.hwModel})`
    tooltip += '\nClick to disconnect'
    return tooltip
  }
  if (connectionStore.reconnectFailed) {
    return 'Auto-reconnect failed - Click to connect manually'
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

async function handleReconnect() {
  reconnecting.value = true
  try {
    // Step 1: Disconnect
    reconnectStatus.value = 'Disconnecting...'
    await connectionStore.disconnect()

    // Step 2: Wait for BLE to settle
    reconnectStatus.value = 'Waiting for BLE...'
    await new Promise(resolve => setTimeout(resolve, 1500))

    // Step 3: Connect
    reconnectStatus.value = 'Scanning for device...'
    const success = await connectionStore.connect()

    if (success) {
      reconnectStatus.value = 'Connected!'
      await new Promise(resolve => setTimeout(resolve, 500))
    } else {
      reconnectStatus.value = 'Connection failed'
    }
  } catch (error) {
    console.error('Reconnect error:', error)
    reconnectStatus.value = 'Error reconnecting'
  } finally {
    reconnecting.value = false
    reconnectStatus.value = ''
  }
}

async function handleResetBle() {
  resetting.value = true
  try {
    const result = await connectionStore.resetBle()
    if (result.success) {
      console.log('BLE reset successful, device found')
    } else {
      console.warn('BLE reset:', result.message)
    }
  } finally {
    resetting.value = false
  }
}

async function handleScan() {
  await connectionStore.scanBleDevices()
}
</script>
