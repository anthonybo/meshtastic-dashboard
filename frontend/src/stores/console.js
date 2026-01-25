import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useConsoleStore = defineStore('console', () => {
  const logs = ref([])
  const maxLogs = ref(500) // Keep last 500 entries
  const filter = ref('') // Filter by type or content
  const pauseUpdates = ref(false)

  // Log types for filtering
  const logTypes = computed(() => {
    const types = new Set(logs.value.map(log => log.type))
    return Array.from(types).sort()
  })

  // Filtered logs
  const filteredLogs = computed(() => {
    if (!filter.value) return logs.value
    const f = filter.value.toLowerCase()
    return logs.value.filter(log =>
      log.type.toLowerCase().includes(f) ||
      JSON.stringify(log.data).toLowerCase().includes(f)
    )
  })

  // Recent logs for dashboard widget (last 20)
  const recentLogs = computed(() => logs.value.slice(-20))

  // Stats
  const stats = computed(() => {
    const typeCount = {}
    for (const log of logs.value) {
      typeCount[log.type] = (typeCount[log.type] || 0) + 1
    }
    return typeCount
  })

  function addLog(type, data, direction = 'in') {
    if (pauseUpdates.value) return

    const entry = {
      id: Date.now() + Math.random(),
      timestamp: new Date().toISOString(),
      type,
      data,
      direction, // 'in' for received, 'out' for sent
      expanded: false
    }

    logs.value.push(entry)

    // Trim old logs
    if (logs.value.length > maxLogs.value) {
      logs.value = logs.value.slice(-maxLogs.value)
    }
  }

  function clearLogs() {
    logs.value = []
  }

  function togglePause() {
    pauseUpdates.value = !pauseUpdates.value
  }

  function setFilter(value) {
    filter.value = value
  }

  function toggleExpanded(logId) {
    const log = logs.value.find(l => l.id === logId)
    if (log) {
      log.expanded = !log.expanded
    }
  }

  function expandAll() {
    logs.value.forEach(log => log.expanded = true)
  }

  function collapseAll() {
    logs.value.forEach(log => log.expanded = false)
  }

  return {
    logs,
    maxLogs,
    filter,
    pauseUpdates,
    logTypes,
    filteredLogs,
    recentLogs,
    stats,
    addLog,
    clearLogs,
    togglePause,
    setFilter,
    toggleExpanded,
    expandAll,
    collapseAll
  }
})
