import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  envDir: '..',
  server: {
    proxy: {
      '/validate': 'http://127.0.0.1:8000',
      '/recommend': 'http://127.0.0.1:8000',
      '/health':    'http://127.0.0.1:8000',
      '/auth':      'http://127.0.0.1:8000',
    },
  },
})
