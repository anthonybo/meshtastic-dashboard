<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-white">Nodes ({{ nodesStore.nodeCount }})</h2>
      <button
        @click="refreshNodes"
        :disabled="nodesStore.loading"
        class="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-300 bg-gray-700 rounded-lg hover:bg-gray-600 disabled:opacity-50 transition-colors"
      >
        <svg
          class="w-4 h-4"
          :class="{ 'animate-spin': nodesStore.loading }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
        Refresh
      </button>
    </div>

    <div class="relative">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search nodes..."
        class="w-full px-4 py-2 pl-10 text-sm text-white bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-mesh-500 focus:border-transparent"
      />
      <svg class="absolute left-3 top-2.5 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
      </svg>
    </div>

    <div v-if="nodesStore.loading" class="flex justify-center py-8">
      <svg class="w-8 h-8 text-mesh-500 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>

    <div v-else-if="filteredNodes.length === 0" class="text-center py-8 text-gray-400">
      <svg class="w-12 h-12 mx-auto mb-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
      <p>No nodes found</p>
    </div>

    <div v-else class="grid gap-3">
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
import NodeCard from './NodeCard.vue'

const nodesStore = useNodesStore()
const searchQuery = ref('')

const filteredNodes = computed(() => {
  if (!searchQuery.value) return nodesStore.nodeList
  const query = searchQuery.value.toLowerCase()
  return nodesStore.nodeList.filter(node => {
    return (
      node.long_name?.toLowerCase().includes(query) ||
      node.short_name?.toLowerCase().includes(query) ||
      node.id?.toLowerCase().includes(query) ||
      node.hw_model?.toLowerCase().includes(query)
    )
  })
})

// Nodes are fetched when connecting - no need to fetch on mount

function refreshNodes() {
  nodesStore.fetchNodes()
}
</script>
