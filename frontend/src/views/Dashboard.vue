<template>
  <div class="space-y-6">
    <header class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-white">Dashboard</h1>
        <p class="text-gray-400">Monitor your Meshtastic mesh network</p>
      </div>
      <div class="flex items-center gap-2">
        <span
          class="flex items-center gap-2 px-3 py-1 rounded-full text-sm"
          :class="connectionStore.wsConnected ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'"
        >
          <span class="w-2 h-2 rounded-full" :class="connectionStore.wsConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'"></span>
          {{ connectionStore.wsConnected ? 'Live' : 'Offline' }}
        </span>
      </div>
    </header>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <!-- Total Nodes -->
      <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div class="flex items-center gap-3">
          <div class="p-2 bg-blue-900 rounded-lg">
            <svg class="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
            </svg>
          </div>
          <div>
            <p class="text-2xl font-bold text-white">{{ nodesStore.nodeCount }}</p>
            <p class="text-sm text-gray-400">Total Nodes</p>
          </div>
        </div>
      </div>

      <!-- Online Nodes -->
      <div class="bg-gray-800 rounded-lg p-4 border border-gray-700" title="Heard from in the last 2 hours (Meshtastic 'online' definition)">
        <div class="flex items-center gap-3">
          <div class="p-2 bg-green-900 rounded-lg">
            <span class="w-6 h-6 flex items-center justify-center">
              <span class="w-3 h-3 bg-green-400 rounded-full animate-pulse"></span>
            </span>
          </div>
          <div>
            <p class="text-2xl font-bold text-green-400">{{ nodesStore.onlineCount }}</p>
            <p class="text-sm text-gray-400">Online</p>
          </div>
        </div>
      </div>

      <!-- Recently Seen -->
      <div class="bg-gray-800 rounded-lg p-4 border border-gray-700" title="Heard from in the last 24 hours">
        <div class="flex items-center gap-3">
          <div class="p-2 bg-yellow-900 rounded-lg">
            <span class="w-6 h-6 flex items-center justify-center">
              <span class="w-3 h-3 bg-yellow-400 rounded-full"></span>
            </span>
          </div>
          <div>
            <p class="text-2xl font-bold text-yellow-400">{{ nodesStore.recentCount }}</p>
            <p class="text-sm text-gray-400">Recent</p>
          </div>
        </div>
      </div>

      <!-- Offline Nodes -->
      <div class="bg-gray-800 rounded-lg p-4 border border-gray-700" title="Not heard from in over 24 hours">
        <div class="flex items-center gap-3">
          <div class="p-2 bg-gray-700 rounded-lg">
            <span class="w-6 h-6 flex items-center justify-center">
              <span class="w-3 h-3 bg-gray-500 rounded-full"></span>
            </span>
          </div>
          <div>
            <p class="text-2xl font-bold text-gray-400">{{ nodesStore.offlineCount }}</p>
            <p class="text-sm text-gray-400">Offline</p>
          </div>
        </div>
      </div>

      <!-- Unknown Nodes (never heard from) -->
      <div class="bg-gray-800 rounded-lg p-4 border border-gray-700" title="Nodes discovered but never directly heard from">
        <div class="flex items-center gap-3">
          <div class="p-2 bg-gray-700 rounded-lg">
            <span class="w-6 h-6 flex items-center justify-center">
              <span class="w-3 h-3 bg-gray-400 rounded-full border border-dashed border-gray-300"></span>
            </span>
          </div>
          <div>
            <p class="text-2xl font-bold text-gray-500">{{ nodesStore.unknownCount }}</p>
            <p class="text-sm text-gray-400">Unknown</p>
          </div>
        </div>
      </div>

      <!-- Messages -->
      <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div class="flex items-center gap-3">
          <div class="p-2 bg-purple-900 rounded-lg">
            <svg class="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
            </svg>
          </div>
          <div>
            <p class="text-2xl font-bold text-white">{{ messagesStore.messages.length }}</p>
            <p class="text-sm text-gray-400">Messages</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Messages Panel -->
      <div class="lg:col-span-2 h-[500px]">
        <MessagePanel />
      </div>

      <!-- Telemetry Panel -->
      <div>
        <TelemetryChart />
      </div>
    </div>

    <!-- Live Console -->
    <div class="h-[300px]">
      <ConsolePanel />
    </div>

    <!-- Recent Nodes -->
    <div>
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-xl font-semibold text-white">Recent Nodes</h2>
        <router-link to="/nodes" class="text-mesh-400 hover:text-mesh-300 text-sm">
          View All {{ nodesStore.nodeCount }} Nodes →
        </router-link>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <NodeCard
          v-for="node in recentNodes"
          :key="node.id"
          :node="node"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useConnectionStore } from '../stores/connection'
import { useNodesStore } from '../stores/nodes'
import { useMessagesStore } from '../stores/messages'
import MessagePanel from '../components/MessagePanel.vue'
import TelemetryChart from '../components/TelemetryChart.vue'
import NodeCard from '../components/NodeCard.vue'
import ConsolePanel from '../components/ConsolePanel.vue'

const connectionStore = useConnectionStore()
const nodesStore = useNodesStore()
const messagesStore = useMessagesStore()

const recentNodes = computed(() => nodesStore.nodeList.slice(0, 6))

onMounted(async () => {
  // Only fetch from device if already connected
  if (connectionStore.connected) {
    await nodesStore.fetchNodes()
  }
  // Always fetch messages from database (these persist)
  await messagesStore.fetchMessages()
})
</script>
