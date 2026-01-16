<template>
  <div
    class="inline-flex items-center whitespace-nowrap"
    :class="showLabel ? badgeClass : ''"
    :title="statusText"
  >
    <!-- Status dot -->
    <span
      class="rounded-full flex-shrink-0"
      :class="[sizeClass, colorClass, pulseClass]"
    ></span>
    <!-- Optional label -->
    <span v-if="showLabel" class="ml-1.5 text-xs font-medium" :class="labelColorClass">
      {{ statusText }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useNodesStore } from '../stores/nodes'
import { useConnectionStore } from '../stores/connection'

const props = defineProps({
  node: {
    type: Object,
    default: null
  },
  nodeId: {
    type: String,
    default: null
  },
  size: {
    type: String,
    default: 'md', // sm, md, lg
    validator: (v) => ['sm', 'md', 'lg'].includes(v)
  },
  showLabel: {
    type: Boolean,
    default: false
  },
  pulse: {
    type: Boolean,
    default: true // Pulse animation for online nodes
  }
})

const nodesStore = useNodesStore()
const connectionStore = useConnectionStore()

const resolvedNode = computed(() => {
  if (props.node) return props.node
  if (props.nodeId) return nodesStore.getNode(props.nodeId)
  return null
})

// Check if this is our connected device
const isConnectedDevice = computed(() => {
  if (!resolvedNode.value || !connectionStore.myNodeNum) return false
  return nodesStore.isMyNode(resolvedNode.value, connectionStore.myNodeNum)
})

const status = computed(() => nodesStore.getNodeStatus(resolvedNode.value, isConnectedDevice.value))
const statusText = computed(() => {
  if (isConnectedDevice.value) return 'Connected'
  return nodesStore.getStatusText(resolvedNode.value)
})

const sizeClass = computed(() => {
  switch (props.size) {
    case 'sm': return 'w-2 h-2'
    case 'lg': return 'w-4 h-4'
    default: return 'w-3 h-3'
  }
})

const colorClass = computed(() => {
  switch (status.value) {
    case 'online': return 'bg-green-500'
    case 'recent': return 'bg-yellow-500'
    case 'offline': return 'bg-gray-500'
    default: return 'bg-gray-400'
  }
})

const labelColorClass = computed(() => {
  switch (status.value) {
    case 'online': return 'text-green-400'
    case 'recent': return 'text-yellow-400'
    case 'offline': return 'text-gray-400'
    default: return 'text-gray-500'
  }
})

const pulseClass = computed(() => {
  if (props.pulse && status.value === 'online') {
    return 'animate-pulse'
  }
  return ''
})

// Badge styling when showing label
const badgeClass = computed(() => {
  switch (status.value) {
    case 'online': return 'px-2 py-0.5 rounded bg-green-900/50 border border-green-700'
    case 'recent': return 'px-2 py-0.5 rounded bg-yellow-900/50 border border-yellow-700'
    case 'offline': return 'px-2 py-0.5 rounded bg-gray-700/50 border border-gray-600'
    default: return 'px-2 py-0.5 rounded bg-gray-700/50 border border-gray-600'
  }
})
</script>
