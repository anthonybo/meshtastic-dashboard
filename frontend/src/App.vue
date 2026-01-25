<template>
  <div class="min-h-screen bg-gray-900 text-white">
    <!-- Sidebar -->
    <aside
      class="fixed left-0 top-0 h-full bg-gray-800 border-r border-gray-700 transition-all duration-300 flex flex-col"
      :class="sidebarCollapsed ? 'w-16' : 'w-64'"
    >
      <!-- Header -->
      <div class="p-4 flex items-center justify-between">
        <h1
          class="text-xl font-bold text-mesh-400 flex items-center gap-2 overflow-hidden whitespace-nowrap"
          :class="sidebarCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100'"
        >
          <svg class="w-6 h-6 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
          <span class="transition-opacity duration-300">Meshtastic</span>
        </h1>
        <!-- Collapse Toggle -->
        <button
          @click="toggleSidebar"
          class="p-1.5 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
          :class="sidebarCollapsed ? 'mx-auto' : ''"
          :title="sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        >
          <svg class="w-5 h-5 transition-transform duration-300" :class="sidebarCollapsed ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7"/>
          </svg>
        </button>
      </div>

      <!-- Navigation -->
      <nav class="mt-4 flex-1">
        <router-link
          to="/"
          class="nav-link flex items-center gap-3 py-3 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
          :class="sidebarCollapsed ? 'px-0 justify-center' : 'px-4'"
          active-class="bg-gray-700 text-white border-l-4 border-mesh-500"
          :title="sidebarCollapsed ? 'Dashboard' : ''"
        >
          <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="whitespace-nowrap">Dashboard</span>
        </router-link>

        <router-link
          to="/nodes"
          class="nav-link flex items-center gap-3 py-3 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
          :class="sidebarCollapsed ? 'px-0 justify-center' : 'px-4'"
          active-class="bg-gray-700 text-white border-l-4 border-mesh-500"
          :title="sidebarCollapsed ? 'Nodes' : ''"
        >
          <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="whitespace-nowrap">Nodes</span>
        </router-link>

        <router-link
          to="/messages"
          class="nav-link flex items-center gap-3 py-3 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
          :class="sidebarCollapsed ? 'px-0 justify-center' : 'px-4'"
          active-class="bg-gray-700 text-white border-l-4 border-mesh-500"
          :title="sidebarCollapsed ? 'Messages' : ''"
        >
          <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="whitespace-nowrap">Messages</span>
        </router-link>

        <router-link
          to="/map"
          class="nav-link flex items-center gap-3 py-3 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
          :class="sidebarCollapsed ? 'px-0 justify-center' : 'px-4'"
          active-class="bg-gray-700 text-white border-l-4 border-mesh-500"
          :title="sidebarCollapsed ? 'Map' : ''"
        >
          <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="whitespace-nowrap">Map</span>
        </router-link>

        <router-link
          to="/console"
          class="nav-link flex items-center gap-3 py-3 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
          :class="sidebarCollapsed ? 'px-0 justify-center' : 'px-4'"
          active-class="bg-gray-700 text-white border-l-4 border-mesh-500"
          :title="sidebarCollapsed ? 'Console' : ''"
        >
          <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="whitespace-nowrap">Console</span>
        </router-link>
      </nav>

      <!-- Connection Status -->
      <div class="p-4 border-t border-gray-700">
        <ConnectionStatus :collapsed="sidebarCollapsed" />
      </div>
    </aside>

    <!-- Main Content -->
    <main
      class="p-6 transition-all duration-300"
      :class="sidebarCollapsed ? 'ml-16' : 'ml-64'"
    >
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useConnectionStore } from './stores/connection'
import ConnectionStatus from './components/ConnectionStatus.vue'

const connectionStore = useConnectionStore()

// Sidebar state - persisted in localStorage
const sidebarCollapsed = ref(localStorage.getItem('sidebarCollapsed') === 'true')

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('sidebarCollapsed', sidebarCollapsed.value)
}

onMounted(() => {
  connectionStore.initWebSocket()
})

onUnmounted(() => {
  connectionStore.closeWebSocket()
})
</script>
