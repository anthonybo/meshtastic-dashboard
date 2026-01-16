import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

// Views
import Dashboard from './views/Dashboard.vue'
import Messages from './views/Messages.vue'
import MapView from './views/MapView.vue'
import NodesView from './views/NodesView.vue'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/nodes', component: NodesView },
  { path: '/messages', component: Messages },
  { path: '/map', component: MapView }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const pinia = createPinia()
const app = createApp(App)

app.use(pinia)
app.use(router)
app.mount('#app')
