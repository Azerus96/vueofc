import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

console.log('[main.ts] Создание приложения Vue...'); // <-- ЛОГ ИНИЦИАЛИЗАЦИИ

const app = createApp(App)

app.use(createPinia())
app.mount('#app')

console.log('[main.ts] Приложение Vue смонтировано.'); // <-- ЛОГ МОНТИРОВАНИЯ
