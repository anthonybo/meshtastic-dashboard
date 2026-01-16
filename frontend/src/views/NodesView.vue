<template>
  <div class="space-y-6">
    <header class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-white">All Nodes</h1>
        <p class="text-gray-400">{{ nodesStore.nodeCount }} nodes in your mesh network</p>
      </div>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search nodes..."
        class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-mesh-500"
      />
    </header>

    <!-- Stats Summary -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <p class="text-2xl font-bold text-white">{{ nodesStore.nodeCount }}</p>
        <p class="text-sm text-gray-400">Total Nodes</p>
      </div>
      <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <p class="text-2xl font-bold text-green-400">{{ directNodes }}</p>
        <p class="text-sm text-gray-400">Direct (0 hops)</p>
      </div>
      <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <p class="text-2xl font-bold text-purple-400">{{ nodesStore.nodesWithPosition.length }}</p>
        <p class="text-sm text-gray-400">With Position</p>
      </div>
      <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <p class="text-2xl font-bold text-blue-400">{{ onlineNodes }}</p>
        <p class="text-sm text-gray-400">Online (1h)</p>
      </div>
    </div>

    <!-- Nodes Grid -->
    <!-- Only show loading spinner if we have no data yet (initial load) -->
    <div v-if="nodesStore.loading && nodesStore.nodeCount === 0" class="flex justify-center py-12">
      <svg class="w-8 h-8 text-mesh-500 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
      </svg>
    </div>

    <div v-else-if="filteredNodes.length === 0" class="text-center py-12 text-gray-400">
      <svg class="w-12 h-12 mx-auto mb-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
      </svg>
      <p v-if="searchQuery">No nodes match "{{ searchQuery }}"</p>
      <p v-else>No nodes found</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <NodeCard
        v-for="node in filteredNodes"
        :key="node.id"
        :node="node"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useNodesStore } from '../stores/nodes'
import NodeCard from '../components/NodeCard.vue'

const nodesStore = useNodesStore()
const searchQuery = ref('')

const filteredNodes = computed(() => {
  if (!searchQuery.value) {
    return nodesStore.nodeList
  }
  const query = searchQuery.value.toLowerCase()
  return nodesStore.nodeList.filter(node =>
    node.long_name?.toLowerCase().includes(query) ||
    node.short_name?.toLowerCase().includes(query) ||
    node.id?.toLowerCase().includes(query)
  )
})

const directNodes = computed(() => {
  return nodesStore.nodeList.filter(n => n.hops_away === 0).length
})

const onlineNodes = computed(() => {
  const oneHourAgo = Date.now() - (60 * 60 * 1000)
  return nodesStore.nodeList.filter(n => {
    if (!n.last_heard) return false
    return new Date(n.last_heard).getTime() > oneHourAgo
  }).length
})
</script>
