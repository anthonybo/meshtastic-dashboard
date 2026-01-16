<template>
  <div class="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors">
    <!-- Header: Avatar + Name -->
    <div class="flex items-center gap-3 mb-2">
      <div class="relative flex-shrink-0">
        <div
          class="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold"
          :class="nodeColorClass"
        >
          {{ node.short_name || node.id?.slice(-4) }}
        </div>
        <!-- Status indicator on avatar -->
        <div class="absolute -bottom-0.5 -right-0.5">
          <NodeStatusIndicator :node="node" size="sm" />
        </div>
      </div>
      <div class="min-w-0 flex-1">
        <h3 class="font-medium text-white truncate">{{ node.long_name || 'Unknown' }}</h3>
        <p class="text-xs text-gray-400 truncate">{{ node.id }}</p>
      </div>
    </div>

    <!-- Badges row: Status + Hops + My Device -->
    <div class="flex items-center gap-2 mb-3 flex-wrap">
      <span
        v-if="isMyDevice"
        class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap bg-cyan-900/50 border border-cyan-600 text-cyan-300"
      >
        My Device
      </span>
      <NodeStatusIndicator :node="node" size="sm" show-label />
      <span
        v-if="!isMyDevice && node.hops_away !== null && node.hops_away !== undefined"
        class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap"
        :class="hopsClass"
      >
        {{ node.hops_away === 0 ? 'Direct' : `${node.hops_away} hop${node.hops_away > 1 ? 's' : ''}` }}
      </span>
    </div>

    <div class="mt-4 grid grid-cols-2 gap-4 text-sm">
      <div v-if="node.hw_model" class="flex items-center gap-2 text-gray-400">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/>
        </svg>
        {{ node.hw_model }}
      </div>

      <div v-if="node.battery_level" class="flex items-center gap-2 text-gray-400">
        <svg class="w-4 h-4" :class="batteryColorClass" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 10h-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2v-3h2v-4z"/>
        </svg>
        <span :class="batteryColorClass">{{ node.battery_level }}%</span>
      </div>

      <div v-if="node.snr !== null && node.snr !== undefined" class="flex items-center gap-2 text-gray-400">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
        </svg>
        {{ node.snr?.toFixed(1) }} dB
      </div>

      <div v-if="node.last_heard" class="flex items-center gap-2 text-gray-400">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        {{ formatTime(node.last_heard) }}
      </div>
    </div>

    <div v-if="node.latitude && node.longitude" class="mt-3 pt-3 border-t border-gray-700">
      <div class="flex items-center gap-2 text-xs text-gray-500">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
        </svg>
        {{ node.latitude?.toFixed(4) }}, {{ node.longitude?.toFixed(4) }}
        <span v-if="node.altitude">@ {{ node.altitude }}m</span>
      </div>
    </div>

    <!-- Actions -->
    <div class="mt-3 pt-3 border-t border-gray-700 flex justify-end gap-1">
      <button
        @click="sendDirectMessage"
        class="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
        title="Send message"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
        </svg>
      </button>
      <button
        v-if="node.latitude && node.longitude"
        @click="showOnMap"
        class="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
        title="Show on map"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessagesStore } from '../stores/messages'
import { useConnectionStore } from '../stores/connection'
import { useNodesStore } from '../stores/nodes'
import NodeStatusIndicator from './NodeStatusIndicator.vue'

const router = useRouter()
const messagesStore = useMessagesStore()
const connectionStore = useConnectionStore()
const nodesStore = useNodesStore()

const props = defineProps({
  node: {
    type: Object,
    required: true
  }
})

// Check if this is our connected device
const isMyDevice = computed(() => {
  return nodesStore.isMyNode(props.node, connectionStore.myNodeNum)
})

function sendDirectMessage() {
  // Set the selected conversation to this node's ID
  messagesStore.setSelectedConversation(props.node.id)
  router.push('/messages')
}

function showOnMap() {
  // Pass node coordinates via query params
  router.push({
    path: '/map',
    query: {
      lat: props.node.latitude,
      lng: props.node.longitude,
      node: props.node.id
    }
  })
}

const nodeColors = [
  'bg-blue-600 text-white',
  'bg-purple-600 text-white',
  'bg-pink-600 text-white',
  'bg-indigo-600 text-white',
  'bg-cyan-600 text-white',
  'bg-teal-600 text-white',
  'bg-orange-600 text-white',
  'bg-amber-600 text-white'
]

const nodeColorClass = computed(() => {
  if (!props.node.num) return 'bg-gray-600 text-white'
  return nodeColors[props.node.num % nodeColors.length]
})

const hopsClass = computed(() => {
  const hops = props.node.hops_away
  if (hops === 0) return 'bg-green-900 text-green-300'
  if (hops <= 2) return 'bg-yellow-900 text-yellow-300'
  return 'bg-red-900 text-red-300'
})

const batteryColorClass = computed(() => {
  const level = props.node.battery_level
  if (!level) return 'text-gray-400'
  if (level > 60) return 'text-green-400'
  if (level > 20) return 'text-yellow-400'
  return 'text-red-400'
})

function formatTime(timestamp) {
  if (!timestamp) return 'Unknown'
  const date = new Date(timestamp)
  const now = new Date()
  const diff = (now - date) / 1000

  if (diff < 60) return 'Just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return date.toLocaleDateString()
}
</script>
