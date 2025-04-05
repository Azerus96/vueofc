/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Определи здесь свои переменные окружения, если они есть
  // readonly VITE_APP_TITLE: string
  // more env variables...
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
