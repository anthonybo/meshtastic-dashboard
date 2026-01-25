<template>
  <div class="font-mono text-sm">
    <template v-if="isExpandable">
      <div
        class="flex items-start cursor-pointer hover:bg-gray-800 rounded px-1 -mx-1"
        @click="expanded = !expanded"
      >
        <span class="text-gray-500 mr-1 select-none w-4 flex-shrink-0">
          {{ expanded ? '▼' : '▶' }}
        </span>
        <span v-if="keyName" class="text-purple-400">{{ keyName }}</span>
        <span v-if="keyName" class="text-gray-500 mr-1">:</span>
        <span class="text-gray-500">
          {{ isArray ? `Array(${dataLength})` : `Object` }}
          <span v-if="!expanded" class="text-gray-600">
            {{ isArray ? '[...]' : '{...}' }}
          </span>
        </span>
      </div>
      <div v-if="expanded" class="ml-4 border-l border-gray-700 pl-2">
        <div v-for="(value, key) in data" :key="key" class="py-0.5">
          <JsonTree :data="value" :keyName="isArray ? `[${key}]` : key" :depth="depth + 1" />
        </div>
      </div>
    </template>
    <template v-else>
      <div class="flex items-start">
        <span class="w-4 flex-shrink-0"></span>
        <span v-if="keyName" class="text-purple-400">{{ keyName }}</span>
        <span v-if="keyName" class="text-gray-500 mr-1">:</span>
        <span :class="valueClass">{{ displayValue }}</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  data: {
    type: [Object, Array, String, Number, Boolean, null],
    default: null
  },
  keyName: {
    type: String,
    default: ''
  },
  depth: {
    type: Number,
    default: 0
  }
})

// Auto-expand first 2 levels
const expanded = ref(props.depth < 2)

const isArray = computed(() => Array.isArray(props.data))

const isExpandable = computed(() => {
  return props.data !== null && typeof props.data === 'object'
})

const dataLength = computed(() => {
  if (isArray.value) return props.data.length
  return Object.keys(props.data).length
})

const valueClass = computed(() => {
  const val = props.data
  if (val === null || val === undefined) return 'text-gray-500'
  if (typeof val === 'string') return 'text-green-400'
  if (typeof val === 'number') return 'text-blue-400'
  if (typeof val === 'boolean') return 'text-yellow-400'
  return 'text-gray-300'
})

const displayValue = computed(() => {
  const val = props.data
  if (val === null) return 'null'
  if (val === undefined) return 'undefined'
  if (typeof val === 'string') return `"${val}"`
  if (typeof val === 'boolean') return val ? 'true' : 'false'
  return String(val)
})
</script>
