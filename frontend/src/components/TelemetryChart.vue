<template>
  <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
    <h3 class="text-lg font-semibold text-white mb-4">Device Telemetry</h3>
    <div v-if="!connectionStore.connected" class="text-center py-8 text-gray-400">
      <p>Connect to device to view telemetry</p>
    </div>
    <div v-else class="space-y-4">
      <!-- Battery Level -->
      <div>
        <div class="flex justify-between text-sm mb-1">
          <span class="text-gray-400">Battery</span>
          <span class="text-white">{{ batteryLevel }}%</span>
        </div>
        <div class="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-300"
            :class="batteryColorClass"
            :style="{ width: `${batteryLevel}%` }"
          ></div>
        </div>
      </div>

      <!-- Voltage -->
      <div class="flex justify-between text-sm">
        <span class="text-gray-400">Voltage</span>
        <span class="text-white">{{ voltage?.toFixed(2) || '--' }} V</span>
      </div>

      <!-- Channel Utilization (ChUtil) -->
      <div>
        <div class="flex justify-between text-sm mb-1">
          <span class="text-gray-400 flex items-center gap-1 group relative">
            ChUtil
            <svg class="w-3.5 h-3.5 text-gray-500 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <div class="absolute bottom-full left-0 mb-2 w-64 p-3 bg-gray-900 border border-gray-600 rounded-lg shadow-xl text-xs text-gray-300 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
              <p class="font-semibold text-white mb-1">Channel Utilization</p>
              <p class="mb-2">Percentage of airtime being used by ALL nodes on this channel. High values indicate a busy network.</p>
              <div class="space-y-1 text-gray-400">
                <p><span class="text-green-400">&lt;25%</span> Healthy</p>
                <p><span class="text-yellow-400">25-40%</span> Moderate (throttling starts)</p>
                <p><span class="text-orange-400">40-50%</span> High (GPS updates reduced)</p>
                <p><span class="text-red-400">&gt;50%</span> Congested (investigate)</p>
              </div>
            </div>
          </span>
          <span class="text-white">{{ channelUtil?.toFixed(1) || '--' }}%</span>
        </div>
        <div class="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-300"
            :class="channelUtilColorClass"
            :style="{ width: `${Math.min(channelUtil || 0, 100)}%` }"
          ></div>
        </div>
        <p class="text-xs mt-1" :class="channelUtilTextClass">{{ channelUtilStatus }}</p>
      </div>

      <!-- Air Utilization TX (AirUtilTx) -->
      <div>
        <div class="flex justify-between text-sm mb-1">
          <span class="text-gray-400 flex items-center gap-1 group relative">
            AirUtilTx
            <svg class="w-3.5 h-3.5 text-gray-500 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <div class="absolute bottom-full left-0 mb-2 w-64 p-3 bg-gray-900 border border-gray-600 rounded-lg shadow-xl text-xs text-gray-300 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
              <p class="font-semibold text-white mb-1">Air Utilization TX</p>
              <p class="mb-2">Percentage of airtime YOUR device uses for transmitting. Keep this low to be a good mesh neighbor.</p>
              <div class="space-y-1 text-gray-400">
                <p><span class="text-green-400">&lt;5%</span> Excellent</p>
                <p><span class="text-yellow-400">5-8%</span> Acceptable</p>
                <p><span class="text-red-400">&gt;8%</span> Too high (reduce messages/telemetry)</p>
              </div>
            </div>
          </span>
          <span class="text-white">{{ airUtilTx?.toFixed(1) || '--' }}%</span>
        </div>
        <div class="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-300"
            :class="airUtilTxColorClass"
            :style="{ width: `${Math.min((airUtilTx || 0) * 10, 100)}%` }"
          ></div>
        </div>
        <p class="text-xs mt-1" :class="airUtilTxTextClass">{{ airUtilTxStatus }}</p>
      </div>

      <!-- Uptime -->
      <div class="flex justify-between text-sm">
        <span class="text-gray-400">Uptime</span>
        <span class="text-white">{{ formatUptime(uptimeSeconds) }}</span>
      </div>

      <!-- My Node Info -->
      <div class="pt-4 border-t border-gray-700">
        <div class="text-xs text-gray-500 space-y-1">
          <p>Node: {{ connectionStore.myNodeNum ? `!${connectionStore.myNodeNum.toString(16)}` : '--' }}</p>
          <p>Firmware: {{ connectionStore.firmwareVersion || '--' }}</p>
          <p>Hardware: {{ connectionStore.hwModel || '--' }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useConnectionStore } from '../stores/connection'
import { useNodesStore } from '../stores/nodes'

const connectionStore = useConnectionStore()
const nodesStore = useNodesStore()

const myNode = computed(() => {
  if (!connectionStore.myNodeNum) return null
  const nodeId = `!${connectionStore.myNodeNum.toString(16)}`
  return nodesStore.getNode(nodeId)
})

const batteryLevel = computed(() => myNode.value?.battery_level || 0)
const voltage = computed(() => myNode.value?.voltage)
const channelUtil = computed(() => myNode.value?.channel_utilization)
const airUtilTx = computed(() => myNode.value?.air_util_tx)
const uptimeSeconds = computed(() => myNode.value?.uptime_seconds)

const batteryColorClass = computed(() => {
  const level = batteryLevel.value
  if (level > 60) return 'bg-green-500'
  if (level > 20) return 'bg-yellow-500'
  return 'bg-red-500'
})

// ChUtil color based on Meshtastic thresholds
const channelUtilColorClass = computed(() => {
  const util = channelUtil.value || 0
  if (util < 25) return 'bg-green-500'
  if (util < 40) return 'bg-yellow-500'
  if (util < 50) return 'bg-orange-500'
  return 'bg-red-500'
})

const channelUtilTextClass = computed(() => {
  const util = channelUtil.value || 0
  if (util < 25) return 'text-green-400'
  if (util < 40) return 'text-yellow-400'
  if (util < 50) return 'text-orange-400'
  return 'text-red-400'
})

const channelUtilStatus = computed(() => {
  const util = channelUtil.value
  if (util == null) return ''
  if (util < 25) return 'Healthy'
  if (util < 40) return 'Moderate - throttling active'
  if (util < 50) return 'High - reduced GPS updates'
  return 'Congested - investigate'
})

// AirUtilTx should stay under ~8%
const airUtilTxColorClass = computed(() => {
  const util = airUtilTx.value || 0
  if (util < 5) return 'bg-green-500'
  if (util < 8) return 'bg-yellow-500'
  return 'bg-red-500'
})

const airUtilTxTextClass = computed(() => {
  const util = airUtilTx.value || 0
  if (util < 5) return 'text-green-400'
  if (util < 8) return 'text-yellow-400'
  return 'text-red-400'
})

const airUtilTxStatus = computed(() => {
  const util = airUtilTx.value
  if (util == null) return ''
  if (util < 5) return 'Excellent'
  if (util < 8) return 'Acceptable'
  return 'Too high - reduce transmissions'
})

function formatUptime(seconds) {
  if (!seconds) return '--'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}
</script>
