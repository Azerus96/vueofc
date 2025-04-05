import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { viteSingleFile } from 'vite-plugin-singlefile' // Импортируем

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    viteSingleFile() // Используем плагин для сборки в один файл
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    // Опционально: можно настроить пороги для предупреждений о размере
    chunkSizeWarningLimit: 2000, // Увеличить лимит (в kB), т.к. все будет в одном файле
    assetsInlineLimit: 10000, // Увеличим лимит для встраивания мелких ассетов (если будут)
    // target: 'esnext' // Убедимся, что используется современный JS
  }
})
