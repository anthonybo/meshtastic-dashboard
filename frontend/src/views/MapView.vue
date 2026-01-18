<template>
  <div class="h-[calc(100vh-6rem)]">
    <header class="mb-4 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-white">Network Map</h1>
        <p class="text-gray-400">View node positions on the mesh network</p>
      </div>
      <span class="text-sm text-gray-400">
        {{ nodesStore.nodesWithPosition.length }} nodes with position
      </span>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-4 gap-4 h-[calc(100%-4rem)]">
      <!-- Map -->
      <div class="lg:col-span-3 h-full">
        <MapViewComponent ref="mapComponent" />
      </div>

      <!-- Sidebar -->
      <div class="h-full flex flex-col gap-4 overflow-hidden">
        <!-- Legend - compact -->
        <div class="bg-gray-800 rounded-lg p-3 border border-gray-700 flex-shrink-0">
          <h3 class="text-sm font-semibold text-white mb-2">Legend</h3>
          <div class="grid grid-cols-2 gap-1 text-xs">
            <div class="flex items-center gap-1">
              <span class="w-2 h-2 rounded-full bg-green-500"></span>
              <span class="text-gray-300">Direct</span>
            </div>
            <div class="flex items-center gap-1">
              <span class="w-2 h-2 rounded-full bg-yellow-500"></span>
              <span class="text-gray-300">1-2 hops</span>
            </div>
            <div class="flex items-center gap-1">
              <span class="w-2 h-2 rounded-full bg-orange-500"></span>
              <span class="text-gray-300">3-4 hops</span>
            </div>
            <div class="flex items-center gap-1">
              <span class="w-2 h-2 rounded-full bg-red-500"></span>
              <span class="text-gray-300">5+ hops</span>
            </div>
          </div>
        </div>

        <!-- Nodes with Position - reduced height -->
        <div class="bg-gray-800 rounded-lg p-3 border border-gray-700 flex-shrink-0 max-h-48 flex flex-col">
          <h3 class="text-sm font-semibold text-white mb-2">Nodes with Position</h3>
          <div class="space-y-1 overflow-y-auto flex-1">
            <div
              v-for="node in nodesStore.nodesWithPosition"
              :key="node.id"
              class="p-1.5 bg-gray-700 rounded text-xs"
            >
              <div class="font-medium text-white truncate">{{ node.long_name || node.id }}</div>
              <div class="text-gray-400">
                {{ node.latitude?.toFixed(4) }}, {{ node.longitude?.toFixed(4) }}
              </div>
            </div>
          </div>
        </div>

        <!-- Chat - takes remaining space -->
        <div class="flex-1 min-h-0">
          <MapChat @focus-node="handleFocusNode" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useNodesStore } from '../stores/nodes'
import MapViewComponent from '../components/MapView.vue'
import MapChat from '../components/MapChat.vue'

const nodesStore = useNodesStore()
const mapComponent = ref(null)

function handleFocusNode({ lat, lng, nodeId }) {
  if (mapComponent.value) {
    mapComponent.value.focusOnNode(nodeId, lat, lng)
  }
}
</script>
