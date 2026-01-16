<template>
  <div class="h-[calc(100vh-6rem)]">
    <header class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-white">Network Map</h1>
        <p class="text-gray-400">View node positions on the mesh network</p>
      </div>
      <span class="text-sm text-gray-400">
        {{ nodesStore.nodesWithPosition.length }} nodes with position
      </span>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100%-5rem)]">
      <!-- Map -->
      <div class="lg:col-span-3 h-full">
        <MapViewComponent />
      </div>

      <!-- Node List Sidebar -->
      <div class="h-full overflow-y-auto space-y-4">
        <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h3 class="text-lg font-semibold text-white mb-3">Legend</h3>
          <div class="space-y-2 text-sm">
            <div class="flex items-center gap-2">
              <span class="w-3 h-3 rounded-full bg-green-500"></span>
              <span class="text-gray-300">Direct (0 hops)</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="w-3 h-3 rounded-full bg-yellow-500"></span>
              <span class="text-gray-300">1-2 hops</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="w-3 h-3 rounded-full bg-orange-500"></span>
              <span class="text-gray-300">3-4 hops</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="w-3 h-3 rounded-full bg-red-500"></span>
              <span class="text-gray-300">5+ hops</span>
            </div>
          </div>
        </div>

        <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h3 class="text-lg font-semibold text-white mb-3">Nodes with Position</h3>
          <div class="space-y-2 max-h-96 overflow-y-auto">
            <div
              v-for="node in nodesStore.nodesWithPosition"
              :key="node.id"
              class="p-2 bg-gray-700 rounded-lg text-sm"
            >
              <div class="font-medium text-white">{{ node.long_name || node.id }}</div>
              <div class="text-xs text-gray-400">
                {{ node.latitude?.toFixed(4) }}, {{ node.longitude?.toFixed(4) }}
              </div>
              <div v-if="node.altitude" class="text-xs text-gray-500">
                {{ node.altitude }}m altitude
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useNodesStore } from '../stores/nodes'
import MapViewComponent from '../components/MapView.vue'

const nodesStore = useNodesStore()
</script>
